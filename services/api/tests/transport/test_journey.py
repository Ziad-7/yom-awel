import hashlib

import pytest
from fastapi.testclient import TestClient

from yom_awel.transport.app import create_app
from yom_awel.transport.fakes import CLEAN_CSV, DIRTY_CSV
from yom_awel.transport.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        secret="s" * 48, database_path=str(tmp_path / "demo.db"), telegram_secret="webhook-secret"
    )


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


def onboard(client, name="أحمد"):
    token = client.post("/api/v1/auth/local-session").json()["access_token"]
    headers = {"Authorization": "Bearer " + token}
    response = client.post("/api/v1/learners/onboard", json={"display_name": name}, headers=headers)
    assert response.status_code == 200, response.text
    return headers


def upload(client, headers, content):
    metadata = {
        "filename": "sales.csv",
        "content_type": "text/csv",
        "size_bytes": len(content),
        "artifact_sha256": hashlib.sha256(content).hexdigest(),
    }
    response = client.post("/api/v1/artifacts/upload-authorization", json=metadata, headers=headers)
    assert response.status_code == 200, response.text
    authorization = response.json()
    response = client.put(
        authorization["upload_url"],
        content=content,
        headers={**headers, **authorization["headers"]},
    )
    assert response.status_code == 200, response.text
    return authorization["artifact_id"], metadata["artifact_sha256"]


def submit(client, headers, content, key):
    task = client.get("/api/v1/tasks/current", headers=headers).json()["task"]
    artifact_id, digest = upload(client, headers, content)
    body = {
        "task_version_id": task["task_version_id"],
        "artifact_id": artifact_id,
        "artifact_sha256": digest,
    }
    headers = {**headers, "Idempotency-Key": key}
    response = client.post("/api/v1/submissions", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json(), body, headers


def test_health_and_protected_routes(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/tasks/current").status_code == 401
    assert client.get("/api/v1/runtime").json()["simulated_evaluation"] is True


def test_fail_retry_pass_history_skills_replay_and_restart(client, settings):
    headers = onboard(client)
    failed, body, keyed = submit(client, headers, DIRTY_CSV, "fail-1")
    assert not failed["evaluation"]["passed"]
    assert failed["feedback"]["used_fallback"]
    replay = client.post("/api/v1/submissions", json=body, headers=keyed)
    assert replay.json() == failed
    passed, body, keyed = submit(client, headers, CLEAN_CSV, "pass-1")
    assert passed["evaluation"]["passed"]
    assert passed["attempt_number"] == 2
    assert client.post("/api/v1/submissions", json=body, headers=keyed).json() == passed
    assert (
        client.get("/api/v1/submissions/" + passed["submission_id"], headers=keyed).json() == passed
    )
    assert len(client.get("/api/v1/attempts", headers=headers).json()) == 2
    assert client.get("/api/v1/skills", headers=headers).json()["skills"][0]["score"] == 100
    with TestClient(create_app(settings)) as restarted:
        assert len(restarted.get("/api/v1/attempts", headers=headers).json()) == 2
        assert (
            restarted.get("/api/v1/tasks/current", headers=headers).json()["status"]
            == "TASK_COMPLETED"
        )


def test_wrong_learner_cannot_upload_read_or_submit(client):
    first, second = onboard(client), onboard(client, "منى")
    outcome, body, _keyed = submit(client, first, DIRTY_CSV, "private")
    assert (
        client.get(
            "/api/v1/submissions/" + outcome["submission_id"],
            headers={**second, "Idempotency-Key": "private"},
        ).status_code
        == 404
    )
    response = client.post(
        "/api/v1/submissions", json=body, headers={**second, "Idempotency-Key": "stolen"}
    )
    assert response.status_code in (403, 404, 422)
    assert (
        client.post(
            "/api/v1/learners/onboard",
            headers=first,
            json={"display_name": "a", "learner_id": "injected"},
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "filename,mime",
    [("payload.exe", "application/octet-stream"), ("../x.csv", "text/csv"), ("x.csv", "text/html")],
)
def test_invalid_file_metadata(client, filename, mime):
    headers = onboard(client)
    response = client.post(
        "/api/v1/artifacts/upload-authorization",
        headers=headers,
        json={
            "filename": filename,
            "content_type": mime,
            "size_bytes": 2,
            "artifact_sha256": "a" * 64,
        },
    )
    assert response.status_code == 415


def test_upload_hash_size_token_and_owner(client):
    headers = onboard(client)
    metadata = {
        "filename": "x.csv",
        "content_type": "text/csv",
        "size_bytes": 2,
        "artifact_sha256": hashlib.sha256(b"ok").hexdigest(),
    }
    auth = client.post(
        "/api/v1/artifacts/upload-authorization", headers=headers, json=metadata
    ).json()
    assert client.put(auth["upload_url"], headers=headers, content=b"ok").status_code == 403
    assert (
        client.put(
            auth["upload_url"], headers={**headers, **auth["headers"]}, content=b"no"
        ).status_code
        == 422
    )
    second = onboard(client, "other")
    assert (
        client.put(
            auth["upload_url"], headers={**second, **auth["headers"]}, content=b"ok"
        ).status_code
        == 403
    )
    assert (
        client.put(
            auth["upload_url"], headers={**headers, **auth["headers"]}, content=b"ok"
        ).status_code
        == 200
    )
    assert (
        client.put(
            auth["upload_url"], headers={**headers, **auth["headers"]}, content=b"ok"
        ).status_code
        == 200
    )


def test_cors_and_size_limit(client):
    for origin, status in [("http://localhost:3000", 200), ("https://evil.test", 400)]:
        response = client.options(
            "/api/v1/tasks/current",
            headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == status
        assert "access-control-allow-credentials" not in response.headers
    assert client.post("/api/v1/learners/onboard", content=b"x" * 65537).status_code == 413
    assert (
        client.put("/api/v1/artifacts/no/content", content=b"x" * (5 * 1024 * 1024 + 1)).status_code
        == 413
    )


def test_cloud_cannot_silently_use_local_storage(tmp_path):
    with (
        pytest.raises(ValueError, match="CLOUD_SERVICES_FACTORY"),
        TestClient(
            create_app(
                Settings(
                    mode="cloud",
                    supabase_url="https://project.supabase.co",
                    cors_origins=("https://web.test",),
                )
            )
        ),
    ):
        pass
