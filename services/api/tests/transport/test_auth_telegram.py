from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from tests.transport.support import CLEAN_CSV, CLEAN_XLSX, DIRTY_CSV, TEST_SECRET, settings_for
from yom_awel.domain.errors import DomainError
from yom_awel.transport.app import create_app
from yom_awel.transport.auth import AUDIENCE, ISSUER, Authenticator
from yom_awel.transport.settings import Settings
from yom_awel.transport.telegram import TelegramClient

AUTH = Authenticator(Settings(secret=TEST_SECRET))
REPO_ROOT = Path(__file__).resolve().parents[4]

PASSING_SQL = (
    b"SELECT region, COUNT(*) AS paid_orders, "
    b"ROUND(SUM(quantity * unit_price), 2) AS total_revenue "
    b"FROM sales WHERE status = 'paid' GROUP BY region ORDER BY region;"
)
FAILING_SQL = b"SELECT 1;"

PASSING_EMAIL = (
    REPO_ROOT / "task_packages" / "client-email" / "1" / "examples" / "pass.en.txt"
).read_bytes()
FAILING_EMAIL = b"Hello"

HEADERS = {"X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret"}
ENDPOINT = "/api/v1/telegram/webhook"


def token(**overrides: Any) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "iss": ISSUER,
        "aud": AUDIENCE,
    } | overrides
    return jwt.encode(claims, TEST_SECRET, algorithm="HS256")


def test_issued_sessions_verify_as_web_identities() -> None:
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
def test_invalid_sessions_are_rejected(candidate: str | None) -> None:
    with pytest.raises(DomainError) as error:
        AUTH.verify(candidate)
    assert error.value.code == "unauthorized"


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.files: list[tuple[str, bytes]] = []
        self.downloads = 0
        self.files_by_id: dict[str, bytes] = {}
        self.fail_download = False
        self.fail_send = False
        self.fail_send_once = False

    async def send(self, chat_id: int, text: str) -> None:
        if self.fail_send:
            raise DomainError("unavailable", "Telegram delivery unavailable")
        if self.fail_send_once:
            self.fail_send_once = False
            raise DomainError("unavailable", "Telegram delivery unavailable")
        self.messages.append(text)

    async def send_file(self, chat_id: int, filename: str, content: bytes) -> None:
        if self.fail_send:
            raise DomainError("unavailable", "Telegram delivery unavailable")
        self.files.append((filename, content))

    async def download(self, file_id: str) -> bytes:
        if self.fail_download:
            raise DomainError("unavailable", "Telegram file unavailable")
        self.downloads += 1
        if file_id in self.files_by_id:
            return self.files_by_id[file_id]
        raise DomainError("unavailable", "Telegram file unavailable")


def update(
    update_id: int | None = 1,
    text: str | None = None,
    content: bytes | None = None,
    filename: str = "sales.csv",
    file_id: str | None = None,
    file_unique_id: str | None = None,
    chat_type: str = "private",
    user_id: int = 123,
    chat_id: int = 123,
    mime_type: str | None = None,
    document_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    msg: dict[str, Any] = {
        "from": {"id": user_id, "first_name": "أحمد"},
        "chat": {"id": chat_id, "type": chat_type},
    }
    if text is not None:
        msg["text"] = text
    if document_override is not None:
        msg["document"] = document_override
    elif content is not None:
        doc: dict[str, Any] = {
            "file_name": filename,
            "file_id": file_id or f"fid_{update_id}",
            "file_unique_id": file_unique_id or f"fuid_{update_id}",
            "file_size": len(content),
        }
        if mime_type:
            doc["mime_type"] = mime_type
        msg["document"] = doc
    res: dict[str, Any] = {"message": msg}
    if update_id is not None:
        res["update_id"] = update_id
    return res


def test_telegram_webhook_secret_authentication(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        assert client.post(ENDPOINT, json=update(1, "/start")).status_code == 401
        assert (
            client.post(
                ENDPOINT,
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
                json=update(1, "/start"),
            ).status_code
            == 401
        )
        assert not bot.messages
        response = client.post(ENDPOINT, headers=HEADERS, json=update(1, "/start"))
        assert response.status_code == 200
        assert bot.messages


@pytest.mark.parametrize("body", [b"{", b"[]"])
def test_telegram_rejects_malformed_update_as_client_error(tmp_path: Path, body: bytes) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    headers = {
        "X-Telegram-Bot-Api-Secret-Token": "test-webhook-secret",
        "Content-Type": "application/json",
    }
    with TestClient(app) as client:
        response = client.post(ENDPOINT, headers=headers, content=body)
    assert response.status_code == 400
    assert response.json()["code"] == "invalid_request"
    assert response.json()["retryable"] is False


def test_telegram_rejects_missing_or_non_integer_update_id(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        res1 = client.post(ENDPOINT, headers=HEADERS, json={"message": {"text": "/start"}})
        assert res1.status_code == 400
        assert res1.json()["code"] == "invalid_request"

        res2 = client.post(
            ENDPOINT,
            headers=HEADERS,
            json={"update_id": "not-an-int", "message": {"text": "/start"}},
        )
        assert res2.status_code == 400
        assert res2.json()["code"] == "invalid_request"


def test_telegram_ignores_group_chats_and_mismatched_senders(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        group_up = update(1, "/start", chat_type="group", user_id=123, chat_id=-100123)
        res = client.post(ENDPOINT, headers=HEADERS, json=group_up)
        assert res.status_code == 200
        assert res.json() == {"ok": True}
        assert not bot.messages
        assert not bot.files

        mismatched_up = update(2, "/start", chat_type="private", user_id=123, chat_id=456)
        res2 = client.post(ENDPOINT, headers=HEADERS, json=mismatched_up)
        assert res2.status_code == 200
        assert not bot.messages


def test_telegram_flow_clean_sales_complete(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        # 1. /start delivers clean-sales brief and dirty csv
        res = client.post(ENDPOINT, headers=HEADERS, json=update(1, "/start"))
        assert res.status_code == 200
        assert "تكليف عملي" in bot.messages[-1]
        assert bot.files == [("sales_dirty.csv", DIRTY_CSV)]

        # 2. Invalid upload (unsupported extension)
        bad_ext = update(2, content=b"print('hello')", filename="script.py")
        client.post(ENDPOINT, headers=HEADERS, json=bad_ext)
        assert "صيغة الملف لا تطابق المهمة الحالية." in bot.messages[-1]

        # 3. Invalid CSV content (binary content)
        bad_csv = update(3, content=b"MZ\x00corrupt", filename="sales.csv")
        bot.files_by_id["fid_3"] = b"MZ\x00corrupt"
        client.post(ENDPOINT, headers=HEADERS, json=bad_csv)
        assert "محتوى الملف أو نوعه غير صالح" in bot.messages[-1]

        # 4. Failing CSV upload (DIRTY_CSV)
        failed = update(4, content=DIRTY_CSV, filename="sales.csv")
        bot.files_by_id["fid_4"] = DIRTY_CSV
        res_fail = client.post(ENDPOINT, headers=HEADERS, json=failed)
        assert res_fail.status_code == 200
        assert "محتاج تعديل وإعادة تسليم" in bot.messages[-1]
        assert "0/100" in bot.messages[-1]
        assert "إرشادات بديلة" in bot.messages[-1]
        for section in ("القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:"):
            assert section in bot.messages[-1]

        # 5. Replay of same failing update does not increment download count or duplicate attempt
        fail_msg = bot.messages[-1]
        downloads_before = bot.downloads
        client.post(ENDPOINT, headers=HEADERS, json=failed)
        assert bot.messages[-1] == fail_msg
        assert bot.downloads == downloads_before

        # 6. Passing CSV upload (CLEAN_CSV)
        passed_csv = update(5, content=CLEAN_CSV, filename="sales.csv")
        bot.files_by_id["fid_5"] = CLEAN_CSV
        res_pass = client.post(ENDPOINT, headers=HEADERS, json=passed_csv)
        assert res_pass.status_code == 200
        assert "التسليم مقبول" in bot.messages[-1]
        assert "100/100" in bot.messages[-1]
        assert "إرشادات بديلة" in bot.messages[-1]

        # 7. Submitting again to an already completed task warns learner
        passed_xlsx = update(
            6,
            content=CLEAN_XLSX,
            filename="sales.xlsx",
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        bot.files_by_id["fid_6"] = CLEAN_XLSX
        res_xlsx = client.post(ENDPOINT, headers=HEADERS, json=passed_xlsx)
        assert res_xlsx.status_code == 200
        assert "المهمة مكتملة بالفعل" in bot.messages[-1]

        # 8. /skills reflects data_cleaning skill
        client.post(ENDPOINT, headers=HEADERS, json=update(7, "/skills"))
        assert "data_cleaning: 100/100" in bot.messages[-1]

        # 9. Fresh learner submitting XLSX directly passes
        res_fresh = client.post(
            ENDPOINT, headers=HEADERS, json=update(10, "/start", user_id=456, chat_id=456)
        )
        assert res_fresh.status_code == 200
        up_xlsx = update(
            11,
            content=CLEAN_XLSX,
            filename="sales.xlsx",
            file_id="fid_11",
            user_id=456,
            chat_id=456,
            mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        bot.files_by_id["fid_11"] = CLEAN_XLSX
        res_xlsx_fresh = client.post(ENDPOINT, headers=HEADERS, json=up_xlsx)
        assert res_xlsx_fresh.status_code == 200
        assert "التسليم مقبول" in bot.messages[-1]
        assert "100/100" in bot.messages[-1]


def test_telegram_flow_sql_report_complete(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        # 1. /tasks lists tasks
        client.post(ENDPOINT, headers=HEADERS, json=update(1, "/tasks"))
        assert "/task sql-report" in bot.messages[-1]
        assert "تقرير المبيعات" in bot.messages[-1]
        assert "SQL" in bot.messages[-1]

        # 2. /task sql-report switches and delivers source file
        client.post(ENDPOINT, headers=HEADERS, json=update(2, "/task sql-report"))
        assert "تقرير المبيعات" in bot.messages[-1]
        assert bot.files[-1][0] == "sql_report_source.csv"

        # 3. Invalid upload: uploading CSV while in SQL task
        mismatch = update(3, content=CLEAN_CSV, filename="sales.csv")
        client.post(ENDPOINT, headers=HEADERS, json=mismatch)
        assert "صيغة الملف لا تطابق المهمة الحالية." in bot.messages[-1]

        # 4. Failing SQL upload
        failed = update(4, content=FAILING_SQL, filename="query.sql", mime_type="text/plain")
        bot.files_by_id["fid_4"] = FAILING_SQL
        client.post(ENDPOINT, headers=HEADERS, json=failed)
        assert "محتاج تعديل وإعادة تسليم" in bot.messages[-1]
        assert "إرشادات بديلة" in bot.messages[-1]

        # 5. Passing SQL upload
        passed = update(5, content=PASSING_SQL, filename="query.sql", mime_type="text/plain")
        bot.files_by_id["fid_5"] = PASSING_SQL
        client.post(ENDPOINT, headers=HEADERS, json=passed)
        assert "التسليم مقبول" in bot.messages[-1]
        assert "100/100" in bot.messages[-1]
        assert "إرشادات بديلة" in bot.messages[-1]

        # 6. Replay passing update
        pass_msg = bot.messages[-1]
        downloads_before = bot.downloads
        client.post(ENDPOINT, headers=HEADERS, json=passed)
        assert bot.messages[-1] == pass_msg
        assert bot.downloads == downloads_before

        # 7. /skills reports sql_reporting
        client.post(ENDPOINT, headers=HEADERS, json=update(6, "/skills"))
        assert "sql_reporting: 100/100" in bot.messages[-1]


def test_telegram_flow_client_email_complete(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        # 1. Switch to client-email
        client.post(ENDPOINT, headers=HEADERS, json=update(1, "/task client-email"))
        assert "اكتب رسالة لتحديث العميل" in bot.messages[-1]
        assert bot.files[-1][0] == "client_email_source.csv"

        # 2. Invalid upload: uploading SQL while in client-email task
        mismatch = update(2, content=PASSING_SQL, filename="query.sql", mime_type="text/plain")
        client.post(ENDPOINT, headers=HEADERS, json=mismatch)
        assert "صيغة الملف لا تطابق المهمة الحالية." in bot.messages[-1]

        # 3. Failing TXT upload
        failed = update(3, content=FAILING_EMAIL, filename="reply.txt", mime_type="text/plain")
        bot.files_by_id["fid_3"] = FAILING_EMAIL
        client.post(ENDPOINT, headers=HEADERS, json=failed)
        assert "محتاج تعديل وإعادة تسليم" in bot.messages[-1]
        assert "إرشادات بديلة" in bot.messages[-1]

        # 4. Passing TXT upload
        passed = update(4, content=PASSING_EMAIL, filename="reply.txt", mime_type="text/plain")
        bot.files_by_id["fid_4"] = PASSING_EMAIL
        client.post(ENDPOINT, headers=HEADERS, json=passed)
        assert "التسليم مقبول" in bot.messages[-1]
        assert "إرشادات بديلة" in bot.messages[-1]

        # 5. Replay passing update
        pass_msg = bot.messages[-1]
        downloads_before = bot.downloads
        client.post(ENDPOINT, headers=HEADERS, json=passed)
        assert bot.messages[-1] == pass_msg
        assert bot.downloads == downloads_before

        # 6. /skills reports customer_communication
        client.post(ENDPOINT, headers=HEADERS, json=update(5, "/skills"))
        assert "customer_communication:" in bot.messages[-1]


def test_telegram_file_size_boundary(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        client.post(ENDPOINT, headers=HEADERS, json=update(1, "/start"))

        # Too large declared in Telegram document metadata
        oversized_doc = {
            "file_name": "sales.csv",
            "file_id": "fid_big",
            "file_unique_id": "fuid_big",
            "file_size": 5 * 1024 * 1024 + 1,
        }
        client.post(ENDPOINT, headers=HEADERS, json=update(2, document_override=oversized_doc))
        assert "أقل من أو يساوي 5 ميجابايت" in bot.messages[-1]

        # Zero or negative declared size
        zero_doc = {
            "file_name": "sales.csv",
            "file_id": "fid_zero",
            "file_unique_id": "fuid_zero",
            "file_size": 0,
        }
        client.post(ENDPOINT, headers=HEADERS, json=update(3, document_override=zero_doc))
        assert "أقل من أو يساوي 5 ميجابايت" in bot.messages[-1]


def test_telegram_malformed_file_metadata(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        client.post(ENDPOINT, headers=HEADERS, json=update(1, "/start"))

        # Missing file_id
        doc_no_fid = {
            "file_name": "sales.csv",
            "file_id": "",
            "file_unique_id": "fuid",
            "file_size": 100,
        }
        client.post(ENDPOINT, headers=HEADERS, json=update(2, document_override=doc_no_fid))
        assert "بيانات الملف" in bot.messages[-1] or "غير صالح" in bot.messages[-1]

        # Missing file_unique_id
        doc_no_fuid = {
            "file_name": "sales.csv",
            "file_id": "fid",
            "file_unique_id": "",
            "file_size": 100,
        }
        client.post(ENDPOINT, headers=HEADERS, json=update(3, document_override=doc_no_fuid))
        assert "بيانات الملف" in bot.messages[-1] or "غير صالح" in bot.messages[-1]

        # Path traversal in file_name
        doc_traversal = {
            "file_name": "../../sales.csv",
            "file_id": "fid_trav",
            "file_unique_id": "fuid_trav",
            "file_size": 100,
        }
        client.post(ENDPOINT, headers=HEADERS, json=update(4, document_override=doc_traversal))
        assert "صيغة الملف لا تطابق المهمة الحالية." in bot.messages[-1]


def test_telegram_download_failure(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    bot.fail_download = True
    app.state.telegram_client = bot
    with TestClient(app) as client:
        client.post(ENDPOINT, headers=HEADERS, json=update(1, "/start"))
        up = update(2, content=CLEAN_CSV, filename="sales.csv")
        bot.files_by_id["fid_2"] = CLEAN_CSV
        response = client.post(ENDPOINT, headers=HEADERS, json=up)
        assert response.status_code == 503
        assert response.json()["code"] == "unavailable"


def test_telegram_send_failure_webhook_retry_replays_safely(tmp_path: Path) -> None:
    app = create_app(settings_for(tmp_path, telegram_secret="test-webhook-secret"))
    bot = FakeBot()
    app.state.telegram_client = bot
    with TestClient(app) as client:
        # Start clean-sales
        client.post(ENDPOINT, headers=HEADERS, json=update(1, "/start"))

        # Submit valid file, but outgoing Telegram sendMessage will fail once
        up = update(2, content=CLEAN_CSV, filename="sales.csv")
        bot.files_by_id["fid_2"] = CLEAN_CSV
        bot.fail_send_once = True

        # First delivery attempt: evaluation succeeds, but bot.send fails on result
        res1 = client.post(ENDPOINT, headers=HEADERS, json=up)
        assert res1.status_code == 503
        assert res1.json()["code"] == "unavailable"
        assert bot.downloads == 1

        # Webhook retry by Telegram with exact same update
        res2 = client.post(ENDPOINT, headers=HEADERS, json=up)
        assert res2.status_code == 200
        assert res2.json() == {"ok": True}
        assert "التسليم مقبول" in bot.messages[-1]
        assert "100/100" in bot.messages[-1]
        # Verify no second download happened
        assert bot.downloads == 1


@pytest.mark.asyncio
async def test_telegram_client_unit() -> None:
    with pytest.raises(DomainError) as exc:
        TelegramClient("")
    assert exc.value.code == "unavailable"

    # Test send
    sent_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent_requests.append(request)
        if "sendMessage" in str(request.url):
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})
        if "sendDocument" in str(request.url):
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 2}})
        if "getFile" in str(request.url):
            return httpx.Response(
                200,
                json={"ok": True, "result": {"file_path": "documents/file.csv", "file_size": 12}},
            )
        if "file/bot" in str(request.url):
            return httpx.Response(200, content=b"col1,col2\n1,2")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = TelegramClient("dummy-token")

    # Monkey-patch httpx.AsyncClient to use our mock transport
    original_client_init = httpx.AsyncClient.__init__

    def mock_init(self: Any, *args: Any, **kwargs: Any) -> None:
        kwargs["transport"] = transport
        original_client_init(self, *args, **kwargs)

    httpx.AsyncClient.__init__ = mock_init  # type: ignore[method-assign]
    try:
        await client.send(12345, "مرحبا")
        assert any("sendMessage" in str(r.url) for r in sent_requests)

        await client.send_file(12345, "sales.csv", b"a,b\n1,2")
        assert any("sendDocument" in str(r.url) for r in sent_requests)

        content = await client.download("valid_file_id")
        assert content == b"col1,col2\n1,2"
    finally:
        httpx.AsyncClient.__init__ = original_client_init  # type: ignore[method-assign]


def test_rate_limit_and_error_redaction(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, rate_limit=2)
    with TestClient(create_app(settings)) as client:
        for _ in range(2):
            assert client.get("/api/v1/health").status_code == 200
        response = client.get("/api/v1/health")
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "60"
