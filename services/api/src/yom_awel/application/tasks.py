from uuid import UUID

from yom_awel.application.commands import CreateUploadCommand
from yom_awel.application.models import (
    CurrentTaskResult,
    UploadAuthorizationResult,
    UploadCompletionResult,
)
from yom_awel.domain.contracts import MAX_ARTIFACT_BYTES
from yom_awel.domain.entities import Artifact, OutboxEvent
from yom_awel.domain.enums import ErrorCategory, LearnerStatus
from yom_awel.domain.errors import DomainError
from yom_awel.ports.artifacts import ArtifactStore
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
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        id_gen: IDGenerator,
        artifact_store: ArtifactStore | None = None,
    ):
        self.uow_factory = uow_factory
        self.clock = clock
        self.id_gen = id_gen
        self.artifact_store = artifact_store

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

            if not command.filename:
                raise DomainError(
                    code="invalid_artifact",
                    message="Artifact invalid",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            if command.size_bytes > MAX_ARTIFACT_BYTES:
                raise DomainError(
                    code="artifact_too_large",
                    message="Artifact exceeds the upload size limit",
                    category=ErrorCategory.VALIDATION,
                    retryable=False,
                )

            artifact_id = self.id_gen.generate()
            now = self.clock.now()

            artifact = Artifact(
                artifact_id=artifact_id,
                learner_id=command.learner_id,
                filename=command.filename,
                size_bytes=command.size_bytes,
                sha256=command.artifact_sha256,
            )
            artifact_store = self.artifact_store or uow.artifacts
            authorization = await artifact_store.authorize_upload(artifact)
            # An injected provider store may be separate from the UoW's
            # repository. Register the same immutable metadata locally/cloud
            # so ProcessSubmission can discover it by learner and artifact ID.
            if artifact_store is not uow.artifacts:
                await uow.artifacts.authorize_upload(artifact)

            await uow.outbox.add(
                OutboxEvent(
                    event_id=self.id_gen.generate(),
                    event_type="artifact.upload_authorized",
                    aggregate_id=command.learner_id,
                    payload={
                        "artifact_id": str(artifact_id),
                        "filename": command.filename,
                        "size_bytes": command.size_bytes,
                        "sha256": artifact.sha256,
                    },
                    created_at=now,
                )
            )

            await uow.commit()
            return UploadAuthorizationResult(
                artifact_id=artifact_id,
                expires_in_seconds=authorization.expires_in_seconds,
                upload_url=authorization.upload_url,
                upload_token=authorization.upload_token,
                headers=dict(authorization.headers),
            )


class CompleteArtifactUpload:
    """Verify one browser upload and make it eligible for submission."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        artifact_store: ArtifactStore | None = None,
    ):
        self.uow_factory = uow_factory
        self.artifact_store = artifact_store

    async def execute(self, learner_id: UUID, artifact_id: UUID) -> UploadCompletionResult:
        async with self.uow_factory() as uow:
            store = self.artifact_store or uow.artifacts
            artifact = await store.complete_upload(artifact_id, learner_id)
            await uow.commit()
            return UploadCompletionResult(artifact_id=artifact.artifact_id)


# Compatibility name retained for transport adapters that adopted the initial
# implementation before the public use-case contract was finalized.
AuthorizeUpload = CreateArtifactUpload
