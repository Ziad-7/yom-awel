import json
import os
from pathlib import Path
from urllib.parse import urlparse

import pytest

from yom_awel.transport.app import create_app
from yom_awel.transport.settings import Settings

ROOT = Path(__file__).resolve().parents[4]


SECRET = "s" * 48
FAKE_KEY = "fake-key-for-test"  # pragma: allowlist secret
CLOUD = {
    "APP_ENV": "cloud",
    "AUTH_SECRET": SECRET,
    "DATABASE_URL": "postgresql://app@db.invalid:6543/postgres",
    "CORS_ORIGINS": "https://web.test",
}


def test_openapi_is_current():
    expected = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
    assert create_app(Settings(secret=SECRET)).openapi() == expected


def test_cloud_settings_read_every_documented_variable():
    settings = Settings.from_env(
        CLOUD
        | {
            "GEMINI_API_KEY": FAKE_KEY,
            "GEMINI_MODEL": "gemini-3.5-flash-lite",
            "FEEDBACK_MODE": "auto",
        }
    )
    assert (settings.mode, settings.cors_origins) == ("cloud", ("https://web.test",))
    assert settings.uses_gemini and settings.secure_cookies
    assert settings.feedback.model == "gemini-3.5-flash-lite"
    for secret in (SECRET, CLOUD["DATABASE_URL"], FAKE_KEY):
        assert secret not in repr(settings)


def test_cloud_fixture_has_no_password_and_env_example_has_no_values():
    assert urlparse(CLOUD["DATABASE_URL"]).password is None
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, value = line.split("=", 1)
            assert name and not value


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"DATABASE_URL": ""}, "DATABASE_URL"),
        ({"DATABASE_URL": "mysql://x"}, "DATABASE_URL"),
        ({"AUTH_SECRET": "short"}, "AUTH_SECRET"),  # pragma: allowlist secret
        ({"AUTH_SECRET": ""}, "AUTH_SECRET"),
        ({"APP_ENV": "production"}, "APP_ENV"),
        ({"FEEDBACK_MODE": "gemini-only"}, "FEEDBACK_MODE"),
        ({"GEMINI_MODEL": "gemini-pro"}, "GEMINI_MODEL"),
        ({"CORS_ORIGINS": "http://web.test"}, "HTTPS"),
    ],
)
def test_cloud_settings_fail_closed(overrides, message):
    with pytest.raises(ValueError, match=message):
        Settings.from_env(CLOUD | overrides)


def test_fallback_mode_ignores_a_configured_key():
    settings = Settings.from_env(CLOUD | {"GEMINI_API_KEY": FAKE_KEY, "FEEDBACK_MODE": "fallback"})
    assert not settings.uses_gemini


def test_local_mode_creates_a_private_signing_key(tmp_path):
    key = tmp_path / "session.key"
    settings = Settings.from_env({"LOCAL_SECRET_PATH": str(key)})
    assert settings.secret == key.read_text(encoding="utf-8")
    if os.name != "nt":
        assert oct(key.stat().st_mode & 0o777) == "0o600"
    assert not settings.secure_cookies


@pytest.mark.parametrize(
    "origin", ["*", "https://*.test", "https://web.test/path", "https://web.test?token=x"]
)
def test_cors_rejects_non_origin_values(origin):
    with pytest.raises(ValueError):
        Settings(secret=SECRET, cors_origins=(origin,)).validate()


def test_local_mode_rejected_on_vercel():
    with pytest.raises(ValueError, match="local storage"):
        Settings.from_env({"VERCEL": "1", "APP_ENV": "local", "AUTH_SECRET": SECRET})


def test_deployment_has_separate_roots_and_bounded_function():
    web = json.loads((ROOT / "apps/web/vercel.json").read_text())
    api = json.loads((ROOT / "services/api/vercel.json").read_text())
    assert web["framework"] == "nextjs"
    assert api["framework"] == "fastapi"
    function = api["functions"]["api/index.py"]
    assert function["maxDuration"] <= 60
    assert "tests/**" in function["excludeFiles"]
    assert (ROOT / "services/api/.python-version").read_text(encoding="utf-8").strip() == ("3.12")
    assert "memory" not in function
    assert "crons" not in api


def test_task_packages_come_from_the_env_then_the_repository_then_the_wheel(monkeypatch, tmp_path):
    from yom_awel.transport import settings as module

    assert module.task_packages_dir({"TASK_PACKAGES_DIR": str(tmp_path)}) == tmp_path
    assert module.task_packages_dir({}) == ROOT / "task_packages"
    monkeypatch.setattr(module, "REPOSITORY_ROOT", tmp_path / "no-checkout")
    assert module.task_packages_dir({}) == module.BUNDLED_TASK_PACKAGES


def test_startup_refuses_an_empty_task_catalog(tmp_path):
    from yom_awel.transport.dependencies import compose

    with pytest.raises(ValueError, match="No published task package"):
        compose(
            Settings(secret=SECRET, task_packages=tmp_path, database_path=str(tmp_path / "x.db"))
        )


def test_cloud_composition_uses_database_url_without_local_storage(monkeypatch, tmp_path):
    from yom_awel.transport import dependencies

    selected = []
    factory = object()

    def postgres(dsn):
        selected.append(dsn)
        return factory

    monkeypatch.setattr(dependencies, "PostgresUnitOfWorkFactory", postgres)
    settings = Settings.from_env(CLOUD)
    assert dependencies._unit_of_work_factory(settings) is factory
    assert selected == [CLOUD["DATABASE_URL"]]
