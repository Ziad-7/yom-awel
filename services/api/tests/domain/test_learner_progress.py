from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from yom_awel.domain.contracts import EvaluationResult
from yom_awel.domain.entities import LearnerProgress
from yom_awel.domain.enums import LearnerStatus


def test_learner_progress_is_immutable() -> None:
    progress = LearnerProgress(
        learner_id=uuid4(),
        current_status=LearnerStatus.ONBOARDING,
        version=1,
        updated_at=datetime.now(UTC),
    )
    with pytest.raises(ValidationError):
        progress.version = 2  # type: ignore


def test_advance_status_increments_version_and_updates() -> None:
    progress = LearnerProgress(
        learner_id=uuid4(),
        current_status=LearnerStatus.ONBOARDING,
        version=1,
        updated_at=datetime.now(UTC),
    )
    new_time = datetime.now(UTC)
    updated = progress.advance_status(LearnerStatus.READY, new_time)

    assert updated is not progress
    assert updated.current_status == LearnerStatus.READY
    assert updated.version == 2
    assert updated.updated_at == new_time


def test_advance_to_completion_requires_evaluation() -> None:
    progress = LearnerProgress(
        learner_id=uuid4(),
        current_status=LearnerStatus.PROCESSING,
        version=1,
        updated_at=datetime.now(UTC),
    )

    with pytest.raises(ValueError, match="Evaluation authority required for completion"):
        progress.advance_status(LearnerStatus.TASK_COMPLETED, datetime.now(UTC))


def test_advance_to_completion_with_passed_evaluation() -> None:
    progress = LearnerProgress(
        learner_id=uuid4(),
        current_status=LearnerStatus.PROCESSING,
        version=1,
        updated_at=datetime.now(UTC),
    )
    evaluation = EvaluationResult(
        evaluator_id="test",
        evaluator_version="1",
        task_version_id=uuid4(),
        passed=True,
        score=100,
        checks=[],
        errors=[],
        summary_ar="test",
        summary_en="test",
        duration_ms=100,
    )

    updated = progress.advance_status(
        LearnerStatus.TASK_COMPLETED, datetime.now(UTC), evaluation=evaluation
    )

    assert updated.current_status == LearnerStatus.TASK_COMPLETED
    assert updated.version == 2


def test_advance_with_failed_evaluation_fails_completion() -> None:
    progress = LearnerProgress(
        learner_id=uuid4(),
        current_status=LearnerStatus.PROCESSING,
        version=1,
        updated_at=datetime.now(UTC),
    )
    evaluation = EvaluationResult(
        evaluator_id="test",
        evaluator_version="1",
        task_version_id=uuid4(),
        passed=False,
        score=0,
        checks=[],
        errors=[],
        summary_ar="test",
        summary_en="test",
        duration_ms=100,
    )

    with pytest.raises(
        ValueError, match="Evaluation resulted in NEEDS_RETRY, expected TASK_COMPLETED"
    ):
        progress.advance_status(
            LearnerStatus.TASK_COMPLETED, datetime.now(UTC), evaluation=evaluation
        )


def test_illegal_transition_raises() -> None:
    progress = LearnerProgress(
        learner_id=uuid4(),
        current_status=LearnerStatus.READY,
        version=1,
        updated_at=datetime.now(UTC),
    )
    from yom_awel.domain.errors import InvalidTransition

    with pytest.raises(InvalidTransition):
        progress.advance_status(LearnerStatus.NEEDS_RETRY, datetime.now(UTC))
