"""Reusable observable contract assertions for local repository adapters."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

import pytest

from yom_awel.domain.contracts import (
    EvaluationResult,
    FeedbackResult,
    SubmissionOutcome,
    TaskVersion,
)
from yom_awel.domain.entities import Artifact, Learner
from yom_awel.domain.enums import Channel, LearnerStatus, SubmissionStatus, TaskStatus
from yom_awel.domain.errors import IdempotencyConflict, OptimisticConflict

NOW = datetime(2026, 9, 21, tzinfo=UTC)
Factory = Callable[[], Any]


def task(task_version_id: UUID | None = None) -> TaskVersion:
    return TaskVersion(
        task_version_id=task_version_id or uuid4(),
        task_id="contract-task",
        version="1",
        instructions_ar="تعليمات",
        instructions_en="Instructions",
        artifact_schema={},
        evaluator_id="evaluator",
        evaluator_version="1",
        pass_threshold=80,
        skill_mappings=[],
        content_hash="a" * 64,
    )


def outcome(submission_id: UUID, task_version_id: UUID) -> SubmissionOutcome:
    return SubmissionOutcome(
        submission_id=submission_id,
        attempt_id=uuid4(),
        attempt_number=1,
        evaluation=EvaluationResult(
            evaluator_id="evaluator",
            evaluator_version="1",
            task_version_id=task_version_id,
            passed=True,
            score=100,
            checks=[],
            errors=[],
            summary_ar="ok",
            summary_en="ok",
            duration_ms=1,
        ),
        feedback=FeedbackResult(
            feedback_text="ok",
            language="en",
            persona_id="tarek",
            prompt_version="tarek-feedback@1",
            provider="test",
            model=None,
            used_fallback=True,
            duration_ms=1,
        ),
        learner_status=LearnerStatus.TASK_COMPLETED,
        task_status=TaskStatus.COMPLETED,
        skills=[],
    )


async def seed(factory: Factory) -> tuple[Learner, TaskVersion, Artifact]:
    learner = Learner(
        learner_id=uuid4(),
        display_name="Contract learner",
        preferred_language="en",
        status=LearnerStatus.ONBOARDING,
        created_at=NOW,
        updated_at=NOW,
    )
    version = task()
    content = b"contract"
    artifact = Artifact(
        artifact_id=uuid4(),
        learner_id=learner.learner_id,
        filename="work.txt",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )
    async with factory() as uow:
        await uow.learners.add(learner)
        await uow.tasks.add(version)
        await uow.artifacts.put(artifact, content)
        await uow.commit()
    return learner, version, artifact


async def assert_reservation_and_finalization(factory: Factory) -> None:
    learner, version, artifact = await seed(factory)
    async with factory() as uow:
        reservation = await uow.submissions.reserve(
            learner.learner_id,
            version.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "contract-key",
            "a" * 64,
            60,
            "worker-a",
        )
        active = await uow.submissions.reserve(
            learner.learner_id,
            version.task_version_id,
            artifact.artifact_id,
            Channel.TELEGRAM,
            "contract-key",
            "a" * 64,
            120,
            "worker-b",
        )
        assert active.submission_id == reservation.submission_id
        assert active.lease_owner == "worker-a"
        with pytest.raises(IdempotencyConflict):
            await uow.submissions.reserve(
                learner.learner_id,
                version.task_version_id,
                artifact.artifact_id,
                Channel.WEB,
                "contract-key",
                "b" * 64,
                60,
                "worker-b",
            )
        await uow.submissions.finalize(
            reservation.reservation_id,
            reservation.version,
            "worker-a",
            outcome(reservation.submission_id, version.task_version_id),
        )
        await uow.commit()

    async with factory() as uow:
        replay = await uow.submissions.get_reservation(learner.learner_id, "contract-key")
        assert replay is not None
        assert replay.status == SubmissionStatus.COMPLETED
        assert replay.outcome is not None
        assert replay.outcome.submission_id == reservation.submission_id


async def assert_progress_rollback_and_cas(factory: Factory) -> None:
    learner, _, _ = await seed(factory)
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner.learner_id)
        assert progress is None
        with pytest.raises(OptimisticConflict):
            await uow.learners.save_progress(
                learner_progress(learner.learner_id, version=2), expected_version=1
            )
        await uow.rollback()


def learner_progress(learner_id: UUID, *, version: int) -> Any:
    # Kept local so this helper exercises the public repository method without
    # coupling adapter tests to implementation-specific state.
    from yom_awel.domain.entities import LearnerProgress

    return LearnerProgress(
        learner_id=learner_id,
        current_status=LearnerStatus.ONBOARDING,
        version=version,
        updated_at=NOW,
    )
