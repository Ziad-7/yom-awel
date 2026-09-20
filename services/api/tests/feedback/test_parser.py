import json

import pytest

from yom_awel.domain.contracts import EvaluationResult
from yom_awel.feedback.errors import ProviderResponseError
from yom_awel.feedback.parser import parse_provider_response


def valid_payload() -> dict[str, object]:
    return {
        "feedback_text": (
            "القرار: التسليم محتاج إعادة شغل. "
            "تأثير الشغل: البيانات الناقصة تؤثر على إجمالي المبيعات. "
            "الخطوة الجاية: راجع البيانات قبل إعادة التسليم. "
            "تفسير الدرجة: حصلت على 0 من 100."
        ),
        "language": "ar-EG",
        "decision": "retry",
        "score": 0,
        "referenced_check_ids": ["clean_data"],
        "reveals_reference_solution": False,
    }


def test_parser_accepts_grounded_response(failed_evaluation: EvaluationResult) -> None:
    result = parse_provider_response(
        json.dumps(valid_payload(), ensure_ascii=False),
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
        lambda payload: payload.update(referenced_check_ids=["invented-check"]),
        lambda payload: payload.update(reveals_reference_solution=True),
        lambda payload: payload.update(feedback_text="English only feedback"),
        lambda payload: payload.update(referenced_check_ids=[]),
    ],
)
def test_parser_rejects_unsafe_or_ungrounded_response(
    failed_evaluation: EvaluationResult, mutation: object
) -> None:
    payload = valid_payload()
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
