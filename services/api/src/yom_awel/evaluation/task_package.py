"""Versioned, immutable task package: the executable definition of one task version."""

import hashlib
import json
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    model_validator,
)

from yom_awel.domain.errors import DomainError

MANIFEST_NAME = "task.json"
# Platform upload limit, matching domain.entities.Artifact.size_bytes. The contract has no
# shared constant yet; one is requested on #2.
MAX_ARTIFACT_BYTES = 5 * 1024 * 1024
TOTAL_POINTS = 100

Identifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]*$")]
Slug = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9-]*$")]
Counter = Annotated[str, StringConstraints(strict=True, pattern=r"^[1-9][0-9]*$")]
Sha256 = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-f0-9]{64}$")]
NonEmpty = Annotated[str, StringConstraints(strict=True, min_length=1)]


class TaskPackageError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__("task_package_invalid", f"Invalid task package: {reason}")


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ArtifactLimits(_Frozen):
    extensions: tuple[Literal["csv", "xlsx", "sql", "txt"], ...] = Field(min_length=1)
    max_bytes: int = Field(strict=True, gt=0, le=MAX_ARTIFACT_BYTES)
    max_expanded_bytes: int = Field(strict=True, gt=0)
    max_sheets: int = Field(strict=True, gt=0)
    max_rows: int = Field(strict=True, gt=0)
    max_columns: int = Field(strict=True, gt=0)


class CleaningPolicy(_Frozen):
    required_columns: tuple[NonEmpty, ...] = Field(min_length=1)
    business_key: NonEmpty
    min_rows: int = Field(strict=True, gt=0)
    target_date_format: NonEmpty
    revenue_tolerance: Decimal = Field(ge=0)
    missing_email_reason_column: NonEmpty
    missing_email_reason_value: NonEmpty

    @model_validator(mode="after")
    def _columns_are_declared(self) -> Self:
        if len(set(self.required_columns)) != len(self.required_columns):
            raise ValueError("required_columns must be unique")
        declared = set(self.required_columns)
        for column in (self.business_key, self.missing_email_reason_column):
            if column not in declared:
                raise ValueError(f"{column} must be a required column")
        return self


class SqlReportPolicy(_Frozen):
    kind: Literal["sql-report"]
    source_path: NonEmpty
    max_query_steps: int = Field(strict=True, gt=0)
    max_output_rows: int = Field(strict=True, gt=0)

    @model_validator(mode="after")
    def _source_is_local(self) -> Self:
        _validate_relative_path(self.source_path)
        return self


class ClientEmailPolicy(_Frozen):
    kind: Literal["client-email"]
    case_file: NonEmpty
    min_words: int = Field(strict=True, gt=0)
    max_words: int = Field(strict=True, gt=0)

    @model_validator(mode="after")
    def _word_range(self) -> Self:
        if self.max_words <= self.min_words:
            raise ValueError("max_words must exceed min_words")
        _validate_relative_path(self.case_file)
        return self


class CheckSpec(_Frozen):
    check_id: Identifier
    points: int = Field(strict=True, ge=0, le=TOTAL_POINTS)
    # A failed critical check fails the attempt whatever the score.
    critical: bool = Field(strict=True)
    skill_id: Identifier
    hint_ar: NonEmpty
    hint_en: NonEmpty


class ContentFile(_Frozen):
    path: NonEmpty
    sha256: Sha256

    @model_validator(mode="after")
    def _path_stays_inside_package(self) -> Self:
        _validate_relative_path(self.path)
        return self


class TaskPackage(_Frozen):
    task_id: Slug
    version: Counter
    status: Literal["draft", "published"]
    evaluator_id: Slug
    evaluator_version: Counter
    pass_threshold: int = Field(strict=True, ge=0, le=TOTAL_POINTS)
    dataset_seed: int = Field(strict=True, ge=0)
    generator_version: NonEmpty
    limits: ArtifactLimits
    policy: CleaningPolicy | SqlReportPolicy | ClientEmailPolicy
    checks: tuple[CheckSpec, ...] = Field(min_length=1)
    content: tuple[ContentFile, ...]

    @model_validator(mode="after")
    def _rubric_is_balanced(self) -> Self:
        check_ids = [check.check_id for check in self.checks]
        if len(set(check_ids)) != len(check_ids):
            raise ValueError("check_id values must be unique")
        if sum(check.points for check in self.checks) != TOTAL_POINTS:
            raise ValueError(f"check points must total {TOTAL_POINTS}")
        return self

    @property
    def critical_check_ids(self) -> frozenset[str]:
        return frozenset(check.check_id for check in self.checks if check.critical)

    @model_validator(mode="after")
    def _published_content_is_pinned(self) -> Self:
        if self.status == "published" and not self.content:
            raise ValueError("a published package must pin its content files")
        if isinstance(self.policy, (SqlReportPolicy, ClientEmailPolicy)):
            source_path = (
                self.policy.source_path
                if isinstance(self.policy, SqlReportPolicy)
                else self.policy.case_file
            )
            if source_path not in {item.path for item in self.content}:
                raise ValueError("the task source file must be pinned")
        return self


def _validate_relative_path(path: str) -> None:
    parts = PurePosixPath(path).parts
    if not parts or PurePosixPath(path).is_absolute() or ".." in parts or "\\" in path:
        raise ValueError("content path must be relative to the package")


def parse_task_package(manifest: str) -> TaskPackage:
    try:
        return TaskPackage.model_validate_json(manifest)
    except ValidationError as error:
        raise TaskPackageError(_first_error(error)) from error


def verify_content(package: TaskPackage, root: Path) -> None:
    """Reject missing, empty, escaping, or modified content files."""

    resolved_root = root.resolve()
    for content in package.content:
        path = (resolved_root / content.path).resolve()
        if not path.is_relative_to(resolved_root):
            raise TaskPackageError(f"{content.path} escapes the package")
        if not path.is_file():
            raise TaskPackageError(f"{content.path} is missing")
        data = path.read_bytes()
        if not data.strip():
            raise TaskPackageError(f"{content.path} is empty")
        if hashlib.sha256(data).hexdigest() != content.sha256:
            raise TaskPackageError(f"{content.path} changed after it was pinned")


def load_task_package(root: Path) -> TaskPackage:
    package = parse_task_package((root / MANIFEST_NAME).read_text(encoding="utf-8"))
    verify_content(package, root)
    return package


def content_hash(package: TaskPackage) -> str:
    """Stable hash of the package, including the pinned hash of every content file."""

    canonical = json.dumps(package.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _first_error(error: ValidationError) -> str:
    first = error.errors()[0]
    location = ".".join(str(part) for part in first["loc"]) or "package"
    return f"{location}: {first['msg']}"
