import pytest

from yom_awel.domain.contracts import EvaluationCheck, EvaluationResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.fallback import CHECK_GUIDANCE, DeterministicFeedbackProvider


async def test_pass_fallback_is_valid_and_does_not_request_rework(
    passed_evaluation: EvaluationResult,
) -> None:
    result = await DeterministicFeedbackProvider().generate(
        passed_evaluation, Language.AR_EG, None
    )
    assert result.language == "ar-EG"
    assert result.persona_id == "eng-tarek"
    assert result.prompt_version == "tarek-feedback@1"
    assert result.provider == "deterministic"
    assert result.model is None
    assert result.used_fallback is True
    assert str(passed_evaluation.score) in result.feedback_text
    assert "إعادة شغل" not in result.feedback_text


async def test_failed_checks_have_grounded_consequence_and_tip(
    failed_evaluation: EvaluationResult,
) -> None:
    result = await DeterministicFeedbackProvider().generate(
        failed_evaluation, Language.AR_EG, None
    )
    assert "بيانات المبيعات غير المكتملة" in result.feedback_text
    assert "قواعد تنظيف البيانات" in result.feedback_text
    assert str(failed_evaluation.score) in result.feedback_text


async def test_many_failed_checks_keep_all_four_sections_and_score(
    failed_evaluation: EvaluationResult,
) -> None:
    checks = [
        EvaluationCheck(check_id=f"unknown_{index}", passed=False, weight=1)
        for index in range(100)
    ]
    evaluation = failed_evaluation.model_copy(update={"checks": checks, "score": 7})
    result = await DeterministicFeedbackProvider().generate(
        evaluation, Language.AR_EG, None
    )
    headings = ("القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:")
    assert all(heading in result.feedback_text for heading in headings)
    assert "7 من 100" in result.feedback_text
    assert "97 فحوصات إضافية" in result.feedback_text
    assert len(result.feedback_text) <= 900


async def test_failure_without_failed_check_still_explains_retry(
    failed_evaluation: EvaluationResult,
) -> None:
    evaluation = failed_evaluation.model_copy(update={"checks": []})
    result = await DeterministicFeedbackProvider().generate(
        evaluation, Language.AR_EG, None
    )
    assert "تأثير الشغل: ." not in result.feedback_text
    assert "الخطوة الجاية:" in result.feedback_text


async def test_oversized_guidance_uses_complete_short_template(
    failed_evaluation: EvaluationResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(CHECK_GUIDANCE, "clean_data", ("سبب " * 300, "إجراء " * 300))
    result = await DeterministicFeedbackProvider().generate(
        failed_evaluation, Language.AR_EG
    )
    assert len(result.feedback_text) <= 900
    assert "الخطوة الجاية:" in result.feedback_text
    assert "تفسير الدرجة: حصلت على 0 من 100" in result.feedback_text

