from __future__ import annotations

import asyncio
import copy
import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID, uuid4

from yom_awel.domain.contracts import SkillsProfile, SkillSummary, SubmissionOutcome, TaskVersion
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


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    def __init__(self, current: datetime) -> None:
        self._current = current

    def now(self) -> datetime:
        return self._current

    def advance(self, **kwargs: int) -> None:
        self._current += timedelta(**kwargs)


@dataclass
class _StoredArtifact:
    metadata: Artifact
    content: bytes


@dataclass
class _State:
    learners: dict[UUID, Learner] = field(default_factory=dict)
    identities: dict[tuple[str, str], ExternalIdentity] = field(default_factory=dict)
    progress: dict[UUID, LearnerProgress] = field(default_factory=dict)
    tasks: dict[UUID, TaskVersion] = field(default_factory=dict)
    task_groups: dict[str, Task] = field(default_factory=dict)
    reservations: dict[UUID, SubmissionReservation] = field(default_factory=dict)
    reservation_keys: dict[tuple[UUID, str], UUID] = field(default_factory=dict)
    attempts: dict[UUID, Attempt] = field(default_factory=dict)
    evidence: dict[UUID, SkillEvidence] = field(default_factory=dict)
    outbox: dict[UUID, OutboxEvent] = field(default_factory=dict)
    evaluations: dict[UUID, EvaluationRecord] = field(default_factory=dict)
    feedback: dict[UUID, FeedbackRecord] = field(default_factory=dict)
    artifacts: dict[UUID, _StoredArtifact] = field(default_factory=dict)
    revision: int = 0


class MemoryDatabase:
    """Committed state shared by all UoWs produced from one factory."""

    def __init__(self, clock: Clock | None = None) -> None:
        self._state = _State()
        self._lock = asyncio.Lock()
        self.clock: Clock = clock or SystemClock()


class _MemoryRepository:
    def __init__(self, uow: MemoryUnitOfWork) -> None:
        self._uow = uow

    @property
    def _state(self) -> _State:
        snapshot = self._uow._snapshot
        if snapshot is None:
            raise RuntimeError("repository used outside unit of work")
        return snapshot


class _Learners(_MemoryRepository):
    async def get(self, learner_id: UUID) -> Learner | None:
        return _copy(self._state.learners.get(learner_id))

    async def get_by_external_identity(
        self, provider: str, provider_subject: str
    ) -> Learner | None:
        identity = self._state.identities.get((provider, provider_subject))
        return _copy(self._state.learners.get(identity.learner_id)) if identity else None

    async def add(self, learner: Learner) -> None:
        if learner.learner_id in self._state.learners:
            raise UniqueConstraintViolation("learners.id")
        self._state.learners[learner.learner_id] = _copy(learner)

    async def add_external_identity(
        self, learner_id: UUID, provider: str, provider_subject: str
    ) -> ExternalIdentity:
        if learner_id not in self._state.learners:
            raise LearnerScopeViolation("external_identity.learner_id")
        key = (provider, provider_subject)
        if key in self._state.identities:
            raise UniqueConstraintViolation("external_identities.provider_subject")
        identity = ExternalIdentity(
            identity_id=uuid4(),
            learner_id=learner_id,
            provider=provider,
            provider_subject=provider_subject,
        )
        self._state.identities[key] = identity
        return _copy(identity)

    async def get_progress(self, learner_id: UUID) -> LearnerProgress | None:
        return _copy(self._state.progress.get(learner_id))

    async def save_progress(self, progress: LearnerProgress, expected_version: int) -> None:
        if progress.learner_id not in self._state.learners:
            raise LearnerScopeViolation("learner_progress.learner_id")
        current = self._state.progress.get(progress.learner_id)
        if current is None:
            if expected_version != 0 or progress.version != 1:
                raise OptimisticConflict("learner_progress")
        elif current.version != expected_version or progress.version != expected_version + 1:
            raise OptimisticConflict("learner_progress")
        self._state.progress[progress.learner_id] = _copy(progress)


class _Tasks(_MemoryRepository):
    async def get(self, task_version_id: UUID) -> TaskVersion | None:
        return _copy(self._state.tasks.get(task_version_id))

    async def get_task(self, task_id: str) -> Task | None:
        return _copy(self._state.task_groups.get(task_id))

    async def get_current_published_version(self, task_id: str) -> TaskVersion | None:
        # Local TaskVersion records are already publication-approved.  Numeric
        # ordering avoids the lexical "10" < "2" trap; UUID breaks ties.
        versions = [item for item in self._state.tasks.values() if item.task_id == task_id]
        if not versions:
            return None

        def order(item: TaskVersion) -> tuple[int, int, str, str]:
            version = item.version
            if version.isdecimal():
                return (1, int(version), "", str(item.task_version_id))
            return (0, 0, version, str(item.task_version_id))

        return _copy(max(versions, key=order))

    async def add(self, task_version: TaskVersion) -> None:
        if task_version.task_version_id in self._state.tasks:
            raise UniqueConstraintViolation("task_versions.id")
        if any(
            item.task_id == task_version.task_id and item.version == task_version.version
            for item in self._state.tasks.values()
        ):
            raise UniqueConstraintViolation("task_versions.task_id_version")
        self._state.tasks[task_version.task_version_id] = _copy(task_version)
        self._state.task_groups.setdefault(
            task_version.task_id, Task(task_id=task_version.task_id, title=task_version.task_id)
        )


class _Submissions(_MemoryRepository):
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
        state = self._state
        if learner_id not in state.learners:
            raise LearnerScopeViolation("submission.learner_id")
        now = self._uow._database.clock.now()
        existing_id = state.reservation_keys.get((learner_id, key))
        if existing_id is not None:
            existing = state.reservations[existing_id]
            if existing.request_fingerprint != request_fingerprint:
                raise IdempotencyConflict(key)
            if existing.status == SubmissionStatus.COMPLETED:
                return _copy(existing)
            if existing.lease_expires_at > now:
                return _copy(existing)
            reclaimed = existing.model_copy(
                update={
                    "lease_owner": lease_owner,
                    "lease_expires_at": now + timedelta(seconds=lease_seconds),
                    "version": existing.version + 1,
                }
            )
            state.reservations[existing_id] = reclaimed
            return _copy(reclaimed)

        if task_version_id not in state.tasks:
            raise NotFound("task_version")
        artifact = state.artifacts.get(artifact_id)
        if artifact is None:
            raise NotFound("artifact")
        if artifact.metadata.learner_id != learner_id:
            raise LearnerScopeViolation("submission.artifact_id")

        reservation = SubmissionReservation(
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
        state.reservations[reservation.reservation_id] = reservation
        state.reservation_keys[(learner_id, key)] = reservation.reservation_id
        return _copy(reservation)

    async def get_reservation(self, learner_id: UUID, key: str) -> SubmissionReservation | None:
        reservation_id = self._state.reservation_keys.get((learner_id, key))
        return _copy(self._state.reservations.get(reservation_id)) if reservation_id else None

    async def expire(
        self,
        learner_id: UUID,
        key: str,
        expected_version: int | None = None,
        lease_owner: str | None = None,
    ) -> None:
        state = self._state
        existing_id = state.reservation_keys.get((learner_id, key))
        if existing_id is None:
            return
        existing = state.reservations[existing_id]
        if expected_version is not None and existing.version != expected_version:
            raise OptimisticConflict("submission_reservation")
        if lease_owner is not None and existing.lease_owner != lease_owner:
            raise ReservationOwnerConflict()
        if existing.status == SubmissionStatus.COMPLETED:
            return
        now = self._uow._database.clock.now()
        expired = existing.model_copy(
            update={
                "lease_expires_at": now,
                "version": existing.version + 1,
            }
        )
        state.reservations[existing_id] = expired

    async def finalize(
        self,
        reservation_id: UUID,
        expected_version: int,
        lease_owner: str,
        outcome: SubmissionOutcome,
    ) -> None:
        current = self._state.reservations.get(reservation_id)
        if current is None:
            raise NotFound("submission_reservation")
        if current.version != expected_version:
            raise OptimisticConflict("submission_reservation")
        if current.status == SubmissionStatus.COMPLETED:
            raise FinalizationConflict("Reservation is already finalized")
        if current.lease_owner != lease_owner:
            raise ReservationOwnerConflict()
        if current.lease_expires_at <= self._uow._database.clock.now():
            raise ReservationExpired()
        if outcome.submission_id != current.submission_id:
            raise SubmissionMismatch()
        if outcome.evaluation.task_version_id != current.task_version_id:
            raise SubmissionMismatch("Outcome task version does not match reservation")
        self._state.reservations[reservation_id] = current.model_copy(
            update={
                "status": SubmissionStatus.COMPLETED,
                "outcome": _copy(outcome),
                "version": current.version + 1,
            }
        )


class _Attempts(_MemoryRepository):
    async def add(self, attempt: Attempt) -> None:
        state = self._state
        if attempt.learner_id not in state.learners:
            raise LearnerScopeViolation("attempt.learner_id")
        if attempt.task_version_id not in state.tasks:
            raise NotFound("task_version")
        reservation = next(
            (
                item
                for item in state.reservations.values()
                if item.submission_id == attempt.submission_id
            ),
            None,
        )
        if reservation is None:
            raise NotFound("submission")
        if (
            reservation.learner_id != attempt.learner_id
            or reservation.task_version_id != attempt.task_version_id
        ):
            raise LearnerScopeViolation("attempt.submission_id")
        if attempt.attempt_id in state.attempts:
            raise UniqueConstraintViolation("attempts.id")
        existing = await self.list_for_task(attempt.learner_id, attempt.task_version_id)
        if any(item.attempt_number == attempt.attempt_number for item in existing):
            raise UniqueConstraintViolation("attempts.learner_task_attempt_number")
        if attempt.attempt_number != len(existing) + 1:
            raise OptimisticConflict("attempt ordering")
        if attempt.evaluation_id not in state.evaluations:
            raise NotFound("evaluation")
        if attempt.feedback_id not in state.feedback:
            raise NotFound("feedback")

        state.attempts[attempt.attempt_id] = _copy(attempt)

    async def get(self, attempt_id: UUID) -> Attempt | None:
        return _copy(self._state.attempts.get(attempt_id))

    async def list_for_task(self, learner_id: UUID, task_version_id: UUID) -> list[Attempt]:
        items = [
            item
            for item in self._state.attempts.values()
            if item.learner_id == learner_id and item.task_version_id == task_version_id
        ]
        return _copy(sorted(items, key=lambda item: (item.attempt_number, str(item.attempt_id))))


class _Skills(_MemoryRepository):
    async def add_evidence(self, evidence: SkillEvidence) -> None:
        state = self._state
        if evidence.learner_id not in state.learners:
            raise LearnerScopeViolation("skill_evidence.learner_id")
        if evidence.task_version_id not in state.tasks:
            raise NotFound("task_version")
        attempt = state.attempts.get(evidence.attempt_id)
        if attempt is None:
            raise NotFound("attempt")
        if (
            attempt.learner_id != evidence.learner_id
            or attempt.task_version_id != evidence.task_version_id
        ):
            raise LearnerScopeViolation("skill_evidence.attempt_id")
        if evidence.evidence_id in state.evidence or any(
            item.attempt_id == evidence.attempt_id
            and item.skill_id == evidence.skill_id
            and item.check_id == evidence.check_id
            for item in state.evidence.values()
        ):
            raise UniqueConstraintViolation("skill_evidence.attempt_skill_check")
        state.evidence[evidence.evidence_id] = _copy(evidence)

    async def list_evidence(self, learner_id: UUID) -> list[SkillEvidence]:
        return _copy(
            sorted(
                (item for item in self._state.evidence.values() if item.learner_id == learner_id),
                key=lambda item: (item.skill_id, item.recorded_at, str(item.evidence_id)),
            )
        )

    async def get_profile(self, learner_id: UUID) -> SkillsProfile:
        totals: dict[str, int] = {}
        for item in await self.list_evidence(learner_id):
            totals[item.skill_id] = min(100, totals.get(item.skill_id, 0) + item.awarded_points)
        return SkillsProfile(
            learner_id=learner_id,
            skills=[
                SkillSummary(skill_id=skill_id, score=score)
                for skill_id, score in sorted(totals.items())
            ],
        )


class _Evaluations(_MemoryRepository):
    async def get(self, evaluation_id: UUID) -> EvaluationRecord | None:
        return _copy(self._state.evaluations.get(evaluation_id))

    async def add(self, record: EvaluationRecord) -> None:
        self._state.evaluations[record.evaluation_id] = _copy(record)


class _Feedback(_MemoryRepository):
    async def get(self, feedback_id: UUID) -> FeedbackRecord | None:
        return _copy(self._state.feedback.get(feedback_id))

    async def add(self, record: FeedbackRecord) -> None:
        self._state.feedback[record.feedback_id] = _copy(record)


class _Outbox(_MemoryRepository):
    async def add(self, event: OutboxEvent) -> None:
        if event.event_id in self._state.outbox:
            raise UniqueConstraintViolation("outbox_events.id")
        self._state.outbox[event.event_id] = _copy(event)

    async def pending(self, limit: int = 100) -> list[OutboxEvent]:
        if limit < 1:
            raise ValueError("limit must be positive")
        events = sorted(
            (event for event in self._state.outbox.values() if event.published_at is None),
            key=lambda event: (event.created_at, str(event.event_id)),
        )
        return _copy(events[:limit])

    async def mark_published(self, event_id: UUID) -> None:
        event = self._state.outbox.get(event_id)
        if event is None:
            raise NotFound("outbox_event")
        self._state.outbox[event_id] = event.model_copy(
            update={"published_at": self._uow._database.clock.now()}
        )


class _Artifacts(_MemoryRepository):
    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None:
        stored = self._state.artifacts.get(artifact_id)
        if stored is None or stored.metadata.learner_id != learner_id:
            return None
        return _copy(stored.metadata)

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None:
        stored = self._state.artifacts.get(artifact_id)
        if stored is None or stored.metadata.learner_id != learner_id:
            return None
        return bytes(stored.content)

    async def put(self, artifact: Artifact, content: bytes) -> Artifact:
        if len(content) != artifact.size_bytes:
            raise ValueError("content size does not match artifact metadata")
        if hashlib.sha256(content).hexdigest() != artifact.sha256:
            raise ValueError("content sha256 does not match artifact metadata")
        if artifact.learner_id not in self._state.learners:
            raise LearnerScopeViolation("artifact.learner_id")
        if artifact.artifact_id in self._state.artifacts:
            raise UniqueConstraintViolation("artifacts.id")
        self._state.artifacts[artifact.artifact_id] = _StoredArtifact(
            _copy(artifact), bytes(content)
        )
        return _copy(artifact)

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None:
        stored = self._state.artifacts.get(artifact_id)
        if stored is None:
            return
        if stored.metadata.learner_id != learner_id:
            raise LearnerScopeViolation("artifact.learner_id")
        del self._state.artifacts[artifact_id]


class MemoryUnitOfWork:
    def __init__(self, database: MemoryDatabase | None = None) -> None:
        self._database = database or MemoryDatabase()
        self._snapshot: _State | None = None
        self._base_revision = 0
        self._active = False
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
        self._active = True
        async with self._database._lock:
            self._snapshot = copy.deepcopy(self._database._state)
            self._base_revision = self._database._state.revision
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.rollback()

    async def commit(self) -> None:
        snapshot = self._snapshot
        if not self._active or snapshot is None:
            raise RuntimeError("unit of work is not active")
        async with self._database._lock:
            if self._database._state.revision != self._base_revision:
                self._snapshot = None
                self._active = False
                raise OptimisticConflict("unit_of_work")
            snapshot.revision = self._database._state.revision + 1
            self._database._state = snapshot
            self._snapshot = None
            self._active = False

    async def rollback(self) -> None:
        self._snapshot = None
        self._active = False


class MemoryUnitOfWorkFactory:
    def __init__(self, database: MemoryDatabase | None = None, clock: Clock | None = None) -> None:
        self.database = database or MemoryDatabase(clock=clock)

    def __call__(self) -> MemoryUnitOfWork:
        return MemoryUnitOfWork(self.database)


class MemoryArtifactStore:
    def __init__(self, database: MemoryDatabase | None = None, clock: Clock | None = None) -> None:
        self._factory = MemoryUnitOfWorkFactory(database=database, clock=clock)

    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None:
        async with self._factory() as uow:
            return await uow.artifacts.get(artifact_id, learner_id)

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None:
        async with self._factory() as uow:
            return await uow.artifacts.download(artifact_id, learner_id)

    async def put(self, artifact: Artifact, content: bytes) -> Artifact:
        async with self._factory() as uow:
            result = await uow.artifacts.put(artifact, content)
            await uow.commit()
            return result

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None:
        async with self._factory() as uow:
            await uow.artifacts.delete(artifact_id, learner_id)
            await uow.commit()


def _copy[T](value: T) -> T:
    return copy.deepcopy(value)
