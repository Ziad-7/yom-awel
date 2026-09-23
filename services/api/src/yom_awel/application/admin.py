from yom_awel.application.commands import ResetDemoLearnerCommand
from yom_awel.domain.entities import OutboxEvent
from yom_awel.domain.enums import ErrorCategory, LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.ports.clock import Clock
from yom_awel.ports.id_generator import IDGenerator
from yom_awel.ports.unit_of_work import UnitOfWorkFactory


class ResetDemoLearner:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock, id_gen: IDGenerator):
        self.uow_factory = uow_factory
        self.clock = clock
        self.id_gen = id_gen

    async def execute(self, command: ResetDemoLearnerCommand) -> None:
        if not command.is_admin:
            raise DomainError(
                code="unauthorized",
                message="Unauthorized to reset learner",
                category=ErrorCategory.AUTHORIZATION,
                retryable=False,
            )

        now = self.clock.now()

        async with self.uow_factory() as uow:
            learner = await uow.learners.get(command.learner_id)
            if not learner:
                raise DomainError(
                    code="not_found",
                    message="Learner not found",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            progress = await uow.learners.get_progress(command.learner_id)
            if not progress:
                raise DomainError(
                    code="not_found",
                    message="Learner progress not found",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            prev_status = progress.current_status
            prev_task = progress.current_task_id

            new_progress = progress.model_copy(
                update={
                    "current_status": LearnerStatus.ONBOARDING,
                    "current_task_id": None,
                    "reset_at": now,
                    "updated_at": now,
                    "version": progress.version + 1,
                }
            )

            await uow.learners.save_progress(new_progress, expected_version=progress.version)

            await uow.outbox.add(
                OutboxEvent(
                    event_id=self.id_gen.generate(),
                    event_type="learner.reset",
                    aggregate_id=command.learner_id,
                    payload={
                        "actor_id": command.admin_actor_id,
                        "reason": command.reason,
                        "previous_status": prev_status.value if prev_status else None,
                        "previous_task_id": str(prev_task) if prev_task else None,
                    },
                    created_at=now,
                )
            )

            await uow.commit()
