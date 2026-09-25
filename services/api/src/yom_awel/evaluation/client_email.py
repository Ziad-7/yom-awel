"""Deterministic, case-grounded grading for client-email@1."""

import csv
import hashlib
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Self

from yom_awel.domain.contracts import (
    ArtifactRef,
    EvaluationCheck,
    EvaluationError,
    EvaluationResult,
    TaskVersion,
)
from yom_awel.domain.errors import DomainError
from yom_awel.evaluation.task_package import (
    ClientEmailPolicy,
    TaskPackage,
    TaskPackageError,
    load_task_package,
)

EVALUATOR_ID = "client-email"
EVALUATOR_VERSION = "1"
CHECK_IDS = (
    "recipient_and_subject",
    "case_facts",
    "action_plan",
    "professional_closing",
)
ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
Clock = Callable[[], int]


class ClientEmailEvaluator:
    def __init__(
        self, package: TaskPackage, root: Path, clock: Clock = time.perf_counter_ns
    ) -> None:
        if (package.evaluator_id, package.evaluator_version) != (
            EVALUATOR_ID,
            EVALUATOR_VERSION,
        ) or {check.check_id for check in package.checks} != set(CHECK_IDS):
            raise DomainError("unsupported_task_package", "Package is not graded by client-email@1")
        if package.status != "published":
            raise DomainError("task_package_unpublished", "Only a published package can be graded")
        if not isinstance(package.policy, ClientEmailPolicy):
            raise TaskPackageError("client-email policy is required")
        self._package = package
        self._clock = clock
        self._policy = package.policy
        self._case = _read_case(root / self._policy.case_file)

    @classmethod
    def from_directory(cls, root: Path, clock: Clock = time.perf_counter_ns) -> Self:
        return cls(load_task_package(root), root, clock)

    async def evaluate(self, task_version: TaskVersion, artifact: ArtifactRef) -> EvaluationResult:
        package = self._package
        if (
            task_version.task_id,
            task_version.version,
            task_version.evaluator_id,
            task_version.evaluator_version,
            task_version.pass_threshold,
        ) != (
            package.task_id,
            package.version,
            EVALUATOR_ID,
            EVALUATOR_VERSION,
            package.pass_threshold,
        ):
            raise DomainError("task_version_mismatch", "Task version does not match package")
        started = self._clock()
        error = _validate_artifact(artifact, package.limits.max_bytes)
        if error is None:
            text = artifact.content.decode("utf-8-sig")
            verdicts = _grade_text(text, self._case, self._policy)
        else:
            verdicts = {check_id: False for check_id in CHECK_IDS}
        checks = [
            EvaluationCheck(
                check_id=spec.check_id,
                passed=verdicts[spec.check_id],
                weight=spec.points,
                details_ar=("الفحص سليم." if verdicts[spec.check_id] else spec.hint_ar),
                details_en=("This check passed." if verdicts[spec.check_id] else spec.hint_en),
                diagnostic_code=f"{spec.check_id}_{'passed' if verdicts[spec.check_id] else 'failed'}",
            )
            for spec in package.checks
        ]
        score = sum(check.weight for check in checks if check.passed)
        passed = (
            error is None
            and score >= package.pass_threshold
            and all(
                check.passed for check in checks if check.check_id in package.critical_check_ids
            )
        )
        return EvaluationResult(
            evaluator_id=EVALUATOR_ID,
            evaluator_version=EVALUATOR_VERSION,
            task_version_id=task_version.task_version_id,
            passed=passed,
            score=score,
            checks=checks,
            errors=[error] if error else [],
            summary_ar=f"النتيجة {score} من 100. {'ناجح' if passed else 'محتاج تعديل'}.",
            summary_en=f"Score {score}/100. {'Passed' if passed else 'Needs revision'}.",
            duration_ms=(self._clock() - started) // 1_000_000,
        )


def _read_case(path: Path) -> dict[str, str]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream))
    except (OSError, UnicodeError, csv.Error) as error:
        raise TaskPackageError("client-email source CSV is unreadable") from error
    required = {
        "customer_name",
        "customer_name_ar",
        "customer_email",
        "order_id",
        "promised_date",
        "updated_delivery_date",
        "refund_amount_egp",
        "response_window_business_days",
    }
    if (
        len(rows) != 1
        or not required <= rows[0].keys()
        or any(not rows[0][key] for key in required)
    ):
        raise TaskPackageError("client-email source CSV needs one complete case")
    return rows[0]


def _validate_artifact(artifact: ArtifactRef, max_bytes: int) -> EvaluationError | None:
    content = artifact.content
    if (
        artifact.size_bytes != len(content)
        or hashlib.sha256(content).hexdigest() != artifact.sha256
    ):
        raise DomainError("artifact_integrity_failed", "Artifact bytes do not match metadata")
    if max(len(content), artifact.size_bytes) > max_bytes:
        return EvaluationError(code="artifact_too_large", message="Email file is too large.")
    if not artifact.filename.lower().endswith(".txt"):
        return EvaluationError(code="unsupported_type", message="Upload a UTF-8 .txt email.")
    if b"\x00" in content or content.startswith(
        (b"PK\x03\x04", b"\xd0\xcf\x11\xe0", b"%PDF-", b"\x89PNG", b"GIF8")
    ):
        return EvaluationError(code="mime_mismatch", message="File is not plain text.")
    try:
        content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return EvaluationError(code="artifact_unreadable", message="Email must use UTF-8 text.")
    return None


def _grade_text(text: str, case: dict[str, str], policy: ClientEmailPolicy) -> dict[str, bool]:
    normalized = text.translate(ARABIC_DIGITS)
    lines = normalized.splitlines()
    to_line = lines[0] if len(lines) > 0 else ""
    subject = lines[1] if len(lines) > 1 else ""
    body = "\n".join(lines[3:]) if len(lines) > 3 and not lines[2].strip() else ""
    lower = body.casefold()
    words = re.findall(r"[\w\u0600-\u06ff]+", body, flags=re.UNICODE)
    recipient_ok = (
        re.fullmatch(rf"To:\s*{re.escape(case['customer_email'])}\s*", to_line, re.IGNORECASE)
        is not None
    )
    subject_ok = (
        re.match(r"^Subject:\s*\S", subject, re.IGNORECASE) is not None
        and case["order_id"].casefold() in subject.casefold()
    )
    facts_ok = (
        all(
            value.casefold() in lower
            for value in (
                case["order_id"],
                case["promised_date"],
                case["updated_delivery_date"],
            )
        )
        and re.search(rf"(?<!\d){re.escape(case['refund_amount_egp'])}(?!\d)\s*(?:egp|جنيه)", lower)
        is not None
    )
    response_window = case["response_window_business_days"]
    response_terms: tuple[str, ...] = (f"{response_window} business days",)
    if response_window == "2":
        response_terms += ("two business days", "يومي عمل", "يومين عمل")
    action_ok = (
        _has_any(lower, ("sorry", "apolog", "نعتذر", "آسف", "اسف"))
        and _has_any(lower, ("refund", "reimburs", "استرداد", "رد المبلغ"))
        and _has_any(lower, response_terms)
        and not _negates_commitment(lower, "refund")
        and not _negates_commitment(lower, "response")
    )
    nonblank_lines = [line.casefold() for line in body.splitlines() if line.strip()]
    greeting = nonblank_lines[0] if nonblank_lines else ""
    closing = "\n".join(nonblank_lines[-3:])
    greeting_ok = _has_any(
        greeting, (case["customer_name"].casefold(), case["customer_name_ar"].casefold())
    )
    closing_ok = _has_any(
        closing, ("best regards", "kind regards", "sincerely", "مع التحية", "تحياتنا")
    ) and _has_any(closing, ("yom awel", "يوم أول"))
    return {
        "recipient_and_subject": recipient_ok and subject_ok and bool(body.strip()),
        "case_facts": facts_ok,
        "action_plan": action_ok,
        "professional_closing": (
            greeting_ok and closing_ok and policy.min_words <= len(words) <= policy.max_words
        ),
    }


def _has_any(text: str, choices: tuple[str, ...]) -> bool:
    return any(choice in text for choice in choices)


def _negates_commitment(text: str, kind: str) -> bool:
    """Reject explicit denials within the same sentence as a required promise.

    This is deliberately narrow: the task uses a finite, published phrase rubric,
    not a claim to understand arbitrary prose. Contradictory positive and negative
    statements also fail instead of receiving credit for containing keywords.
    """

    english_terms = (
        r"refund\w*|reimburs\w*" if kind == "refund" else r"respond\w*|repl(?:y|ies)|response"
    )
    arabic_terms = r"استرداد|رد المبلغ|نعيد" if kind == "refund" else r"نرد|الرد|الاستجابة"
    sentence = r"[^\n.!?؟]{0,60}"
    patterns = (
        rf"\b(?:will|would|can|could|do|does|did|shall|is|are|was|were|have|has)\s+not\b{sentence}\b(?:{english_terms})\b",
        rf"\b(?:won't|can't|cannot|never)\b{sentence}\b(?:{english_terms})\b",
        rf"\b(?:no|without)\s+(?:\w+\s+){{0,3}}(?:{english_terms})\b",
        rf"\b(?:{english_terms})\b{sentence}\b(?:denied|unavailable|cancelled|not (?:available|offered|issued|provided))\b",
        rf"(?:لن|لم)\s+[^\n.!?؟]{{0,35}}(?:{arabic_terms})",
        rf"لا\s+(?:نقدم|نوفر|نعيد|يمكن|يتم|يوجد|نرد)\s*[^\n.!?؟]{{0,30}}(?:{arabic_terms})",
        rf"بدون\s*[^\n.!?؟]{{0,20}}(?:{arabic_terms})",
    )
    return any(re.search(pattern, text) is not None for pattern in patterns)
