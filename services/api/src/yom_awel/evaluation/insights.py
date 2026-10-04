"""Explainable, deterministic insights into one learner's own submission.

Every evaluator builds its insights from the same rule functions it grades with, so an
insight can never disagree with the score. Insights show where the learner's own file
fails a check and what that would cost the business; they never reveal expected values.
"""

from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from yom_awel.domain.contracts import ArtifactRef, TaskVersion

MAX_PREVIEW_ROWS = 200
MAX_PREVIEW_CELL = 200


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CheckInsight(_Frozen):
    check_id: str
    passed: bool
    issue_count: int = Field(ge=0)


class CellIssue(_Frozen):
    """A cell in the learner's file; ``row`` is the spreadsheet row, the header being row 1."""

    row: int = Field(ge=2)
    column: str
    check_id: str
    issue: str


class PreviewRow(_Frozen):
    row: int = Field(ge=2)
    cells: list[str]


class TablePreview(_Frozen):
    columns: list[str]
    rows: list[PreviewRow]
    total_rows: int = Field(ge=0)


ImpactUnit = Literal["egp", "orders", "customers", "regions", "elements"]


class ImpactMetric(_Frozen):
    metric_id: str
    value: Decimal
    unit: ImpactUnit


RegionStatus = Literal["ok", "unexpected", "duplicate", "unreadable"]


class SqlRowFinding(_Frozen):
    cells: list[str]
    region_status: RegionStatus
    count_ok: bool
    revenue_ok: bool


class SqlInsight(_Frozen):
    columns: list[str]
    columns_ok: bool
    rows: list[SqlRowFinding]
    missing_regions: int = Field(ge=0)
    robustness_failed: bool


class EmailElement(_Frozen):
    element_id: str
    check_id: str
    found: bool
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)


class EmailInsight(_Frozen):
    text: str
    elements: list[EmailElement]
    word_count: int = Field(ge=0)
    min_words: int = Field(ge=0)
    max_words: int = Field(ge=0)


class SubmissionInsights(_Frozen):
    kind: Literal["table", "sql", "email"]
    task_id: str
    rejected_code: str | None = None
    checks: list[CheckInsight]
    impact: list[ImpactMetric] = []
    issues: list[CellIssue] = []
    table: TablePreview | None = None
    sql: SqlInsight | None = None
    email: EmailInsight | None = None


class InsightProvider(Protocol):
    async def insights(
        self, task_version: TaskVersion, artifact: ArtifactRef
    ) -> SubmissionInsights: ...


def clip(value: str) -> str:
    return value if len(value) <= MAX_PREVIEW_CELL else value[: MAX_PREVIEW_CELL - 1] + "…"
