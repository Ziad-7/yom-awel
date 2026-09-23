from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

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
    size_bytes: int = Field(..., ge=0)
    # Browsers calculate this before requesting a signed upload.  ``None`` is
    # retained for older local callers; such callers receive a reservation
    # with a deterministic placeholder and must submit the real hash later.
    artifact_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        pattern=r"^[a-f0-9]{64}$",
    )


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
