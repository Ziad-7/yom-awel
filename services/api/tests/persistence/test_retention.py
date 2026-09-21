from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from yom_awel.persistence.retention import (
    ArtifactCleanupService,
    CleanupArtifact,
    InMemoryCleanupQueue,
    InMemoryRetentionStore,
    RetentionArtifact,
    RetentionService,
)

NOW = datetime(2026, 9, 21, 12, tzinfo=UTC)


class FakeDeleter:
    def __init__(self, missing: set[str] | None = None, failures: set[str] | None = None):
        self.missing = missing or set()
        self.failures = failures or set()
        self.deleted: list[str] = []

    async def delete(self, object_path: str) -> None:
        if object_path in self.missing:
            raise FileNotFoundError(object_path)
        if object_path in self.failures:
            raise OSError("storage unavailable")
        self.deleted.append(object_path)


def _artifact(expires: datetime, path: str = "learner/artifact") -> RetentionArtifact:
    return RetentionArtifact(uuid4(), uuid4(), path, expires)


@pytest.mark.asyncio
async def test_unexpired_artifact_is_not_deleted() -> None:
    artifact = _artifact(NOW + timedelta(days=1))
    store = InMemoryRetentionStore([artifact])
    deleter = FakeDeleter()
    result = await RetentionService(store, deleter).run_once(NOW, "worker")
    assert result.claimed == 0 and result.purged == 0 and result.failed == 0
    assert deleter.deleted == []
    assert store.artifacts[artifact.artifact_id].purge_status == "ACTIVE"


@pytest.mark.asyncio
async def test_missing_object_is_idempotently_purged_and_audited() -> None:
    artifact = _artifact(NOW - timedelta(days=1))
    store = InMemoryRetentionStore([artifact])
    service = RetentionService(store, FakeDeleter(missing={artifact.object_path}))
    result = await service.run_once(NOW, "worker")
    assert result.claimed == 1 and result.purged == 1 and result.failed == 0
    assert store.artifacts[artifact.artifact_id].purge_status == "PURGED"
    assert any(item.action == "PURGED" for item in store.audit_log)


@pytest.mark.asyncio
async def test_failed_delete_is_retryable() -> None:
    artifact = _artifact(NOW - timedelta(days=1))
    store = InMemoryRetentionStore([artifact])
    deleter = FakeDeleter(failures={artifact.object_path})
    service = RetentionService(store, deleter)
    result = await service.run_once(NOW, "worker")
    assert result.failed == 1
    assert store.artifacts[artifact.artifact_id].purge_status == "PURGE_FAILED"
    assert any(item.action == "PURGE_FAILED" for item in store.audit_log)

    deleter.failures.clear()
    result = await service.run_once(NOW + timedelta(minutes=1), "worker")
    assert result.purged == 1
    assert store.artifacts[artifact.artifact_id].purge_status == "PURGED"


@pytest.mark.asyncio
async def test_concurrent_claims_are_exclusive() -> None:
    artifact = _artifact(NOW - timedelta(days=1))
    store = InMemoryRetentionStore([artifact])
    first, second = await asyncio.gather(
        store.claim_expired(NOW, "one", 60, 1),
        store.claim_expired(NOW, "two", 60, 1),
    )
    assert len(first) == 1
    assert second == []


@pytest.mark.asyncio
async def test_stale_finalizer_after_expiry_and_reclaim_is_rejected() -> None:
    artifact = _artifact(NOW - timedelta(days=1))
    store = InMemoryRetentionStore([artifact])
    first = await store.claim_expired(NOW, "one", 60, 1)
    assert len(first) == 1
    reclaimed = await store.claim_expired(NOW + timedelta(seconds=61), "two", 60, 1)
    assert len(reclaimed) == 1
    with pytest.raises(RuntimeError):
        await store.finalize_purge(
            artifact.artifact_id, "one", True, {}, now=NOW + timedelta(seconds=61)
        )
    finalized = await store.finalize_purge(
        artifact.artifact_id, "two", True, {}, now=NOW + timedelta(seconds=61)
    )
    assert finalized.purge_status == "PURGED"


@pytest.mark.asyncio
async def test_expired_lease_cannot_finalize_without_reclaim() -> None:
    artifact = _artifact(NOW - timedelta(days=1))
    store = InMemoryRetentionStore([artifact])
    await store.claim_expired(NOW, "one", 60, 1)
    with pytest.raises(RuntimeError):
        await store.finalize_purge(
            artifact.artifact_id, "one", True, {}, now=NOW + timedelta(seconds=61)
        )


@pytest.mark.asyncio
async def test_claim_rejects_invalid_parameters() -> None:
    store = InMemoryRetentionStore()
    with pytest.raises(ValueError):
        await store.claim_expired(NOW, "", 60, 1)
    with pytest.raises(ValueError):
        await store.claim_expired(NOW, "worker", 0, 1)
    with pytest.raises(ValueError):
        await store.claim_expired(NOW, "worker", 60, 0)


@pytest.mark.asyncio
async def test_deletion_request_requires_reconciliation_before_anonymous_cleanup() -> None:
    learner_id = uuid4()
    artifact = RetentionArtifact(
        uuid4(), learner_id, f"{learner_id}/artifact", NOW - timedelta(days=1)
    )
    store = InMemoryRetentionStore([artifact])
    service = RetentionService(store, FakeDeleter(missing={artifact.object_path}))
    await service.request_learner_deletion(learner_id, "admin", NOW)
    assert await service.reconcile_anonymous_learner(learner_id, "admin", NOW) is False
    await service.run_once(NOW, "worker")
    assert await service.reconcile_anonymous_learner(learner_id, "admin", NOW) is True
    assert learner_id in store.reconciled_anonymous
    assert [item.action for item in store.audit_log].count("DELETE_REQUESTED") == 1
    assert [item.action for item in store.audit_log].count("ANONYMOUS_RECONCILED") == 1


@pytest.mark.asyncio
async def test_cleanup_worker_resolves_missing_object_and_retries_failures() -> None:
    entry = CleanupArtifact(uuid4(), uuid4(), uuid4(), "learner/artifact")
    queue = InMemoryCleanupQueue([entry])
    deleter = FakeDeleter(missing={entry.object_path})
    result = await ArtifactCleanupService(queue, deleter).run_once(NOW, "worker")
    assert result == type(result)(claimed=1, resolved=1, failed=0)
    assert entry.cleanup_id in queue.resolved

    failed_entry = CleanupArtifact(uuid4(), uuid4(), uuid4(), "learner/failed")
    retry_queue = InMemoryCleanupQueue([failed_entry])
    retry_deleter = FakeDeleter(failures={failed_entry.object_path})
    service = ArtifactCleanupService(retry_queue, retry_deleter)
    failed = await service.run_once(NOW, "worker")
    assert failed.failed == 1
    retry_deleter.failures.clear()
    recovered = await service.run_once(NOW + timedelta(minutes=1), "worker")
    assert recovered.resolved == 1


@pytest.mark.asyncio
async def test_cleanup_stale_owner_cannot_finalize_reclaimed_lease() -> None:
    entry = CleanupArtifact(uuid4(), uuid4(), uuid4(), "learner/stale")
    queue = InMemoryCleanupQueue([entry])
    first = await queue.claim_pending(NOW, "one", 30, 1)
    assert len(first) == 1
    reclaimed = await queue.claim_pending(NOW + timedelta(seconds=31), "two", 30, 1)
    assert len(reclaimed) == 1
    with pytest.raises(RuntimeError):
        await queue.finalize_cleanup(entry.cleanup_id, "one", True, NOW + timedelta(seconds=31))


def test_migration_security_static_contract() -> None:
    root = Path(__file__).resolve().parents[4]
    migration = next((root / "supabase" / "migrations").glob("*_platform_schema.sql"))
    sql = migration.read_text(encoding="utf-8")
    release_migration = next((root / "supabase" / "migrations").glob("*_release_submission.sql"))
    release_sql = release_migration.read_text(encoding="utf-8")
    cleanup_migration = next(
        (root / "supabase" / "migrations").glob("*_artifact_cleanup_recovery.sql")
    )
    cleanup_sql = cleanup_migration.read_text(encoding="utf-8")
    tables = (
        "learners",
        "external_identities",
        "tasks",
        "task_versions",
        "artifacts",
        "submissions",
        "evaluation_results",
        "feedback_results",
        "attempts",
        "skill_definitions",
        "skill_evidence",
        "learner_progress",
        "outbox_events",
        "retention_audit",
        "learner_deletion_requests",
    )
    for table in tables:
        assert f"'{table}'" in sql
    assert "alter table public.%I enable row level security" in sql
    assert "using (learner_id = (select public.current_learner_id()))" in sql
    assert "values ('submissions', 'submissions', false, 5242880)" in sql
    assert "set search_path = public, pg_temp" in sql
    assert "revoke all on function public.reserve_submission" in sql
    assert "revoke all on function public.current_learner_id() from public, anon" in sql
    assert "grant execute on function public.reserve_submission" in sql
    assert "create policy artifacts_insert_own" not in sql
    assert "create policy artifacts_update_own" not in sql
    assert "for update to authenticated" not in sql
    assert "create policy submission_objects_insert_own" not in sql
    assert "create policy submission_objects_delete_own" not in sql
    for function in (
        "reserve_submission",
        "finalize_submission",
        "claim_expired_artifacts",
        "finalize_artifact_purge",
    ):
        assert f"revoke all on function public.{function}" in sql
        assert f"grant execute on function public.{function}" in sql
    assert sql.count("set search_path = public, pg_temp") >= 3
    assert "create or replace function public.expire_submission" in release_sql
    assert "set search_path = public, pg_temp" in release_sql
    assert "revoke all on function public.expire_submission" in release_sql
    assert "grant execute on function public.expire_submission" in release_sql
    assert "p_expected_version" in release_sql
    assert "p_lease_owner" in release_sql
    assert "from public, anon, authenticated" in release_sql
    assert "create table public.artifact_cleanup_queue" in cleanup_sql
    assert "grant select on public.artifacts to authenticated" in cleanup_sql
    assert "object_path = learner_id::text || '/' || artifact_id::text" in cleanup_sql
    for function in (
        "enqueue_artifact_cleanup",
        "resolve_artifact_cleanup",
        "finalize_artifact_cleanup",
        "tombstone_artifact",
        "claim_artifact_cleanup",
        "release_artifact_cleanup",
        "reserve_artifact",
        "prepare_artifact_delete",
        "activate_artifact",
    ):
        assert "set search_path = public, pg_temp" in cleanup_sql
        assert f"revoke all on function public.{function}" in cleanup_sql
        assert f"grant execute on function public.{function}" in cleanup_sql
    assert (
        "revoke all on table public.artifact_cleanup_queue from anon, authenticated" in cleanup_sql
    )
    assert "for update skip locked" in cleanup_sql
    assert "purge_status = 'ACTIVE'" in cleanup_sql
    assert (
        "purge_status in ('ACTIVE', 'UPLOADING', 'CLAIMED', 'PURGE_FAILED', 'PURGED')"
        in cleanup_sql
    )
    assert "'created', false" in cleanup_sql
    assert "purge_status = 'UPLOADING'" in cleanup_sql
    assert "p_upload_owner text" in cleanup_sql
    assert "p_upload_lease_seconds integer" in cleanup_sql
    assert "purge_lease_owner = p_upload_owner" in cleanup_sql
    assert "purge_lease_expires_at > timezone('utc', now())" in cleanup_sql
    assert "not exists (" in cleanup_sql
    assert "reserve_artifact(uuid, uuid, text, text, bigint, text, text, integer)" in cleanup_sql
    assert "activate_artifact(uuid, uuid, text)" in cleanup_sql

    workflow = (root / ".github" / "workflows" / "retention.yml").read_text(encoding="utf-8")
    assert "actions/checkout@v7" in workflow
    assert 'cron: "17 3 * * *"' in workflow
    assert "workflow_dispatch" in workflow
    assert "astral-sh/setup-uv@v10" in workflow
    assert "SUPABASE_URL: ${{ secrets.SUPABASE_URL }}" in workflow
    assert "SUPABASE_SERVICE_ROLE_KEY: ${{ secrets.SUPABASE_SERVICE_ROLE_KEY }}" in workflow
    assert "--cleanup-queue" in workflow
    assert "--dry-run" not in workflow
    assert "workflow_dispatch:" in workflow
    assert "contents: read" in workflow
    assert "deploy" not in workflow.lower()

    config = (root / "supabase" / "config.toml").read_text(encoding="utf-8")
    assert 'file_size_limit = "5MiB"' in config
    assert "[storage.s3_protocol]\nenabled = false" in config
    assert "[analytics]\nenabled = false" in config
    assert "[storage.vector]\nenabled = false" in config
    assert "[realtime]\nenabled = false" in config
    assert "[studio]\nenabled = false" in config
    assert "[edge_runtime]\nenabled = false" in config
    assert "[experimental.pgdelta]\nenabled = false" in config
