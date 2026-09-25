import asyncio
import hashlib

import httpx
import pytest

from tests.transport.support import CSRF, DIRTY_CSV, TASK_ID, settings_for
from yom_awel.transport.app import create_app
from yom_awel.transport.dependencies import compose


async def upload(client: httpx.AsyncClient, filename: str) -> str:
    digest = hashlib.sha256(DIRTY_CSV).hexdigest()
    authorization = (
        await client.post(
            "/api/v1/artifacts/upload-authorization",
            json={
                "filename": filename,
                "content_type": "text/csv",
                "size_bytes": len(DIRTY_CSV),
                "artifact_sha256": digest,
            },
        )
    ).json()
    await client.put(
        authorization["upload_url"], content=DIRTY_CSV, headers=authorization["headers"]
    )
    return str(authorization["artifact_id"])


@pytest.mark.asyncio
async def test_active_duplicate_returns_202_then_replays_original(tmp_path):
    settings = settings_for(tmp_path)
    services = compose(settings)
    real = services.submissions.evaluator
    entered, release = asyncio.Event(), asyncio.Event()

    class SlowEvaluator:
        async def evaluate(self, task_version, artifact):
            entered.set()
            await release.wait()
            return await real.evaluate(task_version, artifact)

    services.submissions.evaluator = SlowEvaluator()
    app = create_app(settings, services)
    await services.seed_tasks()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test", headers=CSRF
    ) as client:
        await client.post("/api/v1/auth/session")
        await client.post("/api/v1/learners/onboard", json={"display_name": "test"})
        task = (await client.post(f"/api/v1/tasks/{TASK_ID}/start")).json()["task"]
        body = {
            "task_version_id": task["task_version_id"],
            "artifact_id": await upload(client, "sales.csv"),
            "artifact_sha256": hashlib.sha256(DIRTY_CSV).hexdigest(),
        }
        headers = {"Idempotency-Key": "concurrent"}
        first = asyncio.create_task(client.post("/api/v1/submissions", json=body, headers=headers))
        await asyncio.wait_for(entered.wait(), timeout=5)
        try:
            second = await client.post("/api/v1/submissions", json=body, headers=headers)
            assert second.status_code == 202
            assert int(second.headers["Retry-After"]) >= 1
        finally:
            release.set()
        original = await first
        assert original.status_code == 200
        assert original.json()["evaluation"]["score"] == 0
        assert second.json()["submission_id"] == original.json()["submission_id"]
        replay = await client.post("/api/v1/submissions", json=body, headers=headers)
        assert replay.json() == original.json()
        conflict = await client.post(
            "/api/v1/submissions",
            json={**body, "artifact_id": await upload(client, "other.csv")},
            headers=headers,
        )
        assert conflict.status_code == 409


@pytest.mark.asyncio
async def test_switching_tasks_during_sqlite_grading_cannot_overwrite_new_task(tmp_path):
    settings = settings_for(tmp_path)
    services = compose(settings)
    real = services.submissions.evaluator
    entered, release = asyncio.Event(), asyncio.Event()

    class SlowEvaluator:
        async def evaluate(self, task_version, artifact):
            entered.set()
            await release.wait()
            return await real.evaluate(task_version, artifact)

    services.submissions.evaluator = SlowEvaluator()
    app = create_app(settings, services)
    await services.seed_tasks()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test", headers=CSRF
    ) as client:
        await client.post("/api/v1/auth/session")
        await client.post("/api/v1/learners/onboard", json={"display_name": "test"})
        task = (await client.post(f"/api/v1/tasks/{TASK_ID}/start")).json()["task"]
        body = {
            "task_version_id": task["task_version_id"],
            "artifact_id": await upload(client, "sales.csv"),
            "artifact_sha256": hashlib.sha256(DIRTY_CSV).hexdigest(),
        }
        first = asyncio.create_task(
            client.post(
                "/api/v1/submissions",
                json=body,
                headers={"Idempotency-Key": "switch-during-grading"},
            )
        )
        await asyncio.wait_for(entered.wait(), timeout=5)
        try:
            switched = await client.post("/api/v1/tasks/sql-report/start")
            assert switched.status_code == 200, switched.text
        finally:
            release.set()
        stale = await first
        assert stale.status_code == 409
        assert stale.json()["code"] == "task_not_current"
        current = (await client.get("/api/v1/tasks/current")).json()
        assert current["task"]["task_id"] == "sql-report"
        assert current["status"] == "IN_TASK"
        assert (await client.get("/api/v1/attempts")).json() == []
