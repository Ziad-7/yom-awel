import io
import json
import math
from decimal import Decimal
from typing import NoReturn

import pytest
from openpyxl import Workbook

from tests.evaluation.support import (
    PACKAGE,
    REFERENCE,
    as_json,
    evaluate_bytes,
    evaluate_rows,
    failed_checks,
    with_cell,
)
from yom_awel.domain.contracts import EvaluationResult
from yom_awel.evaluation.clean_sales_dataset import COLUMNS, to_csv

CLEAN_CSV = to_csv(REFERENCE.clean)
HEADER, *BODY = CLEAN_CSV.splitlines()


def csv_bytes(header: str, body: list[str]) -> bytes:
    return ("\n".join([header, *body]) + "\n").encode()


def error_codes(content: bytes) -> list[str]:
    return [error.code for error in evaluate_bytes(content).errors]


def reordered(text: str, order: list[int]) -> str:
    return "\n".join(",".join(line.split(",")[i] for i in order) for line in text.splitlines())


def test_column_order_does_not_matter() -> None:
    order = list(reversed(range(len(COLUMNS))))

    assert evaluate_bytes((reordered(CLEAN_CSV, order) + "\n").encode()).score == 100


def test_extra_columns_are_ignored() -> None:
    content = csv_bytes(HEADER + ",notes", [line + ",checked" for line in BODY])

    assert evaluate_bytes(content).score == 100


def test_header_names_are_normalized_once_for_case_and_whitespace() -> None:
    header = ",".join(f"  {name.upper()} " for name in COLUMNS)

    assert evaluate_bytes(csv_bytes(header, BODY)).score == 100


@pytest.mark.parametrize("missing", ["order_id", "missing_email_reason"])
def test_missing_required_column_is_a_stable_error(missing: str) -> None:
    keep = [i for i, name in enumerate(COLUMNS) if name != missing]
    content = (reordered(CLEAN_CSV, keep) + "\n").encode()

    assert error_codes(content) == ["missing_columns"]


def test_duplicate_header_is_a_stable_error() -> None:
    content = csv_bytes(HEADER + ",Order_ID", [line + ",x" for line in BODY])

    assert error_codes(content) == ["duplicate_columns"]


@pytest.mark.parametrize(
    ("content", "code"),
    [(b"", "missing_columns"), (csv_bytes(HEADER, []), "too_few_rows")],
    ids=["empty-file", "header-only"],
)
def test_empty_datasets_fail_with_a_stable_error(content: bytes, code: str) -> None:
    result = evaluate_bytes(content)

    assert [error.code for error in result.errors] == [code]
    assert result.score == 0


def test_min_rows_boundary() -> None:
    assert evaluate_bytes(csv_bytes(HEADER, BODY)).errors == []
    assert error_codes(csv_bytes(HEADER, BODY[:-1])) == ["too_few_rows"]
    assert PACKAGE.policy.min_rows == len(BODY)


def test_blank_lines_are_not_rows() -> None:
    content = csv_bytes(HEADER, [BODY[0], "", ",,,,,,", *BODY[1:]])

    assert evaluate_bytes(content).score == 100


def test_conflicting_duplicate_fails_unique_orders() -> None:
    conflicting = dict(REFERENCE.clean[1], order_id=REFERENCE.clean[0]["order_id"])

    result = evaluate_rows([*REFERENCE.clean, conflicting])

    assert failed_checks(result) == ["unique_orders"]


@pytest.mark.parametrize(("delta", "passes"), [("0.01", True), ("-0.01", True), ("0.02", False)])
def test_revenue_tolerance_is_inclusive_at_one_cent(delta: str, passes: bool) -> None:
    revenue = Decimal(REFERENCE.clean[0]["revenue"]) + Decimal(delta)

    result = evaluate_rows(with_cell(0, "revenue", str(revenue)))

    assert ("valid_numeric_values" not in failed_checks(result)) is passes


@pytest.mark.parametrize(
    "value",
    ["2026-1-5", "2026-01-05T00:00:00Z", "2026-01-05 +02:00", "05/01/2026", "=TODAY()", ""],
)
def test_only_zero_padded_iso_dates_pass(value: str) -> None:
    assert failed_checks(evaluate_rows(with_cell(0, "order_date", value))) == ["standard_dates"]


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("quantity", "=1+1"),
        ("quantity", "1E1"),
        ("quantity", "2.0"),
        ("quantity", "+3"),
        ("quantity", ""),
        ("unit_price", "NaN"),
        ("unit_price", "Infinity"),
        ("unit_price", "=B2*2"),
        ("revenue", "=D2*E2"),
        ("revenue", "1,000.00"),
    ],
)
def test_formulas_and_non_decimal_numbers_fail(column: str, value: str) -> None:
    result = evaluate_rows(with_cell(0, column, value))

    assert failed_checks(result) == ["valid_numeric_values"]


@pytest.mark.parametrize(
    ("email", "reason", "passes"),
    [
        ("", "unavailable", True),
        ("", "", False),
        ("", "Unavailable", False),
        ("buyer@example.com", "", True),
        ("buyer@example", "", False),
        ("two@@example.com", "", False),
    ],
)
def test_customer_contact_rule(email: str, reason: str, passes: bool) -> None:
    rows = with_cell(0, "customer_email", email)
    rows[0]["missing_email_reason"] = reason

    assert ("complete_customer_records" not in failed_checks(evaluate_rows(rows))) is passes


def test_row_order_does_not_change_the_result() -> None:
    forward = evaluate_bytes(csv_bytes(HEADER, BODY))
    backward = evaluate_bytes(csv_bytes(HEADER, list(reversed(BODY))))

    assert as_json(forward) == as_json(backward)


def test_short_rows_read_missing_trailing_cells_as_empty() -> None:
    with_email = next(i for i, row in enumerate(REFERENCE.clean) if row["customer_email"])
    without_email = next(i for i, row in enumerate(REFERENCE.clean) if not row["customer_email"])

    def truncate(index: int) -> list[str]:
        body = list(BODY)
        body[index] = body[index].rsplit(",", 1)[0]
        return body

    assert evaluate_bytes(csv_bytes(HEADER, truncate(with_email))).score == 100
    assert failed_checks(evaluate_bytes(csv_bytes(HEADER, truncate(without_email)))) == [
        "complete_customer_records"
    ]


def reject_constant(name: str) -> NoReturn:
    raise AssertionError(f"non-finite JSON constant {name}")


def assert_finite_json(result: EvaluationResult) -> None:
    json.loads(result.model_dump_json(), parse_constant=reject_constant)


@pytest.mark.parametrize("value", ["NaN", "-nan", "sNaN", "Infinity", "-Infinity", "inf", "1e999"])
@pytest.mark.parametrize("column", ["unit_price", "revenue"])
def test_non_finite_numbers_fail_their_check_and_keep_the_result_finite(
    column: str, value: str
) -> None:
    result = evaluate_rows(with_cell(0, column, value))

    assert failed_checks(result) == ["valid_numeric_values"]
    assert_finite_json(result)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_xlsx_numbers_fail_their_check_and_keep_the_result_finite(
    value: float,
) -> None:
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(COLUMNS)
    for index, row in enumerate(REFERENCE.clean):
        sheet.append([value if index == 0 and c == "revenue" else row[c] for c in COLUMNS])
    buffer = io.BytesIO()
    book.save(buffer)
    result = evaluate_bytes(buffer.getvalue(), filename="sales.xlsx")

    assert failed_checks(result) == ["valid_numeric_values"]
    assert_finite_json(result)
