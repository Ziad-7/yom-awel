from datetime import UTC, datetime
from uuid import uuid4

import pytest

from yom_awel.application.outcome_lookup import GetSubmissionOutcome
from yom_awel.domain.contracts import (
    EvaluationResult,
    FeedbackResult,
    SubmissionOutcome,
    TaskStatus,
)
from yom_awel.domain.entities import Learner, SubmissionReservation
from yom_awel.domain.enums import LearnerStatus, SubmissionStatus
from yom_awel.persistence.memory import MemoryUnitOfWorkFactory


@pytest.mark.asyncio
async def test_get_submission_outcome():
    uow_factory = MemoryUnitOfWorkFactory()
    learner_id = uuid4()
    key = "key1"
    sub_id = uuid4()
    attempt_id = uuid4()

    async with uow_factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="L1",
                preferred_language="en",
                status=LearnerStatus.IN_TASK,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )

        eval_result = EvaluationResult(
            evaluator_id="e",
            evaluator_version="1",
            task_version_id=uuid4(),
            passed=True,
            score=100,
            checks=[],
            errors=[],
            summary_ar="ar",
            summary_en="en",
            duration_ms=10,
        )
        fb_result = FeedbackResult(
            feedback_text="fb",
            language="en",
            persona_id="t",
            prompt_version="1",
            provider="sys",
            model=None,
            used_fallback=False,
            duration_ms=10,
        )

        outcome = SubmissionOutcome(
            submission_id=sub_id,
            attempt_id=attempt_id,
            attempt_number=1,
            evaluation=eval_result,
            feedback=fb_result,
            learner_status=LearnerStatus.TASK_COMPLETED,
            task_status=TaskStatus.COMPLETED,
            skills=[],
        )

        # We manually add reservation
        reservation = SubmissionReservation(
            reservation_id=uuid4(),
            submission_id=sub_id,
            learner_id=learner_id,
            task_version_id=uuid4(),
            idempotency_key=key,
            request_fingerprint="fingerprint",
            status=SubmissionStatus.COMPLETED,
            version=1,
            lease_expires_at=datetime.now(UTC),
            created_at=datetime.now(UTC),
            outcome=outcome,
        )
        uow._database._state.reservation_keys[(learner_id, key)] = reservation.reservation_id
        uow._database._state.reservations[reservation.reservation_id] = reservation

    get_outcome = GetSubmissionOutcome(uow_factory)
    res = await get_outcome.execute(learner_id, key)
    assert res.submission_id == sub_id
    assert res.learner_status == LearnerStatus.TASK_COMPLETED
