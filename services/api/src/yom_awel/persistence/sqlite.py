"""SQLite persistence adapter used by local mode and the contract tests.

The adapter deliberately keeps SQL at the persistence boundary.  Domain
objects are serialized as JSON and reconstructed through their Pydantic
contracts, while each unit of work owns one short-lived SQLite transaction.
No connection is held while evaluator or provider I/O is in progress.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Self, cast
from uuid import UUID, uuid4

from yom_awel.domain.contracts import (
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
from yom_awel.domain.enums import Channel, SubmissionStatus
from yom_awel.domain.errors import (
    FinalizationConflict,
    IdempotencyConflict,
    LearnerScopeViolation,
    NotFound,
    OptimisticConflict,
    ReservationExpired,
    ReservationOwnerConflict,
    SubmissionMismatch,
    TransactionReuse,
    UniqueConstraintViolation,
)
from yom_awel.ports.clock import Clock
from yom_awel.ports.repositories import MAX_SUBMISSION_LEASE_SECONDS

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS learners (
    learner_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    preferred_language TEXT NOT NULL CHECK (preferred_language IN ('ar-EG', 'en')),
    status TEXT NOT NULL CHECK (status IN ('ONBOARDING', 'READY', 'IN_TASK', 'PROCESSING', 'NEEDS_RETRY', 'TASK_COMPLETED', 'PROGRAM_COMPLETED')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    state_machine_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS external_identities (
    identity_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    provider_subject TEXT NOT NULL,
    UNIQUE(provider, provider_subject)
);
CREATE TABLE IF NOT EXISTS task_versions (
    task_version_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    version TEXT NOT NULL,
    instructions_ar TEXT NOT NULL,
    instructions_en TEXT NOT NULL,
    artifact_schema TEXT NOT NULL,
    evaluator_id TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    pass_threshold INTEGER NOT NULL CHECK (pass_threshold BETWEEN 0 AND 100),
    skill_mappings TEXT NOT NULL,
    content_hash TEXT NOT NULL CHECK (length(content_hash) = 64),
    UNIQUE(task_id, version)
);
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    size_bytes INTEGER NOT NULL CHECK (size_bytes BETWEEN 0 AND 5242880),
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    content BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS submissions (
    reservation_id TEXT PRIMARY KEY,
    submission_id TEXT NOT NULL UNIQUE,
    learner_id TEXT NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    task_version_id TEXT NOT NULL REFERENCES task_versions(task_version_id),
    artifact_id TEXT NOT NULL REFERENCES artifacts(artifact_id),
    channel TEXT NOT NULL CHECK (channel IN ('web', 'telegram')),
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('RECEIVED', 'EVALUATING', 'COMPLETED', 'FAILED')),
    created_at TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 1),
    lease_expires_at TEXT NOT NULL,
    lease_owner TEXT,
    outcome TEXT,
    UNIQUE(learner_id, idempotency_key)
);
CREATE TABLE IF NOT EXISTS evaluation_results (
    evaluation_id TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback_results (
    feedback_id TEXT PRIMARY KEY,
    result TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    attempt_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    submission_id TEXT NOT NULL REFERENCES submissions(submission_id),
    task_version_id TEXT NOT NULL REFERENCES task_versions(task_version_id),
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    evaluation_id TEXT NOT NULL REFERENCES evaluation_results(evaluation_id),
    feedback_id TEXT NOT NULL REFERENCES feedback_results(feedback_id),
    evaluator_id TEXT NOT NULL,
    evaluator_version TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    UNIQUE(learner_id, task_version_id, attempt_number)
);
CREATE TABLE IF NOT EXISTS skill_evidence (
    evidence_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL REFERENCES learners(learner_id) ON DELETE CASCADE,
    attempt_id TEXT NOT NULL REFERENCES attempts(attempt_id),
    task_version_id TEXT NOT NULL REFERENCES task_versions(task_version_id),
    skill_id TEXT NOT NULL,
    check_id TEXT NOT NULL,
    awarded_points INTEGER NOT NULL CHECK (awarded_points >= 0),
    available_points INTEGER NOT NULL CHECK (available_points > 0),
    recorded_at TEXT NOT NULL,
    UNIQUE(attempt_id, skill_id, check_id)
);
CREATE TABLE IF NOT EXISTS learner_progress (
    learner_id TEXT PRIMARY KEY REFERENCES learners(learner_id) ON DELETE CASCADE,
    current_status TEXT NOT NULL,
    current_task_id TEXT,
    version INTEGER NOT NULL CHECK (version >= 1),
    updated_at TEXT NOT NULL,
    reset_at TEXT
);
CREATE TABLE IF NOT EXISTS outbox_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_attempts_learner_task
    ON attempts(learner_id, task_version_id, attempt_number);
CREATE INDEX IF NOT EXISTS idx_outbox_pending
    ON outbox_events(published_at, created_at);
CREATE TABLE IF NOT EXISTS adapter_meta (
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL
);
INSERT OR IGNORE INTO adapter_meta(key, value) VALUES ('revision', 0);
"""


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _dt(value: datetime) -> str:
    return _utc(value).isoformat()


def _parse_dt(value: str) -> datetime:
    return _utc(datetime.fromisoformat(value))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _decode(value: str) -> Any:
    return json.loads(value)


def _uuid(value: UUID) -> str:
    return str(value)


class SQLiteDatabase:
    """Connection/schema owner shared by units of work."""

    def __init__(self, path: str | Path = ":memory:", clock: Clock | None = None) -> None:
        self.clock = clock or SystemClock()
        self.path = str(path)
        self._uri = False
        self._anchor: sqlite3.Connection | None = None
        if self.path == ":memory:":
            self.path = f"file:yom_awel_{id(self)}?mode=memory&cache=shared"
            self._uri = True
        elif self.path != "":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._anchor = self._connect()
        self._anchor.executescript(SCHEMA)
        self._anchor.commit()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            uri=self._uri,
            isolation_level=None,
            check_same_thread=False,
            timeout=5.0,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        if not self._uri:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA synchronous = FULL")
        return connection

    def connection(self) -> sqlite3.Connection:
        return self._connect()

    def close(self) -> None:
        if self._anchor is not None:
            self._anchor.close()
            self._anchor = None


class _Repo:
    def __init__(self, uow: SQLiteUnitOfWork) -> None:
        self._uow = uow

    @property
    def db(self) -> sqlite3.Connection:
        connection = self._uow._connection
        if connection is None:
            raise RuntimeError("repository used outside unit of work")
        return connection

    def _one(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return cast(sqlite3.Row | None, self.db.execute(sql, parameters).fetchone())

    def _all(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return cast(list[sqlite3.Row], self.db.execute(sql, parameters).fetchall())


class _Learners(_Repo):
    async def get(self, learner_id: UUID) -> Learner | None:
        row = self._one("SELECT * FROM learners WHERE learner_id = ?", (_uuid(learner_id),))
        return _learner(row) if row else None

    async def get_by_external_identity(
        self, provider: str, provider_subject: str
    ) -> Learner | None:
        row = self._one(
            "SELECT l.* FROM learners l JOIN external_identities i ON i.learner_id=l.learner_id "
            "WHERE i.provider=? AND i.provider_subject=?",
            (provider, provider_subject),
        )
        return _learner(row) if row else None

    async def add(self, learner: Learner) -> None:
        try:
            self.db.execute(
                "INSERT INTO learners VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    _uuid(learner.learner_id),
                    learner.display_name,
                    learner.preferred_language.value,
                    learner.status.value,
                    _dt(learner.created_at),
                    _dt(learner.updated_at),
                    learner.state_machine_version,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("learners.id") from error

    async def add_external_identity(
        self, learner_id: UUID, provider: str, provider_subject: str
    ) -> ExternalIdentity:
        if not await self.get(learner_id):
            raise LearnerScopeViolation("external_identity.learner_id")
        identity = ExternalIdentity(
            identity_id=uuid4(),
            learner_id=learner_id,
            provider=provider,
            provider_subject=provider_subject,
        )
        try:
            self.db.execute(
                "INSERT INTO external_identities VALUES (?, ?, ?, ?)",
                (_uuid(identity.identity_id), _uuid(learner_id), provider, provider_subject),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("external_identities.provider_subject") from error
        return identity

    async def get_progress(self, learner_id: UUID) -> LearnerProgress | None:
        row = self._one("SELECT * FROM learner_progress WHERE learner_id=?", (_uuid(learner_id),))
        return _progress(row) if row else None

    async def save_progress(self, progress: LearnerProgress, expected_version: int) -> None:
        learner_key = _uuid(progress.learner_id)
        if not await self.get(progress.learner_id):
            raise LearnerScopeViolation("learner_progress.learner_id")
        current = self._one(
            "SELECT version FROM learner_progress WHERE learner_id=?", (learner_key,)
        )
        if current is None:
            if expected_version != 0 or progress.version != 1:
                raise OptimisticConflict("learner_progress")
            self.db.execute(
                "INSERT INTO learner_progress VALUES (?, ?, ?, ?, ?, ?)",
                (
                    learner_key,
                    progress.current_status.value,
                    progress.current_task_id,
                    progress.version,
                    _dt(progress.updated_at),
                    _dt(progress.reset_at) if progress.reset_at else None,
                ),
            )
            return
        if int(current["version"]) != expected_version or progress.version != expected_version + 1:
            raise OptimisticConflict("learner_progress")
        updated = self.db.execute(
            "UPDATE learner_progress SET current_status=?, current_task_id=?, version=?, "
            "updated_at=?, reset_at=? WHERE learner_id=? AND version=?",
            (
                progress.current_status.value,
                progress.current_task_id,
                progress.version,
                _dt(progress.updated_at),
                _dt(progress.reset_at) if progress.reset_at else None,
                learner_key,
                expected_version,
            ),
        )
        if updated.rowcount != 1:
            raise OptimisticConflict("learner_progress")


class _Tasks(_Repo):
    async def get(self, task_version_id: UUID) -> TaskVersion | None:
        row = self._one(
            "SELECT * FROM task_versions WHERE task_version_id=?", (_uuid(task_version_id),)
        )
        return _task(row) if row else None

    async def get_task(self, task_id: str) -> Task | None:
        row = self._one("SELECT task_id FROM task_versions WHERE task_id=? LIMIT 1", (task_id,))
        return Task(task_id=row["task_id"], title=row["task_id"]) if row else None

    async def get_current_published_version(self, task_id: str) -> TaskVersion | None:
        # SQLite's local contract stores only approved task versions.  Select
        # numeric publication order in Python rather than lexical SQL order.
        rows = self.db.execute(
            "SELECT * FROM task_versions WHERE task_id=?", (task_id,)
        ).fetchall()
        if not rows:
            return None

        def order(row: sqlite3.Row) -> tuple[int, int, str, str]:
            version = row["version"]
            if version.isdecimal():
                return (1, int(version), "", row["task_version_id"])
            return (0, 0, version, row["task_version_id"])

        return _task(max(rows, key=order))

    async def add(self, task_version: TaskVersion) -> None:
        try:
            self.db.execute(
                "INSERT INTO task_versions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _uuid(task_version.task_version_id),
                    task_version.task_id,
                    task_version.version,
                    task_version.instructions_ar,
                    task_version.instructions_en,
                    _json(task_version.artifact_schema),
                    task_version.evaluator_id,
                    task_version.evaluator_version,
                    task_version.pass_threshold,
                    _json([item.model_dump(mode="json") for item in task_version.skill_mappings]),
                    task_version.content_hash,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("task_versions.task_id_version") from error


class _Artifacts(_Repo):
    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None:
        row = self._one(
            "SELECT artifact_id, learner_id, filename, size_bytes, sha256 FROM artifacts "
            "WHERE artifact_id=? AND learner_id=?",
            (_uuid(artifact_id), _uuid(learner_id)),
        )
        return _artifact(row) if row else None

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None:
        row = self._one(
            "SELECT content FROM artifacts WHERE artifact_id=? AND learner_id=?",
            (_uuid(artifact_id), _uuid(learner_id)),
        )
        return bytes(row["content"]) if row else None

    async def put(self, artifact: Artifact, content: bytes) -> Artifact:
        import hashlib

        if len(content) != artifact.size_bytes:
            raise ValueError("content size does not match artifact metadata")
        if hashlib.sha256(content).hexdigest() != artifact.sha256:
            raise ValueError("content sha256 does not match artifact metadata")
        try:
            self.db.execute(
                "INSERT INTO artifacts VALUES (?, ?, ?, ?, ?, ?)",
                (
                    _uuid(artifact.artifact_id),
                    _uuid(artifact.learner_id),
                    artifact.filename,
                    artifact.size_bytes,
                    artifact.sha256,
                    sqlite3.Binary(content),
                ),
            )
        except sqlite3.IntegrityError as error:
            if not await self._learner_exists(artifact.learner_id):
                raise LearnerScopeViolation("artifact.learner_id") from error
            raise UniqueConstraintViolation("artifacts.id") from error
        return artifact

    async def _learner_exists(self, learner_id: UUID) -> bool:
        return (
            self._one("SELECT 1 FROM learners WHERE learner_id=?", (_uuid(learner_id),)) is not None
        )

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None:
        row = self._one(
            "SELECT learner_id FROM artifacts WHERE artifact_id=?", (_uuid(artifact_id),)
        )
        if row is None:
            return
        if row["learner_id"] != _uuid(learner_id):
            raise LearnerScopeViolation("artifact.learner_id")
        self.db.execute("DELETE FROM artifacts WHERE artifact_id=?", (_uuid(artifact_id),))


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
        if (
            lease_seconds <= 0
            or lease_seconds > MAX_SUBMISSION_LEASE_SECONDS
            or not lease_owner.strip()
        ):
            raise ValueError(
                "lease_seconds must be between 1 and 3600 and lease_owner must be non-empty"
            )
        if not await self._learner_exists(learner_id):
            raise LearnerScopeViolation("submission.learner_id")
        now = self._uow._database.clock.now()
        existing = self._one(
            "SELECT * FROM submissions WHERE learner_id=? AND idempotency_key=?",
            (_uuid(learner_id), key),
        )
        if existing is not None:
            result = _reservation(existing)
            if result.request_fingerprint != request_fingerprint:
                raise IdempotencyConflict(key)
            if result.status == SubmissionStatus.COMPLETED:
                return result
            if result.lease_expires_at > _utc(now):
                return result
            reclaimed = result.model_copy(
                update={
                    "lease_owner": lease_owner,
                    "lease_expires_at": _utc(now) + timedelta(seconds=lease_seconds),
                    "version": result.version + 1,
                }
            )
            self.db.execute(
                "UPDATE submissions SET lease_owner=?, lease_expires_at=?, version=? "
                "WHERE reservation_id=? AND version=?",
                (
                    lease_owner,
                    _dt(reclaimed.lease_expires_at),
                    reclaimed.version,
                    _uuid(result.reservation_id),
                    result.version,
                ),
            )
            return reclaimed
        if not await self._exists("task_versions", "task_version_id", task_version_id):
            raise NotFound("task_version")
        artifact = self._one(
            "SELECT learner_id FROM artifacts WHERE artifact_id=?", (_uuid(artifact_id),)
        )
        if artifact is None:
            raise NotFound("artifact")
        if artifact["learner_id"] != _uuid(learner_id):
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
            lease_expires_at=_utc(now) + timedelta(seconds=lease_seconds),
            created_at=_utc(now),
            lease_owner=lease_owner,
        )
        self.db.execute(
            "INSERT INTO submissions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _uuid(result.reservation_id),
                _uuid(result.submission_id),
                _uuid(learner_id),
                _uuid(task_version_id),
                _uuid(artifact_id),
                channel.value,
                key,
                request_fingerprint,
                result.status.value,
                _dt(result.created_at),
                result.version,
                _dt(result.lease_expires_at),
                lease_owner,
                None,
            ),
        )
        return result

    async def get_reservation(self, learner_id: UUID, key: str) -> SubmissionReservation | None:
        row = self._one(
            "SELECT * FROM submissions WHERE learner_id=? AND idempotency_key=?",
            (_uuid(learner_id), key),
        )
        return _reservation(row) if row else None

    async def expire(
        self,
        learner_id: UUID,
        key: str,
        expected_version: int | None = None,
        lease_owner: str | None = None,
    ) -> None:
        row = self._one(
            "SELECT * FROM submissions WHERE learner_id=? AND idempotency_key=?",
            (_uuid(learner_id), key),
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
        self.db.execute(
            "UPDATE submissions SET lease_expires_at=?, version=? WHERE reservation_id=? AND version=?",
            (
                _dt(self._uow._database.clock.now()),
                result.version + 1,
                _uuid(result.reservation_id),
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
        row = self._one(
            "SELECT * FROM submissions WHERE reservation_id=?", (_uuid(reservation_id),)
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
        updated = self.db.execute(
            "UPDATE submissions SET status=?, outcome=?, version=? WHERE reservation_id=? "
            "AND version=? AND lease_owner=? AND status<>?",
            (
                SubmissionStatus.COMPLETED.value,
                _json(outcome.model_dump(mode="json")),
                expected_version + 1,
                _uuid(reservation_id),
                expected_version,
                lease_owner,
                SubmissionStatus.COMPLETED.value,
            ),
        )
        if updated.rowcount != 1:
            raise OptimisticConflict("submission_reservation")

    async def _learner_exists(self, learner_id: UUID) -> bool:
        return await self._exists("learners", "learner_id", learner_id)

    async def _exists(self, table: str, column: str, value: UUID) -> bool:
        return self._one(f"SELECT 1 FROM {table} WHERE {column}=?", (_uuid(value),)) is not None


class _Attempts(_Repo):
    async def add(self, attempt: Attempt) -> None:
        if not await self._exists("learners", "learner_id", attempt.learner_id):
            raise LearnerScopeViolation("attempt.learner_id")
        if not await self._exists("task_versions", "task_version_id", attempt.task_version_id):
            raise NotFound("task_version")
        reservation = self._one(
            "SELECT learner_id, task_version_id FROM submissions WHERE submission_id=?",
            (_uuid(attempt.submission_id),),
        )
        if reservation is None:
            raise NotFound("submission")
        if reservation["learner_id"] != _uuid(attempt.learner_id) or reservation[
            "task_version_id"
        ] != _uuid(attempt.task_version_id):
            raise LearnerScopeViolation("attempt.submission_id")
        if self._one("SELECT 1 FROM attempts WHERE attempt_id=?", (_uuid(attempt.attempt_id),)):
            raise UniqueConstraintViolation("attempts.id")
        existing = await self.list_for_task(attempt.learner_id, attempt.task_version_id)
        if any(item.attempt_number == attempt.attempt_number for item in existing):
            raise UniqueConstraintViolation("attempts.learner_task_attempt_number")
        if attempt.attempt_number != len(existing) + 1:
            raise OptimisticConflict("attempt ordering")
        if not await self._exists("evaluation_results", "evaluation_id", attempt.evaluation_id):
            raise NotFound("evaluation")
        if not await self._exists("feedback_results", "feedback_id", attempt.feedback_id):
            raise NotFound("feedback")
        try:
            self.db.execute(
                "INSERT INTO attempts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _uuid(attempt.attempt_id),
                    _uuid(attempt.learner_id),
                    _uuid(attempt.submission_id),
                    _uuid(attempt.task_version_id),
                    attempt.attempt_number,
                    _uuid(attempt.evaluation_id),
                    _uuid(attempt.feedback_id),
                    attempt.evaluator_id,
                    attempt.evaluator_version,
                    attempt.prompt_version,
                    _dt(attempt.started_at),
                    _dt(attempt.completed_at) if attempt.completed_at else None,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("attempts.id") from error

    async def get(self, attempt_id: UUID) -> Attempt | None:
        row = self._one("SELECT * FROM attempts WHERE attempt_id=?", (_uuid(attempt_id),))
        return _attempt(row) if row else None

    async def list_for_task(self, learner_id: UUID, task_version_id: UUID) -> list[Attempt]:
        return [
            _attempt(row)
            for row in self._all(
                "SELECT * FROM attempts WHERE learner_id=? AND task_version_id=? "
                "ORDER BY attempt_number, attempt_id",
                (_uuid(learner_id), _uuid(task_version_id)),
            )
        ]

    async def _exists(self, table: str, column: str, value: UUID) -> bool:
        return self._one(f"SELECT 1 FROM {table} WHERE {column}=?", (_uuid(value),)) is not None


class _Skills(_Repo):
    async def add_evidence(self, evidence: SkillEvidence) -> None:
        if not await self._exists("learners", "learner_id", evidence.learner_id):
            raise LearnerScopeViolation("skill_evidence.learner_id")
        if not await self._exists("task_versions", "task_version_id", evidence.task_version_id):
            raise NotFound("task_version")
        attempt = self._one(
            "SELECT learner_id, task_version_id FROM attempts WHERE attempt_id=?",
            (_uuid(evidence.attempt_id),),
        )
        if attempt is None:
            raise NotFound("attempt")
        if attempt["learner_id"] != _uuid(evidence.learner_id) or attempt[
            "task_version_id"
        ] != _uuid(evidence.task_version_id):
            raise LearnerScopeViolation("skill_evidence.attempt_id")
        try:
            self.db.execute(
                "INSERT INTO skill_evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    _uuid(evidence.evidence_id),
                    _uuid(evidence.learner_id),
                    _uuid(evidence.attempt_id),
                    _uuid(evidence.task_version_id),
                    evidence.skill_id,
                    evidence.check_id,
                    evidence.awarded_points,
                    evidence.available_points,
                    _dt(evidence.recorded_at),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("skill_evidence.attempt_skill_check") from error

    async def list_evidence(self, learner_id: UUID) -> list[SkillEvidence]:
        return [
            _evidence(row)
            for row in self._all(
                "SELECT * FROM skill_evidence WHERE learner_id=? ORDER BY skill_id, recorded_at, evidence_id",
                (_uuid(learner_id),),
            )
        ]

    async def get_profile(self, learner_id: UUID) -> SkillsProfile:
        totals: dict[str, int] = {}
        for item in await self.list_evidence(learner_id):
            totals[item.skill_id] = min(100, totals.get(item.skill_id, 0) + item.awarded_points)
        return SkillsProfile(
            learner_id=learner_id,
            skills=[SkillSummary(skill_id=k, score=v) for k, v in sorted(totals.items())],
        )

    async def _exists(self, table: str, column: str, value: UUID) -> bool:
        return self._one(f"SELECT 1 FROM {table} WHERE {column}=?", (_uuid(value),)) is not None


class _Evaluations(_Repo):
    async def get(self, evaluation_id: UUID) -> EvaluationRecord | None:
        row = self._one(
            "SELECT * FROM evaluation_results WHERE evaluation_id=?", (_uuid(evaluation_id),)
        )
        return _evaluation(row) if row else None

    async def add(self, record: EvaluationRecord) -> None:
        try:
            self.db.execute(
                "INSERT INTO evaluation_results VALUES (?, ?, ?)",
                (
                    _uuid(record.evaluation_id),
                    _json(record.result.model_dump(mode="json")),
                    _dt(record.recorded_at),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("evaluation_results.id") from error


class _Feedback(_Repo):
    async def get(self, feedback_id: UUID) -> FeedbackRecord | None:
        row = self._one("SELECT * FROM feedback_results WHERE feedback_id=?", (_uuid(feedback_id),))
        return _feedback(row) if row else None

    async def add(self, record: FeedbackRecord) -> None:
        try:
            self.db.execute(
                "INSERT INTO feedback_results VALUES (?, ?, ?)",
                (
                    _uuid(record.feedback_id),
                    _json(record.result.model_dump(mode="json")),
                    _dt(record.recorded_at),
                ),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("feedback_results.id") from error


class _Outbox(_Repo):
    async def add(self, event: OutboxEvent) -> None:
        try:
            self.db.execute(
                "INSERT INTO outbox_events VALUES (?, ?, ?, ?, ?, ?)",
                (
                    _uuid(event.event_id),
                    event.event_type,
                    _uuid(event.aggregate_id),
                    _json(event.payload),
                    _dt(event.created_at),
                    _dt(event.published_at) if event.published_at else None,
                ),
            )
        except sqlite3.IntegrityError as error:
            raise UniqueConstraintViolation("outbox_events.id") from error

    async def pending(self, limit: int = 100) -> list[OutboxEvent]:
        if limit < 1:
            raise ValueError("limit must be positive")
        return [
            _outbox(row)
            for row in self._all(
                "SELECT * FROM outbox_events WHERE published_at IS NULL ORDER BY created_at, event_id LIMIT ?",
                (limit,),
            )
        ]

    async def mark_published(self, event_id: UUID) -> None:
        updated = self.db.execute(
            "UPDATE outbox_events SET published_at=? WHERE event_id=?",
            (_dt(self._uow._database.clock.now()), _uuid(event_id)),
        )
        if updated.rowcount != 1:
            raise NotFound("outbox_event")


class SQLiteUnitOfWork:
    def __init__(self, database: SQLiteDatabase) -> None:
        self._database = database
        self._connection: sqlite3.Connection | None = None
        self._active = False
        self._base_revision = 0
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
        self._connection = self._database.connection()
        # Deferred transactions allow concurrent read-only units of work to
        # observe the last committed snapshot. SQLite acquires its write lock
        # at the first mutation, keeping reserve/finalize short and atomic.
        self._connection.execute("BEGIN")
        revision = self._connection.execute(
            "SELECT value FROM adapter_meta WHERE key='revision'"
        ).fetchone()
        if revision is None:
            raise RuntimeError("SQLite adapter metadata is not initialized")
        self._base_revision = int(revision[0])
        self._active = True
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.rollback()

    async def commit(self) -> None:
        if not self._active or self._connection is None:
            raise RuntimeError("unit of work is not active")
        try:
            updated = self._connection.execute(
                "UPDATE adapter_meta SET value=value+1 WHERE key='revision' AND value=?",
                (self._base_revision,),
            )
            if updated.rowcount != 1:
                self._connection.rollback()
                raise OptimisticConflict("unit_of_work")
            self._connection.commit()
        except sqlite3.OperationalError as error:
            self._connection.rollback()
            if "locked" in str(error).lower() or "busy" in str(error).lower():
                raise OptimisticConflict("unit_of_work") from error
            raise
        finally:
            self._connection.close()
            self._connection = None
            self._active = False

    async def rollback(self) -> None:
        if self._connection is not None:
            try:
                if self._active:
                    self._connection.rollback()
            finally:
                self._connection.close()
                self._connection = None
        self._active = False


class SQLiteUnitOfWorkFactory:
    def __init__(
        self,
        database: SQLiteDatabase | str | Path = ":memory:",
        clock: Clock | None = None,
    ) -> None:
        self.database = (
            database if isinstance(database, SQLiteDatabase) else SQLiteDatabase(database, clock)
        )

    def __call__(self) -> SQLiteUnitOfWork:
        return SQLiteUnitOfWork(self.database)


def _learner(row: sqlite3.Row) -> Learner:
    return Learner(
        learner_id=UUID(row["learner_id"]),
        display_name=row["display_name"],
        preferred_language=row["preferred_language"],
        status=row["status"],
        created_at=_parse_dt(row["created_at"]),
        updated_at=_parse_dt(row["updated_at"]),
        state_machine_version=row["state_machine_version"],
    )


def _task(row: sqlite3.Row) -> TaskVersion:
    return TaskVersion.model_validate(
        {
            "task_version_id": UUID(row["task_version_id"]),
            "task_id": row["task_id"],
            "version": row["version"],
            "instructions_ar": row["instructions_ar"],
            "instructions_en": row["instructions_en"],
            "artifact_schema": _decode(row["artifact_schema"]),
            "evaluator_id": row["evaluator_id"],
            "evaluator_version": row["evaluator_version"],
            "pass_threshold": row["pass_threshold"],
            "skill_mappings": _decode(row["skill_mappings"]),
            "content_hash": row["content_hash"],
        }
    )


def _artifact(row: sqlite3.Row) -> Artifact:
    return Artifact(
        artifact_id=UUID(row["artifact_id"]),
        learner_id=UUID(row["learner_id"]),
        filename=row["filename"],
        size_bytes=row["size_bytes"],
        sha256=row["sha256"],
    )


def _progress(row: sqlite3.Row) -> LearnerProgress:
    return LearnerProgress(
        learner_id=UUID(row["learner_id"]),
        current_status=row["current_status"],
        current_task_id=row["current_task_id"] if row["current_task_id"] else None,
        version=row["version"],
        updated_at=_parse_dt(row["updated_at"]),
        reset_at=_parse_dt(row["reset_at"]) if row["reset_at"] else None,
    )


def _reservation(row: sqlite3.Row) -> SubmissionReservation:
    outcome = SubmissionOutcome.model_validate(_decode(row["outcome"])) if row["outcome"] else None
    return SubmissionReservation(
        reservation_id=UUID(row["reservation_id"]),
        submission_id=UUID(row["submission_id"]),
        learner_id=UUID(row["learner_id"]),
        task_version_id=UUID(row["task_version_id"]),
        artifact_id=UUID(row["artifact_id"]) if row["artifact_id"] else None,
        channel=row["channel"] if row["channel"] else None,
        idempotency_key=row["idempotency_key"],
        request_fingerprint=row["request_fingerprint"],
        status=row["status"],
        created_at=_parse_dt(row["created_at"]),
        version=row["version"],
        lease_expires_at=_parse_dt(row["lease_expires_at"]),
        lease_owner=row["lease_owner"],
        outcome=outcome,
    )


def _attempt(row: sqlite3.Row) -> Attempt:
    return Attempt(
        attempt_id=UUID(row["attempt_id"]),
        learner_id=UUID(row["learner_id"]),
        submission_id=UUID(row["submission_id"]),
        task_version_id=UUID(row["task_version_id"]),
        attempt_number=row["attempt_number"],
        evaluation_id=UUID(row["evaluation_id"]),
        feedback_id=UUID(row["feedback_id"]),
        evaluator_id=row["evaluator_id"],
        evaluator_version=row["evaluator_version"],
        prompt_version=row["prompt_version"],
        started_at=_parse_dt(row["started_at"]),
        completed_at=_parse_dt(row["completed_at"]) if row["completed_at"] else None,
    )


def _evidence(row: sqlite3.Row) -> SkillEvidence:
    return SkillEvidence(
        evidence_id=UUID(row["evidence_id"]),
        learner_id=UUID(row["learner_id"]),
        attempt_id=UUID(row["attempt_id"]),
        task_version_id=UUID(row["task_version_id"]),
        skill_id=row["skill_id"],
        check_id=row["check_id"],
        awarded_points=row["awarded_points"],
        available_points=row["available_points"],
        recorded_at=_parse_dt(row["recorded_at"]),
    )


def _evaluation(row: sqlite3.Row) -> EvaluationRecord:
    from yom_awel.domain.contracts import EvaluationResult

    return EvaluationRecord(
        evaluation_id=UUID(row["evaluation_id"]),
        result=EvaluationResult.model_validate(_decode(row["result"])),
        recorded_at=_parse_dt(row["recorded_at"]),
    )


def _feedback(row: sqlite3.Row) -> FeedbackRecord:
    from yom_awel.domain.contracts import FeedbackResult

    return FeedbackRecord(
        feedback_id=UUID(row["feedback_id"]),
        result=FeedbackResult.model_validate(_decode(row["result"])),
        recorded_at=_parse_dt(row["recorded_at"]),
    )


def _outbox(row: sqlite3.Row) -> OutboxEvent:
    return OutboxEvent(
        event_id=UUID(row["event_id"]),
        event_type=row["event_type"],
        aggregate_id=UUID(row["aggregate_id"]),
        payload=_decode(row["payload"]),
        created_at=_parse_dt(row["created_at"]),
        published_at=_parse_dt(row["published_at"]) if row["published_at"] else None,
    )
