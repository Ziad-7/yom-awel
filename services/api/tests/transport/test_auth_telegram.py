from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from yom_awel.domain.errors import DomainError
from yom_awel.transport.app import create_app
from yom_awel.transport.auth import Authenticator
from yom_awel.transport.fakes import CLEAN_CSV, DIRTY_CSV
from yom_awel.transport.settings import Settings


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        {},
        {"iss": "https://evil.test"},
        {"aud": "wrong"},
        {"exp": 1},
        {"role": "service_role"},
        {"sub": "invalid"},
    ],
)
async def test_cloud_jwt_claims_and_signature(mutation):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    settings = Settings(
        mode="cloud", supabase_url="https://project.supabase.co", cors_origins=("https://web.test",)
    )
    auth = Authenticator(settings)
    auth.jwks = SimpleNamespace(
        get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key())
    )
    claims = {
        "sub": str(uuid4()),
        "iss": settings.supabase_url + "/auth/v1",
        "aud": "authenticated",
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        "role": "authenticated",
        "is_anonymous": True,
        **mutation,
    }
    token = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "key-1"})
    if mutation:
        with pytest.raises(DomainError):
            await auth.verify("Bearer " + token)
    else:
        assert (await auth.verify("Bearer " + token)).subject == claims["sub"]
        wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with pytest.raises(DomainError):
            await auth.verify(
                "Bearer "
                + jwt.encode(claims, wrong_key, algorithm="RS256", headers={"kid": "key-1"})
            )


@pytest.mark.asyncio
async def test_jwt_requires_kid_and_rejects_hs256_in_cloud():
    auth = Authenticator(Settings(mode="cloud", supabase_url="https://project.supabase.co"))
    with pytest.raises(DomainError):
        await auth.verify(
            "Bearer " + jwt.encode({"sub": str(uuid4())}, "s" * 48, algorithm="HS256")
        )


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


def test_telegram_fail_retry_pass_and_replay(tmp_path):
    app = create_app(
        Settings(
            secret="s" * 48, database_path=str(tmp_path / "app.db"), telegram_secret="test-secret"
        )
    )
    bot = FakeBot()
    app.state.telegram_client = bot
    headers = {"X-Telegram-Bot-Api-Secret-Token": "test-secret"}
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
        assert bot.files == [("sales-demo.csv", DIRTY_CSV)]
        failed = update(2, content=DIRTY_CSV)
        assert client.post(endpoint, headers=headers, json=failed).status_code == 200
        assert "محتاج تعديل" in bot.messages[-1]
        original = bot.messages[-1]
        assert client.post(endpoint, headers=headers, json=failed).status_code == 200
        assert bot.messages[-1] == original
        assert bot.downloads == 1
        bot.content = CLEAN_CSV
        passed = update(3, content=CLEAN_CSV)
        assert client.post(endpoint, headers=headers, json=passed).status_code == 200
        assert "التسليم مقبول" in bot.messages[-1]
        assert client.post(endpoint, headers=headers, json=passed).status_code == 200
        assert bot.downloads == 2
        assert client.post(endpoint, headers=headers, json=update(4, "/skills")).status_code == 200
        assert "100/100" in bot.messages[-1]


@pytest.mark.parametrize("body", [b"{", b"[]"])
def test_telegram_rejects_malformed_update_as_client_error(tmp_path, body):
    app = create_app(
        Settings(
            secret="s" * 48, database_path=str(tmp_path / "app.db"), telegram_secret="test-secret"
        )
    )
    headers = {
        "X-Telegram-Bot-Api-Secret-Token": "test-secret",
        "Content-Type": "application/json",
    }
    with TestClient(app) as client:
        response = client.post("/api/v1/telegram/webhook", headers=headers, content=body)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert response.json()["retryable"] is False


def test_rate_limit_and_error_redaction(tmp_path):
    settings = Settings(secret="s" * 48, database_path=str(tmp_path / "app.db"), rate_limit=2)
    with TestClient(create_app(settings)) as client:
        for _ in range(2):
            assert client.get("/api/v1/health").status_code == 200
        response = client.get("/api/v1/health")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
