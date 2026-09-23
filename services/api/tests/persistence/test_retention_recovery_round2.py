from __future__ import annotations

import asyncio
import importlib.util
import io
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.error import HTTPError
from uuid import UUID, uuid4

import pytest

from yom_awel.application.composition import (
    OpportunisticRetentionCleanup,
    create_submission_processor,
)
from yom_awel.application.submissions import _run_post_commit_cleanup
from yom_awel.persistence import retention as retention_module
from yom_awel.persistence.retention import (
    ArtifactCleanupService,
    CleanupArtifact,
    CleanupRun,
    InMemoryCleanupQueue,
    InMemoryRetentionStore,
    RetentionArtifact,
    RetentionService,
    SupabaseAuthAdminClient,
    SupabaseObjectDeleter,
    SupabaseRetentionStore,
)

ROOT = Path(__file__).resolve().parents[4]
NOW = datetime(2026, 9, 23, 12, tzinfo=UTC)


@pytest.mark.asyncio
async def test_deletion_request_is_idempotent_under_concurrent_retries() -> None:
    learner_id = uuid4()
    store = InMemoryRetentionStore()
    await asyncio.gather(
        *(store.request_deletion(learner_id, "operator", NOW) for _ in range(8))
    )
    assert store.deletion_requests == {learner_id: "operator"}
    assert [event for event in store.audit_log if event.action == "DELETE_REQUESTED"]
    assert sum(event.action == "DELETE_REQUESTED" for event in store.audit_log) == 1


@pytest.mark.asyncio
async def test_retention_service_drains_orphans_before_expired_rows() -> None:
    calls: list[str] = []

    class Queue:
        async def claim_pending(self, now, owner, lease_seconds, limit):
            calls.append("orphans")
            return []

        async def finalize_cleanup(self, cleanup_id, owner, deleted, now):
            return None

    class Store:
        async def claim_expired(self, now, owner, lease_seconds, limit):
            calls.append("expired")
            return []

        async def finalize_purge(self, artifact_id, owner, deleted, details, now=None):
            raise AssertionError("no rows expected")

        async def request_deletion(self, learner_id, actor_id, now):
            return None

        async def reconcile_anonymous(self, learner_id, actor_id, now):
            return False

    await RetentionService(
        Store(),
        deleter=type("D", (), {"delete": lambda *_: None})(),
        cleanup_worker=ArtifactCleanupService(
            Queue(), type("D", (), {"delete": lambda *_: None})()
        ),
    ).run_once(NOW, "worker", 10, 30)
    assert calls == ["orphans", "expired"]


class _Response:
    error = None

    def __init__(self, data):
        self.data = data


class _Rpc:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    async def rpc(self, function, params):
        self.calls.append((function, params))
        return _Response(self.rows)


@pytest.mark.asyncio
async def test_supabase_retention_store_maps_claims_and_sanitizes_provider_errors() -> None:
    artifact_id, learner_id = uuid4(), uuid4()
    rpc = _Rpc(
        [
            {
                "artifact_id": str(artifact_id),
                "learner_id": str(learner_id),
                "object_path": f"{learner_id}/{artifact_id}",
                "retention_expires_at": "2026-09-22T00:00:00+00:00",
                "purge_status": "CLAIMED",
                "purge_lease_owner": "worker",
                "purge_lease_expires_at": "2026-09-23T12:05:00+00:00",
                "purged_at": None,
            }
        ]
    )
    rows = await SupabaseRetentionStore(rpc).claim_expired(NOW, "worker", 300, 10)
    assert rows[0].artifact_id == artifact_id
    assert rpc.calls[0][0] == "claim_expired_artifacts"

    class Broken:
        async def rpc(self, function, params):
            return type("R", (), {"error": {"message": "secret"}, "data": None})()

    with pytest.raises(retention_module.SupabaseRetentionError) as error:
        await SupabaseRetentionStore(Broken()).claim_expired(NOW, "worker", 300, 10)
    assert str(error.value) == "supabase_provider_error"


@pytest.mark.asyncio
async def test_storage_and_auth_404s_are_idempotent(monkeypatch) -> None:
    def missing(request, timeout):
        raise HTTPError(request.full_url, 404, "missing", {}, io.BytesIO())

    monkeypatch.setattr(retention_module, "urlopen", missing)

    async def direct(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(retention_module.asyncio, "to_thread", direct)
    learner_id, artifact_id = uuid4(), uuid4()
    await SupabaseObjectDeleter("https://example.test", "service").delete(
        f"{learner_id}/{artifact_id}"
    )
    await SupabaseAuthAdminClient("https://example.test", "service").delete_user(uuid4())


def test_forward_migration_has_deterministic_recovery_contract() -> None:
    sql = (ROOT / "supabase/migrations/20260923140000_retention_recovery.sql").read_text()
    assert "set is_anonymous = (provider = 'web')" in sql
    assert "anonymous Auth identity required" in sql
    assert "auth_deleted_at timestamptz" in sql
    assert "r.status in ('REQUESTED', 'FAILED', 'RECONCILED')" in sql
    assert "r.status = 'CLAIMED'" in sql
    assert "r.lease_expires_at <= timezone('utc', now())" in sql
    assert "for update skip locked" in sql
    assert "lease_expires_at > timezone('utc', now())" in sql
    assert "on conflict (requested_learner_id) do update" in sql
    assert "md5('retention-audit:' || audit_id::text)::uuid" in sql
    assert "row_number() over" in sql
    assert "drop constraint if exists artifact_cleanup_queue_learner_id_fkey" in sql
    assert "delete from public.outbox_events where aggregate_id = p_learner_id" in sql
    order = [
        "delete from public.skill_evidence",
        "delete from public.attempts",
        "delete from public.evaluation_results",
        "delete from public.feedback_results",
        "delete from public.submissions",
        "delete from public.outbox_events",
        "delete from public.learners",
    ]
    positions = [sql.index(item) for item in order]
    assert positions == sorted(positions)


def test_script_bounds_and_reports_failures(monkeypatch) -> None:
    script_path = ROOT / "services/api/scripts/purge_expired_artifacts.py"
    spec = importlib.util.spec_from_file_location("purge_expired_artifacts", script_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setenv("SUPABASE_URL", "https://example.test")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")

    async def failed(*args, **kwargs):
        return CleanupRun(claimed=1, resolved=0, failed=1)

    monkeypatch.setattr(module, "_run_cleanup", failed)
    assert module.main(["--cleanup-queue", "--limit", "100"]) == 1
    with pytest.raises(SystemExit):
        module.main(["--cleanup-queue", "--limit", "101"])


def test_composition_injects_bounded_post_commit_cleanup() -> None:
    class Runner:
        async def run_once(self, now, owner, limit, lease_seconds):
            UUID(owner)
            assert limit == 7
            assert lease_seconds == 11

    cleanup = OpportunisticRetentionCleanup(Runner(), batch_limit=7, lease_seconds=11)
    asyncio.run(cleanup(NOW))
    processor = create_submission_processor(
        lambda: None, object(), object(), object(), object(), retention_runner=Runner()
    )
    assert processor.post_commit_cleanup is not None


@pytest.mark.asyncio
async def test_post_commit_cleanup_failure_is_isolated() -> None:
    async def failing(now):
        raise RuntimeError("provider details must not escape")

    # This helper is invoked only after the submission transaction commits.
    await _run_post_commit_cleanup(failing, NOW)
