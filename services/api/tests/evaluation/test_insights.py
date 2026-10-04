import asyncio
import csv
import hashlib
import itertools
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from yom_awel.domain.contracts import ArtifactRef, EvaluationResult
from yom_awel.evaluation.catalog import TaskCatalog, csv_to_xlsx
from yom_awel.evaluation.clean_sales_dataset import (
    REFERENCE_SEED,
    Row,
    apply_defects,
    generate,
    to_csv,
)
from yom_awel.evaluation.insights import SubmissionInsights

PACKAGES = Path(__file__).resolve().parents[4] / "task_packages"
CATALOG = TaskCatalog.load(PACKAGES)
EVALUATORS = CATALOG.evaluators()
REFERENCE = generate(REFERENCE_SEED)
SALES_EXAMPLES = PACKAGES / "client-email" / "1" / "examples"
VALID_SQL = """SELECT region, COUNT(*) AS paid_orders,
ROUND(SUM(quantity * unit_price), 2) AS total_revenue
FROM sales WHERE status = 'paid' GROUP BY region ORDER BY region;"""
HARDCODED_SQL = """SELECT 'Alexandria' AS region, 3 + (SELECT COUNT(order_id) FROM sales) * 0 AS paid_orders, 230 AS total_revenue
UNION ALL SELECT 'Aswan', 3, 150.5
UNION ALL SELECT 'Cairo', 4, 414.5
UNION ALL SELECT 'Giza', 4, 314"""


def artifact(content: bytes, filename: str) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=UUID(int=7),
        filename=filename,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )


def run(task_id: str, content: bytes, filename: str) -> tuple[EvaluationResult, SubmissionInsights]:
    task = CATALOG.get(task_id)
    evaluator = EVALUATORS[(task.package.evaluator_id, task.package.evaluator_version)]
    ref = artifact(content, filename)
    return (
        asyncio.run(evaluator.evaluate(task.task_version, ref)),
        asyncio.run(evaluator.insights(task.task_version, ref)),
    )


def assert_consistent(result: EvaluationResult, insights: SubmissionInsights) -> None:
    assert [(c.check_id, c.passed) for c in insights.checks] == [
        (c.check_id, c.passed) for c in result.checks
    ]
    assert insights.rejected_code == (result.errors[0].code if result.errors else None)
    robustness = insights.sql is not None and insights.sql.robustness_failed
    for check in insights.checks:
        explained = check.issue_count > 0 or robustness or insights.rejected_code is not None
        assert check.passed == (check.issue_count == 0) or (not check.passed and explained)


def csv_bytes(rows: list[Row] | tuple[Row, ...]) -> bytes:
    return to_csv(rows).encode()


SALES_INPUTS = [
    ("dirty", csv_bytes(REFERENCE.dirty)),
    ("clean", csv_bytes(REFERENCE.clean)),
    *(
        (defect.defect_id, csv_bytes(apply_defects(REFERENCE.clean, [defect])))
        for defect in REFERENCE.defects
    ),
    *(
        (f"{a.defect_id}+{b.defect_id}", csv_bytes(apply_defects(REFERENCE.clean, [a, b])))
        for a, b in itertools.combinations(REFERENCE.defects, 2)
    ),
    ("empty", b""),
    ("header-only", b"order_id,customer_email\n"),
]


@pytest.mark.parametrize(("name", "content"), SALES_INPUTS, ids=[n for n, _ in SALES_INPUTS])
def test_sales_insights_agree_with_the_grade_for_every_input(name: str, content: bytes) -> None:
    assert_consistent(*run("clean-sales", content, "sales.csv"))


@pytest.mark.parametrize("rows", [REFERENCE.dirty, REFERENCE.clean], ids=["dirty", "clean"])
def test_sales_insights_agree_for_xlsx_too(rows: tuple[Row, ...]) -> None:
    content = csv_to_xlsx(csv_bytes(rows))
    result, insights = run("clean-sales", content, "sales.xlsx")
    assert_consistent(result, insights)
    assert insights == run("clean-sales", csv_bytes(rows), "sales.csv")[1]


def test_clean_file_has_no_issues_and_no_cost() -> None:
    _, insights = run("clean-sales", csv_bytes(REFERENCE.clean), "sales.csv")

    assert insights.issues == []
    assert {metric.value for metric in insights.impact} == {Decimal(0)}
    assert insights.table is not None
    assert insights.table.total_rows == len(REFERENCE.clean)


def test_duplicates_point_at_every_copy_and_price_the_overstatement() -> None:
    duplicates = [d for d in REFERENCE.defects if d.kind == "duplicate_order"]
    rows = apply_defects(REFERENCE.clean, duplicates)
    _, insights = run("clean-sales", csv_bytes(rows), "sales.csv")

    assert {(i.check_id, i.column, i.issue) for i in insights.issues} == {
        ("unique_orders", "order_id", "duplicate_order_id")
    }
    seen: set[str] = set()
    expected = Decimal(0)
    for row in rows:
        if row["order_id"] in seen:
            expected += Decimal(row["revenue"])
        seen.add(row["order_id"])
    impact = {metric.metric_id: metric.value for metric in insights.impact}
    assert impact["revenue_overstated"] == expected > 0
    assert impact["revenue_untrusted"] == 0


def test_issue_rows_are_spreadsheet_rows_even_after_blank_lines() -> None:
    header, first, *rest = csv_bytes(REFERENCE.dirty).decode().splitlines()
    content = "\n".join([header, first, "", ",,,,,,", *rest]).encode() + b"\n"
    _, insights = run("clean-sales", content, "sales.csv")
    assert insights.table is not None
    by_row = {row.row: row.cells for row in insights.table.rows}
    columns = insights.table.columns
    lines = content.decode().splitlines()

    assert 3 not in by_row and 4 not in by_row
    for issue in insights.issues:
        cell = by_row[issue.row][columns.index(issue.column)]
        assert next(csv.reader([lines[issue.row - 1]]))[columns.index(issue.column)] == cell


def test_rejected_sales_file_explains_the_rejection_only() -> None:
    result, insights = run("clean-sales", b"PK\x03\x04 spoofed", "sales.csv")

    assert_consistent(result, insights)
    assert insights.rejected_code == "mime_mismatch"
    assert insights.table is None and insights.issues == [] and insights.impact == []


SQL_QUERIES = [
    VALID_SQL,
    VALID_SQL.replace("paid_orders", "orders"),
    VALID_SQL.replace("WHERE status = 'paid'", "WHERE status = 'paid' AND region != 'Aswan'"),
    VALID_SQL.replace("COUNT(*)", "COUNT(*) + 1"),
    VALID_SQL.replace("SUM(quantity * unit_price)", "SUM(quantity * unit_price) + 1"),
    VALID_SQL.replace(" WHERE status = 'paid'", ""),
    VALID_SQL.replace("GROUP BY region", "GROUP BY region, status"),
    HARDCODED_SQL,
    "DROP TABLE sales",
    "SELECT 1",
]


@pytest.mark.parametrize("query", SQL_QUERIES)
def test_sql_insights_agree_with_the_grade_for_every_query(query: str) -> None:
    assert_consistent(*run("sql-report", query.encode(), "report.sql"))


def test_valid_query_rows_are_all_correct() -> None:
    _, insights = run("sql-report", VALID_SQL.encode(), "report.sql")
    assert insights.sql is not None

    assert insights.sql.columns_ok and not insights.sql.robustness_failed
    assert insights.sql.missing_regions == 0
    assert all(
        (r.region_status, r.count_ok, r.revenue_ok) == ("ok", True, True) for r in insights.sql.rows
    )
    assert insights.impact[0].value == 0


def test_sql_findings_name_the_wrong_part_without_the_expected_value() -> None:
    _, missing = run(
        "sql-report",
        VALID_SQL.replace(
            "WHERE status = 'paid'", "WHERE status = 'paid' AND region != 'Aswan'"
        ).encode(),
        "report.sql",
    )
    _, counts = run("sql-report", VALID_SQL.replace("COUNT(*)", "COUNT(*) + 1").encode(), "r.sql")
    assert missing.sql is not None and counts.sql is not None

    assert missing.sql.missing_regions == 1
    assert "Aswan" not in str(missing.model_dump())
    assert all(not r.count_ok and r.revenue_ok for r in counts.sql.rows)


def test_hard_coded_numbers_are_caught_by_the_robustness_probe() -> None:
    _, insights = run("sql-report", HARDCODED_SQL.encode(), "report.sql")
    assert insights.sql is not None

    assert insights.sql.robustness_failed
    assert all(r.region_status == "ok" for r in insights.sql.rows)


def test_wrong_columns_mark_every_row_unreadable() -> None:
    _, insights = run("sql-report", VALID_SQL.replace("paid_orders", "orders").encode(), "r.sql")
    assert insights.sql is not None

    assert not insights.sql.columns_ok
    assert {r.region_status for r in insights.sql.rows} == {"unreadable"}


EMAIL_PASS = (SALES_EXAMPLES / "pass.en.txt").read_bytes()
EMAIL_INPUTS = [
    ("pass-en", EMAIL_PASS),
    ("pass-ar", (SALES_EXAMPLES / "pass.ar-EG.txt").read_bytes()),
    ("fail-en", (SALES_EXAMPLES / "fail.en.txt").read_bytes()),
    ("wrong-recipient", EMAIL_PASS.replace(b"salma.hassan@example.com", b"x@example.com")),
    ("wrong-date", EMAIL_PASS.replace(b"2026-10-03", b"2026-10-04")),
    ("wrong-amount", EMAIL_PASS.replace(b"120 EGP", b"1200 EGP")),
    ("wrong-window", EMAIL_PASS.replace(b"2 business days", b"3 business days")),
    ("no-closing", EMAIL_PASS.replace(b"Best regards", b"Goodbye")),
    ("crlf", EMAIL_PASS.replace(b"\n", b"\r\n")),
]


@pytest.mark.parametrize(("name", "content"), EMAIL_INPUTS, ids=[n for n, _ in EMAIL_INPUTS])
def test_email_insights_agree_with_the_grade_for_every_email(name: str, content: bytes) -> None:
    assert_consistent(*run("client-email", content, "email.txt"))


@pytest.mark.parametrize("content", [EMAIL_PASS, EMAIL_PASS.replace(b"\n", b"\r\n")])
def test_found_elements_point_at_the_learners_own_words(content: bytes) -> None:
    _, insights = run("client-email", content, "email.txt")
    assert insights.email is not None
    text = insights.email.text
    spans = {
        e.element_id: text[e.start : e.end]
        for e in insights.email.elements
        if e.start is not None and e.end is not None
    }

    assert all(e.found for e in insights.email.elements)
    assert spans["recipient"].startswith("To:")
    assert spans["subject_order"] == spans["order_id"] == "YA-2048"
    assert spans["refund_amount"].startswith("120")
    assert spans["company_signature"].casefold() == "yom awel"


def test_missing_elements_explain_the_failed_check() -> None:
    _, insights = run("client-email", EMAIL_PASS.replace(b"2026-10-03", b"2026-10-04"), "email.txt")
    assert insights.email is not None

    assert [e.element_id for e in insights.email.elements if not e.found] == ["updated_date"]
    assert insights.impact[0].value == 1


def test_rejected_email_explains_the_rejection_only() -> None:
    result, insights = run("client-email", EMAIL_PASS, "email.pdf")

    assert_consistent(result, insights)
    assert insights.rejected_code == "unsupported_type"
    assert insights.email is None
