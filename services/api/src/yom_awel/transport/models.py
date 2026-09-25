from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Output(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class OnboardInput(Input):
    display_name: str = Field(min_length=1, max_length=80, pattern=r"\S")
    preferred_language: Language = Language.AR_EG


class LanguageInput(Input):
    preferred_language: Language


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


class SessionResult(Output):
    expires_in: int


class HealthResult(Output):
    status: str = "ok"


class RuntimeResult(Output):
    mode: Literal["local", "cloud"]
    feedback_provider: Literal["gemini", "deterministic"]


TaskStatus = Literal["available", "in_progress", "completed"]


class TaskSummary(Output):
    task_id: str
    version: str
    task_version_id: UUID
    title_ar: str
    title_en: str
    status: TaskStatus
    pass_threshold: int
    points_total: int


class TaskList(Output):
    tasks: list[TaskSummary]


class CheckInfo(Output):
    check_id: str
    points: int
    critical: bool


class TaskDetail(Output):
    task_id: str
    version: str
    task_version_id: UUID
    title_ar: str
    title_en: str
    brief_ar: str
    brief_en: str
    hints_ar: str
    hints_en: str
    pass_threshold: int
    formats: list[Literal["csv", "xlsx"]]
    submission_formats: list[Literal["csv", "xlsx", "sql", "txt"]]
    max_bytes: int
    checks: list[CheckInfo]


class AttemptResult(Output):
    submission_id: UUID
    attempt_number: int
    evaluation: EvaluationResult
    feedback: FeedbackResult
