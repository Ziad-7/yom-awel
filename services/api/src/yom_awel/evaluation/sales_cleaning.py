"""sales-cleaning@1: deterministic grading of the clean-sales task."""

import re
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
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
# A rule returns how many rows violate it; zero passes the check.
Rule = Callable[[Sequence[Record], CleaningPolicy], int]


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
            grade(spec, RULES[spec.check_id](records, policy)) for spec in self._package.checks
        ]
        return self._result(task_version, checks, [], started)

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
    if not table.rows:
        raise ArtifactRejected("missing_columns")
    header, *body = table.rows
    columns = tuple(name.strip().lower() for name in header)
    if len(set(columns)) != len(columns):
        raise ArtifactRejected("duplicate_columns")
    if not set(policy.required_columns) <= set(columns):
        raise ArtifactRejected("missing_columns")
    records = tuple(_record(columns, row) for row in body if any(cell.strip() for cell in row))
    if len(records) < policy.min_rows:
        raise ArtifactRejected("too_few_rows")
    return records


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


def unique_orders(records: Sequence[Record], policy: CleaningPolicy) -> int:
    keys = [record[policy.business_key].strip() for record in records]
    counts = Counter(keys)
    return sum(not key or counts[key] > 1 for key in keys)


def standard_dates(records: Sequence[Record], policy: CleaningPolicy) -> int:
    return sum(not _is_date(record["order_date"], policy.target_date_format) for record in records)


def valid_numeric_values(records: Sequence[Record], policy: CleaningPolicy) -> int:
    return sum(not _is_valid_amount(record, policy) for record in records)


def complete_customer_records(records: Sequence[Record], policy: CleaningPolicy) -> int:
    return sum(not _has_contact(record, policy) for record in records)


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


def _is_valid_amount(record: Record, policy: CleaningPolicy) -> bool:
    quantity_text = record["quantity"].strip()
    unit_price = _decimal(record["unit_price"])
    revenue = _decimal(record["revenue"])
    if not QUANTITY.match(quantity_text) or int(quantity_text) == 0:
        return False
    if unit_price is None or unit_price < 0 or revenue is None or revenue < 0:
        return False
    return abs(revenue - int(quantity_text) * unit_price) <= policy.revenue_tolerance


def _has_contact(record: Record, policy: CleaningPolicy) -> bool:
    email = record["customer_email"].strip()
    if email:
        return EMAIL.match(email) is not None
    reason = record[policy.missing_email_reason_column].strip()
    return reason == policy.missing_email_reason_value
