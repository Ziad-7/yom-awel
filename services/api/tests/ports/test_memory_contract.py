from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID, uuid4

import pytest

from yom_awel.domain.contracts import (
    EvaluationResult,
    FeedbackResult,
    SkillSummary,
    SubmissionOutcome,
    TaskVersion,
)
from yom_awel.domain.entities import (
    Artifact,
    Attempt,
    Learner,
    LearnerProgress,
    OutboxEvent,
    SkillEvidence,
)
from yom_awel.domain.enums import Channel, LearnerStatus, SubmissionStatus, TaskStatus
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
from yom_awel.persistence.memory import (
    FrozenClock,
    MemoryDatabase,
    MemoryUnitOfWork,
    MemoryUnitOfWorkFactory,
)
from yom_awel.ports.unit_of_work import UnitOfWork, UnitOfWorkFactory

NOW = datetime(2026, 9, 21, tzinfo=UTC)


def make_learner(learner_id: UUID | None = None) -> Learner:
    return Learner(
        learner_id=learner_id or uuid4(),
        display_name="A learner",
        preferred_language="en",
        status=LearnerStatus.ONBOARDING,
        created_at=NOW,
        updated_at=NOW,
    )


def make_task(task_version_id: UUID | None = None, task_id: str = "task") -> TaskVersion:
    return TaskVersion(
        task_version_id=task_version_id or uuid4(),
        task_id=task_id,
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


def make_artifact(learner_id: UUID, content: bytes = b"hello") -> Artifact:
    return Artifact(
        artifact_id=uuid4(),
        learner_id=learner_id,
        filename="work.csv",
        content_type="text/csv",
        size_bytes=len(content),
        sha256=sha256(content).hexdigest(),
    )


async def seed(factory: UnitOfWorkFactory) -> tuple[Learner, TaskVersion, Artifact]:
    item = make_learner()
    task = make_task()
    artifact = make_artifact(item.learner_id)
    async with factory() as uow:
        await uow.learners.add(item)
        await uow.tasks.add(task)
        await uow.artifacts.put(artifact, b"hello")
        await uow.commit()
    return item, task, artifact


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
            persona_id="persona",
            prompt_version="persona@1",
            provider="test",
            model=None,
            used_fallback=True,
            duration_ms=1,
        ),
        learner_status=LearnerStatus.TASK_COMPLETED,
        task_status=TaskStatus.COMPLETED,
        skills=[SkillSummary(skill_id="skill", score=100)],
    )


@pytest.fixture
def factory() -> MemoryUnitOfWorkFactory:
    return MemoryUnitOfWorkFactory(clock=FrozenClock(NOW))


@pytest.mark.asyncio
async def test_factory_shares_committed_state_but_isolates_uncommitted_changes(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    item = make_learner()
    first = factory()
    second = factory()
    async with first:
        await first.learners.add(item)
        async with second:
            assert await second.learners.get(item.learner_id) is None
        await first.commit()
    async with factory() as fresh:
        assert await fresh.learners.get(item.learner_id) == item


@pytest.mark.asyncio
async def test_rollback_exception_normal_exit_and_active_reuse(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    item = make_learner()
    async with factory() as uow:
        await uow.learners.add(item)
        await uow.rollback()
    with pytest.raises(ValueError):
        async with factory() as uow:
            await uow.learners.add(item)
            raise ValueError("discard")
    uow = factory()
    async with uow:
        with pytest.raises(TransactionReuse):
            await uow.__aenter__()
    async with factory() as fresh:
        assert await fresh.learners.get(item.learner_id) is None


@pytest.mark.asyncio
async def test_clean_async_context_exit_rolls_back(factory: MemoryUnitOfWorkFactory) -> None:
    item = make_learner()
    async with factory() as uow:
        await uow.learners.add(item)

    async with factory() as fresh:
        assert await fresh.learners.get(item.learner_id) is None


@pytest.mark.asyncio
async def test_stale_commit_cas_does_not_publish_partial_state(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    first = factory()
    second = factory()
    async with first, second:
        first_item = make_learner()
        second_item = make_learner()
        await first.learners.add(first_item)
        await second.learners.add(second_item)
        await first.commit()
        with pytest.raises(OptimisticConflict):
            await second.commit()
    async with factory() as fresh:
        assert await fresh.learners.get(first_item.learner_id) == first_item
        assert await fresh.learners.get(second_item.learner_id) is None


@pytest.mark.asyncio
async def test_learner_identity_uniqueness_scope_and_progress_cas(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    first, _, _ = await seed(factory)
    second = make_learner()
    progress_v1 = LearnerProgress(
        learner_id=first.learner_id,
        current_status=LearnerStatus.ONBOARDING,
        version=1,
        updated_at=NOW,
    )
    async with factory() as uow:
        await uow.learners.add(second)
        await uow.learners.add_external_identity(first.learner_id, "telegram", "42")
        with pytest.raises(UniqueConstraintViolation):
            await uow.learners.add_external_identity(second.learner_id, "telegram", "42")
        with pytest.raises(OptimisticConflict):
            await uow.learners.save_progress(progress_v1, expected_version=1)
        await uow.learners.save_progress(progress_v1, expected_version=0)
        with pytest.raises(OptimisticConflict):
            await uow.learners.save_progress(progress_v1, expected_version=1)
        with pytest.raises(OptimisticConflict):
            await uow.learners.save_progress(
                progress_v1.model_copy(update={"version": 3}), expected_version=1
            )
        progress_v2 = progress_v1.model_copy(
            update={"version": 2, "current_status": LearnerStatus.READY}
        )
        await uow.learners.save_progress(progress_v2, expected_version=1)
        identity_learner = await uow.learners.get_by_external_identity("telegram", "42")
        assert identity_learner is not None
        assert identity_learner.learner_id == first.learner_id
        assert identity_learner.status == LearnerStatus.READY
        await uow.commit()


@pytest.mark.asyncio
async def test_task_version_uniqueness_and_get(factory: MemoryUnitOfWorkFactory) -> None:
    _, task, _ = await seed(factory)
    async with factory() as uow:
        assert await uow.tasks.get(task.task_version_id) == task
        with pytest.raises(UniqueConstraintViolation):
            await uow.tasks.add(make_task(task_id=task.task_id))


@pytest.mark.asyncio
async def test_reservation_identity_duplicates_reclaim_and_finalization(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    item, task, artifact = await seed(factory)
    async with factory() as uow:
        first = await uow.submissions.reserve(
            item.learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            10,
            "owner-a",
        )
        active = await uow.submissions.reserve(
            item.learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.TELEGRAM,
            "key",
            "fp",
            99,
            "owner-b",
        )
        assert active.submission_id == first.submission_id
        assert active.version == first.version and active.lease_owner == "owner-a"
        with pytest.raises(IdempotencyConflict):
            await uow.submissions.reserve(
                item.learner_id,
                task.task_version_id,
                artifact.artifact_id,
                Channel.WEB,
                "key",
                "different",
                10,
                "owner-b",
            )
        await uow.commit()
    clock = factory.database.clock
    assert isinstance(clock, FrozenClock)
    clock.advance(seconds=11)
    async with factory() as uow:
        reclaimed = await uow.submissions.reserve(
            item.learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            10,
            "owner-b",
        )
        assert (
            reclaimed.submission_id == first.submission_id
            and reclaimed.version == first.version + 1
        )
        with pytest.raises(ReservationOwnerConflict):
            await uow.submissions.finalize(
                reclaimed.reservation_id,
                reclaimed.version,
                "owner-a",
                outcome(reclaimed.submission_id, task.task_version_id),
            )
        await uow.commit()
    clock.advance(seconds=11)
    async with factory() as uow:
        with pytest.raises(ReservationExpired):
            await uow.submissions.finalize(
                reclaimed.reservation_id,
                reclaimed.version,
                "owner-b",
                outcome(reclaimed.submission_id, task.task_version_id),
            )
    clock.advance(seconds=-11)
    async with factory() as uow:
        await uow.submissions.finalize(
            reclaimed.reservation_id,
            reclaimed.version,
            "owner-b",
            outcome(reclaimed.submission_id, task.task_version_id),
        )
        completed = await uow.submissions.get_reservation(item.learner_id, "key")
        assert completed is not None and completed.status == SubmissionStatus.COMPLETED
        with pytest.raises(FinalizationConflict):
            await uow.submissions.finalize(
                reclaimed.reservation_id,
                reclaimed.version + 1,
                "owner-b",
                outcome(reclaimed.submission_id, task.task_version_id),
            )


@pytest.mark.asyncio
async def test_reservation_rejects_foreign_references_and_mismatched_outcome(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    item, task, artifact = await seed(factory)
    other = make_learner()
    async with factory() as uow:
        await uow.learners.add(other)
        with pytest.raises(LearnerScopeViolation):
            await uow.submissions.reserve(
                other.learner_id,
                task.task_version_id,
                artifact.artifact_id,
                Channel.WEB,
                "key",
                "fp",
                10,
                "owner",
            )
        reservation = await uow.submissions.reserve(
            item.learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            10,
            "owner",
        )
        with pytest.raises(SubmissionMismatch):
            await uow.submissions.finalize(
                reservation.reservation_id,
                reservation.version,
                "owner",
                outcome(reservation.submission_id, uuid4()),
            )


@pytest.mark.asyncio
async def test_completed_duplicate_replays_original_reservation_and_outcome(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    item, task, artifact = await seed(factory)
    async with factory() as uow:
        reservation = await uow.submissions.reserve(
            item.learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "completed-key",
            "completed-fingerprint",
            60,
            "original-owner",
        )
        original_outcome = outcome(reservation.submission_id, task.task_version_id)
        await uow.submissions.finalize(
            reservation.reservation_id,
            reservation.version,
            "original-owner",
            original_outcome,
        )
        await uow.commit()

    async with factory() as fresh:
        replay = await fresh.submissions.reserve(
            item.learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "completed-key",
            "completed-fingerprint",
            999,
            "replay-owner",
        )
        assert replay.status == SubmissionStatus.COMPLETED
        assert replay.reservation_id == reservation.reservation_id
        assert replay.submission_id == reservation.submission_id
        assert replay.outcome == original_outcome
        assert replay.version == reservation.version + 1
        assert replay.lease_expires_at == reservation.lease_expires_at
        assert replay.lease_owner == reservation.lease_owner


@pytest.mark.asyncio
async def test_attempts_and_skill_evidence_enforce_audit_scope_order_and_uniqueness(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    item, task, artifact = await seed(factory)
    async with factory() as uow:
        reservation = await uow.submissions.reserve(
            item.learner_id,
            task.task_version_id,
            artifact.artifact_id,
            Channel.WEB,
            "key",
            "fp",
            60,
            "owner",
        )
        from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
        from yom_awel.domain.entities import EvaluationRecord, FeedbackRecord

        eval_id = uuid4()
        fb_id = uuid4()
        await uow.evaluations.add(
            EvaluationRecord(
                evaluation_id=eval_id,
                result=EvaluationResult(
                    evaluator_id="e1",
                    evaluator_version="1",
                    task_version_id=task.task_version_id,
                    passed=True,
                    score=100,
                    checks=[],
                    errors=[],
                    summary_ar="ar",
                    summary_en="en",
                    duration_ms=10,
                ),
                recorded_at=NOW,
            )
        )
        await uow.feedback.add(
            FeedbackRecord(
                feedback_id=fb_id,
                result=FeedbackResult(
                    feedback_text="fb",
                    language="en",
                    persona_id="t",
                    prompt_version="1",
                    provider="sys",
                    model=None,
                    used_fallback=False,
                    duration_ms=10,
                ),
                recorded_at=NOW,
            )
        )
        attempt = Attempt(
            attempt_id=uuid4(),
            learner_id=item.learner_id,
            submission_id=reservation.submission_id,
            task_version_id=task.task_version_id,
            attempt_number=1,
            evaluation_id=eval_id,
            feedback_id=fb_id,
            evaluator_id="evaluator",
            evaluator_version="1",
            prompt_version="persona@1",
            started_at=NOW,
        )
        await uow.attempts.add(attempt)
        with pytest.raises(UniqueConstraintViolation):
            await uow.attempts.add(attempt.model_copy(update={"attempt_id": uuid4()}))
        with pytest.raises(OptimisticConflict):
            await uow.attempts.add(
                attempt.model_copy(update={"attempt_id": uuid4(), "attempt_number": 3})
            )
        evidence = SkillEvidence(
            evidence_id=uuid4(),
            learner_id=item.learner_id,
            attempt_id=attempt.attempt_id,
            task_version_id=task.task_version_id,
            skill_id="skill",
            check_id="check",
            awarded_points=20,
            available_points=20,
            recorded_at=NOW,
        )
        await uow.skills.add_evidence(evidence)
        with pytest.raises(UniqueConstraintViolation):
            await uow.skills.add_evidence(evidence.model_copy(update={"evidence_id": uuid4()}))
        assert (await uow.skills.get_profile(item.learner_id)).skills == [
            SkillSummary(skill_id="skill", score=20)
        ]


@pytest.mark.asyncio
async def test_outbox_order_limit_publish_and_missing_id(factory: MemoryUnitOfWorkFactory) -> None:
    async with factory() as uow:
        events = [
            OutboxEvent(
                event_id=uuid4(), event_type="b", aggregate_id=uuid4(), payload={}, created_at=NOW
            ),
            OutboxEvent(
                event_id=uuid4(),
                event_type="a",
                aggregate_id=uuid4(),
                payload={},
                created_at=NOW + timedelta(seconds=1),
            ),
        ]
        for event in events:
            await uow.outbox.add(event)
        assert [event.event_type for event in await uow.outbox.pending(1)] == ["b"]
        await uow.outbox.mark_published(events[0].event_id)
        assert [event.event_type for event in await uow.outbox.pending()] == ["a"]
        with pytest.raises(NotFound):
            await uow.outbox.mark_published(uuid4())


@pytest.mark.asyncio
async def test_artifact_round_trip_scope_hash_size_uniqueness_and_delete(
    factory: MemoryUnitOfWorkFactory,
) -> None:
    item, _, _ = await seed(factory)
    content = b"bytes"
    artifact = make_artifact(item.learner_id, content)
    async with factory() as uow:
        await uow.artifacts.put(artifact, content)
        assert await uow.artifacts.download(artifact.artifact_id, item.learner_id) == content
        assert await uow.artifacts.download(artifact.artifact_id, uuid4()) is None
        with pytest.raises(ValueError):
            await uow.artifacts.put(make_artifact(item.learner_id), b"wrong")
        with pytest.raises(UniqueConstraintViolation):
            await uow.artifacts.put(artifact, content)
        with pytest.raises(LearnerScopeViolation):
            await uow.artifacts.delete(artifact.artifact_id, uuid4())
        assert await uow.artifacts.get(artifact.artifact_id, item.learner_id) is not None
        await uow.artifacts.delete(artifact.artifact_id, item.learner_id)
        assert await uow.artifacts.get(artifact.artifact_id, item.learner_id) is None


def test_factory_is_typed_as_unit_of_work_factory() -> None:
    factory: Callable[[], UnitOfWork] = MemoryUnitOfWorkFactory(MemoryDatabase())
    assert isinstance(factory(), MemoryUnitOfWork)


@pytest.mark.asyncio
async def test_evaluation_repository(factory):
    async with factory() as uow:
        eval_id = uuid4()
        from yom_awel.domain.contracts import EvaluationResult
        from yom_awel.domain.entities import EvaluationRecord

        result = EvaluationResult(
            evaluator_id="e1",
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
        record = EvaluationRecord(evaluation_id=eval_id, result=result, recorded_at=NOW)

        await uow.evaluations.add(record)
        fetched = await uow.evaluations.get(eval_id)

        assert fetched is not None
        assert fetched.evaluation_id == eval_id
        assert fetched.result.passed is True


@pytest.mark.asyncio
async def test_feedback_repository(factory):
    async with factory() as uow:
        fb_id = uuid4()
        from yom_awel.domain.contracts import FeedbackResult
        from yom_awel.domain.entities import FeedbackRecord

        result = FeedbackResult(
            feedback_text="fb",
            language="en",
            persona_id="tarek",
            prompt_version="1",
            provider="sys",
            model=None,
            used_fallback=False,
            duration_ms=10,
        )
        record = FeedbackRecord(feedback_id=fb_id, result=result, recorded_at=NOW)

        await uow.feedback.add(record)
        fetched = await uow.feedback.get(fb_id)

        assert fetched is not None
        assert fetched.feedback_id == fb_id
        assert fetched.result.feedback_text == "fb"
