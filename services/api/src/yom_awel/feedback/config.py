from dataclasses import dataclass, field
from typing import Literal

from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.gemini import AsyncGeminiClient, GeminiAdapter, TaskContextResolver
from yom_awel.feedback.service import ResilientFeedbackProvider
from yom_awel.ports.feedback import FeedbackProvider


@dataclass(frozen=True)
class FeedbackConfig:
    mode: Literal["fallback", "gemini", "fake"] = "fallback"
    api_key: str | None = field(default=None, repr=False)
    model: str = "gemini-2.5-flash"
    timeout_seconds: float = 10.0


def build_feedback_provider(
    config: FeedbackConfig,
    *,
    task_context_resolver: TaskContextResolver,
    fake_provider: FeedbackProvider | None = None,
    client: AsyncGeminiClient | None = None,
) -> FeedbackProvider:
    """Member 5 selects a mode without changing the shared port or application service."""
    fallback = DeterministicFeedbackProvider()
    if config.mode == "fallback":
        return fallback
    if config.mode == "fake":
        if fake_provider is None:
            raise ValueError("fake mode requires an injected fake provider")
        primary = fake_provider
    elif config.mode == "gemini":
        if not config.api_key:
            return fallback
        primary = GeminiAdapter(
            api_key=config.api_key,
            model=config.model,
            task_context_resolver=task_context_resolver,
            client=client,
            timeout_seconds=config.timeout_seconds,
        )
    else:
        raise ValueError("unknown feedback mode")
    return ResilientFeedbackProvider(primary, fallback, timeout_seconds=config.timeout_seconds)
