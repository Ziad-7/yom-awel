import hashlib
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from yom_awel.evaluation.catalog import csv_to_xlsx
from yom_awel.evaluation.clean_sales_dataset import LEARNER_SEED, apply_defects, generate, to_csv
from yom_awel.transport.settings import REPOSITORY_ROOT, Settings

CSRF = {"X-Yom-Awel": "1"}
TASK_ID = "clean-sales"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TEST_SECRET = "test-only-signing-key-" + "x" * 32  # pragma: allowlist secret

LEARNER_DATA = generate(LEARNER_SEED)
DIRTY_CSV = (
    REPOSITORY_ROOT / "task_packages" / TASK_ID / "1" / "data" / "sales_dirty.csv"
).read_bytes()
CLEAN_CSV = to_csv(LEARNER_DATA.clean).encode()
CLEAN_XLSX = csv_to_xlsx(CLEAN_CSV)
DUPLICATES_CSV = to_csv(
    apply_defects(
        LEARNER_DATA.clean,
        [defect for defect in LEARNER_DATA.defects if defect.kind == "duplicate_order"],
    )
).encode()


def settings_for(tmp_path: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "secret": TEST_SECRET,
        "database_path": str(tmp_path / "learning.sqlite3"),
        "telegram_secret": "test-webhook-secret",  # pragma: allowlist secret
    }
    return Settings(**(values | overrides))


def browser(app: FastAPI) -> TestClient:
    """A separate cookie jar per learner, always sending the CSRF header like the web app."""

    return TestClient(app, headers=CSRF)


def onboard(client: TestClient, name: str = "أحمد", language: str = "ar-EG") -> dict[str, Any]:
    assert client.post("/api/v1/auth/session").status_code == 200
    response = client.post(
        "/api/v1/learners/onboard", json={"display_name": name, "preferred_language": language}
    )
    assert response.status_code == 200, response.text
    return dict(response.json())


def start(client: TestClient) -> dict[str, Any]:
    response = client.post(f"/api/v1/tasks/{TASK_ID}/start")
    assert response.status_code == 200, response.text
    return dict(response.json()["task"])


def upload(
    client: TestClient, content: bytes, filename: str = "sales.csv", mime: str = "text/csv"
) -> tuple[str, str]:
    digest = hashlib.sha256(content).hexdigest()
    response = client.post(
        "/api/v1/artifacts/upload-authorization",
        json={
            "filename": filename,
            "content_type": mime,
            "size_bytes": len(content),
            "artifact_sha256": digest,
        },
    )
    assert response.status_code == 200, response.text
    authorization = response.json()
    response = client.put(
        authorization["upload_url"], content=content, headers=authorization["headers"]
    )
    assert response.status_code == 200, response.text
    return str(authorization["artifact_id"]), digest


def submit(
    client: TestClient,
    content: bytes,
    key: str,
    filename: str = "sales.csv",
    mime: str = "text/csv",
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    task = client.get("/api/v1/tasks/current").json()["task"]
    artifact_id, digest = upload(client, content, filename, mime)
    body = {
        "task_version_id": task["task_version_id"],
        "artifact_id": artifact_id,
        "artifact_sha256": digest,
    }
    headers = {"Idempotency-Key": key}
    response = client.post("/api/v1/submissions", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return dict(response.json()), body, headers
