from datetime import UTC, datetime
from uuid import uuid4

import pytest

from yom_awel.application.admin import ResetDemoLearner
from yom_awel.application.commands import CreateUploadCommand, ResetDemoLearnerCommand
from yom_awel.application.profiles import GetSkillsProfile
from yom_awel.application.tasks import CreateArtifactUpload, GetCurrentTask
from yom_awel.domain.entities import Learner, LearnerProgress, SkillEvidence, TaskVersion
from yom_awel.domain.enums import LearnerStatus
from yom_awel.persistence.memory import MemoryUnitOfWorkFactory


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 21, 10, 0, tzinfo=UTC)


class FakeIDGenerator:
    def generate(self):
        return uuid4()


@pytest.mark.asyncio
async def test_get_current_task():
    uow_factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    learner_id = uuid4()
    task_id = uuid4()

    async with uow_factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="L1",
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
                version="2",
                instructions_ar="a",
                instructions_en="e",
                artifact_schema={},
                evaluator_id="e1",
                evaluator_version="1",
                pass_threshold=50,
                skill_mappings=[],
                content_hash="a" * 64,
            )
        )
        current_task_version_id = uuid4()
        await uow.tasks.add(
            TaskVersion(
                task_version_id=current_task_version_id,
                task_id="t1",
                version="10",
                instructions_ar="new",
                instructions_en="new",
                artifact_schema={},
                evaluator_id="e1",
                evaluator_version="1",
                pass_threshold=50,
                skill_mappings=[],
                content_hash="b" * 64,
            )
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id,
                current_status=LearnerStatus.IN_TASK,
                current_task_id="t1",
                version=1,
                updated_at=clock.now(),
            ),
            expected_version=0,
        )
        await uow.commit()

    get_task = GetCurrentTask(uow_factory)
    res = await get_task.execute(learner_id)
    assert res.status == "IN_TASK"
    assert res.task is not None
    assert res.task.task_version_id == current_task_version_id


@pytest.mark.asyncio
async def test_authorize_upload():
    uow_factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    id_gen = FakeIDGenerator()
    learner_id = uuid4()

    async with uow_factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="L1",
                preferred_language="en",
                status=LearnerStatus.IN_TASK,
                created_at=clock.now(),
                updated_at=clock.now(),
            )
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

    auth = CreateArtifactUpload(uow_factory, clock, id_gen)
    cmd = CreateUploadCommand(learner_id=learner_id, filename="test.txt", size_bytes=100)
    res = await auth.execute(cmd)

    assert res.artifact_id is not None
    assert res.expires_in_seconds > 0

    async with uow_factory() as uow:
        pending = await uow.outbox.pending()
        assert len(pending) == 1
        assert pending[0].event_type == "artifact.upload_authorized"
        assert pending[0].payload["artifact_id"] == str(res.artifact_id)
        reserved = await uow.artifacts.get(res.artifact_id, learner_id)
        assert reserved is not None
        assert res.upload_url is not None


@pytest.mark.asyncio
async def test_get_skills_profile_isolation():
    uow_factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    learner_id1 = uuid4()
    learner_id2 = uuid4()

    async with uow_factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id1,
                display_name="L1",
                preferred_language="en",
                status=LearnerStatus.IN_TASK,
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        )
        await uow.learners.add(
            Learner(
                learner_id=learner_id2,
                display_name="L2",
                preferred_language="en",
                status=LearnerStatus.IN_TASK,
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id1,
                current_status=LearnerStatus.IN_TASK,
                version=1,
                updated_at=clock.now(),
            ),
            expected_version=0,
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id2,
                current_status=LearnerStatus.IN_TASK,
                version=1,
                updated_at=clock.now(),
            ),
            expected_version=0,
        )

        evidence = SkillEvidence(
            evidence_id=uuid4(),
            learner_id=learner_id1,
            attempt_id=uuid4(),
            task_version_id=uuid4(),
            skill_id="s1",
            check_id="c1",
            awarded_points=10,
            available_points=10,
            recorded_at=clock.now(),
        )
        uow._snapshot.evidence[evidence.evidence_id] = evidence
        await uow.commit()

    get_profile = GetSkillsProfile(uow_factory)
    profile1 = await get_profile.execute(learner_id1)
    profile2 = await get_profile.execute(learner_id2)
    assert len(profile1.skills) == 1, (
        f"len is {len(profile1.skills)}, skills in DB: {len(uow_factory()._database._state.evidence)}"
    )
    assert len(profile2.skills) == 0


@pytest.mark.asyncio
async def test_reset_demo_learner():
    uow_factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    id_gen = FakeIDGenerator()
    reset = ResetDemoLearner(uow_factory, clock, id_gen)

    learner_id = uuid4()

    async with uow_factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="Test",
                preferred_language="en",
                status=LearnerStatus.IN_TASK,
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id,
                current_status=LearnerStatus.IN_TASK,
                version=1,
                updated_at=clock.now(),
                current_task_id="reset-task",
            ),
            expected_version=0,
        )
        await uow.commit()

    cmd = ResetDemoLearnerCommand(
        admin_actor_id="admin", is_admin=True, learner_id=learner_id, reason="test"
    )
    await reset.execute(cmd)

    async with uow_factory() as uow:
        learner = await uow.learners.get(learner_id)
        progress = await uow.learners.get_progress(learner_id)
        assert learner is not None
        assert learner.status == progress.current_status
        assert progress.current_status == LearnerStatus.ONBOARDING
        assert progress.current_task_id is None
        assert progress.reset_at == clock.now()

        events = await uow.outbox.pending()
        assert len(events) == 1
        assert events[0].event_type == "learner.reset"
