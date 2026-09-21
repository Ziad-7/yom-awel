from uuid import UUID

from yom_awel.domain.contracts import SubmissionOutcome
from yom_awel.domain.enums import ErrorCategory
from yom_awel.domain.errors import DomainError
from yom_awel.ports.unit_of_work import UnitOfWorkFactory


class GetSubmissionOutcome:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, learner_id: UUID, idempotency_key: str) -> SubmissionOutcome:
        async with self.uow_factory() as uow:
            res = await uow.submissions.get_reservation(learner_id, idempotency_key)
            if not res:
                raise DomainError(
                    code="not_found",
                    message="Submission not found",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            if not res.outcome:
                raise DomainError(
                    code="processing",
                    message="Submission is still processing",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            return res.outcome
