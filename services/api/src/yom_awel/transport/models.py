from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OnboardInput(Input):
    display_name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    preferred_language: Language = Language.AR_EG


class UploadInput(Input):
    filename: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(strict=True, gt=0, le=5 * 1024 * 1024)
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    content_type: str = Field(max_length=100)


class SubmissionInput(Input):
    task_version_id: UUID
    artifact_id: UUID
    artifact_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    learner_note: str | None = Field(default=None, max_length=500)


class SessionResult(BaseModel):
    access_token: str
    expires_in: int = 604800


class HealthResult(BaseModel):
    status: str = "ok"


class RuntimeResult(BaseModel):
    mode: str
    simulated_evaluation: bool


class AttemptResult(BaseModel):
    submission_id: UUID
    attempt_number: int
    evaluation: EvaluationResult
    feedback: FeedbackResult
