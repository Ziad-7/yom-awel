from __future__ import annotations

from typing import Protocol
from uuid import UUID

from yom_awel.domain.contracts import SkillsProfile, SubmissionOutcome, TaskVersion
from yom_awel.domain.entities import (
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
from yom_awel.domain.enums import Channel


class LearnerRepository(Protocol):
    async def get(self, learner_id: UUID) -> Learner | None: ...

    async def get_by_external_identity(
        self, provider: str, provider_subject: str
    ) -> Learner | None: ...

    async def add(self, learner: Learner) -> None: ...

    async def add_external_identity(
        self, learner_id: UUID, provider: str, provider_subject: str
    ) -> ExternalIdentity: ...

    async def save_progress(self, progress: LearnerProgress, expected_version: int) -> None: ...

    async def get_progress(self, learner_id: UUID) -> LearnerProgress | None: ...


class TaskRepository(Protocol):
    async def get(self, task_version_id: UUID) -> TaskVersion | None: ...

    async def get_task(self, task_id: str) -> Task | None: ...

    async def add(self, task_version: TaskVersion) -> None: ...


class SubmissionRepository(Protocol):
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
    ) -> SubmissionReservation: ...

    async def get_reservation(self, learner_id: UUID, key: str) -> SubmissionReservation | None: ...

    async def expire(
        self,
        learner_id: UUID,
        key: str,
        expected_version: int | None = None,
        lease_owner: str | None = None,
    ) -> None: ...

    async def finalize(
        self,
        reservation_id: UUID,
        expected_version: int,
        lease_owner: str,
        outcome: SubmissionOutcome,
    ) -> None: ...


class AttemptRepository(Protocol):
    async def add(self, attempt: Attempt) -> None: ...

    async def get(self, attempt_id: UUID) -> Attempt | None: ...

    async def list_for_task(self, learner_id: UUID, task_version_id: UUID) -> list[Attempt]: ...


class SkillRepository(Protocol):
    async def add_evidence(self, evidence: SkillEvidence) -> None: ...

    async def list_evidence(self, learner_id: UUID) -> list[SkillEvidence]: ...

    async def get_profile(self, learner_id: UUID) -> SkillsProfile: ...


class EvaluationRepository(Protocol):
    async def get(self, evaluation_id: UUID) -> EvaluationRecord | None: ...
    async def add(self, record: EvaluationRecord) -> None: ...


class FeedbackRepository(Protocol):
    async def get(self, feedback_id: UUID) -> FeedbackRecord | None: ...
    async def add(self, record: FeedbackRecord) -> None: ...


class OutboxRepository(Protocol):
    async def add(self, event: OutboxEvent) -> None: ...

    async def pending(self, limit: int = 100) -> list[OutboxEvent]: ...

    async def mark_published(self, event_id: UUID) -> None: ...
