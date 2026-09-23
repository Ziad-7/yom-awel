from uuid import UUID

from yom_awel.domain.contracts import SkillsProfile
from yom_awel.domain.entities import aggregate_skill_evidence
from yom_awel.domain.enums import ErrorCategory
from yom_awel.domain.errors import DomainError
from yom_awel.ports.unit_of_work import UnitOfWorkFactory


class GetSkillsProfile:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, learner_id: UUID) -> SkillsProfile:
        async with self.uow_factory() as uow:
            learner = await uow.learners.get(learner_id)
            if not learner:
                raise DomainError(
                    code="not_found",
                    message="Learner not found",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            progress = await uow.learners.get_progress(learner_id)
            skills = await uow.skills.list_evidence(learner_id)

            if progress:
                reset_at = getattr(progress, "reset_at", None)
                if reset_at is not None:
                    skills = [s for s in skills if s.recorded_at >= reset_at]

            aggregated = aggregate_skill_evidence(skills)
            return SkillsProfile(learner_id=learner_id, skills=aggregated)
