from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient

from tests.transport.support import CLEAN_CSV, DIRTY_CSV, TEST_SECRET, settings_for
from yom_awel.domain.errors import DomainError
from yom_awel.transport.app import create_app
from yom_awel.transport.auth import AUDIENCE, ISSUER, Authenticator
from yom_awel.transport.settings import Settings

AUTH = Authenticator(Settings(secret=TEST_SECRET))


def token(**overrides):
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": ISSUER,
        "aud": AUDIENCE,
    } | overrides
    return jwt.encode(claims, TEST_SECRET, algorithm="HS256")


def test_issued_sessions_verify_as_web_identities():
    identity = AUTH.verify(AUTH.issue())
    assert identity.provider == "web"
    assert identity.subject


@pytest.mark.parametrize(
    "candidate",
    [
        None,
        "",
        "not-a-jwt",
        "x" * 5000,
        token(iss="https://evil.test"),
        token(aud="authenticated"),
        token(exp=datetime.now(UTC) - timedelta(seconds=1)),
        token(sub="not-a-uuid"),
        jwt.encode({"sub": str(uuid4()), "iss": ISSUER, "aud": AUDIENCE}, TEST_SECRET, "HS256"),
        jwt.encode(
            {"sub": str(uuid4()), "iss": ISSUER, "aud": AUDIENCE, "exp": 4102444800},
            "another-signing-key-" + "y" * 32,
            "HS256",
        ),
    ],
    ids=[
        "missing",
        "empty",
        "garbage",
        "oversized",
        "issuer",
        "audience",
        "expired",
        "subject",
        "no-expiry",
        "wrong-key",
    ],
)
def test_invalid_sessions_are_rejected(candidate):
    with pytest.raises(DomainError) as error:
        AUTH.verify(candidate)
    assert error.value.code == "unauthorized"


class FakeBot:
    def __init__(self):
        self.messages = []
        self.files = []
        self.downloads = 0
        self.content = DIRTY_CSV

    async def send(self, chat_id, text):
        self.messages.append(text)

    async def send_file(self, chat_id, filename, content):
        self.files.append((filename, content))

    async def download(self, file_id):
        self.downloads += 1
        return self.content


def update(update_id, text=None, content=None):
    message = {"from": {"id": 123, "first_name": "أحمد"}, "chat": {"id": 123, "type": "private"}}
    if text:
        message["text"] = text
    if content:
        message["document"] = {
            "file_name": "sales.csv",
            "file_id": "test",
            "file_unique_id": str(update_id),
            "file_size": len(content),
        }
    return {"update_id": update_id, "message": message}


def test_telegram_start_download_fail_pass_and_replay(tmp_path):
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}
    with TestClient(app) as client:
        endpoint = "/api/v1/telegram/webhook"
        assert client.post(endpoint, json=update(1, "/start")).status_code == 401
        assert (
            client.post(
                endpoint,
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
                json=update(1, "/start"),
            ).status_code
            == 401
        )
        assert not bot.messages
        assert client.post(endpoint, headers=headers, json=update(1, "/start")).status_code == 200
        assert "تكليف عملي" in bot.messages[-1]
        assert bot.files == [("sales_dirty.csv", DIRTY_CSV)]
        failed = update(2, content=DIRTY_CSV)
        assert client.post(endpoint, headers=headers, json=failed).status_code == 200
        assert "محتاج تعديل" in bot.messages[-1]
        for section in ("القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:"):
            assert section in bot.messages[-1]
        assert "0 من 100" in bot.messages[-1]
        original = bot.messages[-1]
        assert client.post(endpoint, headers=headers, json=failed).status_code == 200
        assert bot.messages[-1] == original
        assert bot.downloads == 1
        bot.content = CLEAN_CSV
        passed = update(3, content=CLEAN_CSV)
        assert client.post(endpoint, headers=headers, json=passed).status_code == 200
        assert "التسليم مقبول" in bot.messages[-1]
        assert "100 من 100" in bot.messages[-1]
        assert client.post(endpoint, headers=headers, json=passed).status_code == 200
        assert bot.downloads == 2
        assert client.post(endpoint, headers=headers, json=update(4, "/skills")).status_code == 200
        assert "100/100" in bot.messages[-1]


@pytest.mark.parametrize("body", [b"{", b"[]"])
def test_telegram_rejects_malformed_update_as_client_error(tmp_path, body):
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    headers = {
        "X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret",
        "Content-Type": "application/json",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/telegram/webhook", headers=headers, content=body)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert response.json()["retryable"] is False


def test_rate_limit_and_error_redaction(tmp_path):
    settings = settings_for(tmp_path, rate_limit=2)
    with TestClient(create_app(settings)) as client:
        for _ in range(2):
            assert client.get("/api/v1/health").status_code == 200
        response = client.get("/api/v1/health")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
