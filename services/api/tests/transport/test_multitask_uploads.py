"""Task-specific upload formats and source downloads across the learner journey."""

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.transport.support import CLEAN_CSV, CSRF, onboard, settings_for, submit
from yom_awel.transport.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(settings_for(tmp_path)), headers=CSRF) as browser:
        onboard(browser)
        yield browser


def _authorize(client: TestClient, filename: str, mime: str, content: bytes):
    return client.post(
        "/api/v1/artifacts/upload-authorization",
        json={
            "filename": filename,
            "content_type": mime,
            "size_bytes": len(content),
            "artifact_sha256": hashlib.sha256(content).hexdigest(),
        },
    )


@pytest.mark.parametrize(
    "task_id,filename,mime,content,other_filename,other_mime,download_name",
    [
        (
            "sql-report",
            "report.sql",
            "text/plain",
            b"SELECT region FROM sales;",
            "email.txt",
            "text/plain",
            "sql_report_source.csv",
        ),
        (
            "client-email",
            "email.txt",
            "text/plain",
            b"To: client@example.com\nSubject: order\n\nHello, sorry for the delay.",
            "report.sql",
            "application/sql",
            "client_email_source.csv",
        ),
    ],
)
def test_task_formats_and_upload_content(
    client, task_id, filename, mime, content, other_filename, other_mime, download_name
):
    started = client.post(f"/api/v1/tasks/{task_id}/start")
    assert started.status_code == 200, started.text
    detail = client.get(f"/api/v1/tasks/{task_id}").json()
    assert detail["formats"] == ["csv", "xlsx"]
    assert detail["submission_formats"] == [filename.rsplit(".", 1)[-1]]
    download = client.get(f"/api/v1/tasks/{task_id}/dataset")
    assert download.status_code == 200
    assert f'filename="{download_name}"' in download.headers["content-disposition"]

    mismatch = _authorize(client, other_filename, other_mime, content)
    assert mismatch.status_code == 415
    assert mismatch.json()["code"] == "unsupported_artifact"

    authorized = _authorize(client, filename, mime, content)
    assert authorized.status_code == 200, authorized.text
    payload = authorized.json()
    put = client.put(payload["upload_url"], headers=payload["headers"], content=content)
    assert put.status_code == 200, put.text


@pytest.mark.parametrize("content", [b"MZ\x00binary", b"%PDF-1.7", b"\xff\xfe", b"hello\x00world"])
def test_plain_text_upload_rejects_spoofed_or_binary_content(client, content):
    assert client.post("/api/v1/tasks/client-email/start").status_code == 200
    payload = _authorize(client, "email.txt", "text/plain", content).json()
    upload = client.put(payload["upload_url"], headers=payload["headers"], content=content)
    assert upload.status_code == 415
    assert upload.json()["code"] == "unsafe_artifact"
    assert client.post(f"/api/v1/artifacts/{payload['artifact_id']}/complete").status_code != 200


def test_all_three_tasks_pass_and_history_survives_switching(client):
    root = Path(__file__).resolve().parents[4]
    cases = [
        ("clean-sales", CLEAN_CSV, "cleaned.csv", "text/csv"),
        (
            "sql-report",
            (
                b"SELECT region, COUNT(*) AS paid_orders, "
                b"ROUND(SUM(quantity * unit_price), 2) AS total_revenue "
                b"FROM sales WHERE status = 'paid' GROUP BY region ORDER BY region;"
            ),
            "report.sql",
            "text/plain",
        ),
        (
            "client-email",
            (root / "task_packages/client-email/1/examples/pass.en.txt").read_bytes(),
            "reply.txt",
            "text/plain",
        ),
    ]
    for task_id, content, filename, mime in cases:
        started = client.post(f"/api/v1/tasks/{task_id}/start")
        assert started.status_code == 200, started.text
        result, _, _ = submit(client, content, task_id, filename, mime)
        assert result["evaluation"]["passed"] is True, result
        assert result["evaluation"]["score"] >= 75
        summary = {item["task_id"]: item for item in client.get("/api/v1/tasks").json()["tasks"]}
        assert summary[task_id]["status"] == "completed"

    attempts = client.get("/api/v1/attempts").json()
    assert len(attempts) == 3
    assert {item["evaluation"]["task_version_id"] for item in attempts} == {
        item["task_version_id"] for item in summary.values()
    }
    assert all(item["status"] == "completed" for item in summary.values())


@pytest.mark.parametrize(
    "task_id,content,filename",
    [
        ("sql-report", b"SELECT 1;", "report.sql"),
        ("client-email", b"Hello", "reply.txt"),
    ],
)
def test_new_task_failures_have_grounded_feedback_and_allow_task_switching(
    client, task_id, content, filename
):
    assert client.post(f"/api/v1/tasks/{task_id}/start").status_code == 200
    result, _, _ = submit(client, content, task_id, filename, "text/plain")
    assert result["evaluation"]["passed"] is False
    feedback = result["feedback"]["feedback_text"]
    assert all(
        heading in feedback
        for heading in ("القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:")
    )
    assert f"{result['evaluation']['score']} من 100" in feedback
    assert "الطلبات المكررة" not in feedback
    other = "client-email" if task_id == "sql-report" else "sql-report"
    assert client.post(f"/api/v1/tasks/{other}/start").status_code == 200
    assert len(client.get("/api/v1/attempts").json()) == 1
