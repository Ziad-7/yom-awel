"""sales-cleaning@1: deterministic grading of the clean-sales task."""

import re
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Self

from yom_awel.domain.contracts import (
    ArtifactRef,
    EvaluationCheck,
    EvaluationError,
    EvaluationResult,
    TaskVersion,
)
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.artifact_validation import ArtifactRejected, Table, inspect_artifact
from yom_awel.evaluation.insights import (
    MAX_PREVIEW_ROWS,
    CellIssue,
    CheckInsight,
    ImpactMetric,
    PreviewRow,
    SubmissionInsights,
    TablePreview,
    clip,
)
from yom_awel.evaluation.task_package import (
    CheckSpec,
    CleaningPolicy,
    TaskPackage,
    load_task_package,
)

EVALUATOR_ID = "sales-cleaning"
EVALUATOR_VERSION = "1"
QUANTITY = re.compile(r"^[0-9]+$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GRADED_COLUMNS = frozenset({"customer_email", "order_date", "quantity", "unit_price", "revenue"})
PASSED_DETAIL = ("الفحص ده سليم.", "This check passed.")
NOT_EVALUATED_DETAIL = (
    "الفحص ماتعملش لأن الملف اترفض.",
    "This check was not run because the file was rejected.",
)

Record = Mapping[str, str]
Clock = Callable[[], int]


@dataclass(frozen=True)
class RowIssue:
    """Why one row fails a check, and which cell shows it."""

    column: str
    code: str


# A rule returns one entry per row: the row's issue, or None. A check passes with no issues.
Rule = Callable[[Sequence[Record], CleaningPolicy], tuple[RowIssue | None, ...]]
NumberedRecords = tuple[tuple[int, Record], ...]


class UnsupportedTaskPackage(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "unsupported_task_package", f"Task package is not graded by {EVALUATOR_ID}@1"
        )


class UnpublishedTaskPackage(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "task_package_unpublished", "Only a published, pinned task package can be graded"
        )


class TaskVersionMismatch(DomainError):
    def __init__(self) -> None:
        super().__init__("task_version_mismatch", "Task version does not match the task package")


class SalesCleaningEvaluator:
    def __init__(self, package: TaskPackage, clock: Clock = time.perf_counter_ns) -> None:
        if not _is_supported(package):
            raise UnsupportedTaskPackage()
        if package.status != "published":
            raise UnpublishedTaskPackage()
        if not isinstance(package.policy, CleaningPolicy):
            raise UnsupportedTaskPackage()
        self._package = package
        self._policy = package.policy
        self._clock = clock

    @classmethod
    def from_directory(cls, root: Path, clock: Clock = time.perf_counter_ns) -> Self:
        """Production binding: verifies every pinned content hash before grading anything."""

        return cls(load_task_package(root), clock)

    async def evaluate(self, task_version: TaskVersion, artifact: ArtifactRef) -> EvaluationResult:
        self._require_matching(task_version)
        started = self._clock()
        try:
            records = parse_records(inspect_artifact(artifact, self._package.limits), self._policy)
        except ArtifactRejected as rejection:
            return self._rejected(task_version, rejection, started)
        policy = self._policy
        checks = [
            grade(spec, _count(RULES[spec.check_id](records, policy)))
            for spec in self._package.checks
        ]
        return self._result(task_version, checks, [], started)

    async def insights(
        self, task_version: TaskVersion, artifact: ArtifactRef
    ) -> SubmissionInsights:
        """Where the learner's own file fails each check, and what that costs the business."""

        self._require_matching(task_version)
        policy = self._policy
        try:
            table = inspect_artifact(artifact, self._package.limits)
            numbered = parse_rows(table, policy)
        except ArtifactRejected as rejection:
            return SubmissionInsights(
                kind="table",
                task_id=self._package.task_id,
                rejected_code=rejection.code,
                checks=[
                    CheckInsight(check_id=spec.check_id, passed=False, issue_count=0)
                    for spec in self._package.checks
                ],
            )
        rows = [number for number, _ in numbered]
        records = [record for _, record in numbered]
        issues = [
            CellIssue(
                row=rows[index], column=issue.column, check_id=spec.check_id, issue=issue.code
            )
            for spec in self._package.checks
            for index, issue in enumerate(RULES[spec.check_id](records, policy))
            if issue is not None
        ]
        columns = [name.strip().lower() for name in table.rows[0]]
        return SubmissionInsights(
            kind="table",
            task_id=self._package.task_id,
            checks=[
                CheckInsight(
                    check_id=spec.check_id,
                    passed=not any(issue.check_id == spec.check_id for issue in issues),
                    issue_count=sum(issue.check_id == spec.check_id for issue in issues),
                )
                for spec in self._package.checks
            ],
            impact=business_impact(records, policy),
            issues=issues,
            table=TablePreview(
                columns=columns,
                rows=[
                    PreviewRow(row=number, cells=[clip(record.get(c, "")) for c in columns])
                    for number, record in numbered[:MAX_PREVIEW_ROWS]
                ],
                total_rows=len(numbered),
            ),
        )

    def _require_matching(self, task_version: TaskVersion) -> None:
        package = self._package
        expected = (
            package.task_id,
            package.version,
            EVALUATOR_ID,
            EVALUATOR_VERSION,
            package.pass_threshold,
        )
        actual = (
            task_version.task_id,
            task_version.version,
            task_version.evaluator_id,
            task_version.evaluator_version,
            task_version.pass_threshold,
        )
        if actual != expected:
            raise TaskVersionMismatch()

    def _rejected(
        self, task_version: TaskVersion, rejection: ArtifactRejected, started: int
    ) -> EvaluationResult:
        checks = [not_evaluated(spec) for spec in self._package.checks]
        error = EvaluationError(code=rejection.code, message=rejection.message)
        return self._result(task_version, checks, [error], started)

    def _result(
        self,
        task_version: TaskVersion,
        checks: list[EvaluationCheck],
        errors: list[EvaluationError],
        started: int,
    ) -> EvaluationResult:
        score = sum(check.weight for check in checks if check.passed)
        passed = not errors and is_passing(score, checks, self._package)
        return EvaluationResult(
            evaluator_id=EVALUATOR_ID,
            evaluator_version=EVALUATOR_VERSION,
            task_version_id=task_version.task_version_id,
            passed=passed,
            score=score,
            checks=checks,
            errors=errors,
            summary_ar=f"النتيجة {score} من 100. {'ناجح' if passed else 'محتاج تعديل'}.",
            summary_en=f"Score {score}/100. {'Passed' if passed else 'Needs revision'}.",
            duration_ms=(self._clock() - started) // 1_000_000,
        )


def _is_supported(package: TaskPackage) -> bool:
    return (
        (package.evaluator_id, package.evaluator_version) == (EVALUATOR_ID, EVALUATOR_VERSION)
        and {spec.check_id for spec in package.checks} == set(RULES)
        and isinstance(package.policy, CleaningPolicy)
        and GRADED_COLUMNS <= set(package.policy.required_columns)
    )


def is_passing(score: int, checks: Iterable[EvaluationCheck], package: TaskPackage) -> bool:
    """Scoring policy v1: ``score >= pass_threshold AND every critical check passed``."""

    critical = package.critical_check_ids
    return score >= package.pass_threshold and all(
        check.passed for check in checks if check.check_id in critical
    )


def diagnostic_code(check_id: str, passed: bool) -> str:
    """The finite v1 check vocabulary: ``<check_id>_passed`` or ``<check_id>_failed``."""

    return f"{check_id}_{'passed' if passed else 'failed'}"


def parse_records(table: Table, policy: CleaningPolicy) -> tuple[Record, ...]:
    return tuple(record for _, record in parse_rows(table, policy))


def parse_rows(table: Table, policy: CleaningPolicy) -> NumberedRecords:
    """Non-blank data rows with their spreadsheet row numbers (the header is row 1)."""

    if not table.rows:
        raise ArtifactRejected("missing_columns")
    header, *body = table.rows
    columns = tuple(name.strip().lower() for name in header)
    if len(set(columns)) != len(columns):
        raise ArtifactRejected("duplicate_columns")
    if not set(policy.required_columns) <= set(columns):
        raise ArtifactRejected("missing_columns")
    numbered = tuple(
        (index + 2, _record(columns, row))
        for index, row in enumerate(body)
        if any(cell.strip() for cell in row)
    )
    if len(numbered) < policy.min_rows:
        raise ArtifactRejected("too_few_rows")
    return numbered


def grade(spec: CheckSpec, failing_rows: int) -> EvaluationCheck:
    passed = failing_rows == 0
    if passed:
        details_ar, details_en = PASSED_DETAIL
    else:
        details_ar = f"{spec.hint_ar} عدد الصفوف اللي محتاجة تتصلح: {failing_rows}."
        details_en = f"{spec.hint_en} Rows to fix: {failing_rows}."
    return EvaluationCheck(
        check_id=spec.check_id,
        passed=passed,
        weight=spec.points,
        details_ar=details_ar,
        details_en=details_en,
        diagnostic_code=diagnostic_code(spec.check_id, passed),
    )


def not_evaluated(spec: CheckSpec) -> EvaluationCheck:
    details_ar, details_en = NOT_EVALUATED_DETAIL
    return EvaluationCheck(
        check_id=spec.check_id,
        passed=False,
        weight=spec.points,
        details_ar=details_ar,
        details_en=details_en,
        diagnostic_code=diagnostic_code(spec.check_id, passed=False),
    )


def unique_orders(records: Sequence[Record], policy: CleaningPolicy) -> tuple[RowIssue | None, ...]:
    key_column = policy.business_key
    keys = [record[key_column].strip() for record in records]
    counts = Counter(keys)
    return tuple(
        RowIssue(key_column, "missing_order_id")
        if not key
        else RowIssue(key_column, "duplicate_order_id")
        if counts[key] > 1
        else None
        for key in keys
    )


def standard_dates(
    records: Sequence[Record], policy: CleaningPolicy
) -> tuple[RowIssue | None, ...]:
    return tuple(
        None
        if _is_date(record["order_date"], policy.target_date_format)
        else RowIssue("order_date", "nonstandard_date")
        for record in records
    )


def valid_numeric_values(
    records: Sequence[Record], policy: CleaningPolicy
) -> tuple[RowIssue | None, ...]:
    return tuple(_amount_issue(record, policy) for record in records)


def complete_customer_records(
    records: Sequence[Record], policy: CleaningPolicy
) -> tuple[RowIssue | None, ...]:
    return tuple(_contact_issue(record, policy) for record in records)


RULES: Mapping[str, Rule] = {
    "unique_orders": unique_orders,
    "standard_dates": standard_dates,
    "valid_numeric_values": valid_numeric_values,
    "complete_customer_records": complete_customer_records,
}


def _record(columns: Sequence[str], row: Sequence[str]) -> Record:
    """Missing trailing cells read as empty; cells beyond the header are ignored."""

    return {name: row[index] if index < len(row) else "" for index, name in enumerate(columns)}


def _is_date(value: str, target_format: str) -> bool:
    try:
        parsed = datetime.strptime(value, target_format).replace(tzinfo=UTC)
        return parsed.strftime(target_format) == value
    except ValueError:
        return False


def _decimal(value: str) -> Decimal | None:
    try:
        number = Decimal(value.strip())
    except InvalidOperation:
        return None
    return number if number.is_finite() else None


def _count(issues: Iterable[RowIssue | None]) -> int:
    return sum(issue is not None for issue in issues)


def _amount_issue(record: Record, policy: CleaningPolicy) -> RowIssue | None:
    quantity_text = record["quantity"].strip()
    unit_price = _decimal(record["unit_price"])
    revenue = _decimal(record["revenue"])
    if not QUANTITY.match(quantity_text) or int(quantity_text) == 0:
        return RowIssue("quantity", "invalid_quantity")
    if unit_price is None or unit_price < 0:
        return RowIssue("unit_price", "invalid_unit_price")
    if revenue is None or revenue < 0:
        return RowIssue("revenue", "invalid_revenue")
    if abs(revenue - int(quantity_text) * unit_price) > policy.revenue_tolerance:
        return RowIssue("revenue", "revenue_mismatch")
    return None


def _contact_issue(record: Record, policy: CleaningPolicy) -> RowIssue | None:
    email = record["customer_email"].strip()
    if email:
        return None if EMAIL.match(email) else RowIssue("customer_email", "invalid_email")
    reason_column = policy.missing_email_reason_column
    if record[reason_column].strip() == policy.missing_email_reason_value:
        return None
    return RowIssue(reason_column, "missing_email_reason")


def business_impact(records: Sequence[Record], policy: CleaningPolicy) -> list[ImpactMetric]:
    """What the defects in the learner's own file would cost the sales report.

    Duplicate copies overstate revenue by their own amounts; rows with broken amounts make
    their revenue untrustworthy; contact gaps and non-standard dates count affected rows.
    """

    duplicates = unique_orders(records, policy)
    amounts = valid_numeric_values(records, policy)
    seen: set[str] = set()
    overstated = Decimal(0)
    untrusted = Decimal(0)
    for record, duplicate, amount in zip(records, duplicates, amounts, strict=True):
        key = record[policy.business_key].strip()
        revenue = _decimal(record["revenue"])
        repeated = duplicate is not None and duplicate.code == "duplicate_order_id" and key in seen
        seen.add(key)
        if repeated and revenue is not None and revenue > 0:
            overstated += revenue
        elif amount is not None and revenue is not None:
            untrusted += abs(revenue)
    return [
        ImpactMetric(metric_id="revenue_overstated", value=overstated, unit="egp"),
        ImpactMetric(metric_id="revenue_untrusted", value=untrusted, unit="egp"),
        ImpactMetric(
            metric_id="customers_unreachable",
            value=Decimal(_count(complete_customer_records(records, policy))),
            unit="customers",
        ),
        ImpactMetric(
            metric_id="orders_off_timeline",
            value=Decimal(_count(standard_dates(records, policy))),
            unit="orders",
        ),
    ]
