import asyncio
from uuid import UUID

import pytest

from yom_awel.domain.contracts import EvaluationResult, TaskVersion
from yom_awel.domain.enums import Language
from yom_awel.feedback.config import FeedbackConfig, build_feedback_provider
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.gemini import GeminiAdapter
from yom_awel.feedback.service import ResilientFeedbackProvider


async def unused_resolver(task_id: UUID) -> TaskVersion | None:
    raise AssertionError("construction must not resolve task context")


@pytest.mark.parametrize("timeout", [float("nan"), float("inf"), -float("inf"), 0, -0.0, -1])
@pytest.mark.parametrize("boundary", ["config", "adapter", "service"])
def test_public_construction_rejects_invalid_timeouts(timeout: float, boundary: str) -> None:
    with pytest.raises(ValueError, match="finite positive"):
        if boundary == "config":
            FeedbackConfig(timeout_seconds=timeout)
        elif boundary == "adapter":
            GeminiAdapter(
                api_key=None,
                model="gemini-2.5-flash",
                task_context_resolver=unused_resolver,
                timeout_seconds=timeout,
            )
        else:
            ResilientFeedbackProvider(
                None, DeterministicFeedbackProvider(), timeout_seconds=timeout
            )


@pytest.mark.parametrize("timeout, expected", [(0.01, 0.01), (10, 10), (11, 10), (1e100, 10)])
def test_all_boundaries_preserve_positive_timeout_and_cap_budget(
    timeout: float, expected: float
) -> None:
    config = FeedbackConfig(timeout_seconds=timeout)
    adapter = GeminiAdapter(
        api_key=None,
        model="gemini-2.5-flash",
        task_context_resolver=unused_resolver,
        timeout_seconds=timeout,
    )
    service = ResilientFeedbackProvider(
        None, DeterministicFeedbackProvider(), timeout_seconds=timeout
    )
    assert config.timeout_seconds == expected
    assert adapter._timeout_seconds == expected
    assert service._timeout_seconds == expected


async def test_small_budget_cancels_real_hanging_gemini_call_and_returns_fallback(
    task: TaskVersion, failed_evaluation: EvaluationResult
) -> None:
    cancelled = asyncio.Event()

    async def resolve_task(task_id: UUID) -> TaskVersion:
        assert task_id == task.task_version_id
        return task

    class HangingClient:
        async def generate_json(self, *, model: str, prompt: str, timeout_seconds: float) -> str:
            assert timeout_seconds == 0.01
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
            raise AssertionError("unreachable")

    provider = build_feedback_provider(
        FeedbackConfig(mode="gemini", api_key="test-only", timeout_seconds=0.01),
        task_context_resolver=resolve_task,
        client=HangingClient(),
    )
    result = await asyncio.wait_for(provider.generate(failed_evaluation, Language.AR_EG), timeout=1)
    assert cancelled.is_set()
    assert result.used_fallback
    assert result.provider == "deterministic"
    assert result.feedback_text == DeterministicFeedbackProvider.render_text(
        failed_evaluation, Language.AR_EG
    )
