import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.errors import ProviderResponseError
from yom_awel.feedback.policy import ACTIVE_FEEDBACK_POLICY

_ARABIC = re.compile(r"[\u0600-\u06ff]")
_AR_SECTIONS = ("القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:")
_EN_SECTIONS = ("Decision:", "Business impact:", "Next action:", "Score explanation:")


class ProviderPayload(BaseModel):
    """Provider wire format, not a replacement for the canonical FeedbackResult."""

    model_config = ConfigDict(extra="forbid", strict=True)

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
        response = ProviderPayload.model_validate(decoded)
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
    failed_check_ids = {check.check_id for check in evaluation.checks if not check.passed}
    if failed_check_ids and not failed_check_ids.intersection(response.referenced_check_ids):
        raise ProviderResponseError("missing_failed_check_reference")

    result = FeedbackResult(
        feedback_text=normalized,
        language=language.value,
        persona_id=ACTIVE_FEEDBACK_POLICY.persona_id,
        prompt_version=ACTIVE_FEEDBACK_POLICY.version,
        provider=provider,
        model=model,
        used_fallback=False,
        duration_ms=max(0, duration_ms),
    )
    validate_grounded_feedback(result, evaluation, language)
    return result


def validate_grounded_feedback(
    result: FeedbackResult, evaluation: EvaluationResult, language: Language
) -> None:
    """Validate prose too, including results returned by another primary provider."""
    text = " ".join(result.feedback_text.split())
    if result.language != language.value:
        raise ProviderResponseError("wrong_language")
    if not text or len(text) > 900:
        raise ProviderResponseError("invalid_feedback_length")
    if language is Language.AR_EG and not _ARABIC.search(text):
        raise ProviderResponseError("non_arabic_response")

    headings = _AR_SECTIONS if language is Language.AR_EG else _EN_SECTIONS
    positions = [text.find(heading) for heading in headings]
    if (
        any(position < 0 for position in positions)
        or positions != sorted(positions)
        or any(text.count(heading) != 1 for heading in headings)
    ):
        raise ProviderResponseError("missing_feedback_sections")
    sections = [
        text[position + len(heading) : positions[index + 1] if index < 3 else None].strip()
        for index, (position, heading) in enumerate(zip(positions, headings, strict=True))
    ]
    if any(not section for section in sections):
        raise ProviderResponseError("empty_feedback_section")
    if language is Language.AR_EG and any(not _ARABIC.search(section) for section in sections):
        raise ProviderResponseError("non_arabic_response")

    if language is Language.AR_EG:
        expected = "التسليم مقبول" if evaluation.passed else "التسليم محتاج إعادة شغل"
        opposite = "التسليم محتاج إعادة شغل" if evaluation.passed else "التسليم مقبول"
        score_pattern = rf"(?<!\d){evaluation.score}(?!\d)\s*من\s*100"
    else:
        expected = "submission accepted" if evaluation.passed else "submission needs rework"
        opposite = "submission needs rework" if evaluation.passed else "submission accepted"
        score_pattern = rf"(?<!\d){evaluation.score}(?!\d)\s*of\s*100"
    if not sections[0].startswith(expected) or opposite in text:
        raise ProviderResponseError("text_contradiction")
    if not re.search(score_pattern, sections[3]):
        raise ProviderResponseError("text_contradiction")
