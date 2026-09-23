from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from yom_awel.ports.artifacts import ArtifactStore
from yom_awel.ports.repositories import (
    AttemptRepository,
    EvaluationRepository,
    FeedbackRepository,
    LearnerRepository,
    OutboxRepository,
    SkillRepository,
    SubmissionRepository,
    TaskRepository,
)


class UnitOfWork(Protocol):
    learners: LearnerRepository
    tasks: TaskRepository
    submissions: SubmissionRepository
    attempts: AttemptRepository
    skills: SkillRepository
    outbox: OutboxRepository
    evaluations: EvaluationRepository
    feedback: FeedbackRepository
    artifacts: ArtifactStore

    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


UnitOfWorkFactory = Callable[[], UnitOfWork]
