"""Ready-made submissions for every task, built from the task's own data.

They power the presenter kit (``demo/generate_demo_files.py``) and judge mode, where a visitor
submits them with one click through the normal upload pipeline. The outcome and score of each
sample are what the real evaluator returns; ``tests/evaluation/test_samples.py`` grades every
one of them, so the labels are tested facts.
"""

import csv
import io
import zipfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Literal

from openpyxl import Workbook
from openpyxl.packaging.core import DocumentProperties
from openpyxl.xml.functions import tostring

from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.catalog import XLSX_MEDIA_TYPE, CatalogTask
from yom_awel.evaluation.clean_sales_dataset import (
    COLUMNS,
    Dataset,
    DefectKind,
    Row,
    apply_defects,
    generate,
    to_csv,
)

# openpyxl stores naive UTC datetimes.
FIXED_TIMESTAMP = datetime(2026, 9, 20, tzinfo=UTC).replace(tzinfo=None)
ZIP_TIMESTAMP = (2026, 9, 20, 0, 0, 0)
WORKBOOK_AUTHOR = "Yom Awel demo kit"
SHEET_TITLE = "sales"
CORE_PROPERTIES = "docProps/core.xml"
DROPPED_COLUMN = "missing_email_reason"
# The half-done learner fixed duplicates and numbers but left dates and missing emails.
HALF_DONE_LEFT_DIRTY: frozenset[DefectKind] = frozenset({"nonstandard_date", "missing_email"})
CSV_MEDIA_TYPE = "text/csv"
TEXT_MEDIA_TYPE = "text/plain"

Builder = Callable[[Dataset], bytes]
Outcome = Literal["pass", "retry", "rejected"]


def cleaned(dataset: Dataset) -> tuple[Row, ...]:
    return dataset.clean


def only_defects(dataset: Dataset, kinds: Iterable[DefectKind]) -> tuple[Row, ...]:
    """The clean rows with only the learner's planted defects of ``kinds`` left in."""

    wanted = frozenset(kinds)
    return apply_defects(dataset.clean, (d for d in dataset.defects if d.kind in wanted))


def csv_bytes(rows: Iterable[Row]) -> bytes:
    return to_csv(rows).encode("utf-8")


def csv_without_column(rows: Iterable[Row], dropped: str) -> bytes:
    buffer = io.StringIO()
    columns = [column for column in COLUMNS if column != dropped]
    writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


def xlsx_bytes(rows: Iterable[Row]) -> bytes:
    """One typed worksheet, the way Excel stores it, with fixed metadata and zip timestamps."""

    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = SHEET_TITLE
    sheet.append(COLUMNS)
    for row in rows:
        sheet.append([typed_cell(column, row[column]) for column in COLUMNS])
    buffer = io.BytesIO()
    book.save(buffer)
    return normalized_zip(buffer.getvalue(), {CORE_PROPERTIES: fixed_core_properties()})


def fixed_core_properties() -> bytes:
    """Saving stamps the current time on ``modified``, so the part is written afresh."""

    properties = DocumentProperties(
        creator=WORKBOOK_AUTHOR,
        lastModifiedBy=WORKBOOK_AUTHOR,
        created=FIXED_TIMESTAMP,
        modified=FIXED_TIMESTAMP,
    )
    xml: str | bytes = tostring(properties.to_tree())
    return xml.encode("utf-8") if isinstance(xml, str) else xml


def typed_cell(column: str, value: str) -> object:
    """ISO dates, whole quantities and amounts become typed cells; anything else stays text."""

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


def normalized_zip(content: bytes, replacements: Mapping[str, bytes]) -> bytes:
    """Rewrite every entry in name order with a fixed timestamp, so the bytes are stable."""

    output = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(content)) as source,
        zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for name in sorted(source.namelist()):
            info = zipfile.ZipInfo(name, date_time=ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            target.writestr(info, replacements.get(name) or source.read(name))
    return output.getvalue()


SALES_FILES: Mapping[str, Builder] = {
    "sales_cleaned.csv": lambda data: csv_bytes(cleaned(data)),
    "sales_cleaned.xlsx": lambda data: xlsx_bytes(cleaned(data)),
    "sales_retry_duplicates.csv": lambda data: csv_bytes(only_defects(data, ["duplicate_order"])),
    "sales_retry_half.xlsx": lambda data: xlsx_bytes(only_defects(data, HALF_DONE_LEFT_DIRTY)),
    "sales_rejected_missing_columns.csv": lambda data: csv_without_column(
        cleaned(data), DROPPED_COLUMN
    ),
}

SQL_CORRECT = """SELECT region, COUNT(*) AS paid_orders,
       ROUND(SUM(quantity * unit_price), 2) AS total_revenue
FROM sales
WHERE status = 'paid'
GROUP BY region
ORDER BY region;
"""
# Every paid order counted, but pending and refunded ones too.
SQL_NO_STATUS_FILTER = """SELECT region, COUNT(*) AS paid_orders,
       ROUND(SUM(quantity * unit_price), 2) AS total_revenue
FROM sales
GROUP BY region
ORDER BY region;
"""
# The right numbers for today's data, typed in by hand: the robustness probe catches it.
SQL_HARDCODED = """SELECT 'Alexandria' AS region, 3 + (SELECT COUNT(order_id) FROM sales) * 0 AS paid_orders,
       230 AS total_revenue
UNION ALL SELECT 'Aswan', 3, 150.5
UNION ALL SELECT 'Cairo', 4, 414.5
UNION ALL SELECT 'Giza', 4, 314;
"""


@dataclass(frozen=True)
class Sample:
    sample_id: str
    filename: str
    media_type: str
    outcome: Outcome
    score: int
    build: Callable[[CatalogTask], bytes]


def _sales(name: str) -> Callable[[CatalogTask], bytes]:
    return lambda task: SALES_FILES[name](generate(task.package.dataset_seed))


def _text(value: str) -> Callable[[CatalogTask], bytes]:
    return lambda task: value.encode("utf-8")


def _example(
    name: str, replace: tuple[bytes, bytes] | None = None
) -> Callable[[CatalogTask], bytes]:
    def build(task: CatalogTask) -> bytes:
        content = (task.package_root / "examples" / name).read_bytes()
        return content.replace(*replace) if replace else content

    return build


SAMPLES: Mapping[str, tuple[Sample, ...]] = {
    "clean-sales": (
        Sample(
            "duplicates_left",
            "sales_retry_duplicates.csv",
            CSV_MEDIA_TYPE,
            "retry",
            75,
            _sales("sales_retry_duplicates.csv"),
        ),
        Sample(
            "half_done_excel",
            "sales_retry_half.xlsx",
            XLSX_MEDIA_TYPE,
            "retry",
            50,
            _sales("sales_retry_half.xlsx"),
        ),
        Sample(
            "column_deleted",
            "sales_rejected_missing_columns.csv",
            CSV_MEDIA_TYPE,
            "rejected",
            0,
            _sales("sales_rejected_missing_columns.csv"),
        ),
        Sample(
            "fully_cleaned",
            "sales_cleaned.xlsx",
            XLSX_MEDIA_TYPE,
            "pass",
            100,
            _sales("sales_cleaned.xlsx"),
        ),
    ),
    "sql-report": (
        Sample("hard_coded", "report.sql", TEXT_MEDIA_TYPE, "retry", 25, _text(SQL_HARDCODED)),
        Sample(
            "no_status_filter",
            "report.sql",
            TEXT_MEDIA_TYPE,
            "retry",
            50,
            _text(SQL_NO_STATUS_FILTER),
        ),
        Sample("correct_query", "report.sql", TEXT_MEDIA_TYPE, "pass", 100, _text(SQL_CORRECT)),
    ),
    "client-email": (
        Sample(
            "wrong_date_reply",
            "reply.txt",
            TEXT_MEDIA_TYPE,
            "retry",
            75,
            # One fact off: the new delivery date the customer will plan around.
            _example("pass.en.txt", (b"2026-10-03", b"2026-10-05")),
        ),
        Sample("vague_reply", "reply.txt", TEXT_MEDIA_TYPE, "retry", 0, _example("fail.en.txt")),
        Sample(
            "complete_reply_en", "reply.txt", TEXT_MEDIA_TYPE, "pass", 100, _example("pass.en.txt")
        ),
        Sample(
            "complete_reply_ar",
            "reply.txt",
            TEXT_MEDIA_TYPE,
            "pass",
            100,
            _example("pass.ar-EG.txt"),
        ),
    ),
}


def samples_for(task_id: str) -> tuple[Sample, ...]:
    return SAMPLES.get(task_id, ())


def sample(task_id: str, sample_id: str) -> Sample:
    found = next((item for item in samples_for(task_id) if item.sample_id == sample_id), None)
    if found is None:
        raise DomainError("not_found", "Sample not found")
    return found
