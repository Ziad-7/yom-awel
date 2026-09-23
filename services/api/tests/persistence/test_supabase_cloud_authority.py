from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import NAMESPACE_OID, uuid4, uuid5

import pytest

ROOT = Path(__file__).resolve().parents[4]


def test_cloud_require_object_formats_invalid_object_error() -> None:
    sql = (ROOT / "supabase/migrations/20260922100000_cloud_progression_authority.sql").read_text(
        encoding="utf-8"
    )
    assert "raise exception 'invalid % object', p_label using errcode = '22023';" in sql


def test_cloud_validators_use_supported_volatility_and_extension_schema() -> None:
    sql = (ROOT / "supabase/migrations/20260922100000_cloud_progression_authority.sql").read_text(
        encoding="utf-8"
    )
    assert "extensions.uuid_generate_v5(" in sql
    for function_name in (
        "_cloud_json_timestamp",
        "_cloud_validate_attempt",
        "_cloud_validate_evidence",
        "_cloud_validate_outcome",
    ):
        start = sql.index(f"create or replace function public.{function_name}(")
        end = sql.index("$$;", start)
        assert "\nlanguage plpgsql\nstable\n" in sql[start:end]


class LocalRpc:
    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key

    async def call(self, function: str, params: Mapping[str, object]) -> tuple[object, bool]:
        def request() -> tuple[object, bool]:
            http_request = Request(
                f"{self.base_url}/rest/v1/rpc/{function}",
                data=json.dumps(params).encode(),
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urlopen(http_request, timeout=10) as response:
                    return json.loads(response.read().decode()), False
            except HTTPError as error:
                error.read()
                return {"status": error.code}, True

        return await asyncio.to_thread(request)


class LocalRest:
    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key

    async def insert(self, table: str, row: Mapping[str, object]) -> Mapping[str, object]:
        def request() -> Mapping[str, object]:
            http_request = Request(
                f"{self.base_url}/rest/v1/{table}",
                data=json.dumps(row).encode(),
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                method="POST",
            )
            with urlopen(http_request, timeout=10) as response:
                value = json.loads(response.read().decode())
            assert isinstance(value, list) and value and isinstance(value[0], Mapping)
            return value[0]

        return await asyncio.to_thread(request)

    async def rows(self, table: str, filters: Mapping[str, object]) -> list[Mapping[str, object]]:
        def request() -> list[Mapping[str, object]]:
            query = urlencode({key: f"eq.{value}" for key, value in filters.items()})
            http_request = Request(
                f"{self.base_url}/rest/v1/{table}?{query}",
                headers={"apikey": self.service_key, "Authorization": f"Bearer {self.service_key}"},
            )
            with urlopen(http_request, timeout=10) as response:
                value = json.loads(response.read().decode())
            return [row for row in value if isinstance(row, Mapping)]

        return await asyncio.to_thread(request)


def _config() -> tuple[str, str] | None:
    base_url = os.getenv("SUPABASE_LOCAL_URL")
    service_key = os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    if not base_url or not service_key:
        return None
    return base_url, service_key


async def seed_case(rest: LocalRest) -> dict[str, object]:
    suffix = uuid4().hex
    learner_id, task_version_id, artifact_id = uuid4(), uuid4(), uuid4()
    task_id = f"cloud-authority-{suffix}"
    skill_id = f"skill-cloud-{suffix}"
    now = datetime.now(UTC).replace(microsecond=0)
    await rest.insert(
        "learners",
        {
            "learner_id": str(learner_id),
            "display_name": "cloud-authority",
            "preferred_language": "en",
            "status": "IN_TASK",
            "state_machine_version": "1",
        },
    )
    await rest.insert("tasks", {"task_id": task_id, "title": "Cloud authority"})
    await rest.insert(
        "task_versions",
        {
            "task_version_id": str(task_version_id),
            "task_id": task_id,
            "version": "10",
            "instructions_ar": "تعليمات",
            "instructions_en": "Instructions",
            "artifact_schema": {},
            "evaluator_id": "eval-1",
            "evaluator_version": "1",
            "pass_threshold": 50,
            "skill_mappings": [{"skill_id": skill_id, "check_id": "clarity", "weight": 3}],
            "content_hash": "a" * 64,
            "status": "PUBLISHED",
            "published_at": now.isoformat(),
            "is_current": True,
        },
    )
    await rest.insert(
        "skill_definitions",
        {"skill_id": skill_id, "title": "Cloud", "description": "Cloud"},
    )
    await rest.insert(
        "artifacts",
        {
            "artifact_id": str(artifact_id),
            "learner_id": str(learner_id),
            "object_path": f"{learner_id}/{artifact_id}",
            "filename": "submission.txt",
            "size_bytes": 1,
            "sha256": "b" * 64,
        },
    )
    await rest.insert(
        "learner_progress",
        {
            "learner_id": str(learner_id),
            "current_status": "PROCESSING",
            "current_task_id": task_id,
            "version": 1,
        },
    )
    return {
        "learner_id": learner_id,
        "task_id": task_id,
        "skill_id": skill_id,
        "task_version_id": task_version_id,
        "artifact_id": artifact_id,
        "completed_at": now,
    }


async def reserve(rpc: LocalRpc, fixture: Mapping[str, object], key: str) -> dict[str, object]:
    value, failed = await rpc.call(
        "reserve_submission",
        {
            "p_learner_id": str(fixture["learner_id"]),
            "p_task_version_id": str(fixture["task_version_id"]),
            "p_artifact_id": str(fixture["artifact_id"]),
            "p_channel": "web",
            "p_idempotency_key": key,
            "p_request_fingerprint": "c" * 64,
            "p_lease_seconds": 300,
            "p_lease_owner": f"owner-{key}",
        },
    )
    assert not failed and isinstance(value, Mapping)
    return dict(value)


def payloads(fixture: Mapping[str, object], reservation: Mapping[str, object]) -> dict[str, object]:
    evaluation_id, feedback_id, attempt_id, event_id = uuid4(), uuid4(), uuid4(), uuid4()
    completed_at = fixture["completed_at"]
    assert isinstance(completed_at, datetime)
    evidence_id = uuid5(
        NAMESPACE_OID,
        f"{attempt_id}:{fixture['task_version_id']}:{fixture['skill_id']}:clarity",
    )
    evaluation = {
        "evaluation_id": str(evaluation_id),
        "evaluator_id": "eval-1",
        "evaluator_version": "1",
        "task_version_id": str(fixture["task_version_id"]),
        "passed": True,
        "score": 100,
        "checks": [{"check_id": "clarity", "passed": True, "weight": 3, "details": "ok"}],
        "errors": [],
        "summary_ar": "جيد",
        "summary_en": "Good",
        "duration_ms": 1,
    }
    feedback = {
        "feedback_id": str(feedback_id),
        "feedback_text": "Good",
        "language": "en",
        "persona_id": "tarek",
        "prompt_version": "1",
        "provider": "deterministic",
        "model": None,
        "used_fallback": True,
        "duration_ms": 0,
    }
    attempt = {
        "attempt_id": str(attempt_id),
        "attempt_number": 1,
        "started_at": completed_at.isoformat(),
        "completed_at": completed_at.isoformat(),
    }
    evidence = [
        {
            "evidence_id": str(evidence_id),
            "skill_id": fixture["skill_id"],
            "check_id": "clarity",
            "awarded_points": 3,
            "available_points": 3,
            "recorded_at": completed_at.isoformat(),
        }
    ]
    outbox = {
        "event_id": str(event_id),
        "event_type": "submission.processed",
        "payload": {"submission_id": str(reservation["submission_id"]), "passed": True},
    }
    public_evaluation = dict(evaluation)
    public_evaluation.pop("evaluation_id")
    public_feedback = dict(feedback)
    public_feedback.pop("feedback_id")
    outcome = {
        "submission_id": str(reservation["submission_id"]),
        "attempt_id": str(attempt_id),
        "attempt_number": 1,
        "evaluation": public_evaluation,
        "feedback": public_feedback,
        "learner_status": "TASK_COMPLETED",
        "task_status": "COMPLETED",
        "skills": [{"skill_id": fixture["skill_id"], "score": 3}],
    }
    return {
        "p_reservation_id": reservation["reservation_id"],
        "p_expected_version": reservation["version"],
        "p_lease_owner": reservation["lease_owner"],
        "p_evaluation": evaluation,
        "p_feedback": feedback,
        "p_attempt": attempt,
        "p_evidence": evidence,
        "p_progress_status": "TASK_COMPLETED",
        "p_progress_expected_version": 1,
        "p_outbox": outbox,
        "p_outcome": outcome,
    }


async def finalise(rpc: LocalRpc, fixture: Mapping[str, object], key: str) -> tuple[object, bool]:
    reservation = await reserve(rpc, fixture, key)
    return await rpc.call("finalize_submission", payloads(fixture, reservation))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cloud_authority_real_rpc_success_and_replay() -> None:
    config = _config()
    if config is None:
        pytest.skip("set SUPABASE_LOCAL_URL and SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    base_url, service_key = config
    rest, rpc = LocalRest(base_url, service_key), LocalRpc(base_url, service_key)
    fixture = await seed_case(rest)
    result, failed = await finalise(rpc, fixture, "success")
    assert not failed and isinstance(result, Mapping)
    replay = await reserve(rpc, fixture, "success")
    assert replay["status"] == "COMPLETED"
    assert len(await rest.rows("attempts", {"learner_id": str(fixture["learner_id"])})) == 1
    assert len(await rest.rows("skill_evidence", {"learner_id": str(fixture["learner_id"])})) == 1
    assert len(await rest.rows("outbox_events", {"aggregate_id": str(fixture["learner_id"])})) == 1


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "forgery", ["failed_status", "evidence", "outbox", "null_required", "missing_required"]
)
async def test_cloud_authority_real_rpc_rejects_forged_payloads(forgery: str) -> None:
    config = _config()
    if config is None:
        pytest.skip("set SUPABASE_LOCAL_URL and SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    base_url, service_key = config
    rest, rpc = LocalRest(base_url, service_key), LocalRpc(base_url, service_key)
    fixture = await seed_case(rest)
    reservation = await reserve(rpc, fixture, forgery)
    params = payloads(fixture, reservation)
    if forgery == "failed_status":
        params["p_evaluation"] = dict(params["p_evaluation"], passed=False)
        public_evaluation = dict(params["p_evaluation"])
        public_evaluation.pop("evaluation_id")
        params["p_outcome"] = dict(params["p_outcome"], evaluation=public_evaluation)
        params["p_outbox"] = dict(
            params["p_outbox"],
            payload={"submission_id": reservation["submission_id"], "passed": False},
        )
    elif forgery == "evidence":
        params["p_evidence"] = [dict(params["p_evidence"][0], skill_id="forged-skill")]
    elif forgery == "null_required":
        params["p_evaluation"] = dict(params["p_evaluation"], score=None)
    elif forgery == "missing_required":
        feedback = dict(params["p_feedback"])
        feedback.pop("provider")
        params["p_feedback"] = feedback
    else:
        params["p_outbox"] = dict(
            params["p_outbox"],
            payload={"submission_id": reservation["submission_id"], "passed": False},
        )
    _, failed = await rpc.call("finalize_submission", params)
    assert failed
    assert (
        await rest.rows("evaluation_results", {"submission_id": str(reservation["submission_id"])})
        == []
    )
    assert await rest.rows("attempts", {"submission_id": str(reservation["submission_id"])}) == []
    assert await rest.rows("outbox_events", {"aggregate_id": str(fixture["learner_id"])}) == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cloud_authority_real_rpc_rollback_published_only_nullable_owner_and_concurrency() -> (
    None
):
    config = _config()
    if config is None:
        pytest.skip("set SUPABASE_LOCAL_URL and SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    base_url, service_key = config
    rest, rpc = LocalRest(base_url, service_key), LocalRpc(base_url, service_key)
    fixture = await seed_case(rest)

    draft_version_id = uuid4()
    await rest.insert(
        "task_versions",
        {
            "task_version_id": str(draft_version_id),
            "task_id": fixture["task_id"],
            "version": "11",
            "instructions_ar": "مسودة",
            "instructions_en": "Draft",
            "artifact_schema": {},
            "evaluator_id": "eval-1",
            "evaluator_version": "1",
            "pass_threshold": 50,
            "skill_mappings": [
                {"skill_id": fixture["skill_id"], "check_id": "clarity", "weight": 3}
            ],
            "content_hash": "d" * 64,
            "status": "DRAFT",
        },
    )
    _, failed = await rpc.call(
        "reserve_submission",
        {
            "p_learner_id": str(fixture["learner_id"]),
            "p_task_version_id": str(draft_version_id),
            "p_artifact_id": str(fixture["artifact_id"]),
            "p_channel": "web",
            "p_idempotency_key": "draft-version",
            "p_request_fingerprint": "c" * 64,
            "p_lease_seconds": 300,
            "p_lease_owner": "draft-owner",
        },
    )
    assert failed

    reservation = await reserve(rpc, fixture, "rollback")
    params = payloads(fixture, reservation)
    params["p_progress_expected_version"] = 999
    _, failed = await rpc.call("finalize_submission", params)
    assert failed
    assert (
        await rest.rows("evaluation_results", {"submission_id": str(reservation["submission_id"])})
        == []
    )
    progress_rows = await rest.rows("learner_progress", {"learner_id": str(fixture["learner_id"])})
    assert progress_rows[0]["version"] == 1

    null_owner = dict(params, p_progress_expected_version=1, p_lease_owner=None)
    _, failed = await rpc.call("finalize_submission", null_owner)
    assert failed
    _, failed = await rpc.call(
        "reserve_submission",
        {
            "p_learner_id": str(fixture["learner_id"]),
            "p_task_version_id": str(fixture["task_version_id"]),
            "p_artifact_id": str(fixture["artifact_id"]),
            "p_channel": "web",
            "p_idempotency_key": "empty-owner",
            "p_request_fingerprint": "c" * 64,
            "p_lease_seconds": 300,
            "p_lease_owner": "",
        },
    )
    assert failed

    # Two keys finalize against the same persisted progress version.  Both
    # execute the real RPC; exactly one can commit its audit projection.
    fixture = await seed_case(rest)
    first = await reserve(rpc, fixture, "race-a")
    second = await reserve(rpc, fixture, "race-b")
    first_result, second_result = await asyncio.gather(
        rpc.call("finalize_submission", payloads(fixture, first)),
        rpc.call("finalize_submission", payloads(fixture, second)),
    )
    assert sum(not failed for _, failed in (first_result, second_result)) == 1
    assert len(await rest.rows("attempts", {"learner_id": str(fixture["learner_id"])})) == 1
    assert len(await rest.rows("skill_evidence", {"learner_id": str(fixture["learner_id"])})) == 1
    assert len(await rest.rows("outbox_events", {"aggregate_id": str(fixture["learner_id"])})) == 1
