from uuid import UUID

import pytest

from yom_awel.domain.contracts import EvaluationResult, TaskVersion
from yom_awel.domain.enums import Language
from yom_awel.feedback.config import FeedbackConfig, build_feedback_provider
from yom_awel.feedback.fallback import DeterministicFeedbackProvider
from yom_awel.feedback.service import ResilientFeedbackProvider


async def unused_resolver(task_id: UUID) -> TaskVersion | None:
    raise AssertionError("fallback must not resolve task context or call a model")


@pytest.mark.parametrize("mode", ["fallback", "gemini"])
async def test_configuration_without_key_is_zero_cost(
    mode: str, failed_evaluation: EvaluationResult
) -> None:
    provider = build_feedback_provider(
        FeedbackConfig(mode=mode),  # type: ignore[arg-type]
        task_context_resolver=unused_resolver,
    )
    result = await provider.generate(failed_evaluation, Language.AR_EG)
    assert result.provider == "deterministic"
    assert result.used_fallback


def test_config_selects_fake_and_gemini_without_application_changes() -> None:
    for config, fake in (
        (FeedbackConfig(mode="fake"), DeterministicFeedbackProvider()),
        (FeedbackConfig(mode="gemini", api_key="test-secret"), None),
    ):
        assert isinstance(
            build_feedback_provider(
                config, task_context_resolver=unused_resolver, fake_provider=fake
            ),
            ResilientFeedbackProvider,
        )
        assert "test-secret" not in repr(config)


def test_fake_mode_requires_explicit_injection() -> None:
    with pytest.raises(ValueError, match="injected fake"):
        build_feedback_provider(FeedbackConfig(mode="fake"), task_context_resolver=unused_resolver)
