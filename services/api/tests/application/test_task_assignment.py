from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from yom_awel.application.tasks import AssignCurrentTask
from yom_awel.domain.contracts import TaskVersion
from yom_awel.domain.entities import Learner, LearnerProgress
from yom_awel.domain.enums import LearnerStatus
from yom_awel.domain.errors import DomainError, OptimisticConflict
from yom_awel.persistence.memory import MemoryUnitOfWorkFactory


class FakeClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 24, 10, 0, tzinfo=UTC)


async def seed_learner(
    factory: MemoryUnitOfWorkFactory,
    clock: FakeClock,
    status: LearnerStatus = LearnerStatus.READY,
    current_task_id: str | None = None,
) -> UUID:
    learner_id = uuid4()
    async with factory() as uow:
        await uow.learners.add(
            Learner(
                learner_id=learner_id,
                display_name="Learner",
                preferred_language="en",
                status=status,
                created_at=clock.now(),
                updated_at=clock.now(),
            )
        )
        await uow.learners.save_progress(
            LearnerProgress(
                learner_id=learner_id,
                current_status=status,
                current_task_id=current_task_id,
                version=1,
                updated_at=clock.now(),
            ),
            expected_version=0,
        )
        await uow.commit()
    return learner_id


async def seed_clean_sales_task(factory: MemoryUnitOfWorkFactory) -> TaskVersion:
    task = TaskVersion(
        task_version_id=uuid4(),
        task_id="clean-sales",
        version="1",
        instructions_ar="تعليمات",
        instructions_en="Instructions",
        artifact_schema={},
        evaluator_id="sales",
        evaluator_version="1",
        pass_threshold=50,
        skill_mappings=[],
        content_hash="a" * 64,
    )
    async with factory() as uow:
        await uow.tasks.add(task)
        await uow.commit()
    return task


@pytest.mark.asyncio
async def test_assigns_current_published_clean_sales_task_from_ready():
    """Fails if READY no longer becomes IN_TASK with the published task."""
    factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    learner_id = await seed_learner(factory, clock)
    task = await seed_clean_sales_task(factory)

    result = await AssignCurrentTask(factory, clock).execute(learner_id)

    assert result.status == "IN_TASK"
    assert result.task == task
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner_id)
        assert progress is not None
        assert progress.current_status == LearnerStatus.IN_TASK
        assert progress.current_task_id == "clean-sales"
        assert progress.version == 2
        assert progress.updated_at == clock.now()


@pytest.mark.asyncio
async def test_repeated_assignment_returns_existing_task_without_another_progression():
    """Fails if a replay writes another progress version."""
    factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    learner_id = await seed_learner(factory, clock)
    task = await seed_clean_sales_task(factory)
    assign = AssignCurrentTask(factory, clock)

    await assign.execute(learner_id)
    result = await assign.execute(learner_id)

    assert result.status == "IN_TASK"
    assert result.task == task
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner_id)
        assert progress is not None
        assert progress.version == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status",
    [
        LearnerStatus.IN_TASK,
        LearnerStatus.PROCESSING,
        LearnerStatus.NEEDS_RETRY,
        LearnerStatus.TASK_COMPLETED,
    ],
)
async def test_existing_task_state_is_returned_idempotently(status: LearnerStatus):
    """Fails if an established task state is reassigned or transitioned."""
    factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    learner_id = await seed_learner(factory, clock, status, "clean-sales")
    task = await seed_clean_sales_task(factory)

    result = await AssignCurrentTask(factory, clock).execute(learner_id)

    assert result.status == status.value
    assert result.task == task
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner_id)
        assert progress is not None
        assert progress.version == 1


@pytest.mark.asyncio
async def test_missing_learner_uses_stable_not_found_error():
    """Fails if a missing learner no longer reports the application not-found contract."""
    with pytest.raises(DomainError, match="Learner progress not found") as error:
        await AssignCurrentTask(MemoryUnitOfWorkFactory(), FakeClock()).execute(uuid4())

    assert error.value.code == "not_found"


@pytest.mark.asyncio
async def test_missing_published_task_uses_stable_task_not_found_error():
    """Fails if READY learners can enter a task without published task content."""
    factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    learner_id = await seed_learner(factory, clock)

    with pytest.raises(DomainError, match="Task not found") as error:
        await AssignCurrentTask(factory, clock).execute(learner_id)

    assert error.value.code == "task_not_found"


class ConflictInjectingLearners:
    def __init__(
        self,
        learners: object,
        factory: MemoryUnitOfWorkFactory,
        clock: FakeClock,
    ) -> None:
        self._learners = learners
        self._factory = factory
        self._clock = clock
        self._injected = False

    def __getattr__(self, name: str):
        return getattr(self._learners, name)

    async def save_progress(self, progress: LearnerProgress, expected_version: int) -> None:
        if self._injected:
            await self._learners.save_progress(progress, expected_version)
            return
        self._injected = True
        async with self._factory() as winner_uow:
            winner = await winner_uow.learners.get_progress(progress.learner_id)
            assert winner is not None
            await winner_uow.learners.save_progress(
                winner.model_copy(
                    update={
                        "current_status": LearnerStatus.IN_TASK,
                        "current_task_id": "clean-sales",
                        "version": winner.version + 1,
                        "updated_at": self._clock.now(),
                    }
                ),
                expected_version=winner.version,
            )
            await winner_uow.commit()
        raise OptimisticConflict("learner_progress")


class ConflictInjectingUnitOfWork:
    def __init__(self, inner: object, factory: MemoryUnitOfWorkFactory, clock: FakeClock) -> None:
        self._inner = inner
        self._factory = factory
        self._clock = clock

    async def __aenter__(self):
        await self._inner.__aenter__()
        self.learners = ConflictInjectingLearners(self._inner.learners, self._factory, self._clock)
        self.tasks = self._inner.tasks
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self._inner.__aexit__(exc_type, exc_value, traceback)

    async def commit(self) -> None:
        await self._inner.commit()


class ConflictInjectingFactory:
    def __init__(self, factory: MemoryUnitOfWorkFactory, clock: FakeClock) -> None:
        self._factory = factory
        self._clock = clock
        self._first = True

    def __call__(self):
        if self._first:
            self._first = False
            return ConflictInjectingUnitOfWork(self._factory(), self._factory, self._clock)
        return self._factory()


@pytest.mark.asyncio
async def test_conflict_returns_competing_winner_current_task():
    """Fails if one optimistic conflict does not reopen and return the winner."""
    factory = MemoryUnitOfWorkFactory()
    clock = FakeClock()
    learner_id = await seed_learner(factory, clock)
    task = await seed_clean_sales_task(factory)

    result = await AssignCurrentTask(ConflictInjectingFactory(factory, clock), clock).execute(learner_id)

    assert result.status == "IN_TASK"
    assert result.task == task
    async with factory() as uow:
        progress = await uow.learners.get_progress(learner_id)
        assert progress is not None
        assert progress.version == 2
