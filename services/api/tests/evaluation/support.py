import asyncio
import hashlib
import io
import json
from collections.abc import Iterable
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import UUID

from openpyxl import Workbook

from yom_awel.domain.contracts import ArtifactRef, EvaluationResult, TaskVersion
from yom_awel.evaluation.clean_sales_dataset import COLUMNS, REFERENCE_SEED, Row, generate, to_csv
from yom_awel.evaluation.sales_cleaning import SalesCleaningEvaluator
from yom_awel.evaluation.task_package import MANIFEST_NAME, TaskPackage, parse_task_package

ROOT = Path(__file__).resolve().parents[4]
PACKAGE_ROOT = ROOT / "task_packages" / "clean-sales" / "1"
PACKAGE: TaskPackage = parse_task_package(
    (PACKAGE_ROOT / MANIFEST_NAME).read_text(encoding="utf-8")
)
TASK_VERSION = TaskVersion.model_validate_json(
    (ROOT / "contracts" / "fixtures" / "task-version-clean-sales.json").read_text("utf-8")
)
REFERENCE = generate(REFERENCE_SEED)
CHECK_IDS = [check.check_id for check in PACKAGE.checks]


def artifact_ref(content: bytes, filename: str = "sales.csv") -> ArtifactRef:
    return ArtifactRef(
        artifact_id=UUID("00000000-0000-0000-0000-000000000005"),
        filename=filename,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )


def evaluate_bytes(
    content: bytes,
    filename: str = "sales.csv",
    evaluator: SalesCleaningEvaluator | None = None,
) -> EvaluationResult:
    grader = evaluator or SalesCleaningEvaluator(PACKAGE, clock=lambda: 0)
    return asyncio.run(grader.evaluate(TASK_VERSION, artifact_ref(content, filename)))


def evaluate_rows(rows: Iterable[Row]) -> EvaluationResult:
    return evaluate_bytes(to_csv(rows).encode())


def to_xlsx(rows: Iterable[Row], *, typed: bool = False) -> bytes:
    """One worksheet holding ``rows``: every cell as text, or typed the way Excel stores it."""

    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.append(COLUMNS)
    for row in rows:
        sheet.append([_typed(column, row[column]) if typed else row[column] for column in COLUMNS])
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def evaluate_xlsx(rows: Iterable[Row], *, typed: bool = False) -> EvaluationResult:
    return evaluate_bytes(to_xlsx(rows, typed=typed), filename="sales.xlsx")


def failed_checks(result: EvaluationResult) -> list[str]:
    return [check.check_id for check in result.checks if not check.passed]


def with_cell(row_index: int, column: str, value: str) -> list[Row]:
    rows = [dict(row) for row in REFERENCE.clean]
    rows[row_index][column] = value
    return rows


def as_json(result: EvaluationResult) -> str:
    return json.dumps(result.model_dump(mode="json"), sort_keys=True, ensure_ascii=False)


def _typed(column: str, value: str) -> object:
    if column == "order_date":
        try:
            return date.fromisoformat(value)
        except ValueError:
            return value
    if column == "quantity" and value.isdigit():
        return int(value)
    if column in {"unit_price", "revenue"}:
        try:
            return float(Decimal(value))
        except InvalidOperation:
            return value
    return value
