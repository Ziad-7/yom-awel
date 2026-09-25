from uuid import UUID

from yom_awel.domain.entities import Learner
from yom_awel.domain.enums import ErrorCategory, Language
from yom_awel.domain.errors import DomainError
from yom_awel.ports.clock import Clock
from yom_awel.ports.unit_of_work import UnitOfWorkFactory


class SetPreferredLanguage:
    """Changes the language used for the learner's future feedback."""

    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock):
        self.uow_factory = uow_factory
        self.clock = clock

    async def execute(self, learner_id: UUID, language: Language) -> Learner:
        async with self.uow_factory() as uow:
            await uow.learners.set_preferred_language(learner_id, language, self.clock.now())
            learner = await uow.learners.get(learner_id)
            if learner is None:
                raise DomainError(
                    code="not_found",
                    message="Learner not found",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )
            await uow.commit()
            return learner
