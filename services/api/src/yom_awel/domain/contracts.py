from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from yom_awel.domain.enums import ErrorCategory, LearnerStatus, TaskStatus


class ArtifactRef(BaseModel):
    artifact_id: UUID
    filename: str = Field(strict=True, max_length=255)
    size_bytes: int = Field(strict=True, ge=0, le=5 * 1024 * 1024)
    sha256: str = Field(strict=True, pattern=r"^[a-f0-9]{64}$")
    model_config = ConfigDict(frozen=True, extra="forbid")


class SkillMapping(BaseModel):
    skill_id: str = Field(strict=True, min_length=1)
    check_id: str = Field(strict=True, min_length=1)
    weight: int = Field(strict=True, ge=0)
    model_config = ConfigDict(frozen=True, extra="forbid")


class TaskVersion(BaseModel):
    task_version_id: UUID
    task_id: str = Field(strict=True, min_length=1)
    version: str = Field(strict=True, min_length=1)
    instructions_ar: str = Field(strict=True, min_length=1)
    instructions_en: str = Field(strict=True, min_length=1)
    artifact_schema: dict[str, JsonValue]
    evaluator_id: str = Field(strict=True, min_length=1)
    evaluator_version: str = Field(strict=True, min_length=1)
    pass_threshold: int = Field(strict=True, ge=0, le=100)
    skill_mappings: list[SkillMapping]
    content_hash: str = Field(strict=True, pattern=r"^[a-f0-9]{64}$")
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationCheck(BaseModel):
    check_id: str = Field(strict=True, min_length=1)
    passed: bool = Field(strict=True)
    weight: int = Field(strict=True, ge=0)
    details: str | None = Field(default=None, strict=True)
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationError(BaseModel):
    code: str = Field(strict=True, min_length=1)
    message: str = Field(strict=True)
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationResult(BaseModel):
    evaluator_id: str = Field(strict=True, min_length=1)
    evaluator_version: str = Field(strict=True, min_length=1)
    task_version_id: UUID
    passed: bool = Field(strict=True)
    score: int = Field(strict=True, ge=0, le=100)
    checks: list[EvaluationCheck]
    errors: list[EvaluationError]
    summary_ar: str = Field(strict=True)
    summary_en: str = Field(strict=True)
    duration_ms: int = Field(strict=True, ge=0)
    model_config = ConfigDict(frozen=True, extra="forbid")


class FeedbackResult(BaseModel):
    feedback_text: str = Field(strict=True)
    language: Literal["ar-EG", "en"]
    persona_id: str = Field(strict=True, min_length=1)
    prompt_version: str = Field(strict=True, min_length=1)
    provider: str = Field(strict=True, min_length=1)
    model: str | None = Field(strict=True)
    used_fallback: bool = Field(strict=True)
    duration_ms: int = Field(strict=True, ge=0)
    model_config = ConfigDict(frozen=True, extra="forbid")


class SkillSummary(BaseModel):
    skill_id: str = Field(strict=True, min_length=1)
    score: int = Field(strict=True, ge=0, le=100)
    model_config = ConfigDict(frozen=True, extra="forbid")


class SkillsProfile(BaseModel):
    learner_id: UUID
    skills: list[SkillSummary]
    model_config = ConfigDict(frozen=True, extra="forbid")


class SubmissionOutcome(BaseModel):
    submission_id: UUID
    attempt_id: UUID
    attempt_number: int = Field(strict=True, ge=1)
    evaluation: EvaluationResult
    feedback: FeedbackResult
    learner_status: LearnerStatus
    task_status: TaskStatus
    skills: list[SkillSummary]
    model_config = ConfigDict(frozen=True, extra="forbid")


class ApplicationError(BaseModel):
    code: str = Field(strict=True, min_length=1)
    category: ErrorCategory
    message: str = Field(strict=True)
    retryable: bool = Field(strict=True)
    model_config = ConfigDict(frozen=True, extra="forbid")
