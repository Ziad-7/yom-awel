"""Regenerate the presenter kit: graded uploads derived from the learner's own dirty file.

Usage: uv run --project services/api python demo/generate_demo_files.py [OUT]
OUT defaults to demo/files. Every file is byte-for-byte reproducible.
"""

import csv
import io
import sys
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from openpyxl import Workbook
from openpyxl.packaging.core import DocumentProperties
from openpyxl.xml.functions import tostring
from yom_awel.evaluation.clean_sales_dataset import (
    COLUMNS,
    LEARNER_SEED,
    Dataset,
    DefectKind,
    Row,
    apply_defects,
    generate,
    to_csv,
)

OUTPUT_DIR = Path(__file__).resolve().parent / "files"
# openpyxl stores naive UTC datetimes.
FIXED_TIMESTAMP = datetime(2026, 9, 20, tzinfo=UTC).replace(tzinfo=None)
ZIP_TIMESTAMP = (2026, 9, 20, 0, 0, 0)
WORKBOOK_AUTHOR = "Yom Awel demo kit"
SHEET_TITLE = "sales"
CORE_PROPERTIES = "docProps/core.xml"
DROPPED_COLUMN = "missing_email_reason"
# The half-done learner fixed duplicates and numbers but left dates and missing emails.
HALF_DONE_LEFT_DIRTY: frozenset[DefectKind] = frozenset(
    {"nonstandard_date", "missing_email"}
)

Builder = Callable[[Dataset], bytes]


def cleaned(dataset: Dataset) -> tuple[Row, ...]:
    return dataset.clean


def only_defects(dataset: Dataset, kinds: Iterable[DefectKind]) -> tuple[Row, ...]:
    """The clean rows with only the learner's planted defects of ``kinds`` left in."""

    wanted = frozenset(kinds)
    return apply_defects(
        dataset.clean, (d for d in dataset.defects if d.kind in wanted)
    )


def csv_bytes(rows: Iterable[Row]) -> bytes:
    return to_csv(rows).encode("utf-8")


def csv_without_column(rows: Iterable[Row], dropped: str) -> bytes:
    buffer = io.StringIO()
    columns = [column for column in COLUMNS if column != dropped]
    writer = csv.DictWriter(
        buffer, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
    )
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


DEMO_FILES: Mapping[str, Builder] = {
    "sales_cleaned.csv": lambda data: csv_bytes(cleaned(data)),
    "sales_cleaned.xlsx": lambda data: xlsx_bytes(cleaned(data)),
    "sales_retry_duplicates.csv": lambda data: csv_bytes(
        only_defects(data, ["duplicate_order"])
    ),
    "sales_retry_half.xlsx": lambda data: xlsx_bytes(
        only_defects(data, HALF_DONE_LEFT_DIRTY)
    ),
    "sales_rejected_missing_columns.csv": lambda data: csv_without_column(
        cleaned(data), DROPPED_COLUMN
    ),
}


def build_all(dataset: Dataset) -> dict[str, bytes]:
    return {name: build(dataset) for name, build in DEMO_FILES.items()}


def write_all(out_dir: Path, files: Mapping[str, bytes]) -> Sequence[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = [out_dir / name for name in files]
    for path, content in zip(paths, files.values(), strict=True):
        path.write_bytes(content)
    return paths


def main(out_dir: Path) -> None:
    for path in write_all(out_dir, build_all(generate(LEARNER_SEED))):
        print(path)


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_DIR)
