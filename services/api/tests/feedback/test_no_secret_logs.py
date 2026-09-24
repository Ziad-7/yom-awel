import logging

from yom_awel.domain.contracts import EvaluationResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.errors import ProviderNetworkError
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.service import ResilientFeedbackProvider


class FailingProvider:
    async def generate(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None,
    ):  # type: ignore[no-untyped-def]
        del evaluation, language, learner_note
        raise ProviderNetworkError()


async def test_logs_include_metrics_but_no_sensitive_bodies(
    failed_evaluation: EvaluationResult,
    caplog,
) -> None:  # type: ignore[no-untyped-def]
    secret = "AIza-secret-value-that-must-not-be-logged"
    note = f"learner@example.com {secret} storage://private/raw.xlsx"
    with caplog.at_level(logging.INFO):
        await ResilientFeedbackProvider(
            FailingProvider(), DeterministicFeedbackProvider()
        ).generate(failed_evaluation, Language.AR_EG, note)
    rendered = " ".join(record.getMessage() for record in caplog.records)
    extras = " ".join(str(record.__dict__) for record in caplog.records)
    for forbidden in (secret, note, "learner@example.com", "private/raw.xlsx"):
        assert forbidden not in rendered
        assert forbidden not in extras
    record = caplog.records[-1]
    assert record.provider_error_code == "network"
    assert record.correlation_id
    assert record.used_fallback is True
    assert record.duration_ms >= 0
