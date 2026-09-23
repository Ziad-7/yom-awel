from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yom_awel.domain.contracts import TaskVersion
from yom_awel.domain.enums import SubmissionStatus
from yom_awel.ports.repositories import MAX_SUBMISSION_LEASE_SECONDS


class ProcessingState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    submission_id: UUID
    status: SubmissionStatus
    # Transport adapters can copy this directly to Retry-After. It is derived
    # from the committed reservation lease, never guessed locally.
    retry_after_seconds: int = Field(strict=True, ge=1, le=MAX_SUBMISSION_LEASE_SECONDS)


class UploadAuthorizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    artifact_id: UUID
    expires_in_seconds: int
    upload_url: str | None = None
    upload_token: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class UploadCompletionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    artifact_id: UUID


class CurrentTaskResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: str
    task: TaskVersion | None = None
