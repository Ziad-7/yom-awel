from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import pytest

from yom_awel.domain.contracts import (
    EvaluationCheck,
    EvaluationResult,
    FeedbackResult,
    SubmissionOutcome,
)
from yom_awel.domain.enums import Channel, LearnerStatus, TaskStatus
from yom_awel.persistence.supabase import (
    SupabasePersistenceError,
    SupabaseSubmissionRepository,
    map_submission_row,
)


@dataclass
class Response:
    data: object
    error: object | None = None


def submission_row(learner_id: UUID, *, status: str = "RECEIVED") -> dict[str, object]:
    now = datetime.now(UTC)
    return {
        "reservation_id": str(uuid4()),
        "submission_id": str(uuid4()),
        "learner_id": str(learner_id),
        "task_version_id": str(uuid4()),
        "artifact_id": str(uuid4()),
        "channel": "web",
        "idempotency_key": "key-1",
        "request_fingerprint": "a" * 64,
        "status": status,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "version": 1,
        "lease_expires_at": (now + timedelta(minutes=5)).isoformat(),
        "lease_owner": "worker-1",
        "outcome": None,
    }


class RpcFake:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    async def rpc(self, function: str, params: Mapping[str, object]) -> Response:
        self.calls.append((function, params))
        return self.response


class LocalRpc:
    def __init__(self, base_url: str, service_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_key = service_key

    async def rpc(self, function: str, params: Mapping[str, object]) -> Response:
        def request() -> Response:
            payload = json.dumps(params).encode("utf-8")
            request = Request(
                f"{self._base_url}/rest/v1/rpc/{function}",
                data=payload,
                headers={
                    "apikey": self._service_key,
                    "Authorization": f"Bearer {self._service_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urlopen(request, timeout=5) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return Response(data)
            except HTTPError as error:
                error.read()
                return Response(None, error={"status": error.code})

        return await asyncio.to_thread(request)


class LocalRest:
    def __init__(self, base_url: str, service_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_key = service_key

    async def insert(self, table: str, row: Mapping[str, object]) -> Mapping[str, object]:
        def request() -> Mapping[str, object]:
            http_request = Request(
                f"{self._base_url}/rest/v1/{table}",
                data=json.dumps(row).encode("utf-8"),
                headers={
                    "apikey": self._service_key,
                    "Authorization": f"Bearer {self._service_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=representation",
                },
                method="POST",
            )
            with urlopen(http_request, timeout=5) as response:
                value = json.loads(response.read().decode("utf-8"))
            if not isinstance(value, list) or not value or not isinstance(value[0], Mapping):
                raise RuntimeError("local Supabase insert returned no row")
            return value[0]

        return await asyncio.to_thread(request)

    async def select_one(
        self, table: str, filters: Mapping[str, object]
    ) -> Mapping[str, object] | None:
        def request() -> Mapping[str, object] | None:
            query = urlencode({key: f"eq.{value}" for key, value in filters.items()})
            http_request = Request(
                f"{self._base_url}/rest/v1/{table}?{query}",
                headers={
                    "apikey": self._service_key,
                    "Authorization": f"Bearer {self._service_key}",
                },
            )
            with urlopen(http_request, timeout=5) as response:
                value = json.loads(response.read().decode("utf-8"))
            if not isinstance(value, list) or not value:
                return None
            return value[0] if isinstance(value[0], Mapping) else None

        return await asyncio.to_thread(request)


class QueryFake:
    def __init__(
        self,
        submission: Mapping[str, object] | None = None,
        skill_mappings: list[Mapping[str, object]] | None = None,
    ) -> None:
        self.submission = submission
        self.skill_mappings = skill_mappings or []

    async def select_one(
        self, table: str, filters: Mapping[str, object]
    ) -> Mapping[str, object] | None:
        if table == "submissions":
            return self.submission
        if table == "task_versions":
            return {
                "task_version_id": filters["task_version_id"],
                "skill_mappings": self.skill_mappings,
            }
        if table == "learner_progress":
            return {
                "learner_id": filters["learner_id"],
                "current_status": "ONBOARDING",
                "current_task_id": None,
                "version": 3,
                "updated_at": datetime.now(UTC).isoformat(),
                "reset_at": None,
            }
        return None


def outcome(task_version_id: UUID, submission_id: UUID) -> SubmissionOutcome:
    return SubmissionOutcome(
        submission_id=submission_id,
        attempt_id=uuid4(),
        attempt_number=1,
        evaluation=EvaluationResult(
            evaluator_id="eval-1",
            evaluator_version="1",
            task_version_id=task_version_id,
            passed=True,
            score=100,
            checks=[],
            errors=[],
            summary_ar="جيد",
            summary_en="Good",
            duration_ms=2,
        ),
        feedback=FeedbackResult(
            feedback_text="Good",
            language="en",
            persona_id="tarek",
            prompt_version="1",
            provider="eng-tarek",
            model="fallback",
            used_fallback=True,
            duration_ms=1,
        ),
        learner_status=LearnerStatus.ONBOARDING,
        task_status=TaskStatus.COMPLETED,
        skills=[],
    )


def test_submission_mapper_rejects_null_and_unknown_rows() -> None:
    learner_id = uuid4()
    row = submission_row(learner_id)
    row["status"] = None
    with pytest.raises(SupabasePersistenceError) as null_error:
        map_submission_row(row)
    assert null_error.value.code == "provider_payload_invalid"

    row = submission_row(learner_id)
    row["provider_private_field"] = "must not be accepted"
    with pytest.raises(SupabasePersistenceError) as unknown_error:
        map_submission_row(row)
    assert unknown_error.value.code == "provider_payload_invalid"


@pytest.mark.asyncio
async def test_reserve_calls_exact_rpc_with_typed_payload() -> None:
    learner_id, task_version_id, artifact_id = uuid4(), uuid4(), uuid4()
    rpc = RpcFake(Response(submission_row(learner_id)))
    repository = SupabaseSubmissionRepository(rpc)
    reservation = await repository.reserve(
        learner_id,
        task_version_id,
        artifact_id,
        Channel.WEB,
        "key-1",
        "a" * 64,
        120,
        "worker-1",
    )
    assert reservation.learner_id == learner_id
    assert rpc.calls == [
        (
            "reserve_submission",
            {
                "p_learner_id": str(learner_id),
                "p_task_version_id": str(task_version_id),
                "p_artifact_id": str(artifact_id),
                "p_channel": "web",
                "p_idempotency_key": "key-1",
                "p_request_fingerprint": "a" * 64,
                "p_lease_seconds": 120,
                "p_lease_owner": "worker-1",
            },
        )
    ]


@pytest.mark.asyncio
async def test_provider_error_is_mapped_without_leaking_details() -> None:
    rpc = RpcFake(Response(None, error={"message": "secret SQL details"}))
    repository = SupabaseSubmissionRepository(rpc)
    with pytest.raises(SupabasePersistenceError) as error:
        await repository.reserve(uuid4(), uuid4(), uuid4(), Channel.WEB, "key", "a" * 64, 30, "w")
    assert error.value.code == "supabase_provider_error"
    assert "secret" not in str(error.value)


@pytest.mark.asyncio
async def test_expire_calls_service_only_cas_rpc() -> None:
    rpc = RpcFake(Response(None))
    repository = SupabaseSubmissionRepository(rpc)
    learner_id = uuid4()
    await repository.expire(learner_id, "key-1", expected_version=4, lease_owner="worker-1")
    assert rpc.calls == [
        (
            "expire_submission",
            {
                "p_learner_id": str(learner_id),
                "p_idempotency_key": "key-1",
                "p_expected_version": 4,
                "p_lease_owner": "worker-1",
            },
        )
    ]


@pytest.mark.asyncio
async def test_expire_maps_stale_owner_or_version_without_leaking_provider_data() -> None:
    rpc = RpcFake(Response(None, error={"message": "stale CAS SQL detail"}))
    repository = SupabaseSubmissionRepository(rpc)
    with pytest.raises(SupabasePersistenceError) as error:
        await repository.expire(uuid4(), "key-1", expected_version=4, lease_owner="stale-worker")
    assert error.value.code == "supabase_provider_error"
    assert "stale CAS" not in str(error.value)


@pytest.mark.asyncio
async def test_expire_requires_owner_and_version_cas() -> None:
    repository = SupabaseSubmissionRepository(RpcFake(Response(None)))
    with pytest.raises(SupabasePersistenceError) as error:
        await repository.expire(uuid4(), "key-1")
    assert error.value.code == "lease_release_requires_cas"


@pytest.mark.asyncio
async def test_finalize_calls_exact_rpc_and_does_not_open_external_transaction() -> None:
    learner_id, task_version_id = uuid4(), uuid4()
    first = submission_row(learner_id)
    first["task_version_id"] = str(task_version_id)
    first["artifact_id"] = str(uuid4())
    rpc = RpcFake(Response(first))
    query = QueryFake(
        first,
        [{"skill_id": "communication", "check_id": "clarity", "weight": 3}],
    )
    repository = SupabaseSubmissionRepository(rpc, query)
    reservation = await repository.reserve(
        learner_id,
        task_version_id,
        UUID(str(first["artifact_id"])),
        Channel.WEB,
        "key-1",
        "a" * 64,
        120,
        "worker-1",
    )
    completed = dict(first)
    completed["status"] = "COMPLETED"
    rpc.response = Response(completed)
    # Finalization must load its reservation from the provider, not depend on
    # the in-process reserve cache (a fresh worker/UoW is a valid caller).
    repository = SupabaseSubmissionRepository(rpc, query)
    final_outcome = outcome(task_version_id, reservation.submission_id).model_copy(
        update={
            "evaluation": outcome(task_version_id, reservation.submission_id).evaluation.model_copy(
                update={
                    "checks": [
                        EvaluationCheck(check_id="clarity", passed=True, weight=3, details="clear")
                    ]
                }
            )
        }
    )
    await repository.finalize(
        reservation.reservation_id,
        reservation.version,
        "worker-1",
        final_outcome,
    )
    assert [call[0] for call in rpc.calls] == ["reserve_submission", "finalize_submission"]
    finalize_params = rpc.calls[-1][1]
    assert finalize_params["p_progress_expected_version"] == 3
    assert finalize_params["p_lease_owner"] == "worker-1"
    evidence = finalize_params["p_evidence"]
    assert isinstance(evidence, list)
    assert evidence[0]["skill_id"] == "communication"
    assert evidence[0]["check_id"] == "clarity"
    assert finalize_params["p_outbox"] == {
        "event_id": finalize_params["p_outbox"]["event_id"],
        "event_type": "submission.processed",
        "payload": {"submission_id": str(reservation.submission_id), "passed": True},
    }


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_supabase_contract_is_opt_in() -> None:
    base_url = os.getenv("SUPABASE_LOCAL_URL")
    if not base_url:
        pytest.skip("set SUPABASE_LOCAL_URL to run local Supabase integration tests")
    service_key = os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    if not service_key:
        pytest.skip("set SUPABASE_LOCAL_SERVICE_ROLE_KEY to run local Supabase integration tests")
    rest = LocalRest(base_url, service_key)
    learner_id, task_version_id, artifact_id = uuid4(), uuid4(), uuid4()
    run_id = uuid4().hex
    task_id = f"local-contract-task-{run_id}"
    skill_id = f"local-skill-{run_id}"
    idempotency_key = f"local-contract-{run_id}"
    await rest.insert(
        "learners",
        {
            "learner_id": str(learner_id),
            "display_name": "local-contract",
            "preferred_language": "en",
            "status": "ONBOARDING",
            "state_machine_version": "1",
        },
    )
    await rest.insert("tasks", {"task_id": task_id, "title": "Contract"})
    await rest.insert(
        "task_versions",
        {
            "task_version_id": str(task_version_id),
            "task_id": task_id,
            "version": "1",
            "instructions_ar": "تعليمات",
            "instructions_en": "Instructions",
            "artifact_schema": {},
            "evaluator_id": "eval-1",
            "evaluator_version": "1",
            "pass_threshold": 50,
            "skill_mappings": [{"skill_id": skill_id, "check_id": "clarity", "weight": 3}],
            "content_hash": "a" * 64,
            "status": "PUBLISHED",
        },
    )
    await rest.insert(
        "skill_definitions",
        {"skill_id": skill_id, "title": "Local", "description": "Local"},
    )
    await rest.insert(
        "artifacts",
        {
            "artifact_id": str(artifact_id),
            "learner_id": str(learner_id),
            "object_path": f"{learner_id}/{artifact_id}",
            "filename": "local.txt",
            "size_bytes": 1,
            "sha256": "b" * 64,
        },
    )
    await rest.insert(
        "learner_progress",
        {"learner_id": str(learner_id), "current_status": "ONBOARDING", "version": 1},
    )
    repository = SupabaseSubmissionRepository(LocalRpc(base_url, service_key), rest)
    reservation = await repository.reserve(
        learner_id,
        task_version_id,
        artifact_id,
        Channel.WEB,
        idempotency_key,
        "c" * 64,
        300,
        "local-worker",
    )
    active_duplicate = await repository.reserve(
        learner_id,
        task_version_id,
        artifact_id,
        Channel.TELEGRAM,
        idempotency_key,
        "c" * 64,
        300,
        "second-worker",
    )
    assert active_duplicate.submission_id == reservation.submission_id
    assert active_duplicate.lease_owner == reservation.lease_owner
    with pytest.raises(SupabasePersistenceError):
        await repository.reserve(
            learner_id,
            task_version_id,
            artifact_id,
            Channel.WEB,
            idempotency_key,
            "d" * 64,
            300,
            "second-worker",
        )
    base_outcome = outcome(task_version_id, reservation.submission_id)
    final = base_outcome.model_copy(
        update={
            "evaluation": base_outcome.evaluation.model_copy(
                update={
                    "checks": [
                        EvaluationCheck(check_id="clarity", passed=True, weight=3, details="ok")
                    ]
                }
            )
        }
    )
    await repository.finalize(
        reservation.reservation_id, reservation.version, "local-worker", final
    )
    replay = await repository.reserve(
        learner_id,
        task_version_id,
        artifact_id,
        Channel.WEB,
        idempotency_key,
        "c" * 64,
        300,
        "replay-worker",
    )
    assert replay.submission_id == reservation.submission_id
    assert replay.status.value == "COMPLETED"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_local_rls_owner_other_anonymous_and_service_boundaries() -> None:
    """Exercise the client boundary with real local JWTs when configured."""

    base_url = os.getenv("SUPABASE_LOCAL_URL")
    service_key = os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    anon_key = os.getenv("SUPABASE_LOCAL_ANON_KEY")
    owner_jwt = os.getenv("SUPABASE_LOCAL_OWNER_JWT")
    other_jwt = os.getenv("SUPABASE_LOCAL_OTHER_JWT")
    owner_subject = os.getenv("SUPABASE_LOCAL_OWNER_SUBJECT")
    if (
        not base_url
        or not service_key
        or not anon_key
        or not owner_jwt
        or not other_jwt
        or not owner_subject
    ):
        pytest.skip(
            "set SUPABASE_LOCAL_URL/service/anon keys and owner/other JWT subjects "
            "for authenticated RLS coverage"
        )

    rest = LocalRest(base_url, service_key)
    existing_identity = await rest.select_one(
        "external_identities", {"provider": "web", "provider_subject": owner_subject}
    )
    if existing_identity is None:
        learner_id = uuid4()
        await rest.insert(
            "learners",
            {
                "learner_id": str(learner_id),
                "display_name": "rls-owner",
                "preferred_language": "en",
                "status": "ONBOARDING",
                "state_machine_version": "1",
            },
        )
        await rest.insert(
            "external_identities",
            {
                "learner_id": str(learner_id),
                "provider": "web",
                "provider_subject": owner_subject,
            },
        )
    else:
        try:
            learner_id = UUID(str(existing_identity["learner_id"]))
        except (KeyError, TypeError, ValueError) as error:
            pytest.fail(f"existing owner identity has invalid learner mapping: {error}")
    artifact_id = uuid4()
    await rest.insert(
        "artifacts",
        {
            "artifact_id": str(artifact_id),
            "learner_id": str(learner_id),
            "object_path": f"{learner_id}/{artifact_id}",
            "filename": "rls.txt",
            "size_bytes": 1,
            "sha256": "d" * 64,
        },
    )

    def status_and_json(
        path: str, *, key: str, token: str, method: str = "GET"
    ) -> tuple[int, object]:
        request = Request(
            f"{base_url.rstrip('/')}{path}",
            data=b"{}" if method == "POST" else None,
            headers={"apikey": key, "Authorization": f"Bearer {token}"},
            method=method,
        )
        try:
            with urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8")
                return response.status, json.loads(body) if body else None
        except HTTPError as error:
            error.read()
            return error.code, None

    path = f"/rest/v1/artifacts?select=artifact_id&artifact_id=eq.{artifact_id}"
    owner_status, owner_rows = await asyncio.to_thread(
        status_and_json, path, key=anon_key, token=owner_jwt
    )
    assert owner_status == 200
    assert owner_rows == [{"artifact_id": str(artifact_id)}]
    other_status, other_rows = await asyncio.to_thread(
        status_and_json, path, key=anon_key, token=other_jwt
    )
    assert other_status == 200
    assert other_rows == []
    anonymous_status, _ = await asyncio.to_thread(
        status_and_json, path, key=anon_key, token=anon_key
    )
    assert anonymous_status in {401, 403}

    rpc_status, _ = await asyncio.to_thread(
        status_and_json,
        "/rest/v1/rpc/reserve_artifact",
        key=anon_key,
        token=owner_jwt,
        method="POST",
    )
    assert rpc_status in {401, 403, 404, 405}
    queue_status, _ = await asyncio.to_thread(
        status_and_json,
        "/rest/v1/artifact_cleanup_queue?select=cleanup_id",
        key=anon_key,
        token=owner_jwt,
    )
    assert queue_status in {401, 403, 404}
