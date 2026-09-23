from uuid import UUID

from yom_awel.application.commands import CreateUploadCommand
from yom_awel.application.models import CurrentTaskResult, UploadAuthorizationResult
from yom_awel.domain.entities import OutboxEvent
from yom_awel.domain.enums import ErrorCategory, LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.ports.clock import Clock
from yom_awel.ports.id_generator import IDGenerator
from yom_awel.ports.unit_of_work import UnitOfWorkFactory


class GetCurrentTask:
    def __init__(self, uow_factory: UnitOfWorkFactory):
        self.uow_factory = uow_factory

    async def execute(self, learner_id: UUID) -> CurrentTaskResult:
        async with self.uow_factory() as uow:
            progress = await uow.learners.get_progress(learner_id)
            if not progress:
                raise DomainError(
                    code="not_found",
                    message="Learner progress not found",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            task = None
            if progress.current_task_id:
                task = await uow.tasks.get_current_published_version(progress.current_task_id)

            return CurrentTaskResult(status=progress.current_status.value, task=task)


class CreateArtifactUpload:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock, id_gen: IDGenerator):
        self.uow_factory = uow_factory
        self.clock = clock
        self.id_gen = id_gen

    async def execute(self, command: CreateUploadCommand) -> UploadAuthorizationResult:
        async with self.uow_factory() as uow:
            progress = await uow.learners.get_progress(command.learner_id)
            if not progress:
                raise DomainError(
                    code="not_found",
                    message="Learner progress not found",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            if progress.current_status not in (LearnerStatus.IN_TASK, LearnerStatus.NEEDS_RETRY):
                raise DomainError(
                    code="invalid_status",
                    message="Learner is not in a task",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            if not command.filename or command.size_bytes > 5 * 1024 * 1024:
                raise DomainError(
                    code="invalid_artifact",
                    message="Artifact invalid",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            artifact_id = self.id_gen.generate()
            now = self.clock.now()

            await uow.outbox.add(
                OutboxEvent(
                    event_id=self.id_gen.generate(),
                    event_type="artifact.upload_authorized",
                    aggregate_id=command.learner_id,
                    payload={
                        "artifact_id": str(artifact_id),
                        "filename": command.filename,
                        "size_bytes": command.size_bytes,
                    },
                    created_at=now,
                )
            )

            await uow.commit()
            return UploadAuthorizationResult(artifact_id=artifact_id, expires_in_seconds=3600)


# Compatibility name retained for transport adapters that adopted the initial
# implementation before the public use-case contract was finalized.
AuthorizeUpload = CreateArtifactUpload
