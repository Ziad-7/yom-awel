from datetime import UTC, datetime
from uuid import uuid4

import pytest

from yom_awel.application.commands import OnboardLearnerCommand
from yom_awel.application.onboarding import OnboardLearner
from yom_awel.domain.enums import LearnerStatus
from yom_awel.persistence.memory import MemoryUnitOfWorkFactory


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 21, 10, 0, tzinfo=UTC)


class FakeIDGenerator:
    def generate(self):
        return uuid4()


@pytest.mark.asyncio
async def test_onboard_learner_success():
    uow_factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    id_gen = FakeIDGenerator()
    onboard = OnboardLearner(uow_factory, clock, id_gen)

    cmd = OnboardLearnerCommand(
        provider="github", provider_subject="123", display_name="Test", preferred_language="en"
    )
    learner = await onboard.execute(cmd)

    assert learner.display_name == "Test"
    assert learner.status == LearnerStatus.READY

    async with uow_factory() as uow:
        progress = await uow.learners.get_progress(learner.learner_id)
        assert progress is not None
        assert progress.current_status == LearnerStatus.READY

        events = await uow.outbox.pending()
        assert len(events) == 1
        assert events[0].event_type == "learner.onboarded"


@pytest.mark.asyncio
async def test_onboard_learner_idempotency():
    uow_factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    id_gen = FakeIDGenerator()
    onboard = OnboardLearner(uow_factory, clock, id_gen)

    cmd = OnboardLearnerCommand(
        provider="github", provider_subject="123", display_name="Test", preferred_language="en"
    )
    learner1 = await onboard.execute(cmd)
    learner2 = await onboard.execute(cmd)

    assert learner1.learner_id == learner2.learner_id
