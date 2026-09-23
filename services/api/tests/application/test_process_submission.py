import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from yom_awel.application.commands import ProcessSubmissionCommand
from yom_awel.application.models import ProcessingState
from yom_awel.application.submissions import ProcessSubmission
from yom_awel.domain.contracts import (
    EvaluationCheck,
    EvaluationResult,
    FeedbackResult,
    SkillMapping,
    SubmissionOutcome,
)
from yom_awel.domain.entities import Artifact, Learner, LearnerProgress, TaskVersion
from yom_awel.domain.enums import Channel, LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.persistence.memory import MemoryUnitOfWorkFactory, _Artifacts

ARTIFACT_CONTENT = b"order_id\n1\n"


class FakeClock:
    def __init__(self):
        self._now = datetime(2026, 9, 21, 10, 0, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: int):
        self._now += timedelta(seconds=seconds)


class FakeIDGenerator:
    def generate(self) -> uuid4:
        return uuid4()


class FakeEvaluator:
    def __init__(self):
        self.call_count = 0
        self.result = None
        self.exception = None
        self.started: asyncio.Event | None = None
        self.release: asyncio.Event | None = None
        self.received_content: bytes | None = None

    async def evaluate(self, task_version, artifact, content):
        self.call_count += 1
        self.received_content = content
        if self.started:
            self.started.set()
        if self.release:
            await self.release.wait()
        if self.exception:
            raise self.exception
        return self.result


class FakeFeedback:
    def __init__(self):
        self.call_count = 0
        self.result = None
        self.exception = None

    async def generate(self, evaluation, language, learner_note=None):
        self.call_count += 1
        if self.exception:
            raise self.exception
        return self.result


@pytest.fixture
def base_setup():
    clock = FakeClock()
    uow_factory = MemoryUnitOfWorkFactory(clock=clock)
    evaluator = FakeEvaluator()
    feedback = FakeFeedback()
    id_gen = FakeIDGenerator()
    return uow_factory, evaluator, feedback, clock, id_gen


async def seed_data(base_setup):
    uow_factory, evaluator, feedback, clock, id_gen = base_setup
    learner_id, task_id, artifact_id = uuid4(), uuid4(), uuid4()
    content_hash = hashlib.sha256(ARTIFACT_CONTENT).hexdigest()

    async with uow_factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="test",
                preferred_language="en",
                status=LearnerStatus.IN_TASK,
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        )
        await uow.tasks.add(
            TaskVersion(
                task_version_id=task_id,
                task_id="t1",
                version="1",
                instructions_ar="a",
                instructions_en="e",
                artifact_schema={},
                evaluator_id="e1",
                evaluator_version="1",
                pass_threshold=50,
                skill_mappings=[SkillMapping(skill_id="s1", check_id="c1", weight=10)],
                content_hash="a" * 64,
            )
        )
        await uow.artifacts.put(
            Artifact(
                artifact_id=artifact_id,
                learner_id=learner_id,
                filename="a.csv",
                size_bytes=len(ARTIFACT_CONTENT),
                sha256=content_hash,
            ),
            ARTIFACT_CONTENT,
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id,
                current_status=LearnerStatus.IN_TASK,
                version=1,
                updated_at=clock.now(),
            ),
            expected_version=0,
        )
        await uow.commit()

    cmd = ProcessSubmissionCommand(
        learner_id=learner_id,
        task_version_id=task_id,
        artifact_id=artifact_id,
        artifact_sha256=content_hash,
        channel=Channel.WEB,
        idempotency_key="key1",
    )
    return cmd, uow_factory, evaluator, feedback, clock, id_gen


@pytest.mark.asyncio
async def test_concurrent_same_key(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)

    # Explicitly signal entry into external evaluation and hold it there.
    # This makes the reservation race deterministic without timing sleeps.
    evaluator.started = asyncio.Event()
    evaluator.release = asyncio.Event()

    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[
            EvaluationCheck(
                check_id="c1",
                passed=True,
                weight=10,
                detail_ar="ت",
                detail_en="d",
                diagnostic_code="c1",
            )
        ],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )
    feedback.result = FeedbackResult(
        feedback_text="fb",
        language="en",
        persona_id="tarek",
        prompt_version="1",
        provider="sys",
        model=None,
        used_fallback=False,
        duration_ms=10,
    )

    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    # First request starts and must reach the evaluator before the duplicate
    # request is dispatched.
    task1 = asyncio.create_task(process.execute(cmd, "owner1"))
    await evaluator.started.wait()

    # Start second request while first is in evaluator
    task2 = asyncio.create_task(process.execute(cmd, "owner2"))

    # Let second request finish (it should immediately return ProcessingState)
    res2 = await task2
    assert isinstance(res2, ProcessingState)
    from yom_awel.domain.enums import SubmissionStatus

    assert res2.status == SubmissionStatus.RECEIVED
    assert res2.retry_after_seconds == 300

    # Now let first request finish.
    evaluator.release.set()
    res1 = await task1
    assert isinstance(res1, SubmissionOutcome)
    assert res2.submission_id == res1.submission_id

    assert evaluator.call_count == 1
    assert evaluator.received_content == ARTIFACT_CONTENT
    assert feedback.call_count == 1

    async with uow_factory() as uow:
        attempts = await uow.attempts.list_for_task(cmd.learner_id, cmd.task_version_id)
        assert len(attempts) == 1
        attempt = attempts[0]
        assert await uow.evaluations.get(attempt.evaluation_id) is not None
        assert await uow.feedback.get(attempt.feedback_id) is not None
        assert len(await uow.skills.list_evidence(cmd.learner_id)) == 1
        assert len(await uow.outbox.pending()) == 1
        progress = await uow.learners.get_progress(cmd.learner_id)
        learner = await uow.learners.get(cmd.learner_id)
        assert progress is not None
        assert learner is not None
        assert learner.status == progress.current_status
        assert progress.current_status == LearnerStatus.TASK_COMPLETED
        # Only the winning finalization advances progress; the competing
        # request did not advance it again.
        assert progress.version == 2


@pytest.mark.asyncio
async def test_committed_submission_survives_post_commit_cleanup_failure(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[
            EvaluationCheck(
                check_id="c1",
                passed=True,
                weight=10,
                detail_ar="ت",
                detail_en="d",
                diagnostic_code="c1",
            )
        ],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=1,
    )
    feedback.result = FeedbackResult(
        feedback_text="fb",
        language="en",
        persona_id="tarek",
        prompt_version="1",
        provider="sys",
        model=None,
        used_fallback=False,
        duration_ms=1,
    )

    async def cleanup_failure(now):
        raise RuntimeError("retention provider failure")

    result = await ProcessSubmission(
        uow_factory, evaluator, feedback, clock, id_gen, cleanup_failure
    ).execute(cmd, "owner")
    assert isinstance(result, SubmissionOutcome)
    async with uow_factory() as uow:
        reservation = await uow.submissions.get_reservation(cmd.learner_id, cmd.idempotency_key)
        assert reservation is not None and reservation.outcome == result


@pytest.mark.asyncio
async def test_concurrent_different_keys_same_task_only_one_advances(base_setup):
    """Two successful keys for one learner/task cannot both commit progression."""

    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    evaluator.started = asyncio.Event()
    evaluator.release = asyncio.Event()
    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[
            EvaluationCheck(
                check_id="c1",
                passed=True,
                weight=10,
                detail_ar="ت",
                detail_en="d",
                diagnostic_code="c1",
            )
        ],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )
    feedback.result = FeedbackResult(
        feedback_text="fb",
        language="en",
        persona_id="tarek",
        prompt_version="1",
        provider="sys",
        model=None,
        used_fallback=False,
        duration_ms=10,
    )
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)
    second = cmd.model_copy(update={"idempotency_key": "key2"})

    first_task = asyncio.create_task(process.execute(cmd, "owner1"))
    await evaluator.started.wait()
    second_task = asyncio.create_task(process.execute(second, "owner2"))
    evaluator.release.set()
    results = await asyncio.gather(first_task, second_task, return_exceptions=True)

    assert sum(isinstance(result, SubmissionOutcome) for result in results) == 1
    assert sum(isinstance(result, DomainError) for result in results) == 1
    async with uow_factory() as uow:
        progress = await uow.learners.get_progress(cmd.learner_id)
        assert progress is not None
        assert progress.current_status == LearnerStatus.TASK_COMPLETED
        assert progress.version == 2
        assert len(await uow.attempts.list_for_task(cmd.learner_id, cmd.task_version_id)) == 1
        assert len(await uow.skills.list_evidence(cmd.learner_id)) == 1
        assert len(await uow.outbox.pending()) == 1


@pytest.mark.asyncio
async def test_duplicate_completed(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )
    feedback.result = FeedbackResult(
        feedback_text="fb",
        language="en",
        persona_id="t",
        prompt_version="1",
        provider="sys",
        model=None,
        used_fallback=False,
        duration_ms=10,
    )

    res1 = await process.execute(cmd, "owner1")
    assert isinstance(res1, SubmissionOutcome)

    evaluator.call_count = 0
    feedback.call_count = 0
    res2 = await process.execute(cmd, "owner2")
    assert isinstance(res2, SubmissionOutcome)
    assert evaluator.call_count == 0


@pytest.mark.asyncio
async def test_fallback_authority(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )
    feedback.exception = TimeoutError("Provider offline")

    res = await process.execute(cmd, "owner1")
    assert isinstance(res, SubmissionOutcome)
    assert res.feedback.used_fallback is True
    assert res.feedback.persona_id == "tarek"
    assert res.feedback.prompt_version == "tarek-feedback@1"
    assert res.feedback.provider == "deterministic"


@pytest.mark.asyncio
async def test_evaluation_failure_releases_reservation(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    evaluator.exception = ValueError("secret provider payload: Evaluation crash")

    with pytest.raises(DomainError) as exc:
        await process.execute(cmd, "owner1")
    assert exc.value.code == "evaluation_failed"
    assert exc.value.message == "We could not evaluate the file right now. Please try again."
    assert "secret provider payload" not in str(exc.value)

    async with uow_factory() as uow:
        res = await uow.submissions.get_reservation(cmd.learner_id, cmd.idempotency_key)
        assert res.lease_expires_at <= clock.now()
        assert await uow.attempts.list_for_task(cmd.learner_id, cmd.task_version_id) == []
        assert await uow.skills.list_evidence(cmd.learner_id) == []
        assert await uow.outbox.pending() == []
        progress = await uow.learners.get_progress(cmd.learner_id)
        assert progress is not None
        assert progress.current_status == LearnerStatus.IN_TASK
        assert progress.version == 1


@pytest.mark.asyncio
async def test_finalization_failure_rolls_back(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )
    feedback.result = FeedbackResult(
        feedback_text="fb",
        language="en",
        persona_id="t",
        prompt_version="1",
        provider="sys",
        model=None,
        used_fallback=False,
        duration_ms=10,
    )

    from yom_awel.domain.errors import FinalizationConflict
    from yom_awel.persistence.memory import _Submissions

    original_finalize = _Submissions.finalize

    async def failing_finalize(*args, **kwargs):
        raise FinalizationConflict("mock")

    _Submissions.finalize = failing_finalize

    try:
        with pytest.raises(DomainError) as exc:
            await process.execute(cmd, "owner1")
        assert exc.value.code == "finalization_conflict"

        async with uow_factory() as uow:
            attempts = await uow.attempts.list_for_task(cmd.learner_id, cmd.task_version_id)
            assert len(attempts) == 0
            assert await uow.skills.list_evidence(cmd.learner_id) == []
            assert await uow.outbox.pending() == []
            progress = await uow.learners.get_progress(cmd.learner_id)
            assert progress is not None
            assert progress.current_status == LearnerStatus.IN_TASK
            assert progress.version == 1
    finally:
        _Submissions.finalize = original_finalize


@pytest.mark.asyncio
async def test_failed_evaluation_no_skill_evidence(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=False,
        score=10,
        checks=[
            EvaluationCheck(
                check_id="c1",
                passed=True,
                weight=10,
                detail_ar="ت",
                detail_en="d",
                diagnostic_code="c1",
            )
        ],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )
    feedback.result = FeedbackResult(
        feedback_text="fb",
        language="en",
        persona_id="t",
        prompt_version="1",
        provider="sys",
        model=None,
        used_fallback=False,
        duration_ms=10,
    )

    res = await process.execute(cmd, "owner1")
    assert isinstance(res, SubmissionOutcome)

    async with uow_factory() as uow:
        evidence = await uow.skills.list_evidence(cmd.learner_id)
        assert len(evidence) == 0


@pytest.mark.asyncio
async def test_missing_artifact_content_releases_reservation_without_evaluating(
    base_setup, monkeypatch
):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    async def content_purged(self, artifact_id, learner_id):
        return None

    monkeypatch.setattr(_Artifacts, "download", content_purged)

    with pytest.raises(DomainError) as exc:
        await process.execute(cmd, "owner1")
    assert exc.value.code == "artifact_not_found"
    assert evaluator.call_count == 0

    async with uow_factory() as uow:
        res = await uow.submissions.get_reservation(cmd.learner_id, cmd.idempotency_key)
        assert res.lease_expires_at <= clock.now()


@pytest.mark.asyncio
async def test_artifact_ownership_hash_validation(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    cmd_invalid = cmd.model_copy(update={"artifact_sha256": "wrong_hash"})

    with pytest.raises(DomainError) as exc:
        await process.execute(cmd_invalid, "owner1")
    assert exc.value.code == "artifact_hash_mismatch"

    # Ensure no reservation created
    async with uow_factory() as uow:
        res = await uow.submissions.get_reservation(cmd.learner_id, cmd.idempotency_key)
        assert res is None


@pytest.mark.asyncio
async def test_task_must_match_learner_current_task_before_reservation(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    async with uow_factory() as uow:
        progress = await uow.learners.get_progress(cmd.learner_id)
        assert progress is not None
        await uow.learners.save_progress(
            progress.model_copy(update={"current_task_id": "another-task", "version": 2}),
            expected_version=1,
        )
        await uow.commit()

    with pytest.raises(DomainError) as exc:
        await ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen).execute(
            cmd, "owner"
        )
    assert exc.value.code == "task_not_current"
    assert evaluator.call_count == 0
    async with uow_factory() as uow:
        assert await uow.submissions.get_reservation(cmd.learner_id, cmd.idempotency_key) is None


@pytest.mark.asyncio
async def test_evaluator_task_version_mismatch(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    evaluator.result = EvaluationResult(
        evaluator_id="e2",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )

    with pytest.raises(DomainError) as exc:
        await process.execute(cmd, "owner1")
    assert exc.value.code == "invalid_evaluator"
    async with uow_factory() as uow:
        reservation = await uow.submissions.get_reservation(cmd.learner_id, cmd.idempotency_key)
        assert reservation is not None
        assert reservation.lease_expires_at <= clock.now()
        assert await uow.attempts.list_for_task(cmd.learner_id, cmd.task_version_id) == []


@pytest.mark.asyncio
async def test_different_fingerprint_conflict(base_setup):
    cmd, uow_factory, evaluator, feedback, clock, id_gen = await seed_data(base_setup)
    process = ProcessSubmission(uow_factory, evaluator, feedback, clock, id_gen)

    evaluator.result = EvaluationResult(
        evaluator_id="e1",
        evaluator_version="1",
        task_version_id=cmd.task_version_id,
        passed=True,
        score=100,
        checks=[],
        errors=[],
        summary_ar="ar",
        summary_en="en",
        duration_ms=10,
    )
    feedback.result = FeedbackResult(
        feedback_text="fb",
        language="en",
        persona_id="t",
        prompt_version="1",
        provider="sys",
        model=None,
        used_fallback=False,
        duration_ms=10,
    )

    await process.execute(cmd, "owner1")

    cmd2 = cmd.model_copy(update={"channel_event_id": "different"})
    with pytest.raises(DomainError) as exc:
        await process.execute(cmd2, "owner2")
    assert exc.value.code == "idempotency_conflict"
