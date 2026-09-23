"""Concrete application composition for local and Supabase deployments."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol
from uuid import uuid4

from yom_awel.application.submissions import ProcessSubmission
from yom_awel.ports.clock import Clock
from yom_awel.ports.evaluation import Evaluator
from yom_awel.ports.feedback import FeedbackProvider
from yom_awel.ports.id_generator import IDGenerator
from yom_awel.ports.unit_of_work import UnitOfWorkFactory


class BoundedRetentionRunner(Protocol):
    async def run_once(
        self, now: datetime, owner: str, limit: int, lease_seconds: int
    ) -> object: ...


class OpportunisticRetentionCleanup:
    """Run a small post-commit cleanup batch with a per-run UUID owner."""

    def __init__(
        self,
        runner: BoundedRetentionRunner,
        *,
        batch_limit: int = 10,
        lease_seconds: int = 300,
    ) -> None:
        if not 1 <= batch_limit <= 100 or lease_seconds < 1:
            raise ValueError("retention cleanup bounds are invalid")
        self.runner = runner
        self.batch_limit = batch_limit
        self.lease_seconds = lease_seconds

    async def __call__(self, now: datetime) -> None:
        await self.runner.run_once(
            now,
            owner=str(uuid4()),
            limit=self.batch_limit,
            lease_seconds=self.lease_seconds,
        )


def create_submission_processor(
    uow_factory: UnitOfWorkFactory,
    evaluator: Evaluator,
    feedback: FeedbackProvider,
    clock: Clock,
    id_gen: IDGenerator,
    *,
    retention_runner: BoundedRetentionRunner | None = None,
    cleanup_limit: int = 10,
    cleanup_lease_seconds: int = 300,
) -> ProcessSubmission:
    """Compose submission processing with bounded post-commit retention."""

    cleanup: Callable[[datetime], Awaitable[None]] | None = None
    if retention_runner is not None:
        cleanup = OpportunisticRetentionCleanup(
            retention_runner,
            batch_limit=cleanup_limit,
            lease_seconds=cleanup_lease_seconds,
        )
    return ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen, cleanup)


# Keep a descriptive alias for composition roots that use a ``build_*`` name.
build_submission_processor = create_submission_processor
