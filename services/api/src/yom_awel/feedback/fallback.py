from collections.abc import Callable
from time import perf_counter

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.policy import ACTIVE_FEEDBACK_POLICY
from yom_awel.ports.feedback import FeedbackProvider

_Guidance = tuple[str, str]

CHECK_GUIDANCE: dict[str, _Guidance] = {
    "unique_orders": (
        "تكرار الطلبات يضخم إجمالي المبيعات ويشوّه التقرير",
        "راجع معرفات الطلبات المكررة ونظّفها قبل إعادة التسليم",
    ),
    "standard_dates": (
        "اختلاف تنسيق التواريخ يربك ترتيب المبيعات عبر الفترات",
        "وحّد تنسيق التواريخ ثم أعد فحص ترتيب السجلات",
    ),
    "valid_numeric_values": (
        "القيم الرقمية غير الصالحة تضعف دقة إجمالي المبيعات",
        "تحقق من قيم الكميات والأسعار وصحح غير الصالح منها",
    ),
    "complete_customer_records": (
        "سجلات العملاء الناقصة تصعّب متابعة الطلبات",
        "أكمل بيانات العملاء المطلوبة ثم أعد التسليم",
    ),
}

_GENERIC_GUIDANCE: _Guidance = (
    "الخطأ المسجّل يقلل موثوقية النتيجة عند استخدامها في الشغل",
    "راجع الفحص المذكور ورسالة المقيم ثم صحح الملف قبل إعادة التسليم",
)


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
        if language is Language.EN:
            text = DeterministicFeedbackProvider._english_text(evaluation)
        elif evaluation.passed:
            text = (
                "القرار: التسليم مقبول.\n"
                "تأثير الشغل: النتيجة بقت موثوقة ويمكن استخدامها في اتخاذ القرار.\n"
                "الخطوة الجاية: راجع ملخصك النهائي واستعد للمهمة التالية.\n"
                f"تفسير الدرجة: حصلت على {evaluation.score} من 100 حسب الفحوصات المحددة."
            )
        else:
            failures = [check for check in evaluation.checks if not check.passed]
            selected = failures[:3]
            consequences = [
                CHECK_GUIDANCE.get(check.check_id, _GENERIC_GUIDANCE)[0] for check in selected
            ]
            actions = [
                CHECK_GUIDANCE.get(check.check_id, _GENERIC_GUIDANCE)[1] for check in selected
            ]
            if not selected:
                consequences = [_GENERIC_GUIDANCE[0]]
                actions = [_GENERIC_GUIDANCE[1]]
            remaining = len(failures) - len(selected)
            if remaining == 1:
                remainder = " وفيه فحص إضافي واحد محتاج مراجعة."
            elif remaining == 2:
                remainder = " وفيه فحصان إضافيان محتاجان مراجعة."
            else:
                remainder = f" وفيه {remaining} فحوصات إضافية محتاجة مراجعة." if remaining else ""
            text = (
                "القرار: التسليم محتاج إعادة شغل.\n"
                f"تأثير الشغل: {'؛ '.join(consequences)}.{remainder}\n"
                f"الخطوة الجاية: {'؛ '.join(actions)}.\n"
                f"تفسير الدرجة: حصلت على {evaluation.score} من 100 حسب الفحوصات المحددة."
            )
        if len(text) > ACTIVE_FEEDBACK_POLICY.maximum_characters:
            text = DeterministicFeedbackProvider._short_text(evaluation, language)
        return text

    @staticmethod
    def _english_text(evaluation: EvaluationResult) -> str:
        if evaluation.passed:
            return (
                "Decision: submission accepted.\n"
                "Business impact: the result is reliable enough for the next workplace step.\n"
                "Next action: review the final summary and continue to the next task.\n"
                f"Score explanation: the deterministic checks awarded {evaluation.score} of 100."
            )
        return (
            "Decision: submission needs rework.\n"
            "Business impact: the failed checks reduce confidence in the report.\n"
            "Next action: review the evaluator details and correct the file before resubmitting.\n"
            f"Score explanation: the deterministic checks awarded {evaluation.score} of 100."
        )

    @staticmethod
    def _short_text(evaluation: EvaluationResult, language: Language) -> str:
        if language is Language.EN:
            decision = "accepted" if evaluation.passed else "needs rework"
            return (
                f"Decision: submission {decision}.\n"
                "Business impact: the evaluated result affects report reliability.\n"
                "Next action: review the recorded checks before the next task.\n"
                f"Score explanation: {evaluation.score} of 100 from deterministic checks."
            )
        decision = "مقبول" if evaluation.passed else "محتاج إعادة شغل"
        return (
            f"القرار: التسليم {decision}.\n"
            "تأثير الشغل: نتيجة الفحوصات تؤثر على موثوقية التقرير.\n"
            "الخطوة الجاية: راجع الفحوصات المسجلة قبل الخطوة التالية.\n"
            f"تفسير الدرجة: حصلت على {evaluation.score} من 100 حسب الفحوصات المحددة."
        )
