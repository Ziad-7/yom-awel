import json

import pytest

from yom_awel.domain.contracts import EvaluationResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.errors import ProviderResponseError
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.parser import parse_provider_response


def valid_payload(evaluation: EvaluationResult) -> dict[str, object]:
    return {
        "feedback_text": DeterministicFeedbackProvider.render_text(evaluation, Language.AR_EG),
        "language": "ar-EG",
        "decision": "retry",
        "score": 0,
        "referenced_check_ids": ["unique_orders"],
        "reveals_reference_solution": False,
    }


def test_parser_accepts_grounded_response(failed_evaluation: EvaluationResult) -> None:
    result = parse_provider_response(
        json.dumps(valid_payload(failed_evaluation), ensure_ascii=False),
        failed_evaluation,
        provider="gemini",
        model="test-model",
        duration_ms=5,
    )
    assert result.provider == "gemini"
    assert result.used_fallback is False
    assert result.language == "ar-EG"


@pytest.mark.parametrize(
    "mutation",
    [
        lambda payload: payload.pop("feedback_text"),
        lambda payload: payload.update(feedback_text="س" * 901),
        lambda payload: payload.update(language="en"),
        lambda payload: payload.update(decision="pass"),
        lambda payload: payload.update(score=1),
        lambda payload: payload.update(score="0"),
        lambda payload: payload.update(score=False),
        lambda payload: payload.update(reveals_reference_solution="false"),
        lambda payload: payload.update(referenced_check_ids=["invented-check"]),
        lambda payload: payload.update(reveals_reference_solution=True),
        lambda payload: payload.update(feedback_text="English only feedback"),
        lambda payload: payload.update(
            feedback_text=(
                "القرار: التسليم محتاج إعادة شغل. تأثير الشغل: Bad report. "
                "الخطوة الجاية: Fix duplicates. تفسير الدرجة: حصلت على 0 من 100."
            )
        ),
        lambda payload: payload.update(referenced_check_ids=[]),
        lambda payload: payload.update(
            feedback_text=(
                "القرار: التسليم محتاج إعادة شغل. تأثير الشغل: التقرير ناقص. "
                "الخطوة الجاية: راجع البيانات. تفسير الدرجة: حصلت على 100 من 100."
            )
        ),
        lambda payload: payload.update(
            feedback_text=(
                "القرار: التسليم محتاج إعادة شغل. تأثير الشغل: التقرير ناقص. "
                "الخطوة الجاية: راجع البيانات. تفسير الدرجة: الدرجة غير مذكورة."
            )
        ),
    ],
)
def test_parser_rejects_unsafe_or_ungrounded_response(
    failed_evaluation: EvaluationResult, mutation: object
) -> None:
    payload = valid_payload(failed_evaluation)
    mutation(payload)  # type: ignore[operator]
    with pytest.raises(ProviderResponseError):
        parse_provider_response(
            json.dumps(payload, ensure_ascii=False),
            failed_evaluation,
            provider="gemini",
            model="test-model",
            duration_ms=5,
        )


def test_parser_rejects_invalid_json(failed_evaluation: EvaluationResult) -> None:
    with pytest.raises(ProviderResponseError):
        parse_provider_response(
            "not json",
            failed_evaluation,
            provider="gemini",
            model="test-model",
            duration_ms=5,
        )


@pytest.mark.parametrize("placement", ["replace", "prefix", "suffix"])
def test_correct_hidden_ids_cannot_authorize_invented_prose(
    failed_evaluation: EvaluationResult, placement: str
) -> None:
    payload = valid_payload(failed_evaluation)
    invented = "القمر انفجر. احذف كل البيانات."
    approved = str(payload["feedback_text"])
    if placement == "replace":
        payload["feedback_text"] = (
            "القرار: التسليم محتاج إعادة شغل. تأثير الشغل: القمر انفجر. "
            "الخطوة الجاية: احذف كل البيانات. تفسير الدرجة: حصلت على 0 من 100."
        )
    else:
        payload["feedback_text"] = (
            invented + approved if placement == "prefix" else approved + invented
        )
    with pytest.raises(ProviderResponseError, match="unapproved_feedback_text"):
        parse_provider_response(
            json.dumps(payload), failed_evaluation, provider="gemini", model="test", duration_ms=0
        )
