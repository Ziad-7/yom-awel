"""Deterministic, case-grounded grading for client-email@1."""

import csv
import hashlib
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
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
from yom_awel.evaluation.insights import (
    CheckInsight,
    EmailElement,
    EmailInsight,
    ImpactMetric,
    SubmissionInsights,
)
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
Span = tuple[int, int] | None
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

    def _require_matching(self, task_version: TaskVersion) -> None:
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

    async def insights(
        self, task_version: TaskVersion, artifact: ArtifactRef
    ) -> SubmissionInsights:
        """Which requirements the learner's own email meets, and where in the text."""

        self._require_matching(task_version)
        error = _validate_artifact(artifact, self._package.limits.max_bytes)
        if error is not None:
            return SubmissionInsights(
                kind="email",
                task_id=self._package.task_id,
                rejected_code=error.code,
                checks=[
                    CheckInsight(check_id=check_id, passed=False, issue_count=0)
                    for check_id in CHECK_IDS
                ],
            )
        text = artifact.content.decode("utf-8-sig")
        elements = _assess(text, self._case, self._policy)
        body = _email_body(text.translate(ARABIC_DIGITS))
        customer_facing = ("case_facts", "action_plan")
        return SubmissionInsights(
            kind="email",
            task_id=self._package.task_id,
            checks=[
                CheckInsight(
                    check_id=check_id,
                    passed=all(e.found for e in elements if e.check_id == check_id),
                    issue_count=sum(not e.found for e in elements if e.check_id == check_id),
                )
                for check_id in CHECK_IDS
            ],
            impact=[
                ImpactMetric(
                    metric_id="customer_questions_left_open",
                    value=Decimal(
                        sum(not e.found for e in elements if e.check_id in customer_facing)
                    ),
                    unit="elements",
                )
            ],
            email=EmailInsight(
                text=text,
                elements=[
                    EmailElement(
                        element_id=e.element_id,
                        check_id=e.check_id,
                        found=e.found,
                        start=e.span[0] if e.span else None,
                        end=e.span[1] if e.span else None,
                    )
                    for e in elements
                ],
                word_count=len(_words(body)),
                min_words=self._policy.min_words,
                max_words=self._policy.max_words,
            ),
        )

    async def evaluate(self, task_version: TaskVersion, artifact: ArtifactRef) -> EvaluationResult:
        package = self._package
        self._require_matching(task_version)
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


@dataclass(frozen=True)
class Element:
    """One graded requirement of the email: found or not, and where in the learner's text."""

    element_id: str
    check_id: str
    found: bool
    span: Span = None


def _grade_text(text: str, case: dict[str, str], policy: ClientEmailPolicy) -> dict[str, bool]:
    elements = _assess(text, case, policy)
    return {
        check_id: all(element.found for element in elements if element.check_id == check_id)
        for check_id in CHECK_IDS
    }


def _assess(text: str, case: dict[str, str], policy: ClientEmailPolicy) -> list[Element]:
    """Every requirement as an element; a check passes when all of its elements are found.

    Spans index the learner's original text: digit normalization maps one character to one.
    """

    normalized = text.translate(ARABIC_DIGITS)
    lines = normalized.splitlines()
    starts = _line_starts(normalized)
    to_line = lines[0] if len(lines) > 0 else ""
    subject = lines[1] if len(lines) > 1 else ""
    body = _email_body(normalized)
    body_start = starts[3] if body else len(normalized)
    lower = body.casefold()
    words = _words(body)

    def where(pattern: str, *, line: int | None = None, last: bool = False) -> Span:
        start = body_start if line is None else starts[line]
        stop = len(normalized) if line is None else start + len(lines[line])
        matches = list(re.compile(pattern, re.IGNORECASE).finditer(normalized, start, stop))
        match = matches[-1] if last and matches else matches[0] if matches else None
        return (match.start(), match.end()) if match else None

    def found(element_id: str, check_id: str, ok: bool, span: Span = None) -> Element:
        return Element(element_id, check_id, ok, span if ok else None)

    recipient_ok = (
        re.fullmatch(rf"To:\s*{re.escape(case['customer_email'])}\s*", to_line, re.IGNORECASE)
        is not None
    )
    subject_ok = (
        re.match(r"^Subject:\s*\S", subject, re.IGNORECASE) is not None
        and case["order_id"].casefold() in subject.casefold()
    )
    refund_amount = rf"(?<!\d){re.escape(case['refund_amount_egp'])}(?!\d)\s*(?:egp|جنيه)"
    response_window = case["response_window_business_days"]
    response_terms: tuple[str, ...] = (f"{response_window} business days",)
    if response_window == "2":
        response_terms += ("two business days", "يومي عمل", "يومين عمل")
    apologies = ("sorry", "apolog", "نعتذر", "آسف", "اسف")
    refunds = ("refund", "reimburs", "استرداد", "رد المبلغ")
    nonblank_lines = [line.casefold() for line in body.splitlines() if line.strip()]
    greeting = nonblank_lines[0] if nonblank_lines else ""
    closing = "\n".join(nonblank_lines[-3:])
    names = (case["customer_name"].casefold(), case["customer_name_ar"].casefold())
    closings = ("best regards", "kind regards", "sincerely", "مع التحية", "تحياتنا")
    companies = ("yom awel", "يوم أول")
    return [
        found("recipient", "recipient_and_subject", recipient_ok, (0, len(to_line))),
        found(
            "subject_order",
            "recipient_and_subject",
            subject_ok,
            where(re.escape(case["order_id"]), line=1) if len(lines) > 1 else None,
        ),
        found("body", "recipient_and_subject", bool(body.strip())),
        *(
            found(
                element_id, "case_facts", case[key].casefold() in lower, where(re.escape(case[key]))
            )
            for element_id, key in (
                ("order_id", "order_id"),
                ("promised_date", "promised_date"),
                ("updated_date", "updated_delivery_date"),
            )
        ),
        found(
            "refund_amount",
            "case_facts",
            re.search(refund_amount, lower) is not None,
            where(refund_amount),
        ),
        found("apology", "action_plan", _has_any(lower, apologies), where(_alternation(apologies))),
        found("refund", "action_plan", _has_any(lower, refunds), where(_alternation(refunds))),
        found(
            "response_window",
            "action_plan",
            _has_any(lower, response_terms),
            where(_alternation(response_terms)),
        ),
        found(
            "commitments_kept",
            "action_plan",
            not _negates_commitment(lower, "refund") and not _negates_commitment(lower, "response"),
        ),
        found(
            "greeting",
            "professional_closing",
            _has_any(greeting, names),
            where(_alternation(names)),
        ),
        found(
            "closing_phrase",
            "professional_closing",
            _has_any(closing, closings),
            where(_alternation(closings), last=True),
        ),
        found(
            "company_signature",
            "professional_closing",
            _has_any(closing, companies),
            where(_alternation(companies), last=True),
        ),
        found("length", "professional_closing", policy.min_words <= len(words) <= policy.max_words),
    ]


def _email_body(normalized: str) -> str:
    """Everything after the To line, the Subject line and one blank line."""

    lines = normalized.splitlines()
    return "\n".join(lines[3:]) if len(lines) > 3 and not lines[2].strip() else ""


def _words(body: str) -> list[str]:
    return re.findall(r"[\w\u0600-\u06ff]+", body, flags=re.UNICODE)


def _line_starts(text: str) -> list[int]:
    starts, offset = [], 0
    for line in text.splitlines(keepends=True):
        starts.append(offset)
        offset += len(line)
    return starts + [offset] * 4


def _alternation(choices: tuple[str, ...]) -> str:
    return "|".join(re.escape(choice) for choice in choices)


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
