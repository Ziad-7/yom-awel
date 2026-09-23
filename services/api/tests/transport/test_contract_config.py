import json
from pathlib import Path

import pytest

from yom_awel.transport.app import create_app
from yom_awel.transport.settings import Settings

ROOT = Path(__file__).resolve().parents[4]


def test_openapi_is_current():
    expected = json.loads((ROOT / "contracts/openapi.json").read_text(encoding="utf-8"))
    assert create_app(Settings(secret="s" * 48)).openapi() == expected


def test_demo_fixtures_match_canonical_contracts():
    for fixture in (ROOT / "services/api/src/yom_awel/transport/demo_data").glob("*.json"):
        assert json.loads(fixture.read_text(encoding="utf-8")) == json.loads(
            (ROOT / "contracts/fixtures" / fixture.name).read_text(encoding="utf-8")
        )


@pytest.mark.parametrize(
    "origin", ["*", "https://*.test", "https://web.test/path", "https://web.test?token=x"]
)
def test_cors_rejects_non_origin_values(origin):
    with pytest.raises(ValueError):
        Settings(secret="s" * 48, cors_origins=(origin,)).validate()


def test_local_mode_rejected_on_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("APP_ENV", "local")
    with pytest.raises(ValueError, match="local storage"):
        Settings.from_env()


def test_deployment_has_separate_roots_and_bounded_function():
    web = json.loads((ROOT / "apps/web/vercel.json").read_text())
    api = json.loads((ROOT / "services/api/vercel.json").read_text())
    assert web["framework"] == "nextjs"
    assert api["framework"] == "fastapi"
    function = api["functions"]["api/index.py"]
    assert function["maxDuration"] <= 60
    assert "tests/**" in function["excludeFiles"]
    assert "memory" not in function
    assert "crons" not in api
