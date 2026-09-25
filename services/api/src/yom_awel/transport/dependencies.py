"""Composition and channel-independent orchestration; grading remains in the ports."""

from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

from yom_awel.application.commands import OnboardLearnerCommand
from yom_awel.application.models import CurrentTaskResult
from yom_awel.application.onboarding import OnboardLearner
from yom_awel.application.preferences import SetPreferredLanguage
from yom_awel.application.profiles import GetSkillsProfile
from yom_awel.application.submissions import ProcessSubmission
from yom_awel.application.tasks import (
    CompleteArtifactUpload,
    CreateArtifactUpload,
    GetCurrentTask,
    StartTask,
)
from yom_awel.domain.contracts import FeedbackResult, TaskVersion
from yom_awel.domain.entities import Learner
from yom_awel.domain.enums import Language, LearnerStatus
from yom_awel.domain.errors import DomainError, UniqueConstraintViolation
from yom_awel.evaluation.catalog import CatalogTask, TaskCatalog
from yom_awel.feedback.config import build_feedback_provider
from yom_awel.persistence.postgres import PostgresUnitOfWorkFactory
from yom_awel.persistence.sqlite import SQLiteUnitOfWorkFactory
from yom_awel.ports.artifacts import ArtifactStore
from yom_awel.ports.evaluation import Evaluator
from yom_awel.ports.feedback import FeedbackProvider
from yom_awel.ports.unit_of_work import UnitOfWorkFactory
from yom_awel.transport.auth import Identity
from yom_awel.transport.models import (
    AttemptResult,
    CheckInfo,
    OnboardInput,
    TaskDetail,
    TaskList,
    TaskStatus,
    TaskSummary,
)
from yom_awel.transport.settings import Settings

COMPLETED = (LearnerStatus.TASK_COMPLETED, LearnerStatus.PROGRAM_COMPLETED)
TRANSLATION_CACHE_SIZE = 256


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
        catalog: TaskCatalog,
        evaluator: Evaluator,
        feedback: FeedbackProvider,
        *,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.factory = factory
        self.catalog = catalog
        self.feedback = feedback
        self.clock, self.ids = Clock(), IDs()
        self.onboarding = OnboardLearner(factory, self.clock, self.ids)
        self.tasks = GetCurrentTask(factory)
        self.start = StartTask(factory, self.clock, self.ids)
        self.language = SetPreferredLanguage(factory, self.clock)
        self.uploads = CreateArtifactUpload(factory, self.clock, self.ids, artifact_store)
        self.completion = CompleteArtifactUpload(factory, artifact_store)
        self.submissions = ProcessSubmission(factory, evaluator, feedback, self.clock, self.ids)
        self.skills = GetSkillsProfile(factory)
        self._translations: OrderedDict[tuple[UUID, Language], FeedbackResult] = OrderedDict()

    async def seed_tasks(self) -> None:
        """Publish every catalog task version; concurrent cold starts may race harmlessly."""

        for task in self.catalog.tasks():
            async with self.factory() as uow:
                if await uow.tasks.get(task.task_version.task_version_id) is not None:
                    continue
                try:
                    await uow.tasks.add(task.task_version)
                    await uow.commit()
                except UniqueConstraintViolation:
                    await uow.rollback()

    async def learner(self, identity: Identity) -> Learner:
        async with self.factory() as uow:
            learner = await uow.learners.get_by_external_identity(
                identity.provider, identity.subject
            )
        if learner is None:
            raise DomainError("not_found", "Onboarding required")
        return learner

    async def onboard(self, identity: Identity, body: OnboardInput) -> Learner:
        await self.onboarding.execute(
            OnboardLearnerCommand(
                provider=identity.provider,
                provider_subject=identity.subject,
                display_name=body.display_name.strip(),
                preferred_language=body.preferred_language,
            )
        )
        return await self.learner(identity)

    async def task_list(self, learner_id: UUID) -> TaskList:
        current = await self.tasks.execute(learner_id)
        completed: set[str] = set()
        async with self.factory() as uow:
            for task in self.catalog.tasks():
                for attempt in await uow.attempts.list_for_task(
                    learner_id, task.task_version.task_version_id
                ):
                    evaluation = await uow.evaluations.get(attempt.evaluation_id)
                    if evaluation and evaluation.result.passed:
                        completed.add(task.task_id)
                        break
        return TaskList(tasks=[_summary(task, current, completed) for task in self.catalog.tasks()])

    def task_detail(self, task_id: str) -> TaskDetail:
        task = self.catalog.get(task_id)
        return TaskDetail(
            task_id=task.task_id,
            version=task.package.version,
            task_version_id=task.task_version.task_version_id,
            title_ar=task.title_ar,
            title_en=task.title_en,
            brief_ar=task.brief_ar,
            brief_en=task.brief_en,
            hints_ar=task.hints_ar,
            hints_en=task.hints_en,
            pass_threshold=task.package.pass_threshold,
            formats=["csv", "xlsx"],
            submission_formats=list(task.package.limits.extensions),
            max_bytes=task.package.limits.max_bytes,
            checks=[
                CheckInfo(check_id=check.check_id, points=check.points, critical=check.critical)
                for check in task.package.checks
            ],
        )

    async def history(self, learner_id: UUID) -> list[AttemptResult]:
        async with self.factory() as uow:
            outcomes = []
            for task in self.catalog.tasks():
                attempts = await uow.attempts.list_for_task(
                    learner_id, task.task_version.task_version_id
                )
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
            return outcomes

    async def feedback_in(
        self, learner_id: UUID, submission_id: UUID, language: Language
    ) -> FeedbackResult:
        """The stored feedback, or the same evaluation explained in the other language.

        Translations are generated on demand and cached in memory, never persisted.
        """

        attempt = next(
            (
                item
                for item in await self.history(learner_id)
                if item.submission_id == submission_id
            ),
            None,
        )
        if attempt is None:
            raise DomainError("not_found", "Submission not found")
        if attempt.feedback.language == language.value:
            return attempt.feedback
        key = (submission_id, language)
        cached = self._translations.get(key)
        if cached is None:
            cached = await self.feedback.generate(attempt.evaluation, language)
            self._translations[key] = cached
            if len(self._translations) > TRANSLATION_CACHE_SIZE:
                self._translations.popitem(last=False)
        return cached


def compose(settings: Settings) -> Services:
    catalog = TaskCatalog.load(settings.task_packages)
    if not catalog.tasks():
        raise ValueError(f"No published task package found under {settings.task_packages}")

    async def resolve(task_version_id: UUID) -> TaskVersion | None:
        return catalog.find_version(task_version_id)

    feedback = build_feedback_provider(settings.feedback, task_context_resolver=resolve)
    return Services(
        _unit_of_work_factory(settings), catalog, catalog.evaluator_registry(), feedback
    )


def _unit_of_work_factory(settings: Settings) -> UnitOfWorkFactory:
    if settings.mode == "cloud":
        return cast(UnitOfWorkFactory, PostgresUnitOfWorkFactory(settings.database_url))
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
    return cast(UnitOfWorkFactory, SQLiteUnitOfWorkFactory(settings.database_path))


def _summary(
    task: CatalogTask, current: CurrentTaskResult, completed: set[str] | None = None
) -> TaskSummary:
    return TaskSummary(
        task_id=task.task_id,
        version=task.package.version,
        task_version_id=task.task_version.task_version_id,
        title_ar=task.title_ar,
        title_en=task.title_en,
        status=_status(task.task_id, current, completed or set()),
        pass_threshold=task.package.pass_threshold,
        points_total=sum(check.points for check in task.package.checks),
    )


def _status(task_id: str, current: CurrentTaskResult, completed: set[str]) -> TaskStatus:
    if task_id in completed:
        return "completed"
    if current.task is None or current.task.task_id != task_id:
        return "available"
    return "completed" if LearnerStatus(current.status) in COMPLETED else "in_progress"
