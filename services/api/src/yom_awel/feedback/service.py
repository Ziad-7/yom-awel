import asyncio
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult
from yom_awel.domain.enums import Language
from yom_awel.feedback.errors import FeedbackProviderError, ProviderTimeoutError
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.ports.feedback import FeedbackProvider

_Sleep = Callable[[float], Awaitable[None]]
_Clock = Callable[[], float]
_CorrelationIdFactory = Callable[[], str]


class ResilientFeedbackProvider(FeedbackProvider):
    def __init__(
        self,
        primary: FeedbackProvider | None,
        fallback: DeterministicFeedbackProvider,
        *,
        timeout_seconds: float = 10.0,
        sleep: _Sleep = asyncio.sleep,
        clock: _Clock = perf_counter,
        correlation_id_factory: _CorrelationIdFactory = lambda: str(uuid4()),
        logger: logging.Logger | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._timeout_seconds = min(timeout_seconds, 10.0)
        self._sleep = sleep
        self._clock = clock
        self._correlation_id_factory = correlation_id_factory
        self._logger = logger or logging.getLogger(__name__)

    async def generate(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None = None,
    ) -> FeedbackResult:
        started = self._clock()
        correlation_id = self._correlation_id_factory()
        if self._primary is None:
            return await self._use_fallback(
                evaluation,
                language,
                learner_note,
                started,
                "missing_credentials",
                correlation_id,
            )
        try:
            async with asyncio.timeout(self._timeout_seconds):
                return await self._generate_with_retry(
                    evaluation, language, learner_note, started
                )
        except TimeoutError:
            error: Exception = ProviderTimeoutError()
        except Exception as caught:  # noqa: BLE001 - every provider failure must fall back
            error = caught
        code = error.code if isinstance(error, FeedbackProviderError) else "unexpected"
        return await self._use_fallback(
            evaluation, language, learner_note, started, code, correlation_id
        )

    async def _generate_with_retry(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None,
        started: float,
    ) -> FeedbackResult:
        assert self._primary is not None
        try:
            return await self._primary.generate(evaluation, language, learner_note)
        except FeedbackProviderError as error:
            elapsed = self._clock() - started
            if error.code == "quota" and error.retry_after_seconds is None:
                raise
            delay = error.retry_after_seconds or 0.0
            if not error.retryable or elapsed + delay >= self._timeout_seconds:
                raise
            if delay:
                await self._sleep(delay)
            return await self._primary.generate(evaluation, language, learner_note)

    async def _use_fallback(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None,
        started: float,
        error_code: str,
        correlation_id: str,
    ) -> FeedbackResult:
        result = await self._fallback.generate(evaluation, language, learner_note)
        self._logger.info(
            "feedback_provider_fallback",
            extra={
                "provider_error_code": error_code,
                "correlation_id": correlation_id,
                "duration_ms": max(0, round((self._clock() - started) * 1000)),
                "used_fallback": True,
            },
        )
        return result
