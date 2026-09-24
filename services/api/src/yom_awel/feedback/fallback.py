from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter

from yom_awel.domain.contracts import EvaluationCheck, EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.personas import PERSONAS
from yom_awel.feedback.policy import ACTIVE_FEEDBACK_POLICY
from yom_awel.ports.feedback import FeedbackProvider

_Guidance = tuple[str, str]
_Sections = tuple[str, str, str, str]

# Grading policy of task clean-sales@1 (learning-objectives.yaml pass_policy). The
# evaluation carries the outcome but not the rule, so the explanation restates it.
PASS_THRESHOLD = 75
CRITICAL_CHECK_IDS = frozenset({"unique_orders"})

SECTION_HEADINGS: dict[Language, tuple[str, str, str, str]] = {
    Language.AR_EG: ("القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:"),
    Language.EN: ("Decision:", "Business impact:", "Next action:", "Score explanation:"),
}

# Per failed check: (business impact, next action). Never quotes learner cells.
CHECK_GUIDANCE: dict[str, dict[Language, _Guidance]] = {
    "unique_orders": {
        Language.AR_EG: (
            "تكرار الطلبات بيضخّم إجمالي المبيعات ويبوّظ التقرير",
            "راجع معرفات الطلبات المكررة وخلّي لكل طلب سطر واحد بس",
        ),
        Language.EN: (
            "duplicate orders inflate total revenue and distort the sales report",
            "review repeated order IDs and keep exactly one row per order",
        ),
    },
    "standard_dates": {
        Language.AR_EG: (
            "اختلاف تنسيق التواريخ بيلخبط ترتيب المبيعات بين الفترات",
            "وحّد كل التواريخ على صيغة YYYY-MM-DD",
        ),
        Language.EN: (
            "mixed date formats scramble the order of sales across periods",
            "convert every order date to the ISO format YYYY-MM-DD",
        ),
    },
    "valid_numeric_values": {
        Language.AR_EG: (
            "القيم الرقمية الغلط بتضعف دقة إجمالي المبيعات",
            "خلّي الكميات والأسعار موجبة واتأكد إن الإيراد يساوي الكمية في سعر الوحدة",
        ),
        Language.EN: (
            "invalid quantities or prices make the revenue totals unreliable",
            (
                "keep quantities and unit prices positive and make revenue equal quantity"
                " times unit price"
            ),
        ),
    },
    "complete_customer_records": {
        Language.AR_EG: (
            "سجلات العملاء الناقصة بتصعّب متابعة الطلبات",
            "سيب كل الطلبات واكتب unavailable في missing_email_reason لأي عميل من غير إيميل",
        ),
        Language.EN: (
            "incomplete customer records make orders hard to follow up",
            (
                "keep every order and write unavailable in missing_email_reason for each"
                " customer without an email"
            ),
        ),
    },
}

_GENERIC_GUIDANCE: dict[Language, _Guidance] = {
    Language.AR_EG: (
        "المشكلة المسجّلة بتقلل الثقة في النتيجة لما نستخدمها في الشغل",
        "راجع الفحص المذكور ورسالة المقيّم وصحّح الملف",
    ),
    Language.EN: (
        "the recorded issue lowers confidence in the result at work",
        "review the named check and the evaluator message and correct the file",
    ),
}

# Rejection vocabulary v1, verbatim from task_packages/clean-sales/1/learning-objectives.yaml.
REJECTION_MESSAGES: dict[str, dict[Language, str]] = {
    "unsupported_type": {
        Language.AR_EG: "صيغة الملف غير مدعومة. يرجى رفع ملف CSV أو XLSX صالح.",
        Language.EN: "Unsupported file format. Please upload a valid CSV or XLSX spreadsheet.",
    },
    "artifact_too_large": {
        Language.AR_EG: "حجم الملف يتجاوز الحد الأقصى المسموح (5 ميجابايت).",
        Language.EN: "File size exceeds the 5 MiB limit.",
    },
    "mime_mismatch": {
        Language.AR_EG: "محتوى الملف لا يطابق صيغة CSV أو XLSX المعلنة.",
        Language.EN: "File content does not match its declared CSV or XLSX format.",
    },
    "expanded_size_exceeded": {
        Language.AR_EG: "محتوى ملف العمل بعد فك الضغط يتجاوز حد المعالجة الآمن.",
        Language.EN: "Expanded workbook content exceeds the safe processing limit.",
    },
    "sheet_limit_exceeded": {
        Language.AR_EG: "يجب أن يحتوي ملف العمل على ورقة العمل النشطة المدعومة فقط.",
        Language.EN: "Workbook must contain only the supported active worksheet.",
    },
    "artifact_unreadable": {
        Language.AR_EG: (
            "تعذر قراءة الملف كجدول بيانات صالح (مثل بنية تالفة، أو ماكرو مفعّل، أو ملف محمي بكلمة سر)."
        ),
        Language.EN: (
            "File cannot be parsed as a tabular spreadsheet "
            "(e.g. corrupt structure, macro workbook, or password protected)."
        ),
    },
    "missing_columns": {
        Language.AR_EG: "أعمدة أساسية مطلوبة مفقودة من الملف.",
        Language.EN: "Required column headers are missing.",
    },
    "duplicate_columns": {
        Language.AR_EG: "تم العثور على أسماء أعمدة مكررة في صف العناوين.",
        Language.EN: "Duplicate column names detected in the header row.",
    },
    "too_few_rows": {
        Language.AR_EG: "الملف المنظف يحتوي على أقل من الحد الأدنى المطلوب (40 صفاً).",
        Language.EN: "Cleaned dataset contains fewer than the required 40 rows.",
    },
}

# What to do about each rejection. Generic to the code, so no file content is echoed.
REJECTION_ACTIONS: dict[str, dict[Language, str]] = {
    "unsupported_type": {
        Language.AR_EG: "احفظ الملف المنظف بصيغة CSV أو XLSX",
        Language.EN: "save the cleaned sheet as CSV or XLSX",
    },
    "artifact_too_large": {
        Language.AR_EG: "صغّر الملف لأقل من 5 ميجابايت وسيب جدول الطلبات بس من غير أوراق أو تنسيقات زيادة",
        Language.EN: "bring the file under 5 MiB by keeping only the orders table, without extra"
        " sheets or formatting",
    },
    "mime_mismatch": {
        Language.AR_EG: "افتح الملف واحفظه من جديد بنفس صيغة امتداده بدل ما تغيّر الامتداد بإيدك",
        Language.EN: "open the file and save it again in the format its extension names instead of"
        " renaming the extension",
    },
    "expanded_size_exceeded": {
        Language.AR_EG: "احفظ نسخة فيها جدول الطلبات بس من غير صور أو تنسيقات تقيلة، أو صدّرها CSV",
        Language.EN: "save a copy with only the orders table and no images or heavy formatting,"
        " or export it as CSV",
    },
    "sheet_limit_exceeded": {
        Language.AR_EG: "خلّي في الملف ورقة واحدة بس فيها جدول الطلبات وامسح أي أوراق تانية",
        Language.EN: "keep a single worksheet holding the orders table and delete any other sheets",
    },
    "artifact_unreadable": {
        Language.AR_EG: "احفظ الملف تاني كـ CSV أو XLSX عادي من غير ماكرو ولا كلمة سر",
        Language.EN: "save it again as a plain CSV or XLSX without macros or a password",
    },
    "missing_columns": {
        Language.AR_EG: "رجّع صف العناوين بكل الأعمدة المطلوبة بأسمائها الأصلية زي ما في ملف المهمة",
        Language.EN: "restore the header row with every required column under its original name,"
        " as in the task file",
    },
    "duplicate_columns": {
        Language.AR_EG: "خلّي كل اسم عمود يظهر مرة واحدة بس في صف العناوين وامسح العمود المكرر",
        Language.EN: "make each column name appear once in the header row and remove the repeated"
        " column",
    },
    "too_few_rows": {
        Language.AR_EG: "سيب كل الطلبات السليمة عشان الملف المنظف يفضل فيه 40 طلب على الأقل",
        Language.EN: "keep every valid order so the cleaned file has at least 40 orders",
    },
}


@dataclass(frozen=True, slots=True)
class _Voice:
    """Tarek's fixed phrasing for one language; placeholders are filled from the evaluation."""

    accepted: str
    accepted_with_gaps: str
    rework: str
    critical_blocks: str
    not_graded: str
    passed_impact: str
    passed_impact_with_gaps: str
    passed_action: str
    passed_action_with_gaps: str
    rejected_impact: str
    retry_action: str
    score_passed: str
    score_critical: str
    score_below_with_critical: str
    score_below: str
    score_rejected: str
    one_more: str
    two_more: str
    many_more: str
    separator: str
    signature: str


_TAREK = PERSONAS[ACTIVE_FEEDBACK_POLICY.persona_id]

_VOICES: dict[Language, _Voice] = {
    Language.AR_EG: _Voice(
        accepted="التسليم مقبول. شغل نضيف.",
        accepted_with_gaps="التسليم مقبول، وفاضل حاجة بسيطة تتظبط.",
        rework="التسليم محتاج إعادة شغل.",
        critical_blocks="الطلبات المكررة بتمنع النجاح مهما كانت الدرجة.",
        not_graded="الملف ما اتقيّمش: {reason}",
        passed_impact="التقرير اليومي يقدر يعتمد على الملف ده، كل طلب محسوب مرة واحدة والأرقام مظبوطة.",
        passed_impact_with_gaps="الملف ينفع للتقرير، بس {consequences}.",
        passed_action="كمّل على المهمة الجاية بنفس خطوات التنظيف دي.",
        passed_action_with_gaps="قبل المهمة اللي بعد كده، {actions}.",
        rejected_impact=(
            "مفيش ولا فحص اشتغل على الملف، فمفيش أرقام نقدر نعتمد عليها في تقرير المبيعات لسه."
        ),
        retry_action="{actions}، وبعدين ارفع الملف تاني.",
        score_passed="حصلت على {score} من 100، وده بيوصلك لحد النجاح ({threshold}).",
        score_critical=(
            "حصلت على {score} من 100، ودي درجة بتوصل لحد النجاح ({threshold})، بس فحص الطلبات"
            " المكررة أساسي ولازم ينجح عشان التسليم يعدّي."
        ),
        score_below_with_critical=(
            "حصلت على {score} من 100 وحد النجاح {threshold}، وكمان فحص الطلبات المكررة لازم ينجح."
        ),
        score_below="حصلت على {score} من 100 وحد النجاح {threshold}، يعني ناقصك {missing} درجة.",
        score_rejected="حصلت على {score} من 100 لأن الفحوصات ما اتشغلتش على الملف ده.",
        one_more=" وفيه فحص إضافي واحد محتاج مراجعة.",
        two_more=" وفيه فحصان إضافيان محتاجان مراجعة.",
        many_more=" وفيه {count} فحوصات إضافية محتاجة مراجعة.",
        separator="؛ ",
        signature=f"{_TAREK.name_ar}، {_TAREK.workplace_role}",
    ),
    Language.EN: _Voice(
        accepted="submission accepted. Clean, solid work.",
        accepted_with_gaps="submission accepted, with a small gap left to close.",
        rework="submission needs rework.",
        critical_blocks="Duplicate orders block passing, whatever the score.",
        not_graded="The file was not graded: {reason}",
        passed_impact=(
            "the daily sales report can rely on this file, with every order counted once and"
            " numbers that add up."
        ),
        passed_impact_with_gaps="the file works for the report, but {consequences}.",
        passed_action="carry the same cleaning steps into the next task.",
        passed_action_with_gaps="before the next task, {actions}.",
        rejected_impact=(
            "none of the checks could run, so the sales report has no numbers it can rely on yet."
        ),
        retry_action="{actions}, then upload the file again.",
        score_passed="{score} of 100 meets the pass mark of {threshold}.",
        score_critical=(
            "{score} of 100 reaches the pass mark of {threshold}, but the duplicate orders check"
            " is critical, so the submission cannot pass until it does."
        ),
        score_below_with_critical=(
            "{score} of 100 is below the pass mark of {threshold}, and the duplicate orders"
            " check must also pass."
        ),
        score_below=(
            "{score} of 100 is below the pass mark of {threshold}; you need {missing} more points."
        ),
        score_rejected="{score} of 100, because the checks could not run on this file.",
        one_more=" One more check also needs review.",
        two_more=" Two more checks also need review.",
        many_more=" {count} more checks also need review.",
        separator="; ",
        signature=f"{_TAREK.name_en}, {_TAREK.workplace_role_en}",
    ),
}

_MAX_LISTED_FAILURES = 3


class DeterministicFeedbackProvider(FeedbackProvider):
    def __init__(self, clock: Callable[[], float] = perf_counter) -> None:
        self._clock = clock

    async def generate(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None = None,
    ) -> FeedbackResult:
        del learner_note
        started = self._clock()
        text = self.render_text(evaluation, language)
        duration_ms = max(0, round((self._clock() - started) * 1000))
        return FeedbackResult(
            feedback_text=text,
            language=language.value,
            persona_id=ACTIVE_FEEDBACK_POLICY.persona_id,
            prompt_version=ACTIVE_FEEDBACK_POLICY.version,
            provider="deterministic",
            model=None,
            used_fallback=True,
            duration_ms=duration_ms,
        )

    @staticmethod
    def render_text(evaluation: EvaluationResult, language: Language) -> str:
        """The sole approved learner-visible rendering for this evaluation."""
        text = _compose(_sections(evaluation, language, compact=False), language)
        if len(text) > ACTIVE_FEEDBACK_POLICY.maximum_characters:
            text = _compose(_sections(evaluation, language, compact=True), language)
        return text


def _rejection_code(evaluation: EvaluationResult) -> str | None:
    """The first known rejection: the file was refused, so its checks never ran."""
    return next(
        (error.code for error in evaluation.errors if error.code in REJECTION_MESSAGES), None
    )


def _compose(sections: _Sections, language: Language) -> str:
    lines = (
        f"{heading} {body}"
        for heading, body in zip(SECTION_HEADINGS[language], sections, strict=True)
    )
    return "\n".join((_VOICES[language].signature, *lines))


def _sections(evaluation: EvaluationResult, language: Language, *, compact: bool) -> _Sections:
    voice = _VOICES[language]
    code = _rejection_code(evaluation)
    if code is not None:
        return (
            f"{voice.rework} {voice.not_graded.format(reason=REJECTION_MESSAGES[code][language])}",
            voice.rejected_impact,
            voice.retry_action.format(actions=REJECTION_ACTIONS[code][language]),
            voice.score_rejected.format(score=evaluation.score),
        )
    failures = sorted(
        (check for check in evaluation.checks if not check.passed),
        key=lambda check: check.check_id not in CRITICAL_CHECK_IDS,
    )
    listed = [_GENERIC_GUIDANCE[language]] if compact else _guidance(failures, language)
    consequences = voice.separator.join(dict.fromkeys(item[0] for item in listed))
    actions = voice.separator.join(dict.fromkeys(item[1] for item in listed))
    if evaluation.passed:
        return (
            voice.accepted_with_gaps if failures else voice.accepted,
            voice.passed_impact_with_gaps.format(consequences=consequences)
            if failures
            else voice.passed_impact,
            voice.passed_action_with_gaps.format(actions=actions)
            if failures
            else voice.passed_action,
            voice.score_passed.format(score=evaluation.score, threshold=PASS_THRESHOLD),
        )
    critical_failed = any(check.check_id in CRITICAL_CHECK_IDS for check in failures)
    remainder = "" if compact else _remainder(len(failures) - len(listed), voice)
    return (
        f"{voice.rework} {voice.critical_blocks}" if critical_failed else voice.rework,
        f"{consequences}.{remainder}",
        voice.retry_action.format(actions=actions),
        _retry_score(evaluation.score, critical_failed, voice),
    )


def _guidance(failures: Sequence[EvaluationCheck], language: Language) -> list[_Guidance]:
    if not failures:
        return [_GENERIC_GUIDANCE[language]]
    return [
        CHECK_GUIDANCE.get(check.check_id, _GENERIC_GUIDANCE)[language]
        for check in failures[:_MAX_LISTED_FAILURES]
    ]


def _remainder(count: int, voice: _Voice) -> str:
    if count <= 0:
        return ""
    if count == 1:
        return voice.one_more
    if count == 2:
        return voice.two_more
    return voice.many_more.format(count=count)


def _retry_score(score: int, critical_failed: bool, voice: _Voice) -> str:
    if critical_failed:
        template = (
            voice.score_critical if score >= PASS_THRESHOLD else voice.score_below_with_critical
        )
    else:
        template = voice.score_below
    return template.format(
        score=score, threshold=PASS_THRESHOLD, missing=max(0, PASS_THRESHOLD - score)
    )
