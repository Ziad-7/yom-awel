"""Real SQL report grading and untrusted-query boundaries."""

import asyncio
import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from yom_awel.domain.contracts import ArtifactRef
from yom_awel.evaluation.catalog import build_task_version
from yom_awel.evaluation.sql_report import SqlReportEvaluator
from yom_awel.evaluation.task_package import load_task_package

ROOT = Path(__file__).resolve().parents[4] / "task_packages" / "sql-report" / "1"
PACKAGE = load_task_package(ROOT)
VERSION = build_task_version(PACKAGE, "مهمة SQL", "SQL task")
VALID = """SELECT region, COUNT(*) AS paid_orders,
ROUND(SUM(quantity * unit_price), 2) AS total_revenue
FROM sales WHERE status = 'paid' GROUP BY region ORDER BY region;"""


def grade(query: str | bytes, filename: str = "report.sql"):
    content = query.encode("utf-8") if isinstance(query, str) else query
    artifact = ArtifactRef(
        artifact_id=uuid4(),
        filename=filename,
        content=content,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
    return asyncio.run(SqlReportEvaluator.from_directory(ROOT).evaluate(VERSION, artifact))


def failed(result) -> set[str]:
    return {check.check_id for check in result.checks if not check.passed}


def test_valid_grouped_paid_sales_passes_all_four_checks() -> None:
    result = grade(VALID)
    assert result.passed is True
    assert result.score == 100
    assert result.errors == []
    assert failed(result) == set()


def test_wrong_aliases_fail_schema_even_when_values_are_right() -> None:
    result = grade(VALID.replace("paid_orders", "orders"))
    assert result.score == 0
    assert "report_columns" in failed(result)


def test_missing_paid_region_fails_region_coverage() -> None:
    result = grade(
        VALID.replace("WHERE status = 'paid'", "WHERE status = 'paid' AND region != 'Aswan'")
    )
    assert result.passed is False
    assert "paid_regions" in failed(result)


def test_count_and_revenue_grade_actual_query_output() -> None:
    wrong_count = grade(VALID.replace("COUNT(*)", "COUNT(*) + 1"))
    wrong_revenue = grade(
        VALID.replace("SUM(quantity * unit_price)", "SUM(quantity * unit_price) + 1")
    )
    assert failed(wrong_count) == {"paid_order_counts"}
    assert failed(wrong_revenue) == {"paid_revenue"}


def test_pending_and_cancelled_orders_are_not_counted() -> None:
    result = grade(VALID.replace(" WHERE status = 'paid'", ""))
    assert result.passed is False
    assert {"paid_order_counts", "paid_revenue"} <= failed(result)


def test_hardcoded_exact_answer_without_reading_sales_is_rejected() -> None:
    query = """SELECT 'Alexandria' AS region, 3 AS paid_orders, 230 AS total_revenue
UNION ALL SELECT 'Aswan', 3, 150.5
UNION ALL SELECT 'Cairo', 4, 414.5
UNION ALL SELECT 'Giza', 4, 314"""

    result = grade(query)

    assert result.passed is False
    assert result.score == 0
    assert [error.code for error in result.errors] == ["sql_query_rejected"]


def test_hardcoded_answers_with_noop_sales_read_fail_hidden_dataset() -> None:
    query = """SELECT 'Alexandria' AS region, 3 + (SELECT COUNT(*) FROM sales) * 0 AS paid_orders, 230 AS total_revenue
UNION ALL SELECT 'Aswan', 3, 150.5
UNION ALL SELECT 'Cairo', 4, 414.5
UNION ALL SELECT 'Giza', 4, 314"""

    result = grade(query)

    assert result.passed is False
    assert {"paid_regions", "paid_order_counts", "paid_revenue"} <= failed(result)


@pytest.mark.parametrize(
    "query",
    [
        "DROP TABLE sales",
        "UPDATE sales SET status = 'paid'",
        "PRAGMA database_list",
        "ATTACH DATABASE ':memory:' AS extra",
        "SELECT * FROM sqlite_master",
        "SELECT load_extension('evil')",
        "SELECT 1; DELETE FROM sales",
        "WITH RECURSIVE loop(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM loop) SELECT x FROM loop",
        "SELECT * FROM sales CROSS JOIN sales AS b CROSS JOIN sales AS c CROSS JOIN sales AS d",
    ],
)
def test_unsafe_or_invalid_sql_fails_safely(query: str) -> None:
    result = grade(query)
    assert result.passed is False
    assert result.score == 0
    assert result.errors
    assert query not in result.errors[0].message


def test_non_utf8_and_wrong_extension_fail_safely() -> None:
    for query, filename in [(b"\xff\xfe", "report.sql"), (VALID, "report.csv")]:
        result = grade(query, filename)
        assert result.score == 0
        assert result.errors


def test_same_query_is_reproducible() -> None:
    outcomes = [grade(VALID) for _ in range(3)]
    assert {(o.score, o.passed, tuple(c.diagnostic_code for c in o.checks)) for o in outcomes} == {
        (
            100,
            True,
            tuple(
                f"{check_id}_passed"
                for check_id in (
                    "report_columns",
                    "paid_regions",
                    "paid_order_counts",
                    "paid_revenue",
                )
            ),
        )
    }
