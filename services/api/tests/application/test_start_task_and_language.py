from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from yom_awel.application.commands import OnboardLearnerCommand
from yom_awel.application.onboarding import OnboardLearner
from yom_awel.application.preferences import SetPreferredLanguage
from yom_awel.application.tasks import StartTask
from yom_awel.domain.enums import Language, LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.catalog import TaskCatalog
from yom_awel.persistence.memory import FrozenClock, MemoryUnitOfWorkFactory

NOW = datetime(2026, 9, 24, tzinfo=UTC)
TASK = TaskCatalog.load(Path(__file__).resolve().parents[4] / "task_packages").get("clean-sales")


class IDs:
    def generate(self):
        return uuid4()


@pytest.fixture
async def world():
    clock = FrozenClock(NOW)
    factory = MemoryUnitOfWorkFactory(clock=clock)
    async with factory() as uow:
        await uow.tasks.add(TASK.task_version)
        await uow.commit()
    learner = await OnboardLearner(factory, clock, IDs()).execute(
        OnboardLearnerCommand(
            provider="web", provider_subject="s-1", display_name="نور", preferred_language="en"
        )
    )
    return factory, clock, learner


async def test_start_moves_a_ready_learner_into_the_task_and_emits_an_event(world):
    factory, clock, learner = world

    result = await StartTask(factory, clock, IDs()).execute(learner.learner_id, "clean-sales")

    assert result.status == LearnerStatus.IN_TASK.value
    assert result.task == TASK.task_version
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner.learner_id)
        events = await uow.outbox.pending()
    assert (progress.current_task_id, progress.version) == ("clean-sales", 2)
    assert "task.started" in {event.event_type for event in events}


async def test_starting_the_current_task_again_changes_nothing(world):
    factory, clock, learner = world
    start = StartTask(factory, clock, IDs())
    first = await start.execute(learner.learner_id, "clean-sales")

    assert await start.execute(learner.learner_id, "clean-sales") == first
    async with factory() as uow:
        assert (await uow.learners.get_progress(learner.learner_id)).version == 2


async def test_unknown_task_and_unknown_learner_are_not_found(world):
    factory, clock, learner = world
    start = StartTask(factory, clock, IDs())

    for learner_id, task_id in ((learner.learner_id, "sql-report"), (uuid4(), "clean-sales")):
        with pytest.raises(DomainError) as error:
            await start.execute(learner_id, task_id)
        assert error.value.code == "not_found"


async def test_a_learner_busy_with_another_task_cannot_start_a_new_one(world):
    factory, clock, learner = world
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner.learner_id)
        await uow.learners.save_progress(
            progress.model_copy(
                update={
                    "current_status": LearnerStatus.IN_TASK,
                    "current_task_id": "other-task",
                    "version": progress.version + 1,
                }
            ),
            expected_version=progress.version,
        )
        await uow.commit()

    with pytest.raises(DomainError) as error:
        await StartTask(factory, clock, IDs()).execute(learner.learner_id, "clean-sales")
    assert error.value.code == "invalid_status"


async def test_language_preference_is_saved(world):
    factory, clock, learner = world

    updated = await SetPreferredLanguage(factory, clock).execute(learner.learner_id, Language.AR_EG)

    assert updated.preferred_language is Language.AR_EG
    async with factory() as uow:
        assert (await uow.learners.get(learner.learner_id)).preferred_language is Language.AR_EG
