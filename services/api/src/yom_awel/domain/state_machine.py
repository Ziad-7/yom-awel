from yom_awel.domain.contracts import EvaluationResult
from yom_awel.domain.enums import LearnerStatus
from yom_awel.domain.errors import InvalidTransition

ALLOWED_TRANSITIONS = {
    (LearnerStatus.ONBOARDING, LearnerStatus.READY),
    (LearnerStatus.READY, LearnerStatus.IN_TASK),
    (LearnerStatus.IN_TASK, LearnerStatus.PROCESSING),
    (LearnerStatus.PROCESSING, LearnerStatus.NEEDS_RETRY),
    (LearnerStatus.PROCESSING, LearnerStatus.IN_TASK),
    (LearnerStatus.NEEDS_RETRY, LearnerStatus.PROCESSING),
    (LearnerStatus.PROCESSING, LearnerStatus.TASK_COMPLETED),
    (LearnerStatus.TASK_COMPLETED, LearnerStatus.READY),
    (LearnerStatus.TASK_COMPLETED, LearnerStatus.PROGRAM_COMPLETED),
}


def transition(current: LearnerStatus, target: LearnerStatus) -> LearnerStatus:
    if target in (LearnerStatus.TASK_COMPLETED, LearnerStatus.PROGRAM_COMPLETED):
        raise InvalidTransition(
            current=current,
            target=target,
            message=f"Cannot transition to {target} without deterministic evaluation authority",
        )
    if (current, target) not in ALLOWED_TRANSITIONS:
        raise InvalidTransition(current=current, target=target)
    return target


def evaluate_transition(
    current: LearnerStatus, evaluation: EvaluationResult, is_final_task: bool = False
) -> LearnerStatus:
    if not evaluation.passed:
        return transition(current, LearnerStatus.NEEDS_RETRY)

    target = LearnerStatus.TASK_COMPLETED
    if (current, target) not in ALLOWED_TRANSITIONS:
        raise InvalidTransition(current=current, target=target)

    if is_final_task:
        if (target, LearnerStatus.PROGRAM_COMPLETED) not in ALLOWED_TRANSITIONS:
            raise InvalidTransition(current=target, target=LearnerStatus.PROGRAM_COMPLETED)
        return LearnerStatus.PROGRAM_COMPLETED

    return target
