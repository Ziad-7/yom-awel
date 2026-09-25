"""Bounded transport checks before persistence; no task grading rules.

Cloud Storage metadata must additionally be verified by Member2's completion
contract (issue #26). These checks protect local PUT and Telegram ingress.
"""

import csv
import io
import stat
import zipfile
import zlib
from pathlib import PurePosixPath

from yom_awel.domain.errors import DomainError

MAX_BYTES = 5 * 1024 * 1024
MAX_EXPANDED_BYTES = 50 * 1024 * 1024
MIME_TYPES = {
    "csv": {"text/csv", "application/vnd.ms-excel", "application/octet-stream"},
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",
    },
    "sql": {"application/sql", "text/plain", "application/octet-stream"},
    "txt": {"text/plain", "application/octet-stream"},
}


def validate_metadata(filename: str, content_type: str) -> None:
    extension = filename.rsplit(".", 1)[-1].lower()
    if (
        not 1 <= len(filename) <= 255
        or any(char in filename for char in ("/", "\\", "\x00"))
        or content_type not in MIME_TYPES.get(extension, set())
    ):
        raise DomainError("unsupported_artifact", "Unsupported filename or content type")


def validate_content(filename: str, content_type: str, content: bytes) -> None:
    validate_metadata(filename, content_type)
    if not 0 < len(content) <= MAX_BYTES:
        raise DomainError("too_large", "Invalid artifact size")
    try:
        if filename.lower().endswith(".csv"):
            _csv(content)
        elif filename.lower().endswith(".xlsx"):
            _xlsx(content)
        else:
            _plain_text(content)
    except (
        ValueError,
        UnicodeError,
        csv.Error,
        zipfile.BadZipFile,
        RuntimeError,
        NotImplementedError,
        EOFError,
        zlib.error,
    ) as exc:
        raise DomainError("unsafe_artifact", "Artifact signature or structure is invalid") from exc


def _csv(content: bytes) -> None:
    if content.startswith(
        (b"MZ", b"PK", b"\xd0\xcf\x11\xe0", b"\x7fELF", b"%PDF", b"\x89PNG", b"GIF8")
    ):
        raise ValueError("Binary signature")
    text = content.decode("utf-8-sig")
    if any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        raise ValueError("Binary control characters")
    for row in csv.reader(io.StringIO(text, newline=""), strict=True):
        # Parsing verifies CSV syntax, without inspecting any business values.
        del row


def _plain_text(content: bytes) -> None:
    if content.startswith(
        (b"MZ", b"PK", b"\xd0\xcf\x11\xe0", b"\x7fELF", b"%PDF", b"\x89PNG", b"GIF8")
    ):
        raise ValueError("Binary signature")
    text = content.decode("utf-8-sig")
    if not text.strip() or any(ord(char) < 32 and char not in "\r\n\t" for char in text):
        raise ValueError("Empty or binary text")


def _xlsx(content: bytes) -> None:
    if not content.startswith(b"PK\x03\x04"):
        raise ValueError("Missing XLSX signature")
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.infolist()
        names = {entry.filename for entry in entries}
        if (
            len(entries) > 1000
            or len(names) != len(entries)
            or not {"[Content_Types].xml", "xl/workbook.xml"} <= names
            or not any(
                name.startswith("xl/worksheets/") and name.endswith(".xml") for name in names
            )
            or sum(entry.file_size for entry in entries) > MAX_EXPANDED_BYTES
        ):
            raise ValueError("Invalid workbook directory")
        expanded = 0
        for entry in entries:
            path = PurePosixPath(entry.filename)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in entry.filename
                or ":" in entry.filename
                or entry.flag_bits & 1
                or stat.S_ISLNK(entry.external_attr >> 16)
                or "vbaproject" in entry.filename.lower()
                or entry.file_size > max(1, entry.compress_size) * 200
            ):
                raise ValueError("Unsafe workbook entry")
            tail = b""
            with archive.open(entry) as stream:
                while chunk := stream.read(65536):
                    expanded += len(chunk)
                    if expanded > MAX_EXPANDED_BYTES:
                        raise ValueError("Expanded size exceeded")
                    probe = (tail + chunk).upper()
                    if entry.filename.endswith(".xml") and (
                        b"<!DOCTYPE" in probe or b"<!ENTITY" in probe
                    ):
                        raise ValueError("XML entity declarations are unsupported")
                    tail = probe[-16:]
