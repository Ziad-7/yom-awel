from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal, Self

from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.gemini import (
    FREE_TIER_MODELS,
    AsyncGeminiClient,
    GeminiAdapter,
    TaskContextResolver,
)
from yom_awel.feedback.service import ResilientFeedbackProvider
from yom_awel.feedback.timeouts import validate_timeout_seconds
from yom_awel.ports.feedback import FeedbackProvider

DEFAULT_MODEL = "gemini-2.5-flash"


class FeedbackConfigError(ValueError):
    """Invalid feedback settings. Messages name the variable, never its value."""


@dataclass(frozen=True)
class FeedbackConfig:
    mode: Literal["fallback", "gemini", "fake"] = "fallback"
    api_key: str | None = field(default=None, repr=False)
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.model not in FREE_TIER_MODELS:
            raise FeedbackConfigError(
                f"GEMINI_MODEL must be one of: {', '.join(sorted(FREE_TIER_MODELS))}"
            )
        object.__setattr__(self, "timeout_seconds", validate_timeout_seconds(self.timeout_seconds))

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> Self:
        """FEEDBACK_MODE=auto uses Gemini only when GEMINI_API_KEY is set; fallback never does."""
        api_key = environ.get("GEMINI_API_KEY", "").strip() or None
        model = environ.get("GEMINI_MODEL", "").strip() or DEFAULT_MODEL
        feedback_mode = environ.get("FEEDBACK_MODE", "").strip().lower() or "auto"
        if feedback_mode not in {"auto", "fallback"}:
            raise FeedbackConfigError("FEEDBACK_MODE must be auto or fallback")
        if feedback_mode == "auto" and api_key is not None:
            return cls(mode="gemini", api_key=api_key, model=model)
        return cls(mode="fallback", model=model)


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
