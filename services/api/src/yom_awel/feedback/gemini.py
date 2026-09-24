import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter
from typing import Any, Protocol
from uuid import UUID

from yom_awel.domain.contracts import EvaluationResult, FeedbackResult, TaskVersion
from yom_awel.domain.enums import Language
from yom_awel.feedback.errors import (
    FeedbackProviderError,
    MissingCredentialsError,
    ProviderNetworkError,
    ProviderQuotaError,
    ProviderRefusalError,
    ProviderResponseError,
    ProviderTimeoutError,
)
from yom_awel.feedback.parser import ProviderPayload, parse_provider_response
from yom_awel.feedback.prompt import build_provider_request
from yom_awel.ports.feedback import FeedbackProvider


class AsyncGeminiClient(Protocol):
    async def generate_json(self, *, model: str, prompt: str, timeout_seconds: float) -> str: ...


TaskContextResolver = Callable[[UUID], Awaitable[TaskVersion | None]]
FREE_TIER_MODELS = frozenset({"gemini-2.5-flash", "gemini-2.5-flash-lite"})


class GoogleGenAIClient:
    """Small lazy SDK wrapper; importing this module never requires a configured key."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._client: Any | None = None

    async def generate_json(self, *, model: str, prompt: str, timeout_seconds: float) -> str:
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self._api_key)
        async with asyncio.timeout(timeout_seconds):
            response = await self._client.aio.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_json_schema": ProviderPayload.model_json_schema(),
                },
            )
        text = getattr(response, "text", None)
        if not text:
            raise ProviderRefusalError()
        return str(text)


class GeminiAdapter(FeedbackProvider):
    def __init__(
        self,
        *,
        api_key: str | None,
        model: str,
        task_context_resolver: TaskContextResolver,
        client: AsyncGeminiClient | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        if model not in FREE_TIER_MODELS:
            raise ValueError("Gemini model must be an approved free-tier model")
        self._api_key = api_key
        self._model = model
        self._task_context_resolver = task_context_resolver
        self._client = client
        self._timeout_seconds = min(timeout_seconds, 10.0)

    async def generate(
        self,
        evaluation: EvaluationResult,
        language: Language,
        learner_note: str | None = None,
    ) -> FeedbackResult:
        if self._client is None:
            if not self._api_key:
                raise MissingCredentialsError()
            self._client = GoogleGenAIClient(self._api_key)
        task = await self._task_context_resolver(evaluation.task_version_id)
        if task is None:
            raise ProviderResponseError("task_context_missing")
        request = build_provider_request(task, evaluation, learner_note, language)
        started = perf_counter()
        try:
            async with asyncio.timeout(self._timeout_seconds):
                payload = await self._client.generate_json(
                    model=self._model,
                    prompt=request.serialized(),
                    timeout_seconds=self._timeout_seconds,
                )
        except FeedbackProviderError:
            raise
        except TimeoutError as exc:
            raise ProviderTimeoutError() from exc
        except Exception as exc:
            raise _map_sdk_error(exc) from exc
        duration_ms = round((perf_counter() - started) * 1000)
        return parse_provider_response(
            payload,
            evaluation,
            provider="gemini",
            model=self._model,
            duration_ms=duration_ms,
            language=language,
        )


def _map_sdk_error(error: Exception) -> FeedbackProviderError:
    description = f"{type(error).__name__} {error}".lower()
    if "quota" in description or "rate" in description or "429" in description:
        return ProviderQuotaError()
    if "refusal" in description or "safety" in description or "blocked" in description:
        return ProviderRefusalError()
    if "timeout" in description:
        return ProviderTimeoutError()
    return ProviderNetworkError()
