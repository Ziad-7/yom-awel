import asyncio
import hashlib

import httpx
import pytest

from yom_awel.transport.app import create_app
from yom_awel.transport.dependencies import compose
from yom_awel.transport.fakes import DIRTY_CSV, FixtureEvaluator
from yom_awel.transport.settings import Settings


@pytest.mark.asyncio
async def test_active_duplicate_returns_202_then_replays_original(tmp_path):
    settings = Settings(secret="s" * 48, database_path=str(tmp_path / "learning.db"))
    services = compose(settings)
    entered, release = asyncio.Event(), asyncio.Event()

    class SlowEvaluator(FixtureEvaluator):
        async def evaluate(self, task_version, artifact):
            entered.set()
            await release.wait()
            return await super().evaluate(task_version, artifact)

    services.submissions.evaluator = SlowEvaluator()
    app = create_app(settings, services)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app), base_url="http://test"
    ) as client:
        session = (await client.post("/api/v1/auth/local-session")).json()
        client.headers["Authorization"] = "Bearer " + session["access_token"]
        await client.post("/api/v1/learners/onboard", json={"display_name": "test"})
        task = (await client.get("/api/v1/tasks/current")).json()["task"]
        digest = hashlib.sha256(DIRTY_CSV).hexdigest()
        upload = (
            await client.post(
                "/api/v1/artifacts/upload-authorization",
                json={
                    "filename": "sales.csv",
                    "content_type": "text/csv",
                    "size_bytes": len(DIRTY_CSV),
                    "artifact_sha256": digest,
                },
            )
        ).json()
        await client.put(upload["upload_url"], content=DIRTY_CSV, headers=upload["headers"])
        body = {
            "task_version_id": task["task_version_id"],
            "artifact_id": upload["artifact_id"],
            "artifact_sha256": digest,
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
        assert second.json()["submission_id"] == original.json()["submission_id"]
        replay = await client.post("/api/v1/submissions", json=body, headers=headers)
        assert replay.json() == original.json()
        other_upload = (
            await client.post(
                "/api/v1/artifacts/upload-authorization",
                json={
                    "filename": "other.csv",
                    "content_type": "text/csv",
                    "size_bytes": len(DIRTY_CSV),
                    "artifact_sha256": digest,
                },
            )
        ).json()
        await client.put(
            other_upload["upload_url"], content=DIRTY_CSV, headers=other_upload["headers"]
        )
        conflict = await client.post(
            "/api/v1/submissions",
            json={**body, "artifact_id": other_upload["artifact_id"]},
            headers=headers,
        )
        assert conflict.status_code == 409
