"""Postgres persistence adapter used by cloud mode.

It mirrors the SQLite adapter's repositories and error mapping one to one.
Each unit of work owns one connection and one READ COMMITTED transaction,
opened through the Supabase transaction pooler, so session state is never
relied on: search_path, timezone and statement_timeout are set per
transaction, and prepared statements are disabled.

Where SQLite serializes writers with its database-wide write lock and a
revision counter, this adapter takes row locks (SELECT ... FOR UPDATE) on
the learner, progress and reservation rows it compare-and-sets, and a
transaction-scoped advisory lock for submission reservations. Writers for
different learners therefore never conflict with each other.

The DSN is never logged or included in an error: connection failures raise
PersistenceUnavailable without chaining the driver exception.
"""

from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, LiteralString, Self
from uuid import UUID, uuid4

import psycopg
from psycopg import AsyncConnection, AsyncCursor, errors, sql
from psycopg.rows import DictRow, dict_row
from psycopg.types.json import Jsonb

from yom_awel.domain.contracts import (
    EvaluationResult,
    FeedbackResult,
    SkillsProfile,
    SkillSummary,
    SubmissionOutcome,
    TaskVersion,
)
from yom_awel.domain.entities import (
    Artifact,
    Attempt,
    EvaluationRecord,
    ExternalIdentity,
    FeedbackRecord,
    Learner,
    LearnerProgress,
    OutboxEvent,
    SkillEvidence,
    SubmissionReservation,
    Task,
)
from yom_awel.domain.enums import Channel, ErrorCategory, LearnerStatus, SubmissionStatus
from yom_awel.domain.errors import (
    ArtifactIntegrityFailure,
    ArtifactNotReady,
    FinalizationConflict,
    IdempotencyConflict,
    LearnerScopeViolation,
    NotFound,
    OptimisticConflict,
    PersistenceError,
    ReservationExpired,
    ReservationOwnerConflict,
    SubmissionMismatch,
    TransactionReuse,
    UniqueConstraintViolation,
)
from yom_awel.persistence.postgres_schema import SCHEMA_LOCK_KEY, TABLES, validate_schema_name
from yom_awel.ports.artifacts import ArtifactUploadAuthorization
from yom_awel.ports.clock import Clock
from yom_awel.ports.repositories import MAX_SUBMISSION_LEASE_SECONDS

# Transaction-scoped advisory lock serializing submission reservations across
# every API instance, the cross-process equivalent of SQLite's reservation lock.
SUBMISSION_LOCK_KEY = 0x796F6D6177656C32
DEFAULT_CONNECT_TIMEOUT_SECONDS = 10
DEFAULT_STATEMENT_TIMEOUT = "15s"

Params = tuple[Any, ...]
Row = DictRow
Existence = Literal["learner", "task_version", "evaluation", "feedback"]

_EXISTS: dict[Existence, LiteralString] = {
    "learner": "SELECT 1 FROM learners WHERE learner_id=%s",
    "task_version": "SELECT 1 FROM task_versions WHERE task_version_id=%s",
    "evaluation": "SELECT 1 FROM evaluation_results WHERE evaluation_id=%s",
    "feedback": "SELECT 1 FROM feedback_results WHERE feedback_id=%s",
}
# Lock-timeout, serialization and deadlock failures mean a concurrent writer
# won; callers treat them exactly like a failed compare-and-set.
_CONFLICTS = (errors.LockNotAvailable, errors.SerializationFailure, errors.DeadlockDetected)


class PersistenceUnavailable(PersistenceError):
    """The database could not be reached or failed; carries no driver detail."""

    def __init__(self) -> None:
        super().__init__(
            "unavailable",
            "Persistence is temporarily unavailable",
            category=ErrorCategory.INFRASTRUCTURE,
            retryable=True,
        )


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _optional_utc(value: datetime | None) -> datetime | None:
    return _utc(value) if value is not None else None


class PostgresDatabase:
    """Connection settings and one-time schema bootstrap shared by units of work."""

    def __init__(
        self,
        dsn: str,
        *,
        schema: str = "yom_awel",
        clock: Clock | None = None,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
        statement_timeout: str = DEFAULT_STATEMENT_TIMEOUT,
    ) -> None:
        if connect_timeout < 1:
            raise ValueError("connect_timeout must be positive")
        self._dsn = dsn
        self.schema = validate_schema_name(schema)
        self.clock = clock or SystemClock()
        self.connect_timeout = connect_timeout
        self.statement_timeout = statement_timeout
        self._ready = False
        self._bootstrap_lock = asyncio.Lock()

    def __repr__(self) -> str:
        return f"PostgresDatabase(schema={self.schema!r})"

    async def connect(self) -> AsyncConnection[Row]:
        try:
            return await AsyncConnection.connect(
                self._dsn,
                prepare_threshold=None,
                connect_timeout=self.connect_timeout,
                row_factory=dict_row,
            )
        except psycopg.Error:
            raise PersistenceUnavailable() from None

    async def configure(self, connection: AsyncConnection[Row]) -> None:
        """Apply per-transaction settings; the pooler may hand out any backend."""

        await connection.execute(
            "SELECT set_config('search_path', %s, true), set_config('timezone', 'UTC', true), "
            "set_config('statement_timeout', %s, true)",
            (f"{self.schema}, pg_temp", self.statement_timeout),
        )

    async def ensure_schema(self) -> None:
        if self._ready:
            return
        async with self._bootstrap_lock:
            if self._ready:
                return
            connection = await self.connect()
            try:
                await self._create_schema(connection)
                await connection.commit()
            except psycopg.Error:
                raise PersistenceUnavailable() from None
            finally:
                await connection.close()
            self._ready = True

    async def _create_schema(self, connection: AsyncConnection[Row]) -> None:
        await connection.execute("SELECT pg_advisory_xact_lock(%s)", (SCHEMA_LOCK_KEY,))
        cursor = await connection.execute(
            "SELECT 1 FROM pg_namespace WHERE nspname=%s", (self.schema,)
        )
        # CREATE SCHEMA IF NOT EXISTS still demands CREATE on the database, which
        # the least-privilege role lacks once an administrator created the schema.
        if await cursor.fetchone() is None:
            await connection.execute(
                sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(self.schema))
            )
        await self.configure(connection)
        for statement in TABLES:
            await connection.execute(statement)


class _Repo:
    def __init__(self, uow: PostgresUnitOfWork) -> None:
        self._uow = uow

    @property
    def db(self) -> AsyncConnection[Row]:
        connection = self._uow._connection
        if connection is None:
            raise RuntimeError("repository used outside unit of work")
        return connection

    async def _execute(self, query: LiteralString, parameters: Params = ()) -> AsyncCursor[Row]:
        return await self._uow._execute(query, parameters)

    async def _one(self, query: LiteralString, parameters: Params = ()) -> Row | None:
        return await (await self._execute(query, parameters)).fetchone()

    async def _all(self, query: LiteralString, parameters: Params = ()) -> list[Row]:
        return await (await self._execute(query, parameters)).fetchall()

    async def _insert(self, query: LiteralString, parameters: Params) -> bool:
        """Run one write inside a savepoint; False when a constraint rejected it.

        The savepoint keeps the transaction usable after a violation, matching
        SQLite, where a failed statement does not abort the transaction.
        """

        try:
            async with self.db.transaction():
                await self._execute(query, parameters)
        except errors.IntegrityError:
            return False
        return True

    async def _exists(self, kind: Existence, value: UUID) -> bool:
        return await self._one(_EXISTS[kind], (value,)) is not None

    async def _lock_learner(self, learner_id: UUID) -> bool:
        """Lock the learner row, ordering all per-learner writers; False if absent."""

        row = await self._one(
            "SELECT 1 FROM learners WHERE learner_id=%s FOR UPDATE", (learner_id,)
        )
        return row is not None


class _Learners(_Repo):
    async def get(self, learner_id: UUID) -> Learner | None:
        row = await self._one("SELECT * FROM learners WHERE learner_id=%s", (learner_id,))
        return _learner(row) if row else None

    async def get_by_external_identity(
        self, provider: str, provider_subject: str
    ) -> Learner | None:
        row = await self._one(
            "SELECT l.* FROM learners l JOIN external_identities i ON i.learner_id=l.learner_id "
            "WHERE i.provider=%s AND i.provider_subject=%s",
            (provider, provider_subject),
        )
        return _learner(row) if row else None

    async def add(self, learner: Learner) -> None:
        inserted = await self._insert(
            "INSERT INTO learners (learner_id, display_name, preferred_language, status, "
            "created_at, updated_at, state_machine_version) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                learner.learner_id,
                learner.display_name,
                learner.preferred_language.value,
                learner.status.value,
                _utc(learner.created_at),
                _utc(learner.updated_at),
                learner.state_machine_version,
            ),
        )
        if not inserted:
            raise UniqueConstraintViolation("learners.id")

    async def add_external_identity(
        self, learner_id: UUID, provider: str, provider_subject: str
    ) -> ExternalIdentity:
        if not await self._exists("learner", learner_id):
            raise LearnerScopeViolation("external_identity.learner_id")
        identity = ExternalIdentity(
            identity_id=uuid4(),
            learner_id=learner_id,
            provider=provider,
            provider_subject=provider_subject,
        )
        inserted = await self._insert(
            "INSERT INTO external_identities (identity_id, learner_id, provider, provider_subject) "
            "VALUES (%s, %s, %s, %s)",
            (identity.identity_id, learner_id, provider, provider_subject),
        )
        if not inserted:
            raise UniqueConstraintViolation("external_identities.provider_subject")
        return identity

    async def get_progress(self, learner_id: UUID) -> LearnerProgress | None:
        row = await self._one("SELECT * FROM learner_progress WHERE learner_id=%s", (learner_id,))
        return _progress(row) if row else None

    async def save_progress(self, progress: LearnerProgress, expected_version: int) -> None:
        learner_id = progress.learner_id
        if not await self._lock_learner(learner_id):
            raise LearnerScopeViolation("learner_progress.learner_id")
        current = await self._one(
            "SELECT version FROM learner_progress WHERE learner_id=%s FOR UPDATE", (learner_id,)
        )
        updated_at = _utc(progress.updated_at)
        if current is None:
            if expected_version != 0 or progress.version != 1:
                raise OptimisticConflict("learner_progress")
            inserted = await self._insert(
                "INSERT INTO learner_progress (learner_id, current_status, current_task_id, "
                "version, updated_at, reset_at) VALUES (%s, %s, %s, %s, %s, %s)",
                (
                    learner_id,
                    progress.current_status.value,
                    progress.current_task_id,
                    progress.version,
                    updated_at,
                    _optional_utc(progress.reset_at),
                ),
            )
            if not inserted:
                raise OptimisticConflict("learner_progress")
        else:
            if int(current["version"]) != expected_version or (
                progress.version != expected_version + 1
            ):
                raise OptimisticConflict("learner_progress")
            updated = await self._execute(
                "UPDATE learner_progress SET current_status=%s, current_task_id=%s, version=%s, "
                "updated_at=%s, reset_at=%s WHERE learner_id=%s AND version=%s",
                (
                    progress.current_status.value,
                    progress.current_task_id,
                    progress.version,
                    updated_at,
                    _optional_utc(progress.reset_at),
                    learner_id,
                    expected_version,
                ),
            )
            if updated.rowcount != 1:
                raise OptimisticConflict("learner_progress")
        await self._execute(
            "UPDATE learners SET status=%s, updated_at=%s WHERE learner_id=%s",
            (progress.current_status.value, updated_at, learner_id),
        )


class _Tasks(_Repo):
    async def get(self, task_version_id: UUID) -> TaskVersion | None:
        row = await self._one(
            "SELECT * FROM task_versions WHERE task_version_id=%s", (task_version_id,)
        )
        return _task(row) if row else None

    async def get_task(self, task_id: str) -> Task | None:
        row = await self._one(
            "SELECT task_id FROM task_versions WHERE task_id=%s LIMIT 1", (task_id,)
        )
        return Task(task_id=row["task_id"], title=row["task_id"]) if row else None

    async def get_current_published_version(self, task_id: str) -> TaskVersion | None:
        # Like SQLite, only approved task versions are stored. Select numeric
        # publication order in Python rather than lexical SQL order.
        rows = await self._all("SELECT * FROM task_versions WHERE task_id=%s", (task_id,))
        if not rows:
            return None

        def order(row: Row) -> tuple[int, int, str, str]:
            version = str(row["version"])
            if version.isdecimal():
                return (1, int(version), "", str(row["task_version_id"]))
            return (0, 0, version, str(row["task_version_id"]))

        return _task(max(rows, key=order))

    async def add(self, task_version: TaskVersion) -> None:
        inserted = await self._insert(
            "INSERT INTO task_versions (task_version_id, task_id, version, instructions_ar, "
            "instructions_en, artifact_schema, evaluator_id, evaluator_version, pass_threshold, "
            "skill_mappings, content_hash) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                task_version.task_version_id,
                task_version.task_id,
                task_version.version,
                task_version.instructions_ar,
                task_version.instructions_en,
                Jsonb(task_version.artifact_schema),
                task_version.evaluator_id,
                task_version.evaluator_version,
                task_version.pass_threshold,
                Jsonb([item.model_dump(mode="json") for item in task_version.skill_mappings]),
                task_version.content_hash,
            ),
        )
        if not inserted:
            raise UniqueConstraintViolation("task_versions.task_id_version")


class _Artifacts(_Repo):
    """Artifact metadata and bytes (bytea, at most 5 MiB) in one table.

    Integrity is checked in the database with sha256(), so metadata lookups
    never transfer the bytes; only download() returns them.
    """

    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None:
        row = await self._one(
            "SELECT artifact_id, learner_id, filename, size_bytes, sha256 FROM artifacts "
            "WHERE artifact_id=%s AND learner_id=%s AND octet_length(content)=size_bytes "
            "AND encode(sha256(content), 'hex')=sha256",
            (artifact_id, learner_id),
        )
        return _artifact(row) if row else None

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None:
        row = await self._one(
            "SELECT content, size_bytes, sha256 FROM artifacts "
            "WHERE artifact_id=%s AND learner_id=%s",
            (artifact_id, learner_id),
        )
        if row is None:
            return None
        content = bytes(row["content"])
        if (
            len(content) != int(row["size_bytes"])
            or hashlib.sha256(content).hexdigest() != row["sha256"]
        ):
            return None
        return content

    async def authorize_upload(
        self, artifact: Artifact, *, expires_in_seconds: int = 300
    ) -> ArtifactUploadAuthorization:
        if expires_in_seconds < 1:
            raise ValueError("expires_in_seconds must be positive")
        existing = await self._one(
            "SELECT learner_id, filename, size_bytes, sha256 FROM artifacts "
            "WHERE artifact_id=%s FOR UPDATE",
            (artifact.artifact_id,),
        )
        if existing is not None:
            if not _same_metadata(existing, artifact):
                raise UniqueConstraintViolation("artifacts.id")
        else:
            if not await self._exists("learner", artifact.learner_id):
                raise LearnerScopeViolation("artifact.learner_id")
            if not await self._insert_row(artifact, b""):
                raise UniqueConstraintViolation("artifacts.id")
        return ArtifactUploadAuthorization(
            artifact=artifact,
            upload_url=f"/artifacts/{artifact.learner_id}/{artifact.artifact_id}",
            upload_token=None,
            expires_in_seconds=expires_in_seconds,
        )

    async def complete_upload(self, artifact_id: UUID, learner_id: UUID) -> Artifact:
        row = await self._one(
            "SELECT artifact_id, learner_id, filename, size_bytes, sha256, "
            "octet_length(content) AS stored_bytes, "
            "encode(sha256(content), 'hex') AS stored_sha256 "
            "FROM artifacts WHERE artifact_id=%s AND learner_id=%s",
            (artifact_id, learner_id),
        )
        if row is None:
            raise ArtifactNotReady()
        if int(row["stored_bytes"]) != int(row["size_bytes"]):
            raise ArtifactNotReady()
        if row["stored_sha256"] != row["sha256"]:
            raise ArtifactIntegrityFailure()
        return _artifact(row)

    async def put(self, artifact: Artifact, content: bytes) -> Artifact:
        if len(content) != artifact.size_bytes:
            raise ValueError("content size does not match artifact metadata")
        if hashlib.sha256(content).hexdigest() != artifact.sha256:
            raise ValueError("content sha256 does not match artifact metadata")
        existing = await self._one(
            "SELECT learner_id, filename, size_bytes, sha256, "
            "octet_length(content) AS stored_bytes FROM artifacts "
            "WHERE artifact_id=%s FOR UPDATE",
            (artifact.artifact_id,),
        )
        if existing is not None:
            # Only an authorized, still empty placeholder may receive bytes.
            if not _same_metadata(existing, artifact) or int(existing["stored_bytes"]) == int(
                existing["size_bytes"]
            ):
                raise UniqueConstraintViolation("artifacts.id")
            await self._execute(
                "UPDATE artifacts SET content=%s WHERE artifact_id=%s",
                (content, artifact.artifact_id),
            )
            return artifact
        if not await self._insert_row(artifact, content):
            if not await self._exists("learner", artifact.learner_id):
                raise LearnerScopeViolation("artifact.learner_id")
            raise UniqueConstraintViolation("artifacts.id")
        return artifact

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None:
        row = await self._one(
            "SELECT learner_id FROM artifacts WHERE artifact_id=%s FOR UPDATE", (artifact_id,)
        )
        if row is None:
            return
        if row["learner_id"] != learner_id:
            raise LearnerScopeViolation("artifact.learner_id")
        await self._execute("DELETE FROM artifacts WHERE artifact_id=%s", (artifact_id,))

    async def _insert_row(self, artifact: Artifact, content: bytes) -> bool:
        return await self._insert(
            "INSERT INTO artifacts (artifact_id, learner_id, filename, size_bytes, sha256, "
            "content) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                artifact.artifact_id,
                artifact.learner_id,
                artifact.filename,
                artifact.size_bytes,
                artifact.sha256,
                content,
            ),
        )


class _Submissions(_Repo):
    async def reserve(
        self,
        learner_id: UUID,
        task_version_id: UUID,
        artifact_id: UUID,
        channel: Channel,
        key: str,
        request_fingerprint: str,
        lease_seconds: int,
        lease_owner: str,
    ) -> SubmissionReservation:
        await self._uow.acquire_submission_lock()
        if (
            lease_seconds <= 0
            or lease_seconds > MAX_SUBMISSION_LEASE_SECONDS
            or not lease_owner.strip()
        ):
            raise ValueError(
                "lease_seconds must be between 1 and 3600 and lease_owner must be non-empty"
            )
        if not await self._exists("learner", learner_id):
            raise LearnerScopeViolation("submission.learner_id")
        now = _utc(self._uow._database.clock.now())
        existing = await self._one(
            "SELECT * FROM submissions WHERE learner_id=%s AND idempotency_key=%s FOR UPDATE",
            (learner_id, key),
        )
        if existing is not None:
            result = _reservation(existing)
            if result.request_fingerprint != request_fingerprint:
                raise IdempotencyConflict(key)
            if result.status == SubmissionStatus.COMPLETED:
                return result
            if result.lease_expires_at > now:
                return result
            reclaimed = result.model_copy(
                update={
                    "lease_owner": lease_owner,
                    "lease_expires_at": now + timedelta(seconds=lease_seconds),
                    "version": result.version + 1,
                }
            )
            updated = await self._execute(
                "UPDATE submissions SET lease_owner=%s, lease_expires_at=%s, version=%s "
                "WHERE reservation_id=%s AND version=%s",
                (
                    lease_owner,
                    reclaimed.lease_expires_at,
                    reclaimed.version,
                    result.reservation_id,
                    result.version,
                ),
            )
            if updated.rowcount != 1:
                raise OptimisticConflict("submission_reservation")
            return reclaimed
        task = await self._uow.tasks.get(task_version_id)
        if task is None:
            raise NotFound("task_version")
        progress = await self._uow.learners.get_progress(learner_id)
        if progress is not None:
            if progress.current_task_id is not None and progress.current_task_id != task.task_id:
                raise SubmissionMismatch("Submission task is not the learner's current task")
            if progress.current_status not in (
                LearnerStatus.IN_TASK,
                LearnerStatus.PROCESSING,
                LearnerStatus.NEEDS_RETRY,
            ):
                raise SubmissionMismatch("Learner is not eligible for task submission")
        artifact = await self._one(
            "SELECT learner_id FROM artifacts WHERE artifact_id=%s", (artifact_id,)
        )
        if artifact is None:
            raise NotFound("artifact")
        if artifact["learner_id"] != learner_id:
            raise LearnerScopeViolation("submission.artifact_id")
        result = SubmissionReservation(
            reservation_id=uuid4(),
            submission_id=uuid4(),
            learner_id=learner_id,
            task_version_id=task_version_id,
            artifact_id=artifact_id,
            channel=channel,
            idempotency_key=key,
            request_fingerprint=request_fingerprint,
            status=SubmissionStatus.RECEIVED,
            version=1,
            lease_expires_at=now + timedelta(seconds=lease_seconds),
            created_at=now,
            lease_owner=lease_owner,
        )
        inserted = await self._insert(
            "INSERT INTO submissions (reservation_id, submission_id, learner_id, task_version_id, "
            "artifact_id, channel, idempotency_key, request_fingerprint, status, created_at, "
            "version, lease_expires_at, lease_owner, outcome) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)",
            (
                result.reservation_id,
                result.submission_id,
                learner_id,
                task_version_id,
                artifact_id,
                channel.value,
                key,
                request_fingerprint,
                result.status.value,
                result.created_at,
                result.version,
                result.lease_expires_at,
                lease_owner,
            ),
        )
        if inserted:
            return result
        # Unreachable while every writer holds the advisory lock, but a writer
        # that bypassed it may have won the unique-key race: replay its row.
        raced_row = await self._one(
            "SELECT * FROM submissions WHERE learner_id=%s AND idempotency_key=%s",
            (learner_id, key),
        )
        if raced_row is None:
            raise OptimisticConflict("submission_reservation")
        raced = _reservation(raced_row)
        if raced.request_fingerprint != request_fingerprint:
            raise IdempotencyConflict(key)
        return raced

    async def get_reservation(self, learner_id: UUID, key: str) -> SubmissionReservation | None:
        row = await self._one(
            "SELECT * FROM submissions WHERE learner_id=%s AND idempotency_key=%s",
            (learner_id, key),
        )
        return _reservation(row) if row else None

    async def expire(
        self,
        learner_id: UUID,
        key: str,
        expected_version: int | None = None,
        lease_owner: str | None = None,
    ) -> None:
        row = await self._one(
            "SELECT * FROM submissions WHERE learner_id=%s AND idempotency_key=%s FOR UPDATE",
            (learner_id, key),
        )
        if row is None:
            return
        result = _reservation(row)
        if expected_version is not None and result.version != expected_version:
            raise OptimisticConflict("submission_reservation")
        if lease_owner is not None and result.lease_owner != lease_owner:
            raise ReservationOwnerConflict()
        if result.status == SubmissionStatus.COMPLETED:
            return
        await self._execute(
            "UPDATE submissions SET lease_expires_at=%s, version=%s "
            "WHERE reservation_id=%s AND version=%s",
            (
                _utc(self._uow._database.clock.now()),
                result.version + 1,
                result.reservation_id,
                result.version,
            ),
        )

    async def finalize(
        self,
        reservation_id: UUID,
        expected_version: int,
        lease_owner: str,
        outcome: SubmissionOutcome,
    ) -> None:
        row = await self._one(
            "SELECT * FROM submissions WHERE reservation_id=%s FOR UPDATE", (reservation_id,)
        )
        if row is None:
            raise NotFound("submission_reservation")
        current = _reservation(row)
        if current.version != expected_version:
            raise OptimisticConflict("submission_reservation")
        if current.status == SubmissionStatus.COMPLETED:
            raise FinalizationConflict("Reservation is already finalized")
        if current.lease_owner != lease_owner:
            raise ReservationOwnerConflict()
        if current.lease_expires_at <= _utc(self._uow._database.clock.now()):
            raise ReservationExpired()
        if outcome.submission_id != current.submission_id:
            raise SubmissionMismatch()
        if outcome.evaluation.task_version_id != current.task_version_id:
            raise SubmissionMismatch("Outcome task version does not match reservation")
        updated = await self._execute(
            "UPDATE submissions SET status=%s, outcome=%s, version=%s WHERE reservation_id=%s "
            "AND version=%s AND lease_owner=%s AND status<>%s",
            (
                SubmissionStatus.COMPLETED.value,
                Jsonb(outcome.model_dump(mode="json")),
                expected_version + 1,
                reservation_id,
                expected_version,
                lease_owner,
                SubmissionStatus.COMPLETED.value,
            ),
        )
        if updated.rowcount != 1:
            raise OptimisticConflict("submission_reservation")


class _Attempts(_Repo):
    async def add(self, attempt: Attempt) -> None:
        # The learner row lock orders concurrent finalizers, so the attempt
        # count read below cannot change before this transaction ends.
        if not await self._lock_learner(attempt.learner_id):
            raise LearnerScopeViolation("attempt.learner_id")
        if not await self._exists("task_version", attempt.task_version_id):
            raise NotFound("task_version")
        reservation = await self._one(
            "SELECT learner_id, task_version_id FROM submissions WHERE submission_id=%s",
            (attempt.submission_id,),
        )
        if reservation is None:
            raise NotFound("submission")
        if (
            reservation["learner_id"] != attempt.learner_id
            or reservation["task_version_id"] != attempt.task_version_id
        ):
            raise LearnerScopeViolation("attempt.submission_id")
        if await self._one("SELECT 1 FROM attempts WHERE attempt_id=%s", (attempt.attempt_id,)):
            raise UniqueConstraintViolation("attempts.id")
        existing = await self.list_for_task(attempt.learner_id, attempt.task_version_id)
        if any(item.attempt_number == attempt.attempt_number for item in existing):
            raise UniqueConstraintViolation("attempts.learner_task_attempt_number")
        if attempt.attempt_number != len(existing) + 1:
            raise OptimisticConflict("attempt ordering")
        if not await self._exists("evaluation", attempt.evaluation_id):
            raise NotFound("evaluation")
        if not await self._exists("feedback", attempt.feedback_id):
            raise NotFound("feedback")
        inserted = await self._insert(
            "INSERT INTO attempts (attempt_id, learner_id, submission_id, task_version_id, "
            "attempt_number, evaluation_id, feedback_id, evaluator_id, evaluator_version, "
            "prompt_version, started_at, completed_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                attempt.attempt_id,
                attempt.learner_id,
                attempt.submission_id,
                attempt.task_version_id,
                attempt.attempt_number,
                attempt.evaluation_id,
                attempt.feedback_id,
                attempt.evaluator_id,
                attempt.evaluator_version,
                attempt.prompt_version,
                _utc(attempt.started_at),
                _optional_utc(attempt.completed_at),
            ),
        )
        if not inserted:
            raise UniqueConstraintViolation("attempts.id")

    async def get(self, attempt_id: UUID) -> Attempt | None:
        row = await self._one("SELECT * FROM attempts WHERE attempt_id=%s", (attempt_id,))
        return _attempt(row) if row else None

    async def list_for_task(self, learner_id: UUID, task_version_id: UUID) -> list[Attempt]:
        rows = await self._all(
            "SELECT * FROM attempts WHERE learner_id=%s AND task_version_id=%s "
            "ORDER BY attempt_number, attempt_id",
            (learner_id, task_version_id),
        )
        return [_attempt(row) for row in rows]


class _Skills(_Repo):
    async def add_evidence(self, evidence: SkillEvidence) -> None:
        if not await self._exists("learner", evidence.learner_id):
            raise LearnerScopeViolation("skill_evidence.learner_id")
        if not await self._exists("task_version", evidence.task_version_id):
            raise NotFound("task_version")
        attempt = await self._one(
            "SELECT learner_id, task_version_id FROM attempts WHERE attempt_id=%s",
            (evidence.attempt_id,),
        )
        if attempt is None:
            raise NotFound("attempt")
        if (
            attempt["learner_id"] != evidence.learner_id
            or attempt["task_version_id"] != evidence.task_version_id
        ):
            raise LearnerScopeViolation("skill_evidence.attempt_id")
        inserted = await self._insert(
            "INSERT INTO skill_evidence (evidence_id, learner_id, attempt_id, task_version_id, "
            "skill_id, check_id, awarded_points, available_points, recorded_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                evidence.evidence_id,
                evidence.learner_id,
                evidence.attempt_id,
                evidence.task_version_id,
                evidence.skill_id,
                evidence.check_id,
                evidence.awarded_points,
                evidence.available_points,
                _utc(evidence.recorded_at),
            ),
        )
        if not inserted:
            raise UniqueConstraintViolation("skill_evidence.attempt_skill_check")

    async def list_evidence(self, learner_id: UUID) -> list[SkillEvidence]:
        rows = await self._all(
            "SELECT * FROM skill_evidence WHERE learner_id=%s "
            "ORDER BY skill_id, recorded_at, evidence_id",
            (learner_id,),
        )
        return [_evidence(row) for row in rows]

    async def get_profile(self, learner_id: UUID) -> SkillsProfile:
        totals: dict[str, int] = {}
        for item in await self.list_evidence(learner_id):
            totals[item.skill_id] = min(100, totals.get(item.skill_id, 0) + item.awarded_points)
        return SkillsProfile(
            learner_id=learner_id,
            skills=[SkillSummary(skill_id=k, score=v) for k, v in sorted(totals.items())],
        )


class _Evaluations(_Repo):
    async def get(self, evaluation_id: UUID) -> EvaluationRecord | None:
        row = await self._one(
            "SELECT * FROM evaluation_results WHERE evaluation_id=%s", (evaluation_id,)
        )
        return _evaluation(row) if row else None

    async def add(self, record: EvaluationRecord) -> None:
        inserted = await self._insert(
            "INSERT INTO evaluation_results (evaluation_id, result, recorded_at) "
            "VALUES (%s, %s, %s)",
            (
                record.evaluation_id,
                Jsonb(record.result.model_dump(mode="json")),
                _utc(record.recorded_at),
            ),
        )
        if not inserted:
            raise UniqueConstraintViolation("evaluation_results.id")


class _Feedback(_Repo):
    async def get(self, feedback_id: UUID) -> FeedbackRecord | None:
        row = await self._one("SELECT * FROM feedback_results WHERE feedback_id=%s", (feedback_id,))
        return _feedback(row) if row else None

    async def add(self, record: FeedbackRecord) -> None:
        inserted = await self._insert(
            "INSERT INTO feedback_results (feedback_id, result, recorded_at) VALUES (%s, %s, %s)",
            (
                record.feedback_id,
                Jsonb(record.result.model_dump(mode="json")),
                _utc(record.recorded_at),
            ),
        )
        if not inserted:
            raise UniqueConstraintViolation("feedback_results.id")


class _Outbox(_Repo):
    async def add(self, event: OutboxEvent) -> None:
        inserted = await self._insert(
            "INSERT INTO outbox_events (event_id, event_type, aggregate_id, payload, created_at, "
            "published_at) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                event.event_id,
                event.event_type,
                event.aggregate_id,
                Jsonb(event.payload),
                _utc(event.created_at),
                _optional_utc(event.published_at),
            ),
        )
        if not inserted:
            raise UniqueConstraintViolation("outbox_events.id")

    async def pending(self, limit: int = 100) -> list[OutboxEvent]:
        if limit < 1:
            raise ValueError("limit must be positive")
        rows = await self._all(
            "SELECT * FROM outbox_events WHERE published_at IS NULL "
            "ORDER BY created_at, event_id LIMIT %s",
            (limit,),
        )
        return [_outbox(row) for row in rows]

    async def mark_published(self, event_id: UUID) -> None:
        updated = await self._execute(
            "UPDATE outbox_events SET published_at=%s WHERE event_id=%s",
            (_utc(self._uow._database.clock.now()), event_id),
        )
        if updated.rowcount != 1:
            raise NotFound("outbox_event")


class PostgresUnitOfWork:
    def __init__(self, database: PostgresDatabase) -> None:
        self._database = database
        self._connection: AsyncConnection[Row] | None = None
        self._active = False
        self._submission_lock_acquired = False
        self.learners = _Learners(self)
        self.tasks = _Tasks(self)
        self.submissions = _Submissions(self)
        self.attempts = _Attempts(self)
        self.skills = _Skills(self)
        self.outbox = _Outbox(self)
        self.evaluations = _Evaluations(self)
        self.feedback = _Feedback(self)
        self.artifacts = _Artifacts(self)

    async def __aenter__(self) -> Self:
        if self._active:
            raise TransactionReuse()
        await self._database.ensure_schema()
        connection = await self._database.connect()
        try:
            await self._database.configure(connection)
        except psycopg.Error:
            await connection.close()
            raise PersistenceUnavailable() from None
        self._connection = connection
        self._active = True
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.rollback()

    async def commit(self) -> None:
        if not self._active or self._connection is None:
            raise RuntimeError("unit of work is not active")
        try:
            await self._connection.commit()
        except _CONFLICTS:
            raise OptimisticConflict("unit_of_work") from None
        except psycopg.Error:
            raise PersistenceUnavailable() from None
        finally:
            await self._close()

    async def rollback(self) -> None:
        if self._connection is not None:
            try:
                if self._active:
                    await self._connection.rollback()
            except psycopg.OperationalError:
                # The connection is gone; the server already discarded the transaction.
                pass
            finally:
                await self._close()
        self._active = False

    async def acquire_submission_lock(self) -> None:
        """Serialize reservations across instances until this transaction ends.

        READ COMMITTED takes a fresh snapshot per statement, so unlike SQLite no
        transaction restart is needed to observe a concurrently committed winner.
        """

        if not self._active or self._connection is None:
            raise RuntimeError("unit of work is not active")
        if self._submission_lock_acquired:
            return
        await self._execute("SELECT pg_advisory_xact_lock(%s)", (SUBMISSION_LOCK_KEY,))
        self._submission_lock_acquired = True

    async def _execute(self, query: LiteralString, parameters: Params = ()) -> AsyncCursor[Row]:
        if self._connection is None:
            raise RuntimeError("repository used outside unit of work")
        try:
            return await self._connection.execute(query, parameters)
        except _CONFLICTS:
            raise OptimisticConflict("unit_of_work") from None
        except psycopg.OperationalError:
            raise PersistenceUnavailable() from None

    async def _close(self) -> None:
        connection, self._connection = self._connection, None
        self._active = False
        self._submission_lock_acquired = False
        if connection is not None:
            await connection.close()


class PostgresUnitOfWorkFactory:
    """Cloud-mode unit-of-work factory; one connection and transaction per unit."""

    def __init__(
        self,
        dsn: str,
        *,
        schema: str = "yom_awel",
        clock: Clock | None = None,
        connect_timeout: int = DEFAULT_CONNECT_TIMEOUT_SECONDS,
    ) -> None:
        self.database = PostgresDatabase(
            dsn, schema=schema, clock=clock, connect_timeout=connect_timeout
        )

    def __repr__(self) -> str:
        return f"PostgresUnitOfWorkFactory(schema={self.database.schema!r})"

    def __call__(self) -> PostgresUnitOfWork:
        return PostgresUnitOfWork(self.database)


def _same_metadata(row: Row, artifact: Artifact) -> bool:
    return (
        row["learner_id"] == artifact.learner_id
        and row["filename"] == artifact.filename
        and int(row["size_bytes"]) == artifact.size_bytes
        and row["sha256"] == artifact.sha256
    )


def _learner(row: Row) -> Learner:
    return Learner(
        learner_id=row["learner_id"],
        display_name=row["display_name"],
        preferred_language=row["preferred_language"],
        status=row["status"],
        created_at=_utc(row["created_at"]),
        updated_at=_utc(row["updated_at"]),
        state_machine_version=row["state_machine_version"],
    )


def _task(row: Row) -> TaskVersion:
    return TaskVersion.model_validate(
        {
            "task_version_id": row["task_version_id"],
            "task_id": row["task_id"],
            "version": row["version"],
            "instructions_ar": row["instructions_ar"],
            "instructions_en": row["instructions_en"],
            "artifact_schema": row["artifact_schema"],
            "evaluator_id": row["evaluator_id"],
            "evaluator_version": row["evaluator_version"],
            "pass_threshold": row["pass_threshold"],
            "skill_mappings": row["skill_mappings"],
            "content_hash": row["content_hash"],
        }
    )


def _artifact(row: Row) -> Artifact:
    return Artifact(
        artifact_id=row["artifact_id"],
        learner_id=row["learner_id"],
        filename=row["filename"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
    )


def _progress(row: Row) -> LearnerProgress:
    return LearnerProgress(
        learner_id=row["learner_id"],
        current_status=row["current_status"],
        current_task_id=row["current_task_id"] or None,
        version=row["version"],
        updated_at=_utc(row["updated_at"]),
        reset_at=_optional_utc(row["reset_at"]),
    )


def _reservation(row: Row) -> SubmissionReservation:
    outcome = row["outcome"]
    return SubmissionReservation(
        reservation_id=row["reservation_id"],
        submission_id=row["submission_id"],
        learner_id=row["learner_id"],
        task_version_id=row["task_version_id"],
        artifact_id=row["artifact_id"],
        channel=row["channel"],
        idempotency_key=row["idempotency_key"],
        request_fingerprint=row["request_fingerprint"],
        status=row["status"],
        created_at=_utc(row["created_at"]),
        version=row["version"],
        lease_expires_at=_utc(row["lease_expires_at"]),
        lease_owner=row["lease_owner"],
        outcome=SubmissionOutcome.model_validate(outcome) if outcome is not None else None,
    )


def _attempt(row: Row) -> Attempt:
    return Attempt(
        attempt_id=row["attempt_id"],
        learner_id=row["learner_id"],
        submission_id=row["submission_id"],
        task_version_id=row["task_version_id"],
        attempt_number=row["attempt_number"],
        evaluation_id=row["evaluation_id"],
        feedback_id=row["feedback_id"],
        evaluator_id=row["evaluator_id"],
        evaluator_version=row["evaluator_version"],
        prompt_version=row["prompt_version"],
        started_at=_utc(row["started_at"]),
        completed_at=_optional_utc(row["completed_at"]),
    )


def _evidence(row: Row) -> SkillEvidence:
    return SkillEvidence(
        evidence_id=row["evidence_id"],
        learner_id=row["learner_id"],
        attempt_id=row["attempt_id"],
        task_version_id=row["task_version_id"],
        skill_id=row["skill_id"],
        check_id=row["check_id"],
        awarded_points=row["awarded_points"],
        available_points=row["available_points"],
        recorded_at=_utc(row["recorded_at"]),
    )


def _evaluation(row: Row) -> EvaluationRecord:
    return EvaluationRecord(
        evaluation_id=row["evaluation_id"],
        result=EvaluationResult.model_validate(row["result"]),
        recorded_at=_utc(row["recorded_at"]),
    )


def _feedback(row: Row) -> FeedbackRecord:
    return FeedbackRecord(
        feedback_id=row["feedback_id"],
        result=FeedbackResult.model_validate(row["result"]),
        recorded_at=_utc(row["recorded_at"]),
    )


def _outbox(row: Row) -> OutboxEvent:
    return OutboxEvent(
        event_id=row["event_id"],
        event_type=row["event_type"],
        aggregate_id=row["aggregate_id"],
        payload=row["payload"],
        created_at=_utc(row["created_at"]),
        published_at=_optional_utc(row["published_at"]),
    )
