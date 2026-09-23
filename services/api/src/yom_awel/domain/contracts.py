from typing import Annotated, Any, Literal, TypeVar
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, JsonValue

from yom_awel.domain.enums import ErrorCategory, LearnerStatus, TaskStatus


class ArtifactRef(BaseModel):
    artifact_id: UUID
    filename: str = Field(strict=True, max_length=255)
    size_bytes: int = Field(strict=True, ge=0)
    sha256: str = Field(strict=True, pattern=r"^[a-f0-9]{64}$")
    # Internal evaluator input. It is deliberately excluded from serialized
    # contracts and outcomes so raw learner artifacts are never persisted in
    # events or API payloads.
    content: bytes = Field(default=b"", repr=False, exclude=True)
    model_config = ConfigDict(frozen=True, extra="forbid")


class SkillMapping(BaseModel):
    skill_id: str = Field(strict=True, min_length=1)
    check_id: str = Field(strict=True, min_length=1)
    weight: int = Field(strict=True, ge=0)
    model_config = ConfigDict(frozen=True, extra="forbid")


K = TypeVar("K")
V = TypeVar("V")
T = TypeVar("T")


class FrozenDict(dict[K, V]):
    def __setitem__(self, key: Any, value: Any) -> None:
        raise TypeError("Immutable")

    def __delitem__(self, key: Any) -> None:
        raise TypeError("Immutable")

    def clear(self) -> None:
        raise TypeError("Immutable")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("Immutable")

    def popitem(self) -> tuple[Any, Any]:
        raise TypeError("Immutable")

    def update(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("Immutable")

    def setdefault(self, key: Any, default: Any = None) -> Any:
        raise TypeError("Immutable")

    def __ior__(self, other: Any) -> Any:  # type: ignore[misc]
        raise TypeError("Immutable")

    def __deepcopy__(self, memo: Any) -> Any:
        import copy

        return self.__class__(copy.deepcopy(dict(self), memo))


class FrozenList(list[T]):
    def __setitem__(self, key: Any, value: Any) -> None:
        raise TypeError("Immutable")

    def __delitem__(self, key: Any) -> None:
        raise TypeError("Immutable")

    def clear(self) -> None:
        raise TypeError("Immutable")

    def append(self, x: Any) -> None:
        raise TypeError("Immutable")

    def extend(self, iterable: Any) -> None:
        raise TypeError("Immutable")

    def insert(self, i: Any, x: Any) -> None:
        raise TypeError("Immutable")

    def pop(self, *args: Any, **kwargs: Any) -> Any:
        raise TypeError("Immutable")

    def remove(self, x: Any) -> None:
        raise TypeError("Immutable")

    def reverse(self) -> None:
        raise TypeError("Immutable")

    def sort(self, *args: Any, **kwargs: Any) -> None:
        raise TypeError("Immutable")

    def __iadd__(self, other: Any) -> Any:  # type: ignore[misc]
        raise TypeError("Immutable")

    def __imul__(self, other: Any) -> Any:  # type: ignore[misc]
        raise TypeError("Immutable")

    def __deepcopy__(self, memo: Any) -> Any:
        import copy

        return self.__class__(copy.deepcopy(list(self), memo))


def deep_freeze(obj: Any) -> Any:
    if isinstance(obj, dict):
        return FrozenDict({k: deep_freeze(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return FrozenList(deep_freeze(v) for v in obj)
    return obj


DeepFrozenDict = Annotated[dict[str, JsonValue], AfterValidator(deep_freeze)]
DeepFrozenListMapping = Annotated[list[SkillMapping], AfterValidator(deep_freeze)]


class TaskVersion(BaseModel):
    task_version_id: UUID
    task_id: str = Field(strict=True, min_length=1)
    version: str = Field(strict=True, min_length=1)
    instructions_ar: str = Field(strict=True, min_length=1)
    instructions_en: str = Field(strict=True, min_length=1)
    artifact_schema: DeepFrozenDict
    evaluator_id: str = Field(strict=True, min_length=1)
    evaluator_version: str = Field(strict=True, min_length=1)
    pass_threshold: int = Field(strict=True, ge=0, le=100)
    skill_mappings: DeepFrozenListMapping
    content_hash: str = Field(strict=True, pattern=r"^[a-f0-9]{64}$")
    model_config = ConfigDict(frozen=True, extra="forbid")


class EvaluationCheck(BaseModel):
    check_id: str = Field(strict=True, min_length=1)
    passed: bool = Field(strict=True)
    weight: int = Field(strict=True, ge=0)
    details_ar: str = Field(strict=True)
    details_en: str = Field(strict=True)
    diagnostic_code: str = Field(strict=True, min_length=1)
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
