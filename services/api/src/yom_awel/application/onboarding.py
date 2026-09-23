from yom_awel.application.commands import OnboardLearnerCommand
from yom_awel.domain.entities import Learner, LearnerProgress, OutboxEvent
from yom_awel.domain.enums import ErrorCategory, LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.ports.clock import Clock
from yom_awel.ports.id_generator import IDGenerator
from yom_awel.ports.unit_of_work import UnitOfWorkFactory


class OnboardLearner:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock, id_gen: IDGenerator):
        self.uow_factory = uow_factory
        self.clock = clock
        self.id_gen = id_gen

    async def execute(self, command: OnboardLearnerCommand) -> Learner:
        now = self.clock.now()

        async with self.uow_factory() as uow:
            existing_learner = await uow.learners.get_by_external_identity(
                command.provider, command.provider_subject
            )
            if existing_learner:
                return existing_learner

            learner_id = self.id_gen.generate()
            learner = Learner(
                learner_id=learner_id,
                display_name=command.display_name,
                preferred_language=command.preferred_language,
                status=LearnerStatus.READY,
                created_at=now,
                updated_at=now,
            )

            await uow.learners.add(learner)

            try:
                await uow.learners.add_external_identity(
                    learner_id=learner_id,
                    provider=command.provider,
                    provider_subject=command.provider_subject,
                )
            except Exception as e:
                # E.g. UniqueConstraintViolation
                raise DomainError(
                    code="identity_conflict",
                    message="Identity already registered",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                ) from e

            progress = LearnerProgress(
                learner_id=learner_id, current_status=LearnerStatus.READY, version=1, updated_at=now
            )
            await uow.learners.save_progress(progress, expected_version=0)

            await uow.outbox.add(
                OutboxEvent(
                    event_id=self.id_gen.generate(),
                    event_type="learner.onboarded",
                    aggregate_id=learner_id,
                    payload={"provider": command.provider},
                    created_at=now,
                )
            )

            await uow.commit()
            return learner
