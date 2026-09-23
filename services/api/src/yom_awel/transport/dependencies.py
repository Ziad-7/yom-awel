"""Composition and channel-independent orchestration; grading remains in the ports."""

import importlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from yom_awel.application.commands import OnboardLearnerCommand
from yom_awel.application.onboarding import OnboardLearner
from yom_awel.application.profiles import GetSkillsProfile
from yom_awel.application.submissions import ProcessSubmission
from yom_awel.application.tasks import CompleteArtifactUpload, CreateArtifactUpload, GetCurrentTask
from yom_awel.domain.entities import Learner
from yom_awel.domain.enums import LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.domain.state_machine import transition
from yom_awel.persistence.sqlite import SQLiteUnitOfWorkFactory
from yom_awel.ports.artifacts import ArtifactStore
from yom_awel.ports.evaluation import Evaluator
from yom_awel.ports.feedback import FeedbackProvider
from yom_awel.ports.unit_of_work import UnitOfWorkFactory
from yom_awel.transport.auth import Identity
from yom_awel.transport.fakes import FixtureEvaluator, FixtureFeedback, demo_task
from yom_awel.transport.models import AttemptResult, OnboardInput
from yom_awel.transport.settings import Settings


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class IDs:
    def generate(self) -> UUID:
        return uuid4()


class Services:
    def __init__(
        self,
        factory: UnitOfWorkFactory,
        evaluator: Evaluator,
        feedback: FeedbackProvider,
        *,
        starter: Callable[[UUID], Awaitable[None]],
        simulated: bool = False,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.factory = factory
        self.starter = starter
        self.simulated = simulated
        self.clock, self.ids = Clock(), IDs()
        self.onboarding = OnboardLearner(factory, self.clock, self.ids)
        self.tasks = GetCurrentTask(factory)
        self.uploads = CreateArtifactUpload(factory, self.clock, self.ids, artifact_store)
        self.completion = CompleteArtifactUpload(factory, artifact_store)
        self.submissions = ProcessSubmission(factory, evaluator, feedback, self.clock, self.ids)
        self.skills = GetSkillsProfile(factory)

    async def learner(self, identity: Identity) -> Learner:
        async with self.factory() as uow:
            learner = await uow.learners.get_by_external_identity(
                identity.provider, identity.subject
            )
        if learner is None:
            raise DomainError("not_found", "Onboarding required")
        return learner

    async def onboard(self, identity: Identity, body: OnboardInput) -> Learner:
        learner = await self.onboarding.execute(
            OnboardLearnerCommand(
                provider=identity.provider,
                provider_subject=identity.subject,
                display_name=body.display_name.strip(),
                preferred_language=body.preferred_language,
            )
        )
        await self.starter(learner.learner_id)
        return await self.learner(identity)

    async def history(self, learner_id: UUID) -> list[AttemptResult]:
        current = await self.tasks.execute(learner_id)
        if current.task is None:
            return []
        async with self.factory() as uow:
            attempts = await uow.attempts.list_for_task(learner_id, current.task.task_version_id)
            outcomes = []
            for attempt in attempts:
                evaluation = await uow.evaluations.get(attempt.evaluation_id)
                feedback = await uow.feedback.get(attempt.feedback_id)
                if evaluation and feedback:
                    outcomes.append(
                        AttemptResult(
                            submission_id=attempt.submission_id,
                            attempt_number=attempt.attempt_number,
                            evaluation=evaluation.result,
                            feedback=feedback.result,
                        )
                    )
            return sorted(outcomes, key=lambda item: item.attempt_number)


def compose(settings: Settings) -> Services:
    if settings.mode == "cloud":
        if not settings.cloud_factory:
            raise ValueError("Cloud requires CLOUD_SERVICES_FACTORY; never use SQLite on Vercel")
        module, name = settings.cloud_factory.split(":", 1)
        services = getattr(importlib.import_module(module), name)(settings)
        if not isinstance(services, Services) or services.simulated:
            raise ValueError("Cloud factory must supply real Services")
        return services
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    factory = SQLiteUnitOfWorkFactory(settings.database_path)

    async def start_local_fixture(learner_id: UUID) -> None:
        # Local-only bootstrap until member2 exposes task assignment as a use case.
        # Transitions are authorized by the existing domain state machine.
        async with factory() as uow:
            task = demo_task()
            if await uow.tasks.get(task.task_version_id) is None:
                await uow.tasks.add(task)
            progress = await uow.learners.get_progress(learner_id)
            if progress and progress.current_status == LearnerStatus.READY:
                updated = progress.model_copy(
                    update={
                        "current_status": transition(
                            progress.current_status, LearnerStatus.IN_TASK
                        ),
                        "current_task_id": task.task_id,
                        "version": progress.version + 1,
                        "updated_at": datetime.now(UTC),
                    }
                )
                await uow.learners.save_progress(updated, expected_version=progress.version)
            await uow.commit()

    return Services(
        cast(UnitOfWorkFactory, factory),
        FixtureEvaluator(),
        FixtureFeedback(),
        starter=start_local_fixture,
        simulated=True,
    )
