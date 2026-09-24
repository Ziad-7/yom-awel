import logging
from uuid import UUID

import pytest

from yom_awel.domain.contracts import EvaluationResult, TaskVersion
from yom_awel.domain.enums import Language
from yom_awel.feedback.config import FeedbackConfig, FeedbackConfigError, build_feedback_provider
from yom_awel.feedback.fallback import DeterministicFeedbackProvider


async def unused_resolver(task_id: UUID) -> TaskVersion | None:
    raise AssertionError("fallback must not resolve task context or call a model")


FAKE_KEY = "fake-gemini-key-for-tests-only"


@pytest.mark.parametrize(
    ("environ", "mode", "api_key", "model"),
    [
        ({}, "fallback", None, "gemini-2.5-flash"),
        ({"GEMINI_API_KEY": "  "}, "fallback", None, "gemini-2.5-flash"),
        ({"GEMINI_API_KEY": FAKE_KEY}, "gemini", FAKE_KEY, "gemini-2.5-flash"),
        ({"GEMINI_API_KEY": FAKE_KEY, "FEEDBACK_MODE": "auto"}, "gemini", FAKE_KEY, None),
        ({"GEMINI_API_KEY": FAKE_KEY, "FEEDBACK_MODE": " AUTO "}, "gemini", FAKE_KEY, None),
        ({"GEMINI_API_KEY": FAKE_KEY, "FEEDBACK_MODE": "fallback"}, "fallback", None, None),
        ({"FEEDBACK_MODE": ""}, "fallback", None, None),
        ({"GEMINI_MODEL": "gemini-2.5-flash-lite"}, "fallback", None, "gemini-2.5-flash-lite"),
        (
            {"GEMINI_API_KEY": FAKE_KEY, "GEMINI_MODEL": "gemini-2.5-flash-lite"},
            "gemini",
            FAKE_KEY,
            "gemini-2.5-flash-lite",
        ),
        ({"GEMINI_MODEL": " "}, "fallback", None, "gemini-2.5-flash"),
    ],
)
def test_from_env_selects_mode_key_and_model(
    environ: dict[str, str], mode: str, api_key: str | None, model: str | None
) -> None:
    config = FeedbackConfig.from_env(environ)
    assert config.mode == mode
    assert config.api_key == api_key
    assert config.model == (model or "gemini-2.5-flash")


@pytest.mark.parametrize(
    ("environ", "variable"),
    [
        ({"GEMINI_MODEL": "gemini-2.5-pro"}, "GEMINI_MODEL"),
        ({"GEMINI_MODEL": FAKE_KEY, "GEMINI_API_KEY": FAKE_KEY}, "GEMINI_MODEL"),
        ({"FEEDBACK_MODE": "gemini"}, "FEEDBACK_MODE"),
        ({"FEEDBACK_MODE": FAKE_KEY, "GEMINI_API_KEY": FAKE_KEY}, "FEEDBACK_MODE"),
    ],
)
def test_from_env_rejects_invalid_settings_without_echoing_values(
    environ: dict[str, str], variable: str
) -> None:
    with pytest.raises(FeedbackConfigError) as error:
        FeedbackConfig.from_env(environ)
    assert variable in str(error.value)
    assert FAKE_KEY not in str(error.value)
    assert FAKE_KEY not in repr(error.value)


def test_direct_construction_also_rejects_unapproved_models() -> None:
    with pytest.raises(FeedbackConfigError, match="GEMINI_MODEL"):
        FeedbackConfig(mode="gemini", api_key=FAKE_KEY, model="gemini-1.0-pro")


def test_key_never_appears_in_repr_or_str() -> None:
    config = FeedbackConfig.from_env({"GEMINI_API_KEY": FAKE_KEY})
    assert config.api_key == FAKE_KEY
    for rendered in (repr(config), str(config), f"{config}", f"{config!r}"):
        assert FAKE_KEY not in rendered


def test_integrator_call_builds_fallback_without_key() -> None:
    provider = build_feedback_provider(
        FeedbackConfig.from_env({"FEEDBACK_MODE": "auto"}), task_context_resolver=unused_resolver
    )
    assert isinstance(provider, DeterministicFeedbackProvider)


class LeakyFailingClient:
    """Stands in for the SDK raising an error whose text includes the key."""

    calls = 0

    async def generate_json(self, *, model: str, prompt: str, timeout_seconds: float) -> str:
        del model, timeout_seconds
        self.calls += 1
        assert FAKE_KEY not in prompt
        raise RuntimeError(f"API key {FAKE_KEY} rejected")


async def test_key_never_reaches_logs_on_provider_failure(
    task: TaskVersion, failed_evaluation: EvaluationResult, caplog: pytest.LogCaptureFixture
) -> None:
    async def resolve(task_version_id: UUID) -> TaskVersion:
        del task_version_id
        return task

    client = LeakyFailingClient()
    with caplog.at_level(logging.DEBUG):
        config = FeedbackConfig.from_env({"GEMINI_API_KEY": FAKE_KEY})
        provider = build_feedback_provider(config, task_context_resolver=resolve, client=client)
        result = await provider.generate(failed_evaluation, Language.EN)
    assert client.calls == 1
    assert result.used_fallback
    assert caplog.records
    for record in caplog.records:
        assert FAKE_KEY not in record.getMessage()
        assert FAKE_KEY not in str(record.__dict__)
    assert FAKE_KEY not in caplog.text
