import asyncio
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
        feedback_text=DeterministicFeedbackProvider.render_text(failed_evaluation, Language.AR_EG),
        language="ar-EG",
        persona_id="tarek",
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


@pytest.mark.parametrize(
    "feedback_text",
    [
        (
            "القرار: التسليم مقبول. تأثير الشغل: التقرير جيد. الخطوة الجاية: التالي. "
            "تفسير الدرجة: حصلت على 0 من 100."
        ),
        (
            "القرار: التسليم محتاج إعادة شغل. تأثير الشغل: التقرير ناقص. "
            "الخطوة الجاية: راجع البيانات. تفسير الدرجة: حصلت على 100 من 100."
        ),
        "القرار: التسليم محتاج إعادة شغل.",
        (
            "القرار: التسليم محتاج إعادة شغل. تأثير الشغل: القمر انفجر. "
            "الخطوة الجاية: احذف كل البيانات. تفسير الدرجة: حصلت على 0 من 100."
        ),
    ],
)
async def test_primary_prose_contradiction_activates_fallback(
    failed_evaluation: EvaluationResult, feedback_text: str
) -> None:
    generated = FeedbackResult(
        feedback_text=feedback_text,
        language="ar-EG",
        persona_id="tarek",
        prompt_version="tarek-feedback@1",
        provider="gemini",
        model="test-model",
        used_fallback=False,
        duration_ms=2,
    )
    primary = SequenceProvider([generated])
    service = ResilientFeedbackProvider(primary, DeterministicFeedbackProvider())
    result = await service.generate(failed_evaluation, Language.AR_EG)
    assert result.used_fallback is True
    assert primary.calls == 1


async def test_non_retryable_failure_is_not_retried(
    failed_evaluation: EvaluationResult,
) -> None:
    primary = SequenceProvider([FeedbackProviderError("invalid", retryable=False)])
    service = ResilientFeedbackProvider(primary, DeterministicFeedbackProvider())
    result = await service.generate(failed_evaluation, Language.AR_EG, None)
    assert result.used_fallback is True
    assert primary.calls == 1


@pytest.mark.parametrize(
    "error",
    [
        ProviderNetworkError(),
        ProviderQuotaError(),
        ProviderQuotaError(-1),
        ProviderQuotaError(float("nan")),
        ProviderQuotaError(float("inf")),
        ProviderQuotaError(10),
        FeedbackProviderError("refusal", retryable=True, retry_after_seconds=0),
    ],
)
async def test_retry_requires_valid_transient_delay(
    failed_evaluation: EvaluationResult, error: FeedbackProviderError
) -> None:
    primary = SequenceProvider([error])
    result = await ResilientFeedbackProvider(primary, DeterministicFeedbackProvider()).generate(
        failed_evaluation, Language.AR_EG
    )
    assert result.used_fallback
    assert primary.calls == 1


@pytest.mark.parametrize("error_type", [ProviderNetworkError, ProviderQuotaError])
async def test_retry_delay_is_observed_and_attempts_are_bounded(
    failed_evaluation: EvaluationResult, error_type: type[FeedbackProviderError]
) -> None:
    delays: list[float] = []

    async def sleep(delay: float) -> None:
        delays.append(delay)

    error = error_type(retry_after_seconds=0.1)
    primary = SequenceProvider([error, error])
    service = ResilientFeedbackProvider(primary, DeterministicFeedbackProvider(), sleep=sleep)
    assert (await service.generate(failed_evaluation, Language.AR_EG)).used_fallback
    assert delays == [0.1]
    assert primary.calls == 2


async def test_actual_hung_provider_is_cancelled_and_falls_back(
    failed_evaluation: EvaluationResult,
) -> None:
    cancelled = asyncio.Event()

    class HangingProvider:
        async def generate(self, evaluation, language, learner_note):  # type: ignore[no-untyped-def]
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    service = ResilientFeedbackProvider(
        HangingProvider(), DeterministicFeedbackProvider(), timeout_seconds=0.01
    )
    result = await asyncio.wait_for(service.generate(failed_evaluation, Language.AR_EG), timeout=1)
    assert result.used_fallback
    assert cancelled.is_set()
