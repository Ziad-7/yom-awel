from collections.abc import Iterable

import pytest

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.errors import (
    FeedbackProviderError,
    ProviderNetworkError,
    ProviderQuotaError,
    ProviderRefusalError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.service import ResilientFeedbackProvider


class SequenceProvider:
    def __init__(self, results: Iterable[FeedbackResult | Exception]) -> None:
        self._results = iter(results)
        self.calls = 0

    async def generate(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None,
    ) -> FeedbackResult:
        del evaluation, language, learner_note
        self.calls += 1
        result = next(self._results)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.mark.parametrize(
    "error",
    [
        ProviderTimeoutError(),
        ProviderQuotaError(),
        ProviderNetworkError(),
        ProviderRefusalError(),
        ProviderResponseError("malformed_response"),
        ProviderResponseError("score_contradiction"),
        RuntimeError("unexpected"),
    ],
)
async def test_all_provider_failures_return_valid_fallback(
    failed_evaluation: EvaluationResult,
    error: Exception,
) -> None:
    primary = SequenceProvider([error, error])
    service = ResilientFeedbackProvider(primary, DeterministicFeedbackProvider())
    result = await service.generate(failed_evaluation, Language.AR_EG, None)
    assert result.used_fallback is True
    assert result.provider == "deterministic"
    assert str(failed_evaluation.score) in result.feedback_text


async def test_missing_provider_is_normal_fallback_path(
    failed_evaluation: EvaluationResult,
) -> None:
    service = ResilientFeedbackProvider(None, DeterministicFeedbackProvider())
    result = await service.generate(failed_evaluation, Language.AR_EG, None)
    assert result.used_fallback is True


async def test_transient_failure_retries_once(
    failed_evaluation: EvaluationResult,
) -> None:
    generated = FeedbackResult(
        feedback_text="التسليم محتاج تعديل في الصفوف المكررة.",
        language="ar-EG",
        persona_id="eng-tarek",
        prompt_version="tarek-feedback@1",
        provider="gemini",
        model="test-model",
        used_fallback=False,
        duration_ms=2,
    )
    primary = SequenceProvider([ProviderQuotaError(retry_after_seconds=0), generated])
    service = ResilientFeedbackProvider(primary, DeterministicFeedbackProvider())
    result = await service.generate(failed_evaluation, Language.AR_EG, None)
    assert result == generated
    assert primary.calls == 2


async def test_non_retryable_failure_is_not_retried(
    failed_evaluation: EvaluationResult,
) -> None:
    primary = SequenceProvider([FeedbackProviderError("invalid", retryable=False)])
    service = ResilientFeedbackProvider(primary, DeterministicFeedbackProvider())
    result = await service.generate(failed_evaluation, Language.AR_EG, None)
    assert result.used_fallback is True
    assert primary.calls == 1

