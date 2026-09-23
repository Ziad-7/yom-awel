"""Opt-in local Supabase behavioral coverage for retention recovery.

Set SUPABASE_LOCAL_URL and SUPABASE_LOCAL_SERVICE_ROLE_KEY when running the
local Docker Supabase stack.  The test intentionally uses only PostgREST/RPC,
so it also exercises the migration's real locking, FK, and trigger behavior.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import pytest


def _config() -> tuple[str, str] | None:
    url, key = os.getenv("SUPABASE_LOCAL_URL"), os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    return (url, key) if url and key else None


class LocalSupabase:
    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key

    def _headers(self, *, body: bool = False) -> dict[str, str]:
        headers = {"apikey": self.service_key, "Authorization": f"Bearer {self.service_key}"}
        if body:
            headers.update({"Content-Type": "application/json", "Prefer": "return=representation"})
        return headers

    async def insert(self, table: str, row: Mapping[str, object]) -> Mapping[str, object]:
        def request() -> Mapping[str, object]:
            response_request = Request(
                f"{self.base_url}/rest/v1/{table}",
                data=json.dumps(row).encode(),
                headers=self._headers(body=True),
                method="POST",
            )
            with urlopen(response_request, timeout=10) as response:
                value = json.loads(response.read().decode())
            assert isinstance(value, list) and value and isinstance(value[0], Mapping)
            return value[0]

        return await asyncio.to_thread(request)

    async def update(
        self, table: str, filters: Mapping[str, object], values: Mapping[str, object]
    ) -> None:
        def request() -> None:
            query = urlencode({key: f"eq.{value}" for key, value in filters.items()})
            response_request = Request(
                f"{self.base_url}/rest/v1/{table}?{query}",
                data=json.dumps(values).encode(),
                headers=self._headers(body=True),
                method="PATCH",
            )
            with urlopen(response_request, timeout=10):
                return

        await asyncio.to_thread(request)

    async def rows(self, table: str, filters: Mapping[str, object]) -> list[Mapping[str, object]]:
        def request() -> list[Mapping[str, object]]:
            query = urlencode({key: f"eq.{value}" for key, value in filters.items()})
            response_request = Request(
                f"{self.base_url}/rest/v1/{table}?{query}",
                headers=self._headers(),
            )
            with urlopen(response_request, timeout=10) as response:
                value = json.loads(response.read().decode())
            return [row for row in value if isinstance(row, Mapping)]

        return await asyncio.to_thread(request)

    async def rpc(self, function: str, params: Mapping[str, object]) -> tuple[object, bool]:
        def request() -> tuple[object, bool]:
            response_request = Request(
                f"{self.base_url}/rest/v1/rpc/{function}",
                data=json.dumps(params).encode(),
                headers={**self._headers(body=True), "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urlopen(response_request, timeout=10) as response:
                    body = response.read()
                    return (None if not body else json.loads(body.decode())), False
            except HTTPError as error:
                error.read()
                return {"status": error.code}, True

        return await asyncio.to_thread(request)


async def _seed(rest: LocalSupabase, *, complete: bool = True) -> dict[str, UUID]:
    suffix = uuid4().hex
    ids = {
        name: uuid4() for name in ("learner", "identity", "task_version", "artifact", "submission")
    }
    ids.update({name: uuid4() for name in ("evaluation", "feedback", "attempt", "event")})
    task_id, skill_id = f"retention-task-{suffix}", f"retention-skill-{suffix}"
    now = datetime.now(UTC).replace(microsecond=0)
    await rest.insert("learners", {
        "learner_id": str(ids["learner"]), "display_name": "retention", "preferred_language": "en",
        "status": "IN_TASK", "state_machine_version": "1",
    })
    await rest.insert("external_identities", {
        "identity_id": str(ids["identity"]), "learner_id": str(ids["learner"]),
        "provider": "web", "provider_subject": str(uuid4()), "is_anonymous": True,
    })
    await rest.insert("tasks", {"task_id": task_id, "title": "Retention"})
    await rest.insert("task_versions", {
        "task_version_id": str(ids["task_version"]), "task_id": task_id, "version": "1",
        "instructions_ar": "تعليمات", "instructions_en": "Instructions", "artifact_schema": {},
        "evaluator_id": "eval", "evaluator_version": "1", "pass_threshold": 50,
        "skill_mappings": [{"skill_id": skill_id, "check_id": "c", "weight": 1}],
        "content_hash": "a" * 64, "status": "PUBLISHED", "published_at": now.isoformat(),
        "is_current": True,
    })
    await rest.insert(
        "skill_definitions",
        {"skill_id": skill_id, "title": "Retention", "description": "Retention"},
    )
    await rest.insert("artifacts", {
        "artifact_id": str(ids["artifact"]), "learner_id": str(ids["learner"]),
        "object_path": f"{ids['learner']}/{ids['artifact']}", "filename": "answer.txt",
        "size_bytes": 1, "sha256": "b" * 64, "purge_status": "PURGED" if complete else "ACTIVE",
    })
    if complete:
        await rest.insert("submissions", {
            "reservation_id": str(uuid4()), "submission_id": str(ids["submission"]),
            "learner_id": str(ids["learner"]), "task_version_id": str(ids["task_version"]),
            "artifact_id": str(ids["artifact"]), "channel": "web", "idempotency_key": suffix,
            "request_fingerprint": "c" * 64, "status": "COMPLETED",
            "lease_expires_at": (now + timedelta(minutes=5)).isoformat(),
        })
        await rest.insert("evaluation_results", {
            "evaluation_id": str(ids["evaluation"]), "submission_id": str(ids["submission"]),
            "evaluator_id": "eval",
            "evaluator_version": "1",
            "task_version_id": str(ids["task_version"]),
            "passed": True, "score": 100, "checks": [], "errors": [],
            "summary_ar": "جيد", "summary_en": "Good", "duration_ms": 1,
        })
        await rest.insert("feedback_results", {
            "feedback_id": str(ids["feedback"]), "submission_id": str(ids["submission"]),
            "feedback_text": "Good", "language": "en", "persona_id": "tarek",
            "prompt_version": "1",
            "provider": "deterministic",
            "used_fallback": True,
            "duration_ms": 0,
        })
        await rest.insert("attempts", {
            "attempt_id": str(ids["attempt"]), "learner_id": str(ids["learner"]),
            "submission_id": str(ids["submission"]), "task_version_id": str(ids["task_version"]),
            "attempt_number": 1,
            "evaluation_id": str(ids["evaluation"]),
            "feedback_id": str(ids["feedback"]),
            "evaluator_id": "eval", "evaluator_version": "1", "prompt_version": "1",
            "started_at": now.isoformat(), "completed_at": now.isoformat(),
        })
        await rest.insert("skill_evidence", {
            "learner_id": str(ids["learner"]), "attempt_id": str(ids["attempt"]),
            "task_version_id": str(ids["task_version"]), "skill_id": skill_id, "check_id": "c",
            "awarded_points": 1, "available_points": 1,
        })
        await rest.insert("outbox_events", {
            "event_id": str(ids["event"]), "event_type": "retention.test",
            "aggregate_id": str(ids["learner"]), "payload": {"test": True},
        })
    _, failed = await rest.rpc(
        "enqueue_artifact_cleanup",
        {
            "p_learner_id": str(ids["learner"]),
            "p_artifact_id": str(ids["artifact"]),
            "p_object_path": f"{ids['learner']}/{ids['artifact']}",
            "p_sha256": "b" * 64,
            "p_size_bytes": 1,
            "p_reason": "UPLOAD_FAILED",
        },
    )
    assert not failed
    if complete:
        _, failed = await rest.rpc(
            "resolve_artifact_cleanup",
            {"p_learner_id": str(ids["learner"]), "p_artifact_id": str(ids["artifact"])},
        )
        assert not failed
    return ids


@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_learner_erasure_blocks_unresolved_rows_and_preserves_orphans() -> None:
    config = _config()
    if config is None:
        pytest.skip("set SUPABASE_LOCAL_URL and SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    rest = LocalSupabase(*config)

    blocked_artifact = await _seed(rest, complete=False)
    request, failed = await rest.rpc(
        "request_learner_deletion",
        {"p_learner_id": str(blocked_artifact["learner"]), "p_requested_by": "integration"},
    )
    assert not failed and isinstance(request, Mapping)
    _, failed = await rest.rpc(
        "erase_learner_application_data",
        {"p_learner_id": str(blocked_artifact["learner"]), "p_actor_id": "integration"},
    )
    assert failed

    complete = await _seed(rest)
    request, failed = await rest.rpc(
        "request_learner_deletion",
        {"p_learner_id": str(complete["learner"]), "p_requested_by": "integration"},
    )
    assert not failed and isinstance(request, Mapping)
    request_retry, failed = await rest.rpc(
        "request_learner_deletion",
        {"p_learner_id": str(complete["learner"]), "p_requested_by": "integration-retry"},
    )
    assert not failed and request_retry["request_id"] == request["request_id"]
    erased, failed = await rest.rpc(
        "erase_learner_application_data",
        {"p_learner_id": str(complete["learner"]), "p_actor_id": "integration"},
    )
    assert not failed and erased is True
    for table in (
        "learners",
        "submissions",
        "evaluation_results",
        "feedback_results",
        "attempts",
        "skill_evidence",
        "outbox_events",
    ):
        if table in {"evaluation_results", "feedback_results"}:
            filters = {"submission_id": str(complete["submission"])}
        elif table == "outbox_events":
            filters = {"aggregate_id": str(complete["learner"])}
        else:
            filters = {"learner_id": str(complete["learner"])}
        assert await rest.rows(table, filters) == []
    assert await rest.rows("artifact_cleanup_queue", {"learner_id": str(complete["learner"])})
    audits = await rest.rows("retention_audit", {"requested_learner_id": str(complete["learner"])})
    assert sum(row["action"] == "DELETE_REQUESTED" for row in audits) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_claim_reclaims_expired_worker_lease() -> None:
    config = _config()
    if config is None:
        pytest.skip("set SUPABASE_LOCAL_URL and SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    rest = LocalSupabase(*config)
    seeded = await _seed(rest, complete=False)
    request, failed = await rest.rpc(
        "request_learner_deletion",
        {"p_learner_id": str(seeded["learner"]), "p_requested_by": "integration"},
    )
    assert not failed and isinstance(request, Mapping)
    await rest.update(
        "learner_deletion_requests",
        {"request_id": request["request_id"]},
        {
            "status": "CLAIMED",
            "lease_owner": "crashed-worker",
            "lease_expires_at": "2000-01-01T00:00:00Z",
        },
    )
    claimed, failed = await rest.rpc(
        "claim_learner_deletion_requests", {"p_lease_owner": "recovery-worker", "p_limit": 10}
    )
    assert not failed and any(row["request_id"] == request["request_id"] for row in claimed)
