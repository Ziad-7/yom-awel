"""Bounded, deterministic grading of a learner's SQLite sales report query."""

import csv
import hashlib
import io
import re
import sqlite3
import time
from collections.abc import Callable
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
from yom_awel.evaluation.task_package import SqlReportPolicy, TaskPackage, load_task_package

EVALUATOR_ID = "sql-report"
EVALUATOR_VERSION = "1"
CHECK_IDS = ("report_columns", "paid_regions", "paid_order_counts", "paid_revenue")
OUTPUT_COLUMNS = ("region", "paid_orders", "total_revenue")
SOURCE_COLUMNS = ("order_id", "region", "status", "quantity", "unit_price")
MAX_QUERY_BYTES = 65536
MAX_OUTPUT_COLUMNS = 10
MAX_CELL_CHARS = 4096
FUNCTIONS = frozenset({"sum", "count", "round", "lower", "upper", "trim", "coalesce", "abs"})
Clock = Callable[[], int]
SourceRow = tuple[str, str, str, int, str]
SourceRows = tuple[SourceRow, ...]


class SqlReportEvaluator:
    def __init__(self, package: TaskPackage, source: bytes, clock: Clock = time.perf_counter_ns):
        if (package.evaluator_id, package.evaluator_version) != (EVALUATOR_ID, EVALUATOR_VERSION):
            raise DomainError("unsupported_task_package", "SQL report evaluator needs sql-report@1")
        if package.status != "published" or {c.check_id for c in package.checks} != set(CHECK_IDS):
            raise DomainError(
                "task_package_invalid", "SQL report package is not published or balanced"
            )
        if not isinstance(package.policy, SqlReportPolicy):
            raise DomainError("task_package_invalid", "SQL report policy is required")
        self._package = package
        self._policy = package.policy
        self._source = _read_source(source)
        self._clock = clock

    @classmethod
    def from_directory(cls, root: Path, clock: Clock = time.perf_counter_ns) -> Self:
        package = load_task_package(root)
        if not isinstance(package.policy, SqlReportPolicy):
            raise DomainError("task_package_invalid", "SQL report policy is required")
        source = root / package.policy.source_path
        if not source.resolve().is_relative_to(root.resolve()):
            raise DomainError("task_package_invalid", "SQL source path escapes task package")
        return cls(package, source.read_bytes(), clock)

    async def evaluate(self, task_version: TaskVersion, artifact: ArtifactRef) -> EvaluationResult:
        package = self._package
        if (
            task_version.task_id,
            task_version.version,
            task_version.evaluator_id,
            task_version.evaluator_version,
            task_version.pass_threshold,
        ) != (
            package.task_id,
            package.version,
            EVALUATOR_ID,
            EVALUATOR_VERSION,
            package.pass_threshold,
        ):
            raise DomainError("task_version_mismatch", "SQL task version differs from package")
        started = self._clock()
        try:
            query = _read_query(artifact, package.limits.max_bytes)
            names, rows = self._execute(query, self._source)
            failures = self._grade(names, rows, self._source)
            probe = _probe_source(self._source)
            probe_names, probe_rows = self._execute(query, probe)
            failures.update(self._grade(probe_names, probe_rows, probe))
            errors: list[EvaluationError] = []
        except QueryRejected as rejection:
            failures = set(CHECK_IDS)
            errors = [EvaluationError(code=rejection.code, message=rejection.message)]
        checks = [
            EvaluationCheck(
                check_id=spec.check_id,
                passed=spec.check_id not in failures,
                weight=spec.points,
                details_ar=("الفحص سليم." if spec.check_id not in failures else spec.hint_ar),
                details_en=(
                    "This check passed." if spec.check_id not in failures else spec.hint_en
                ),
                diagnostic_code=f"{spec.check_id}_{'failed' if spec.check_id in failures else 'passed'}",
            )
            for spec in package.checks
        ]
        score = sum(c.weight for c in checks if c.passed)
        passed = (
            not errors
            and score >= package.pass_threshold
            and all(c.passed for c in checks if c.check_id in package.critical_check_ids)
        )
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
            duration_ms=max(0, (self._clock() - started) // 1_000_000),
        )

    def _execute(
        self, query: str, source: SourceRows
    ) -> tuple[tuple[str, ...], list[tuple[object, ...]]]:
        policy = self._policy
        connection = sqlite3.connect(":memory:")
        try:
            connection.execute(
                "CREATE TABLE sales (order_id TEXT, region TEXT, status TEXT, quantity INTEGER, unit_price NUMERIC)"
            )
            connection.executemany("INSERT INTO sales VALUES (?, ?, ?, ?, ?)", source)
            connection.commit()
            deadline = time.monotonic() + 0.5
            remaining = policy.max_query_steps
            read_sales = False

            def progress() -> int:
                nonlocal remaining
                remaining -= 100
                return int(remaining < 0 or time.monotonic() > deadline)

            def authorize(
                action: int,
                arg1: str | None,
                arg2: str | None,
                _db: str | None,
                _trigger: str | None,
            ) -> int:
                nonlocal read_sales
                if action == sqlite3.SQLITE_SELECT:
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_READ and arg1 == "sales" and arg2 in SOURCE_COLUMNS:
                    read_sales = True
                    return sqlite3.SQLITE_OK
                if action == sqlite3.SQLITE_FUNCTION and (arg2 or "").lower() in FUNCTIONS:
                    return sqlite3.SQLITE_OK
                return sqlite3.SQLITE_DENY

            connection.set_authorizer(authorize)
            connection.set_progress_handler(progress, 100)
            try:
                cursor = connection.execute(query)
                names = tuple(str(col[0]).lower() for col in cursor.description or ())
                if len(names) > MAX_OUTPUT_COLUMNS:
                    raise QueryRejected("sql_output_too_large", "Query returned too many columns")
                rows = cursor.fetchmany(policy.max_output_rows + 1)
                if len(rows) > policy.max_output_rows or any(
                    len(str(cell)) > MAX_CELL_CHARS for row in rows for cell in row
                ):
                    raise QueryRejected(
                        "sql_output_too_large", "Query output exceeds the safe limit"
                    )
                if not read_sales:
                    raise QueryRejected(
                        "sql_query_rejected", "Query must read from the sales table"
                    )
                return names, rows
            except sqlite3.Error as error:
                # Error text can include learner SQL or data; never echo it.
                raise QueryRejected(
                    "sql_query_rejected", "Query is invalid or exceeds the safe execution limit"
                ) from error
            finally:
                connection.set_progress_handler(None, 0)
                connection.set_authorizer(None)
        finally:
            connection.close()

    def _grade(
        self, names: tuple[str, ...], rows: list[tuple[object, ...]], source: SourceRows
    ) -> set[str]:
        failures: set[str] = set()
        if names != OUTPUT_COLUMNS:
            return set(CHECK_IDS)
        actual: dict[str, tuple[int, Decimal]] = {}
        for region, count, revenue in rows:
            if not isinstance(region, str) or region in actual:
                return set(CHECK_IDS) - {"report_columns"}
            try:
                if not isinstance(count, (int, str)):
                    raise TypeError("count must be numeric")
                paid_count = int(count)
                paid_revenue = Decimal(str(revenue)).quantize(Decimal("0.01"))
            except (ValueError, TypeError, InvalidOperation):
                return set(CHECK_IDS) - {"report_columns"}
            actual[region] = (paid_count, paid_revenue)
        expected: dict[str, tuple[int, Decimal]] = {}
        for _order, region, status, quantity, price in source:
            if status != "paid":
                continue
            old_count, old_revenue = expected.get(region, (0, Decimal(0)))
            expected[region] = (old_count + 1, old_revenue + quantity * Decimal(str(price)))
        if set(actual) != set(expected):
            failures.add("paid_regions")
        if any(
            actual.get(region, (None, None))[0] != count for region, (count, _) in expected.items()
        ):
            failures.add("paid_order_counts")
        if any(
            actual.get(region, (None, None))[1] != revenue
            for region, (_, revenue) in expected.items()
        ):
            failures.add("paid_revenue")
        return failures


class QueryRejected(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _read_query(artifact: ArtifactRef, max_bytes: int) -> str:
    content = artifact.content
    if (
        len(content) != artifact.size_bytes
        or hashlib.sha256(content).hexdigest() != artifact.sha256
    ):
        raise DomainError(
            "artifact_integrity_failed", "Uploaded SQL does not match its recorded metadata"
        )
    if len(content) > min(max_bytes, MAX_QUERY_BYTES):
        raise QueryRejected("artifact_too_large", "SQL file exceeds the size limit")
    if not artifact.filename.lower().endswith(".sql") or b"\x00" in content:
        raise QueryRejected("unsupported_type", "Upload a UTF-8 .sql file")
    try:
        query = content.decode("utf-8-sig").strip()
    except UnicodeDecodeError as error:
        raise QueryRejected("artifact_unreadable", "SQL file must be UTF-8 text") from error
    if not re.match(r"(?is)^select\b", query):
        raise QueryRejected("sql_query_rejected", "Submit one SELECT query")
    return query


def _read_source(content: bytes) -> SourceRows:
    try:
        rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline="")))
        if not rows or tuple(rows[0]) != SOURCE_COLUMNS:
            raise ValueError("wrong source header")
        return tuple(
            (
                row["order_id"],
                row["region"],
                row["status"],
                int(row["quantity"]),
                str(Decimal(row["unit_price"])),
            )
            for row in rows
        )
    except (UnicodeDecodeError, ValueError, KeyError, InvalidOperation) as error:
        raise DomainError("task_package_invalid", "SQL source data is invalid") from error


def _probe_source(source: SourceRows) -> SourceRows:
    """A second dataset makes a memorized answer fail while preserving task semantics."""

    paid_index = next((i for i, row in enumerate(source) if row[2] == "paid"), None)
    if paid_index is None:
        raise DomainError("task_package_invalid", "SQL source needs paid orders")
    rows = list(source)
    order_id, region, status, quantity, price = rows[paid_index]
    rows[paid_index] = (order_id, region, status, quantity + 3, price)
    rows.append(("SO-PROBE-EXISTING", region, "paid", 2, "17.25"))
    new_region = "Validation region"
    while new_region in {row[1] for row in rows}:
        new_region += " x"
    rows.append(("SO-PROBE-NEW", new_region, "paid", 4, "23.50"))
    return tuple(rows)
