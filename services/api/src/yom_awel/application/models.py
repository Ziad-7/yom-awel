from uuid import UUID

from pydantic import BaseModel, ConfigDict

from yom_awel.domain.contracts import TaskVersion
from yom_awel.domain.enums import SubmissionStatus


class ProcessingState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    submission_id: UUID
    status: SubmissionStatus


class UploadAuthorizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    artifact_id: UUID
    expires_in_seconds: int


class CurrentTaskResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: str
    task: TaskVersion | None = None
