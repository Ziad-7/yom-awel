from yom_awel.domain.contracts import EvaluationResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.fallback import DeterministicFeedbackProvider


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

