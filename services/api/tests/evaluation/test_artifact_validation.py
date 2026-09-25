import hashlib
import io
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import openpyxl.xml
import pytest
import yaml
from openpyxl import Workbook

from yom_awel.domain.contracts import ArtifactRef
from yom_awel.evaluation.artifact_validation import (
    OLE_SIGNATURE,
    REJECTION_MESSAGES,
    TABLE_LIMIT_CODE,
    ArtifactRejected,
    ArtifactSizeMismatch,
    Table,
    inspect_artifact,
)
from yom_awel.evaluation.task_package import ArtifactLimits

LEARNING_OBJECTIVES = (
    Path(__file__).resolve().parents[4]
    / "task_packages"
    / "clean-sales"
    / "1"
    / "learning-objectives.yaml"
)
LIMITS = ArtifactLimits(
    extensions=("csv", "xlsx"),
    max_bytes=16_384,
    max_expanded_bytes=65_536,
    max_sheets=1,
    max_rows=3,
    max_columns=4,
)
SHEET = "xl/worksheets/sheet1.xml"
HEADER = ("order_id", "quantity")


def ref(filename: str, content: bytes, size_bytes: int | None = None) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=UUID("00000000-0000-0000-0000-000000000005"),
        filename=filename,
        size_bytes=len(content) if size_bytes is None else size_bytes,
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )


def workbook(*rows: tuple[Any, ...], sheets: int = 1) -> bytes:
    book = Workbook()
    for row in rows:
        book.active.append(row)  # type: ignore[union-attr]
    for index in range(1, sheets):
        book.create_sheet(f"Sheet{index + 1}")
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def repackaged(content: bytes, **entries: str | bytes | None) -> bytes:
    """Rewrite a workbook's ZIP entries; ``None`` removes an entry."""

    buffer = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(content)) as source,
        zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as target,
    ):
        for item in source.infolist():
            if item.filename not in entries:
                target.writestr(item, source.read(item))
        for name, data in entries.items():
            if data is not None:
                target.writestr(name, data)
    return buffer.getvalue()


def sheet_xml(rows: str) -> str:
    namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    return f'<worksheet xmlns="{namespace}"><sheetData>{rows}</sheetData></worksheet>'


def rejection(filename: str, content: bytes, limits: ArtifactLimits = LIMITS) -> str:
    with pytest.raises(ArtifactRejected) as error:
        inspect_artifact(ref(filename, content), limits)
    return error.value.code


def test_accepts_a_utf8_csv_and_returns_its_rows() -> None:
    content = "﻿order_id,customer_email\nSO-1,أحمد@example.com\n".encode()

    result = inspect_artifact(ref("sales.CSV", content), LIMITS)

    assert result == Table(rows=(("order_id", "customer_email"), ("SO-1", "أحمد@example.com")))


def test_reads_the_active_worksheet_as_the_text_a_csv_export_would_hold() -> None:
    content = workbook(
        ("order_id", "order_date", "quantity", "revenue"),
        ("SO-1", date(2026, 1, 5), 3, 12.5),
        ("SO-2", datetime.fromisoformat("2026-01-05T09:30"), True, "=C3*2"),
        ("SO-3", "05/01/2026", None, None),
    )

    assert inspect_artifact(ref("sales.xlsx", content), LIMITS).rows == (
        ("order_id", "order_date", "quantity", "revenue"),
        ("SO-1", "2026-01-05", "3", "12.5"),
        ("SO-2", "2026-01-05 09:30:00", "TRUE", "=C3*2"),
        ("SO-3", "05/01/2026"),
    )


def test_the_same_table_reads_identically_from_csv_and_xlsx() -> None:
    rows = [HEADER, ("SO-1", "3"), ("", ""), ("SO-2", "4")]
    csv_content = "".join(",".join(row) + "\n" for row in rows).encode()
    xlsx_content = workbook(*(tuple(cell or None for cell in row) for row in rows))

    from_csv = inspect_artifact(ref("s.csv", csv_content), LIMITS)
    from_xlsx = inspect_artifact(ref("s.xlsx", xlsx_content), LIMITS)

    assert [row for row in from_csv.rows if any(row)] == [row for row in from_xlsx.rows if row]


@pytest.mark.parametrize(
    ("filename", "content", "code"),
    [
        ("sales.xlsx", b"order_id\nSO-1\n", "mime_mismatch"),
        ("sales.csv", workbook(HEADER), "mime_mismatch"),
        ("sales.csv", OLE_SIGNATURE + b"legacy", "mime_mismatch"),
        ("sales.csv", b"order_id\x00\n", "mime_mismatch"),
        ("sales.xlsx", OLE_SIGNATURE + b"encrypted package", "artifact_unreadable"),
        ("sales.xls", b"order_id\n", "unsupported_type"),
        ("sales.xlsm", workbook(HEADER), "unsupported_type"),
        ("sales", b"order_id\n", "unsupported_type"),
        ("sales.csv.exe", b"order_id\n", "unsupported_type"),
    ],
    ids=[
        "csv-named-xlsx",
        "xlsx-named-csv",
        "ole-named-csv",
        "binary-csv",
        "password-protected",
        "xls",
        "xlsm",
        "no-extension",
        "double-extension",
    ],
)
def test_rejects_types_that_do_not_match_their_signature(
    filename: str, content: bytes, code: str
) -> None:
    assert rejection(filename, content) == code


def test_rejects_extensions_the_task_does_not_allow() -> None:
    csv_only = LIMITS.model_copy(update={"extensions": ("csv",)})

    assert rejection("sales.xlsx", workbook(HEADER), csv_only) == "unsupported_type"


def test_accepts_exactly_the_byte_limit_and_rejects_one_more() -> None:
    exact = b"a\n" * (LIMITS.max_bytes // 2)
    at_limit = LIMITS.model_copy(update={"max_rows": len(exact)})

    assert inspect_artifact(ref("s.csv", exact), at_limit).rows
    assert rejection("s.csv", exact + b"a", at_limit) == "artifact_too_large"


def test_rejects_a_declared_size_above_the_limit_before_reading_content() -> None:
    declared = ref("sales.csv", b"", size_bytes=LIMITS.max_bytes + 1)

    with pytest.raises(ArtifactRejected) as error:
        inspect_artifact(declared, LIMITS)
    assert error.value.code == "artifact_too_large"


def test_a_size_mismatch_is_a_storage_error_not_a_learner_rejection() -> None:
    content = b"order_id\n"
    declared = ref("sales.csv", content, size_bytes=len(content) + 1)

    with pytest.raises(ArtifactSizeMismatch) as error:
        inspect_artifact(declared, LIMITS)
    assert error.value.code == "artifact_size_mismatch"
    assert error.value.code not in REJECTION_MESSAGES


@pytest.mark.parametrize(
    ("filename", "at_limit", "over_limit"),
    [
        ("s.csv", b"h\n1\n2\n3\n", b"h\n1\n2\n3\n4\n"),
        ("s.xlsx", workbook(("h",), (1,), (2,), (3,)), workbook(("h",), (1,), (2,), (3,), (4,))),
        ("s.csv", b"a,b,c,d\n", b"a,b,c,d,e\n"),
        ("s.xlsx", workbook(("a", "b", "c", "d")), workbook(("a", "b", "c", "d", "e"))),
    ],
    ids=["csv-rows", "xlsx-rows", "csv-columns", "xlsx-columns"],
)
def test_row_and_column_limits_are_inclusive(
    filename: str, at_limit: bytes, over_limit: bytes
) -> None:
    assert inspect_artifact(ref(filename, at_limit), LIMITS).rows
    assert rejection(filename, over_limit) == TABLE_LIMIT_CODE


def test_trailing_empty_cells_and_rows_do_not_count_against_xlsx_limits() -> None:
    content = workbook(("a", "b", None, None, None, None), ("1", "2"), (None,), (None,), (None,))

    assert inspect_artifact(ref("s.xlsx", content), LIMITS).rows == (("a", "b"), ("1", "2"))


@pytest.mark.parametrize(
    "overflow",
    [
        '<row r="6"><c r="A6" t="inlineStr"><is><t>hidden row</t></is></c></row>',
        '<row r="2"><c r="F2" t="inlineStr"><is><t>hidden column</t></is></c></row>',
        '<row r="999999999"><c r="A999999999" t="inlineStr"><is><t>forged row</t></is></c></row>',
    ],
    ids=["sparse-row", "sparse-column", "forged-row"],
)
def test_xlsx_nonempty_cells_past_the_read_window_are_rejected(overflow: str) -> None:
    forged = sheet_xml('<row r="1"><c r="A1" t="inlineStr"><is><t>h</t></is></c></row>' + overflow)
    content = repackaged(workbook(("h",)), **{SHEET: forged})

    assert rejection("s.xlsx", content) == TABLE_LIMIT_CODE


def test_xlsx_empty_cells_past_the_read_window_do_not_count_against_limits() -> None:
    empty = sheet_xml(
        '<row r="1"><c r="A1" t="inlineStr"><is><t>h</t></is></c></row>'
        '<row r="999999999"><c r="A999999999"/></row>'
    )
    content = repackaged(workbook(("h",)), **{SHEET: empty})

    assert inspect_artifact(ref("s.xlsx", content), LIMITS).rows == (("h",),)


@pytest.mark.parametrize(
    "content",
    ["order_id\nأحمد\n".encode("cp1256"), b'order_id\n"unterminated\n' + b"x" * 200_000],
    ids=["not-utf8", "unterminated-quote"],
)
def test_rejects_unreadable_csv(content: bytes) -> None:
    limits = LIMITS.model_copy(update={"max_bytes": len(content)})

    assert rejection("s.csv", content, limits) == "artifact_unreadable"


def test_rejects_expanded_size_above_the_limit_before_decompressing() -> None:
    bomb = repackaged(
        workbook(HEADER), **{"xl/sharedStrings.xml": b"0" * (LIMITS.max_expanded_bytes + 1)}
    )

    assert len(bomb) < LIMITS.max_bytes
    assert rejection("s.xlsx", bomb) == "expanded_size_exceeded"


@pytest.mark.parametrize(
    "part",
    ["xl/vbaProject.bin", "xl/macrosheets/sheet1.xml", "xl/externalLinks/externalLink1.xml"],
    ids=["vba-macro", "excel4-macro-sheet", "external-link"],
)
def test_rejects_macros_and_external_links(part: str) -> None:
    assert rejection("s.xlsx", repackaged(workbook(HEADER), **{part: b"x"})) == (
        "artifact_unreadable"
    )


def test_rejects_extra_worksheets() -> None:
    assert rejection("s.xlsx", workbook(HEADER, sheets=2)) == "sheet_limit_exceeded"


def test_a_chartsheet_counts_as_a_sheet() -> None:
    content = repackaged(workbook(HEADER), **{"xl/chartsheets/sheet1.xml": "<chartsheet/>"})

    assert rejection("s.xlsx", content) == "sheet_limit_exceeded"


ENTITY_EXPANSION = (
    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
    '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
    + sheet_xml('<row r="1"><c r="A1" t="inlineStr"><is><t>&lol2;</t></is></c></row>')
)


@pytest.mark.parametrize(
    "content",
    [
        repackaged(workbook(HEADER), **{SHEET: None}),
        repackaged(workbook(HEADER), **{"xl/workbook.xml": None}),
        repackaged(workbook(HEADER), **{"../evil.xml": "x"}),
        repackaged(workbook(HEADER), **{"/abs.xml": "x"}),
        repackaged(workbook(HEADER), **{"xl/workbook.xml": "<workbook>"}),
        repackaged(workbook(HEADER), **{SHEET: ENTITY_EXPANSION}),
        workbook(HEADER)[:-40],
        b"PK\x03\x04 not a real archive",
    ],
    ids=[
        "no-sheet",
        "no-workbook",
        "traversal",
        "absolute",
        "corrupt-workbook-xml",
        "entity-expansion",
        "truncated",
        "garbage",
    ],
)
def test_rejects_malformed_workbooks_without_crashing(content: bytes) -> None:
    assert rejection("s.xlsx", content) == "artifact_unreadable"


def test_workbook_xml_is_parsed_with_defusedxml() -> None:
    assert openpyxl.xml.DEFUSEDXML


def test_rejection_vocabulary_is_the_merged_v1_vocabulary_verbatim() -> None:
    vocabulary = yaml.safe_load(LEARNING_OBJECTIVES.read_text(encoding="utf-8"))
    rejections = vocabulary["diagnostic_vocabulary"]["rejections"]

    assert REJECTION_MESSAGES == {
        item["code"]: (item["learner_message_ar"], item["learner_message_en"])
        for item in rejections
    }
    assert TABLE_LIMIT_CODE in REJECTION_MESSAGES


@pytest.mark.parametrize("code", sorted(REJECTION_MESSAGES))
def test_every_rejection_carries_both_messages(code: str) -> None:
    error = ArtifactRejected(code)
    message_ar, message_en = REJECTION_MESSAGES[code]

    assert error.message == message_en
    assert error.details == {"message_ar": message_ar}
