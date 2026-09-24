from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from yom_awel.domain.contracts import ArtifactContentType, artifact_content_type
from yom_awel.domain.enums import Channel, Language


class OnboardLearnerCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    provider: str = Field(..., min_length=1)
    provider_subject: str = Field(..., min_length=1)
    display_name: str = Field(..., min_length=1)
    preferred_language: Language


class CreateUploadCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    learner_id: UUID
    filename: str = Field(..., min_length=1)
    content_type: ArtifactContentType
    size_bytes: int = Field(..., ge=0)
    # Browsers calculate this before requesting a signed upload.  The server
    # reserves only immutable metadata that it can verify after upload.
    artifact_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )

    @model_validator(mode="after")
    def validate_content_type(self) -> "CreateUploadCommand":
        if self.content_type != artifact_content_type(self.filename):
            raise ValueError("content_type must match filename")
        return self


class ProcessSubmissionCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    learner_id: UUID
    task_version_id: UUID
    artifact_id: UUID
    artifact_sha256: str = Field(..., min_length=64, max_length=64)
    channel: Channel
    idempotency_key: str = Field(..., min_length=1)
    learner_note: str | None = None
    channel_event_id: str | None = None


class ResetDemoLearnerCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    admin_actor_id: str = Field(..., min_length=1)
    is_admin: bool
    learner_id: UUID
    reason: str = Field(..., min_length=1)
