import hashlib
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from yom_awel.domain.enums import ErrorCategory
from yom_awel.domain.errors import ArtifactIntegrityFailure, DomainError, PersistenceError
from yom_awel.transport.app import create_app
from yom_awel.transport.dependencies import compose
from yom_awel.transport.fakes import CLEAN_CSV, DIRTY_CSV
from yom_awel.transport.settings import Settings


@pytest.fixture
def context(tmp_path):
    settings = Settings(secret="s" * 48, database_path=str(tmp_path / "review.db"))
    services = compose(settings)
    with TestClient(create_app(settings, services)) as client:
        token = client.post("/api/v1/auth/local-session").json()["access_token"]
        client.headers["Authorization"] = "Bearer " + token
        assert (
            client.post("/api/v1/learners/onboard", json={"display_name": "نور"}).status_code == 200
        )
        yield client, services


def authorize(client, content, filename="sales.csv", mime="text/csv"):
    response = client.post(
        "/api/v1/artifacts/upload-authorization",
        json={
            "filename": filename,
            "content_type": mime,
            "size_bytes": len(content),
            "artifact_sha256": hashlib.sha256(content).hexdigest(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def submit(client, content, key):
    auth = authorize(client, content)
    assert (
        client.put(auth["upload_url"], headers=auth["headers"], content=content).status_code == 200
    )
    task = client.get("/api/v1/tasks/current").json()["task"]
    return client.post(
        "/api/v1/submissions",
        headers={"Idempotency-Key": key},
        json={
            "task_version_id": task["task_version_id"],
            "artifact_id": auth["artifact_id"],
            "artifact_sha256": hashlib.sha256(content).hexdigest(),
        },
    )


def test_real_arabic_feedback_distinguishes_fail_and_pass(context):
    client, _ = context
    results = [
        submit(client, content, key).json()
        for content, key in [(DIRTY_CSV, "fail"), (CLEAN_CSV, "pass")]
    ]
    assert results[0]["feedback"]["feedback_text"] != results[1]["feedback"]["feedback_text"]
    for result in results:
        feedback, evaluation = result["feedback"], result["evaluation"]
        assert feedback["language"] == "ar-EG"
        assert feedback["used_fallback"] is True
        assert feedback["provider"] == "deterministic"
        text = feedback["feedback_text"]
        assert all(
            section in text
            for section in ["القرار:", "تأثير الشغل:", "الخطوة الجاية:", "تفسير الدرجة:"]
        )
        assert f"{evaluation['score']} من 100" in text
        assert ("التسليم مقبول" if evaluation["passed"] else "التسليم محتاج إعادة شغل") in text


def test_actual_evaluator_outage_is_retryable_evaluation_failure(context):
    client, services = context

    class UnavailableEvaluator:
        async def evaluate(self, task, artifact):
            raise OSError("private provider error and credential")

    services.submissions.evaluator = UnavailableEvaluator()
    response = submit(client, DIRTY_CSV, "outage")
    assert response.status_code == 503
    assert response.json()["category"] == "evaluation"
    assert response.json()["retryable"] is True
    assert response.json()["code"] == "evaluation_failed"
    assert int(response.headers["Retry-After"]) > 0
    assert "credential" not in response.text


@pytest.mark.parametrize(
    "error,status,category,retryable",
    [
        (
            DomainError(
                "finalization_conflict",
                "private",
                category=ErrorCategory.PERSISTENCE,
                retryable=True,
                retry_after_seconds=17,
            ),
            409,
            "persistence",
            True,
        ),
        (ArtifactIntegrityFailure(), 422, "validation", False),
        (PersistenceError("learner_scope_violation", "private"), 403, "authorization", False),
        (PersistenceError("database_unavailable", "private DSN"), 503, "persistence", True),
        (
            DomainError("bad_input", "private", category=ErrorCategory.VALIDATION, retryable=False),
            422,
            "validation",
            False,
        ),
        (
            DomainError(
                "provider_failed", "private", category=ErrorCategory.PROVIDER, retryable=False
            ),
            503,
            "provider",
            False,
        ),
        (DomainError("unknown_code", "private"), 503, "infrastructure", True),
    ],
)
def test_application_error_metadata_survives_transport(context, error, status, category, retryable):
    client, services = context

    async def failure(_):
        raise error

    services.skills.execute = failure
    response = client.get("/api/v1/skills")
    assert response.status_code == status
    assert response.json()["category"] == category
    assert response.json()["retryable"] is retryable
    assert ("Retry-After" in response.headers) is retryable
    if error.code == "finalization_conflict":
        assert response.headers["Retry-After"] == "17"
    assert "private" not in response.text
    assert response.headers["Cache-Control"] == "no-store"


def test_upload_mime_cannot_change_after_authorization(context):
    client, _ = context
    auth = authorize(client, DIRTY_CSV)
    for mime in ("application/x-msdownload", "application/octet-stream", ""):
        response = client.put(
            auth["upload_url"], headers={**auth["headers"], "Content-Type": mime}, content=DIRTY_CSV
        )
        assert response.status_code == 415
        assert response.json()["retryable"] is False
    assert client.post(f"/api/v1/artifacts/{auth['artifact_id']}/complete").status_code != 200


def workbook(payload=b"<worksheet/>", extra=None):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
        archive.writestr("xl/worksheets/sheet1.xml", payload)
        if extra:
            archive.writestr(*extra)
    return stream.getvalue()


@pytest.mark.parametrize(
    "filename,content",
    [
        ("sales.csv", b"MZ\x00executable"),
        ("sales.csv", b"%PDF-1.7 fake"),
        ("sales.csv", workbook()),
        ("sales.xlsx", DIRTY_CSV),
        ("sales.xlsx", workbook(b"a" * (2 * 1024 * 1024))),
        ("sales.xlsx", workbook(extra=("../outside.xml", b"<x/>"))),
        ("sales.xlsx", workbook(extra=("xl/vbaProject.bin", b"macro"))),
        ("sales.xlsx", workbook(b'<!DOCTYPE x [<!ENTITY a "payload">]><x/>')),
    ],
)
def test_spoofed_and_compressed_artifacts_never_complete(context, filename, content):
    client, _ = context
    mime = (
        "text/csv"
        if filename.endswith(".csv")
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    auth = authorize(client, content, filename, mime)
    response = client.put(auth["upload_url"], headers=auth["headers"], content=content)
    assert response.status_code == 415, response.text
    assert response.json()["code"] == "unsafe_artifact"
    assert client.post(f"/api/v1/artifacts/{auth['artifact_id']}/complete").status_code != 200
    assert client.get("/api/v1/attempts").json() == []


def test_structurally_safe_xlsx_upload_completes(context):
    client, _ = context
    content = workbook()
    auth = authorize(
        client,
        content,
        "sales.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert (
        client.put(auth["upload_url"], headers=auth["headers"], content=content).status_code == 200
    )
