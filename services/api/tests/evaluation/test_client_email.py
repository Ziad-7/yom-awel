import asyncio
import hashlib
import shutil
from pathlib import Path
from uuid import UUID

import pytest

from yom_awel.domain.contracts import ArtifactRef
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.catalog import build_task_version
from yom_awel.evaluation.client_email import CHECK_IDS, ClientEmailEvaluator
from yom_awel.evaluation.task_package import TaskPackageError, load_task_package

ROOT = Path(__file__).resolve().parents[4] / "task_packages" / "client-email" / "1"


def _evaluate(content: bytes, filename: str = "email.txt"):
    package = load_task_package(ROOT)
    evaluator = ClientEmailEvaluator(package, ROOT, clock=lambda: 0)
    version = build_task_version(package, "تعليمات", "Instructions")
    artifact = ArtifactRef(
        artifact_id=UUID("00000000-0000-0000-0000-000000000001"),
        filename=filename,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )
    return asyncio.run(evaluator.evaluate(version, artifact))


@pytest.mark.parametrize("name", ["pass.en.txt", "pass.ar-EG.txt"])
def test_bilingual_complete_email_passes(name: str) -> None:
    result = _evaluate((ROOT / "examples" / name).read_bytes())

    assert (result.score, result.passed, result.errors) == (100, True, [])
    assert [check.check_id for check in result.checks] == list(CHECK_IDS)


def test_weak_email_fails_all_four_checks() -> None:
    result = _evaluate((ROOT / "examples" / "fail.en.txt").read_bytes())

    assert (result.score, result.passed) == (0, False)
    assert [check.diagnostic_code for check in result.checks] == [
        f"{check_id}_failed" for check_id in CHECK_IDS
    ]


@pytest.mark.parametrize(
    ("old", "new", "failed"),
    [
        (b"salma.hassan@example.com", b"wrong@example.com", "recipient_and_subject"),
        (b"YA-2048", b"YA-2049", "recipient_and_subject"),
        (b"2026-10-03", b"2026-10-04", "case_facts"),
        (b"120 EGP", b"1200 EGP", "case_facts"),
        (b"2 business days", b"3 business days", "action_plan"),
        (b"Best regards", b"Goodbye", "professional_closing"),
    ],
)
def test_focused_defect_fails_its_check(old: bytes, new: bytes, failed: str) -> None:
    original = (ROOT / "examples" / "pass.en.txt").read_bytes()
    result = _evaluate(original.replace(old, new))

    assert failed in [check.check_id for check in result.checks if not check.passed]
    assert result.passed is (failed not in {"recipient_and_subject", "case_facts", "action_plan"})


@pytest.mark.parametrize(
    ("example", "old", "new"),
    [
        (
            "pass.en.txt",
            "We will provide a refund of 120 EGP",
            "We will not provide a refund of 120 EGP",
        ),
        (
            "pass.en.txt",
            "We will provide a refund of 120 EGP",
            "No refund of 120 EGP will be provided",
        ),
        (
            "pass.en.txt",
            "We will provide a refund of 120 EGP",
            "We are not issuing a refund of 120 EGP",
        ),
        (
            "pass.en.txt",
            "We will provide a refund of 120 EGP",
            "A refund of 120 EGP is not available",
        ),
        (
            "pass.en.txt",
            "will respond within 2 business days",
            "will not respond within 2 business days",
        ),
        (
            "pass.ar-EG.txt",
            "سنقدم استرداد 120 جنيه",
            "لن نقدم استرداد 120 جنيه",
        ),
        (
            "pass.ar-EG.txt",
            "سنقدم استرداد 120 جنيه",
            "لا يوجد استرداد 120 جنيه",
        ),
        (
            "pass.ar-EG.txt",
            "وسيرد فريق خدمة العملاء خلال يومي عمل",
            "ولن نرد خلال يومي عمل",
        ),
    ],
)
def test_negated_commitment_cannot_pass(example: str, old: str, new: str) -> None:
    original = (ROOT / "examples" / example).read_text(encoding="utf-8")
    assert old in original
    result = _evaluate(original.replace(old, new).encode("utf-8"))

    assert result.score == 75
    assert result.passed is False
    assert next(check for check in result.checks if check.check_id == "action_plan").passed is False


def test_unrelated_delivery_negation_keeps_positive_refund_and_response() -> None:
    original = (ROOT / "examples" / "pass.en.txt").read_text(encoding="utf-8")
    modified = original.replace(
        "will arrive later than planned", "cannot arrive on the original date"
    )

    result = _evaluate(modified.encode("utf-8"))

    assert (result.score, result.passed) == (100, True)


@pytest.mark.parametrize(
    ("content", "filename", "code"),
    [
        (b"hello", "email.pdf", "unsupported_type"),
        (b"PK\x03\x04fake", "email.txt", "mime_mismatch"),
        (b"\xff\xfe", "email.txt", "artifact_unreadable"),
    ],
)
def test_invalid_upload_is_rejected(content: bytes, filename: str, code: str) -> None:
    result = _evaluate(content, filename)

    assert (result.score, result.passed) == (0, False)
    assert [error.code for error in result.errors] == [code]


def test_large_upload_is_rejected() -> None:
    result = _evaluate(b"a" * 65537)
    assert [error.code for error in result.errors] == ["artifact_too_large"]


def test_modified_case_file_cannot_be_graded(tmp_path: Path) -> None:
    copied = shutil.copytree(ROOT, tmp_path / "client-email")
    with (copied / "data" / "source.csv").open("a", encoding="utf-8") as stream:
        stream.write("extra")

    with pytest.raises(TaskPackageError, match="changed after it was pinned"):
        ClientEmailEvaluator.from_directory(copied)


def test_tampered_artifact_metadata_fails_integrity() -> None:
    package = load_task_package(ROOT)
    evaluator = ClientEmailEvaluator(package, ROOT, clock=lambda: 0)
    version = build_task_version(package, "تعليمات", "Instructions")
    artifact = ArtifactRef(
        artifact_id=UUID("00000000-0000-0000-0000-000000000001"),
        filename="email.txt",
        size_bytes=3,
        sha256="0" * 64,
        content=b"bad",
    )

    with pytest.raises(DomainError) as error:
        asyncio.run(evaluator.evaluate(version, artifact))
    assert error.value.code == "artifact_integrity_failed"
