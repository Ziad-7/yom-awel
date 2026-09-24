import asyncio
import shutil
from decimal import Decimal
from itertools import count
from pathlib import Path

import pytest

from tests.evaluation.support import (
    CHECK_IDS,
    PACKAGE,
    PACKAGE_ROOT,
    REFERENCE,
    TASK_VERSION,
    artifact_ref,
    as_json,
    evaluate_bytes,
    evaluate_rows,
    evaluate_xlsx,
    failed_checks,
    with_cell,
)
from yom_awel.domain.contracts import EvaluationCheck
from yom_awel.evaluation.clean_sales_dataset import Defect, apply_defects, to_csv
from yom_awel.evaluation.registry import EvaluatorRegistry, UnknownEvaluator
from yom_awel.evaluation.sales_cleaning import (
    EVALUATOR_ID,
    EVALUATOR_VERSION,
    SalesCleaningEvaluator,
    TaskVersionMismatch,
    UnpublishedTaskPackage,
    UnsupportedTaskPackage,
    is_passing,
)
from yom_awel.evaluation.task_package import TaskPackageError

DEFECT_KIND_TO_CHECK = {
    "duplicate_order": "unique_orders",
    "nonstandard_date": "standard_dates",
    "negative_value": "valid_numeric_values",
    "missing_email": "complete_customer_records",
}


def test_clean_reference_scores_100_with_no_errors() -> None:
    result = evaluate_rows(REFERENCE.clean)

    assert result.passed is True
    assert result.score == 100
    assert result.errors == []
    assert [check.check_id for check in result.checks] == CHECK_IDS
    assert [check.diagnostic_code for check in result.checks] == [
        f"{check_id}_passed" for check_id in CHECK_IDS
    ]


def test_learner_dirty_artifact_fails_every_check() -> None:
    content = (PACKAGE_ROOT / "data" / "sales_dirty.csv").read_bytes()

    result = evaluate_bytes(content)

    assert result.passed is False
    assert result.score == 0
    assert result.errors == []
    assert failed_checks(result) == CHECK_IDS


@pytest.mark.parametrize("defect", REFERENCE.defects, ids=lambda defect: defect.defect_id)
def test_each_planted_defect_fails_only_its_check(defect: Defect) -> None:
    result = evaluate_rows(apply_defects(REFERENCE.clean, [defect]))

    check_id = DEFECT_KIND_TO_CHECK[defect.kind]

    assert failed_checks(result) == [check_id]
    assert result.score == 75
    assert result.passed is (check_id not in PACKAGE.critical_check_ids)


def test_score_75_with_the_critical_check_failed_needs_a_retry() -> None:
    duplicate = next(d for d in REFERENCE.defects if d.kind == "duplicate_order")

    result = evaluate_rows(apply_defects(REFERENCE.clean, [duplicate]))

    assert (result.score, result.passed) == (75, False)
    assert failed_checks(result) == ["unique_orders"]


def check(check_id: str, passed: bool) -> EvaluationCheck:
    return EvaluationCheck(
        check_id=check_id,
        passed=passed,
        weight=25,
        details_ar="تفاصيل",
        details_en="details",
        diagnostic_code=f"{check_id}_{'passed' if passed else 'failed'}",
    )


@pytest.mark.parametrize(
    ("score", "critical_passed", "passed"),
    [(74, True, False), (75, False, False), (75, True, True), (100, True, True)],
)
def test_pass_rule_boundary_matrix(score: int, critical_passed: bool, passed: bool) -> None:
    checks = [check("unique_orders", critical_passed), check("standard_dates", True)]

    assert is_passing(score, checks, PACKAGE) is passed


def test_two_failed_checks_drop_below_the_pass_threshold() -> None:
    date_defect, email_defect = (
        next(d for d in REFERENCE.defects if d.kind == kind)
        for kind in ("nonstandard_date", "missing_email")
    )

    result = evaluate_rows(apply_defects(REFERENCE.clean, [date_defect, email_defect]))

    assert result.score == 50
    assert result.passed is False


@pytest.mark.parametrize(
    ("column", "value", "check_id", "rows_to_fix"),
    [
        ("order_id", "SO-1002", "unique_orders", 2),
        ("order_id", "", "unique_orders", 1),
        ("order_date", "2026-02-30", "standard_dates", 1),
        ("quantity", "0", "valid_numeric_values", 1),
        ("unit_price", "-1.00", "valid_numeric_values", 1),
        ("revenue", "-1.00", "valid_numeric_values", 1),
        ("revenue", str(Decimal(REFERENCE.clean[0]["revenue"]) + 5), "valid_numeric_values", 1),
        ("customer_email", "not-an-email", "complete_customer_records", 1),
    ],
)
def test_failed_check_reports_its_diagnostic_code_without_echoing_cells(
    column: str, value: str, check_id: str, rows_to_fix: int
) -> None:
    result = evaluate_rows(with_cell(0, column, value))
    failed = next(check for check in result.checks if check.check_id == check_id)

    assert failed_checks(result) == [check_id]
    assert failed.diagnostic_code == f"{check_id}_failed"
    assert failed.details_en.endswith(f"Rows to fix: {rows_to_fix}.")
    assert not value or value not in failed.details_en + failed.details_ar


def test_rejected_file_returns_one_error_and_every_check_failed() -> None:
    result = evaluate_bytes(b"PK\x03\x04 spoofed", filename="sales.csv")

    assert result.passed is False
    assert result.score == 0
    assert [(error.code, error.message) for error in result.errors] == [
        ("mime_mismatch", "File content does not match its declared CSV or XLSX format.")
    ]
    assert [check.diagnostic_code for check in result.checks] == [
        f"{check_id}_failed" for check_id in CHECK_IDS
    ]


@pytest.mark.parametrize("typed", [False, True], ids=["text-cells", "typed-cells"])
def test_xlsx_and_csv_of_the_same_table_grade_identically(typed: bool) -> None:
    datasets = [REFERENCE.clean, REFERENCE.dirty] + [
        apply_defects(REFERENCE.clean, [defect]) for defect in REFERENCE.defects
    ]

    for rows in datasets:
        assert as_json(evaluate_xlsx(rows, typed=typed)) == as_json(evaluate_rows(rows))


def test_xlsx_formula_cells_never_pass() -> None:
    result = evaluate_xlsx(with_cell(0, "revenue", "=D2*E2"))

    assert failed_checks(result) == ["valid_numeric_values"]


def test_same_artifact_and_versions_always_produce_the_same_result() -> None:
    content = (PACKAGE_ROOT / "data" / "sales_dirty.csv").read_bytes()

    assert len({as_json(evaluate_bytes(content)) for _ in range(5)}) == 1


def test_duration_comes_from_the_injected_clock() -> None:
    ticks = count(start=0, step=7_000_000)
    evaluator = SalesCleaningEvaluator(PACKAGE, clock=lambda: next(ticks))

    result = evaluate_bytes(to_csv(REFERENCE.clean).encode(), evaluator=evaluator)

    assert result.duration_ms == 7


@pytest.mark.parametrize(
    "field", ["task_id", "version", "evaluator_id", "evaluator_version", "pass_threshold"]
)
def test_rejects_a_task_version_the_package_does_not_describe(field: str) -> None:
    value = 50 if field == "pass_threshold" else "other"
    task_version = TASK_VERSION.model_copy(update={field: value})
    content = b"order_id\n"
    evaluator = SalesCleaningEvaluator(PACKAGE)

    with pytest.raises(TaskVersionMismatch):
        asyncio.run(evaluator.evaluate(task_version, artifact_ref(content)))


def test_rejects_a_package_it_cannot_grade() -> None:
    other = PACKAGE.model_copy(update={"evaluator_version": "2"})

    with pytest.raises(UnsupportedTaskPackage):
        SalesCleaningEvaluator(other)


def test_refuses_a_draft_package() -> None:
    with pytest.raises(UnpublishedTaskPackage) as error:
        SalesCleaningEvaluator(PACKAGE.model_copy(update={"status": "draft"}))
    assert error.value.code == "task_package_unpublished"


def test_production_binding_grades_from_the_verified_package_directory() -> None:
    evaluator = SalesCleaningEvaluator.from_directory(PACKAGE_ROOT, clock=lambda: 0)

    result = evaluate_bytes(to_csv(REFERENCE.clean).encode(), evaluator=evaluator)

    assert (result.score, result.passed) == (100, True)


def test_production_binding_refuses_modified_content(tmp_path: Path) -> None:
    copy = shutil.copytree(PACKAGE_ROOT, tmp_path / "clean-sales")
    with (copy / "content" / "brief.en.md").open("a", encoding="utf-8") as brief:
        brief.write("\nEdited after review.\n")

    with pytest.raises(TaskPackageError, match="changed after it was pinned"):
        SalesCleaningEvaluator.from_directory(copy)


def test_registry_delegates_to_the_exact_version() -> None:
    registry = EvaluatorRegistry(
        {(EVALUATOR_ID, EVALUATOR_VERSION): SalesCleaningEvaluator(PACKAGE, clock=lambda: 0)}
    )
    content = (PACKAGE_ROOT / "data" / "sales_dirty.csv").read_bytes()

    result = asyncio.run(registry.evaluate(TASK_VERSION, artifact_ref(content)))

    assert as_json(result) == as_json(evaluate_bytes(content))


@pytest.mark.parametrize("key", [("sales-cleaning", "2"), ("other", "1")])
def test_registry_never_falls_back_to_another_version(key: tuple[str, str]) -> None:
    registry = EvaluatorRegistry(
        {(EVALUATOR_ID, EVALUATOR_VERSION): SalesCleaningEvaluator(PACKAGE)}
    )
    task_version = TASK_VERSION.model_copy(
        update={"evaluator_id": key[0], "evaluator_version": key[1]}
    )
    content = b"order_id\n"

    with pytest.raises(UnknownEvaluator) as error:
        asyncio.run(registry.evaluate(task_version, artifact_ref(content)))
    assert error.value.code == "unknown_evaluator"
