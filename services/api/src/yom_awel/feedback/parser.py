import json
import re
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.errors import ProviderResponseError
from yom_awel.feedback.policy import ACTIVE_FEEDBACK_POLICY

_ARABIC = re.compile(r"[\u0600-\u06ff]")
_AR_SECTIONS = ("القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:")
_EN_SECTIONS = ("Decision:", "Business impact:", "Next action:", "Score explanation:")


class _ProviderPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback_text: str = Field(min_length=1, max_length=900)
    language: Literal["ar-EG", "en"]
    decision: Literal["pass", "retry"]
    score: int = Field(ge=0, le=100)
    referenced_check_ids: list[str] = Field(max_length=20)
    reveals_reference_solution: bool


def parse_provider_response(
    payload: str,
    evaluation: EvaluationResult,
    *,
    provider: str,
    model: str,
    duration_ms: int,
    language: Language = Language.AR_EG,
) -> FeedbackResult:
    try:
        decoded = json.loads(payload)
        response = _ProviderPayload.model_validate(decoded)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        raise ProviderResponseError("malformed_response") from exc

    expected_decision = "pass" if evaluation.passed else "retry"
    if response.language != language.value:
        raise ProviderResponseError("wrong_language")
    if response.decision != expected_decision:
        raise ProviderResponseError("grade_contradiction")
    if response.score != evaluation.score:
        raise ProviderResponseError("score_contradiction")
    known_checks = {check.check_id for check in evaluation.checks}
    if not set(response.referenced_check_ids).issubset(known_checks):
        raise ProviderResponseError("invented_check")
    if response.reveals_reference_solution:
        raise ProviderResponseError("solution_disclosure")
    normalized = " ".join(response.feedback_text.split())
    if language is Language.AR_EG and not _ARABIC.search(normalized):
        raise ProviderResponseError("non_arabic_response")
    headings = _AR_SECTIONS if language is Language.AR_EG else _EN_SECTIONS
    positions = [normalized.find(heading) for heading in headings]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        raise ProviderResponseError("missing_feedback_sections")
    if language is Language.AR_EG:
        expected_text_decision = (
            "القرار: التسليم مقبول"
            if evaluation.passed
            else "القرار: التسليم محتاج إعادة شغل"
        )
    else:
        expected_text_decision = (
            "Decision: submission accepted"
            if evaluation.passed
            else "Decision: submission needs rework"
        )
    if expected_text_decision not in normalized or str(evaluation.score) not in normalized:
        raise ProviderResponseError("text_contradiction")
    failed_check_ids = {check.check_id for check in evaluation.checks if not check.passed}
    if failed_check_ids and not failed_check_ids.intersection(response.referenced_check_ids):
        raise ProviderResponseError("missing_failed_check_reference")

    return FeedbackResult(
        feedback_text=normalized,
        language=cast(Literal["ar-EG", "en"], language.value),
        persona_id=ACTIVE_FEEDBACK_POLICY.persona_id,
        prompt_version=ACTIVE_FEEDBACK_POLICY.version,
        provider=provider,
        model=model,
        used_fallback=False,
        duration_ms=max(0, duration_ms),
    )
