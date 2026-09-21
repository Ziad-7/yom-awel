from uuid import uuid4

import pytest

from yom_awel.domain.contracts import EvaluationResult
from yom_awel.domain.enums import LearnerStatus
from yom_awel.domain.errors import InvalidTransition
from yom_awel.domain.state_machine import evaluate_transition, transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        # Meaningful illegal pairs
        (LearnerStatus.ONBOARDING, LearnerStatus.PROCESSING),
        (LearnerStatus.READY, LearnerStatus.TASK_COMPLETED),
        (LearnerStatus.NEEDS_RETRY, LearnerStatus.PROGRAM_COMPLETED),
        (LearnerStatus.PROGRAM_COMPLETED, LearnerStatus.IN_TASK),
        (LearnerStatus.ONBOARDING, LearnerStatus.TASK_COMPLETED),
        (LearnerStatus.PROCESSING, LearnerStatus.READY),
        (LearnerStatus.TASK_COMPLETED, LearnerStatus.PROCESSING),
    ],
)
def test_invalid_transition_is_rejected(current: LearnerStatus, target: LearnerStatus) -> None:
    with pytest.raises(InvalidTransition) as exc_info:
        transition(current, target)

    assert exc_info.value.code == "invalid_transition"
    assert exc_info.value.details["current"] == current
    assert exc_info.value.details["target"] == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (LearnerStatus.ONBOARDING, LearnerStatus.READY),
        (LearnerStatus.READY, LearnerStatus.IN_TASK),
        (LearnerStatus.IN_TASK, LearnerStatus.PROCESSING),
        (LearnerStatus.PROCESSING, LearnerStatus.NEEDS_RETRY),
        (LearnerStatus.PROCESSING, LearnerStatus.IN_TASK),
        (LearnerStatus.NEEDS_RETRY, LearnerStatus.PROCESSING),
    ],
)
def test_valid_transitions(current: LearnerStatus, target: LearnerStatus) -> None:
    assert transition(current, target) == target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (LearnerStatus.PROCESSING, LearnerStatus.TASK_COMPLETED),
        (LearnerStatus.TASK_COMPLETED, LearnerStatus.PROGRAM_COMPLETED),
    ],
)
def test_completion_transitions_blocked_in_raw_api(
    current: LearnerStatus, target: LearnerStatus
) -> None:
    with pytest.raises(InvalidTransition) as exc_info:
        transition(current, target)
    assert "without deterministic evaluation authority" in str(exc_info.value)
    assert exc_info.value.code == "invalid_transition"
    assert exc_info.value.details["current"] == current
    assert exc_info.value.details["target"] == target


@pytest.fixture
def base_evaluation() -> dict:
    return {
        "evaluator_id": "test",
        "evaluator_version": "1",
        "task_version_id": uuid4(),
        "passed": True,
        "score": 100,
        "checks": [],
        "errors": [],
        "summary_ar": "test",
        "summary_en": "test",
        "duration_ms": 100,
    }


def test_failed_evaluation_produces_needs_retry(base_evaluation: dict) -> None:
    base_evaluation["passed"] = False
    base_evaluation["score"] = 50
    eval_result = EvaluationResult.model_validate(base_evaluation)

    result = evaluate_transition(LearnerStatus.PROCESSING, eval_result)
    assert result == LearnerStatus.NEEDS_RETRY


def test_passed_evaluation_produces_task_completed(base_evaluation: dict) -> None:
    eval_result = EvaluationResult.model_validate(base_evaluation)

    result = evaluate_transition(LearnerStatus.PROCESSING, eval_result)
    assert result == LearnerStatus.TASK_COMPLETED


def test_passed_evaluation_final_task_produces_program_completed(base_evaluation: dict) -> None:
    eval_result = EvaluationResult.model_validate(base_evaluation)

    result = evaluate_transition(LearnerStatus.PROCESSING, eval_result, is_final_task=True)
    assert result == LearnerStatus.PROGRAM_COMPLETED


def test_feedback_fields_not_accepted() -> None:
    # Function signature itself doesn't accept feedback. We can just check it raises TypeError if passed.
    with pytest.raises(TypeError):
        evaluate_transition(LearnerStatus.PROCESSING, None, feedback=True)  # type: ignore
