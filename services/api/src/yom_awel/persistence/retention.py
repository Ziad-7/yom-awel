"""Provider-neutral artifact retention workflow.

The production Supabase adapter calls the migration's claim/finalize RPCs;
this small in-memory implementation makes lease, retry, tombstone, and audit
semantics testable without a database or cloud credentials.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol, cast
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

PurgeStatus = Literal["ACTIVE", "CLAIMED", "PURGE_FAILED", "PURGED"]
AuditAction = Literal[
    "PURGE_CLAIMED",
    "PURGED",
    "PURGE_FAILED",
    "DELETE_REQUESTED",
    "ANONYMOUS_RECONCILED",
]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(frozen=True)
class RetentionArtifact:
    artifact_id: UUID
    learner_id: UUID
    object_path: str
    retention_expires_at: datetime
    purge_status: PurgeStatus = "ACTIVE"
    purge_lease_owner: str | None = None
    purge_lease_expires_at: datetime | None = None
    purged_at: datetime | None = None


@dataclass(frozen=True)
class RetentionAudit:
    audit_id: UUID
    artifact_id: UUID | None
    learner_id: UUID | None
    action: AuditAction
    actor_id: str
    requested_learner_id: UUID | None = None
    details: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class RetentionStore(Protocol):
    async def claim_expired(
        self, now: datetime, owner: str, lease_seconds: int, limit: int
    ) -> list[RetentionArtifact]: ...

    async def finalize_purge(
        self,
        artifact_id: UUID,
        owner: str,
        deleted: bool,
        details: dict[str, str],
        now: datetime | None = None,
    ) -> RetentionArtifact: ...

    async def request_deletion(self, learner_id: UUID, actor_id: str, now: datetime) -> None: ...

    async def reconcile_anonymous(self, learner_id: UUID, actor_id: str, now: datetime) -> bool: ...


class ObjectDeleter(Protocol):
    async def delete(self, object_path: str) -> None: ...


class SupabaseRetentionError(RuntimeError):
    """Sanitized provider error for server-only retention operations."""

    def __init__(self, code: str = "supabase_provider_error") -> None:
        super().__init__(code)
        self.code = code


class SupabaseRpc(Protocol):
    async def rpc(self, function: str, params: Mapping[str, object]) -> object: ...


def _rpc_payload(response: object) -> object:
    """Extract a transport response without leaking provider error details."""

    error = getattr(response, "error", None)
    if error is not None:
        raise SupabaseRetentionError()
    return getattr(response, "data", response)


def _as_row(value: object) -> Mapping[str, object]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    raise SupabaseRetentionError("provider_payload_invalid")


def _as_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise SupabaseRetentionError("provider_payload_invalid")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SupabaseRetentionError("provider_payload_invalid") from exc
    return _utc(parsed)


def _map_retention_artifact(value: object) -> RetentionArtifact:
    row = _as_row(value)
    try:
        return RetentionArtifact(
            artifact_id=UUID(str(row["artifact_id"])),
            learner_id=UUID(str(row["learner_id"])),
            object_path=str(row["object_path"]),
            retention_expires_at=_as_datetime(row["retention_expires_at"]),
            purge_status=cast(PurgeStatus, str(row.get("purge_status", "CLAIMED"))),
            purge_lease_owner=(
                str(row["purge_lease_owner"]) if row.get("purge_lease_owner") else None
            ),
            purge_lease_expires_at=(
                _as_datetime(row["purge_lease_expires_at"])
                if row.get("purge_lease_expires_at")
                else None
            ),
            purged_at=(
                _as_datetime(row["purged_at"]) if row.get("purged_at") else None
            ),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SupabaseRetentionError("provider_payload_invalid") from exc


class SupabaseRetentionStore:
    """Production retention row store backed by service-only Postgres RPCs."""

    def __init__(self, rpc: SupabaseRpc) -> None:
        self._rpc = rpc

    async def claim_expired(
        self, now: datetime, owner: str, lease_seconds: int, limit: int
    ) -> list[RetentionArtifact]:
        try:
            response = await self._rpc.rpc(
                "claim_expired_artifacts",
                {"p_limit": limit, "p_lease_owner": owner, "p_lease_seconds": lease_seconds},
            )
            payload = _rpc_payload(response)
            if payload is None:
                return []
            if not isinstance(payload, list):
                raise SupabaseRetentionError("provider_payload_invalid")
            return [_map_retention_artifact(item) for item in payload]
        except SupabaseRetentionError:
            raise
        except Exception as exc:
            raise SupabaseRetentionError() from exc

    async def finalize_purge(
        self,
        artifact_id: UUID,
        owner: str,
        deleted: bool,
        details: dict[str, str],
        now: datetime | None = None,
    ) -> RetentionArtifact:
        try:
            response = await self._rpc.rpc(
                "finalize_artifact_purge",
                {
                    "p_artifact_id": str(artifact_id),
                    "p_lease_owner": owner,
                    "p_deleted": deleted,
                    "p_details": details,
                },
            )
            return _map_retention_artifact(_rpc_payload(response))
        except SupabaseRetentionError:
            raise
        except Exception as exc:
            raise SupabaseRetentionError() from exc

    async def request_deletion(self, learner_id: UUID, actor_id: str, now: datetime) -> None:
        try:
            response = await self._rpc.rpc(
                "request_learner_deletion",
                {
                    "p_learner_id": str(learner_id),
                    "p_requested_by": actor_id,
                },
            )
            _rpc_payload(response)
        except SupabaseRetentionError:
            raise
        except Exception as exc:
            raise SupabaseRetentionError() from exc

    async def reconcile_anonymous(self, learner_id: UUID, actor_id: str, now: datetime) -> bool:
        try:
            response = await self._rpc.rpc(
                "erase_learner_application_data",
                {"p_learner_id": str(learner_id), "p_actor_id": actor_id},
            )
            payload = _rpc_payload(response)
            if isinstance(payload, list):
                payload = payload[0] if payload else False
            return bool(payload)
        except SupabaseRetentionError:
            raise
        except Exception as exc:
            raise SupabaseRetentionError() from exc

    async def claim_deletion_requests(
        self, owner: str, limit: int
    ) -> list[tuple[UUID, UUID, str]]:
        """Claim reconciled anonymous deletion requests for Auth cleanup.

        The RPC returns only UUIDs and the Auth subject; no provider payload is
        propagated to callers or logs.
        """

        try:
            response = await self._rpc.rpc(
                "claim_learner_deletion_requests",
                {"p_lease_owner": owner, "p_limit": limit},
            )
            payload = _rpc_payload(response)
            if payload is None:
                return []
            if not isinstance(payload, list):
                raise SupabaseRetentionError("provider_payload_invalid")
            claims: list[tuple[UUID, UUID, str]] = []
            for value in payload:
                row = _as_row(value)
                try:
                    claims.append(
                        (
                            UUID(str(row["request_id"])),
                            UUID(str(row["learner_id"])),
                            str(row["auth_user_id"]),
                        )
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise SupabaseRetentionError("provider_payload_invalid") from exc
            return claims
        except SupabaseRetentionError:
            raise
        except Exception as exc:
            raise SupabaseRetentionError() from exc

    async def finalize_deletion_request(
        self, request_id: UUID, owner: str, success: bool
    ) -> None:
        try:
            response = await self._rpc.rpc(
                "finalize_learner_deletion_request",
                {
                    "p_request_id": str(request_id),
                    "p_lease_owner": owner,
                    "p_success": success,
                },
            )
            _rpc_payload(response)
        except SupabaseRetentionError:
            raise
        except Exception as exc:
            raise SupabaseRetentionError() from exc


class SupabaseObjectDeleter:
    """Service-role deleter for the private submissions bucket.

    A provider 404 is deliberately normalized to ``FileNotFoundError`` so a
    retry after a successful object delete is idempotent.
    """

    def __init__(self, base_url: str, service_role_key: str, bucket: str = "submissions") -> None:
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key
        self._bucket = bucket

    async def delete(self, object_path: str) -> None:
        parts = object_path.split("/")
        if len(parts) != 2:
            raise SupabaseRetentionError("invalid_object_path")
        try:
            UUID(parts[0])
            UUID(parts[1])
        except ValueError as exc:
            raise SupabaseRetentionError("invalid_object_path") from exc

        def request() -> None:
            http_request = Request(
                f"{self._base_url}/storage/v1/object/"
                f"{quote(self._bucket)}/{quote(object_path, safe='/')}",
                headers={
                    "apikey": self._service_role_key,
                    "Authorization": f"Bearer {self._service_role_key}",
                },
                method="DELETE",
            )
            try:
                with urlopen(http_request, timeout=15):
                    return
            except HTTPError as error:
                error.read()
                if error.code == 404:
                    raise FileNotFoundError(object_path) from error
                raise SupabaseRetentionError() from error
            except OSError as exc:
                raise SupabaseRetentionError() from exc

        await asyncio.to_thread(request)

    async def delete_object(self, object_path: str) -> None:
        """Explicit object-named alias for storage adapter callers."""

        await self.delete(object_path)


class SupabaseAuthAdminClient:
    """Minimal Supabase Auth admin API client with safe, idempotent deletes."""

    def __init__(self, base_url: str, service_role_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_role_key = service_role_key

    async def delete_user(self, user_id: UUID | str) -> None:
        user_text = str(user_id)
        try:
            UUID(user_text)
        except ValueError as exc:
            raise SupabaseRetentionError("invalid_auth_user_id") from exc

        def request() -> None:
            http_request = Request(
                f"{self._base_url}/auth/v1/admin/users/{quote(user_text, safe='')}",
                headers={
                    "apikey": self._service_role_key,
                    "Authorization": f"Bearer {self._service_role_key}",
                },
                method="DELETE",
            )
            try:
                with urlopen(http_request, timeout=15):
                    return
            except HTTPError as error:
                error.read()
                if error.code == 404:
                    return
                raise SupabaseRetentionError() from error
            except OSError as exc:
                raise SupabaseRetentionError() from exc

        await asyncio.to_thread(request)

    async def delete_anonymous_user(self, user_id: UUID | str) -> None:
        """Delete an anonymous user; 404 remains idempotent."""

        await self.delete_user(user_id)


class LocalObjectDeleter:
    """Delete generated paths below a configured local artifact root."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()

    async def delete(self, object_path: str) -> None:
        path = (self.root / object_path).resolve()
        if self.root not in path.parents:
            raise ValueError("artifact path escapes retention root")
        path.unlink()


class InMemoryRetentionStore:
    def __init__(self, artifacts: list[RetentionArtifact] | None = None) -> None:
        self.artifacts = {item.artifact_id: item for item in artifacts or []}
        self.audit_log: list[RetentionAudit] = []
        self.deletion_requests: dict[UUID, str] = {}
        self.reconciled_anonymous: set[UUID] = set()
        self._lock = asyncio.Lock()

    async def claim_expired(
        self, now: datetime, owner: str, lease_seconds: int, limit: int
    ) -> list[RetentionArtifact]:
        if lease_seconds <= 0 or limit < 1 or not owner:
            raise ValueError("owner, lease_seconds, and limit are required")
        current = _utc(now)
        claimed: list[RetentionArtifact] = []
        async with self._lock:
            candidates = sorted(
                self.artifacts.values(),
                key=lambda item: (item.retention_expires_at, str(item.artifact_id)),
            )
            for item in candidates:
                lease_expired = (
                    item.purge_lease_expires_at is None or item.purge_lease_expires_at <= current
                )
                eligible = item.retention_expires_at <= current and (
                    item.purge_status in ("ACTIVE", "PURGE_FAILED")
                    or (item.purge_status == "CLAIMED" and lease_expired)
                )
                if not eligible or len(claimed) >= limit:
                    continue
                updated = replace(
                    item,
                    purge_status="CLAIMED",
                    purge_lease_owner=owner,
                    purge_lease_expires_at=current + timedelta(seconds=lease_seconds),
                )
                self.artifacts[item.artifact_id] = updated
                claimed.append(updated)
                self.audit_log.append(
                    RetentionAudit(
                        audit_id=uuid4(),
                        artifact_id=item.artifact_id,
                        learner_id=item.learner_id,
                        action="PURGE_CLAIMED",
                        actor_id=owner,
                        requested_learner_id=item.learner_id,
                        created_at=current,
                    )
                )
        return claimed

    async def finalize_purge(
        self,
        artifact_id: UUID,
        owner: str,
        deleted: bool,
        details: dict[str, str],
        now: datetime | None = None,
    ) -> RetentionArtifact:
        async with self._lock:
            item = self.artifacts[artifact_id]
            current = _utc(now or datetime.now(UTC))
            if (
                item.purge_status != "CLAIMED"
                or item.purge_lease_owner != owner
                or item.purge_lease_expires_at is None
                or item.purge_lease_expires_at <= current
            ):
                raise RuntimeError("artifact purge lease conflict")
            updated = replace(
                item,
                purge_status="PURGED" if deleted else "PURGE_FAILED",
                purge_lease_owner=None,
                purge_lease_expires_at=None,
                purged_at=current if deleted else None,
            )
            self.artifacts[artifact_id] = updated
            self.audit_log.append(
                RetentionAudit(
                    audit_id=uuid4(),
                    artifact_id=artifact_id,
                    learner_id=item.learner_id,
                    action="PURGED" if deleted else "PURGE_FAILED",
                    actor_id=owner,
                    requested_learner_id=item.learner_id,
                    details=dict(details),
                    created_at=current,
                )
            )
            return updated

    async def request_deletion(self, learner_id: UUID, actor_id: str, now: datetime) -> None:
        async with self._lock:
            self.deletion_requests[learner_id] = actor_id
            self.audit_log.append(
                RetentionAudit(
                    audit_id=uuid4(),
                    artifact_id=None,
                    learner_id=learner_id,
                    action="DELETE_REQUESTED",
                    actor_id=actor_id,
                    requested_learner_id=learner_id,
                    created_at=_utc(now),
                )
            )

    async def reconcile_anonymous(self, learner_id: UUID, actor_id: str, now: datetime) -> bool:
        async with self._lock:
            rows = [item for item in self.artifacts.values() if item.learner_id == learner_id]
            if any(item.purge_status != "PURGED" for item in rows):
                return False
            self.reconciled_anonymous.add(learner_id)
            self.audit_log.append(
                RetentionAudit(
                    audit_id=uuid4(),
                    artifact_id=None,
                    learner_id=learner_id,
                    action="ANONYMOUS_RECONCILED",
                    actor_id=actor_id,
                    requested_learner_id=learner_id,
                    created_at=_utc(now),
                )
            )
            return True


@dataclass(frozen=True)
class RetentionRun:
    claimed: int
    purged: int
    failed: int


class RetentionService:
    def __init__(
        self,
        store: RetentionStore,
        deleter: ObjectDeleter,
        cleanup_worker: ArtifactCleanupService | None = None,
    ):
        self.store = store
        self.deleter = deleter
        self.cleanup_worker = cleanup_worker

    async def run_once(
        self, now: datetime, owner: str, limit: int = 100, lease_seconds: int = 300
    ) -> RetentionRun:
        # Reconcile orphaned queue entries before touching rows that are still
        # part of the normal retention lifecycle.  A dangling object must not
        # be mistaken for a live artifact during the same bounded run.
        if self.cleanup_worker is not None:
            await self.cleanup_worker.run_once(now, owner, limit, lease_seconds)
        rows = await self.store.claim_expired(now, owner, lease_seconds, limit)
        purged = 0
        failed = 0
        for row in rows:
            try:
                await self.deleter.delete(row.object_path)
            except FileNotFoundError:
                await self.store.finalize_purge(
                    row.artifact_id,
                    owner,
                    True,
                    {"result": "missing_object_idempotent"},
                    now=now,
                )
                purged += 1
            except Exception as error:  # noqa: BLE001
                await self.store.finalize_purge(
                    row.artifact_id,
                    owner,
                    False,
                    {"error": type(error).__name__, "result": "retryable"},
                    now=now,
                )
                failed += 1
            else:
                await self.store.finalize_purge(row.artifact_id, owner, True, {}, now=now)
                purged += 1
        return RetentionRun(claimed=len(rows), purged=purged, failed=failed)

    async def request_learner_deletion(
        self, learner_id: UUID, actor_id: str, now: datetime
    ) -> None:
        await self.store.request_deletion(learner_id, actor_id, now)

    async def reconcile_anonymous_learner(
        self, learner_id: UUID, actor_id: str, now: datetime
    ) -> bool:
        return await self.store.reconcile_anonymous(learner_id, actor_id, now)


@dataclass(frozen=True)
class CleanupArtifact:
    cleanup_id: UUID
    learner_id: UUID
    artifact_id: UUID
    object_path: str
    attempts: int = 0
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None


class CleanupQueueStore(Protocol):
    async def claim_pending(
        self, now: datetime, owner: str, lease_seconds: int, limit: int
    ) -> list[CleanupArtifact]: ...

    async def finalize_cleanup(
        self, cleanup_id: UUID, owner: str, deleted: bool, now: datetime
    ) -> None: ...


@dataclass(frozen=True)
class CleanupRun:
    claimed: int
    resolved: int
    failed: int


class InMemoryCleanupQueue:
    """Lease-safe cleanup queue used by local mode and deterministic tests."""

    def __init__(self, entries: list[CleanupArtifact] | None = None) -> None:
        self.entries = {item.cleanup_id: item for item in entries or []}
        self.resolved: set[UUID] = set()
        self._lock = asyncio.Lock()

    async def claim_pending(
        self, now: datetime, owner: str, lease_seconds: int, limit: int
    ) -> list[CleanupArtifact]:
        if not owner or lease_seconds <= 0 or limit < 1:
            raise ValueError("owner, lease_seconds, and limit are required")
        current = _utc(now)
        claimed: list[CleanupArtifact] = []
        async with self._lock:
            for item in sorted(self.entries.values(), key=lambda value: str(value.cleanup_id)):
                if item.cleanup_id in self.resolved:
                    continue
                lease_expired = item.lease_expires_at is None or item.lease_expires_at <= current
                if item.lease_owner is not None and not lease_expired:
                    continue
                updated = replace(
                    item,
                    attempts=item.attempts + 1,
                    lease_owner=owner,
                    lease_expires_at=current + timedelta(seconds=lease_seconds),
                )
                self.entries[item.cleanup_id] = updated
                claimed.append(updated)
                if len(claimed) == limit:
                    break
        return claimed

    async def finalize_cleanup(
        self, cleanup_id: UUID, owner: str, deleted: bool, now: datetime
    ) -> None:
        async with self._lock:
            item = self.entries[cleanup_id]
            current = _utc(now)
            if (
                item.lease_owner != owner
                or item.lease_expires_at is None
                or item.lease_expires_at <= current
            ):
                raise RuntimeError("cleanup lease conflict")
            if deleted:
                self.resolved.add(cleanup_id)
            self.entries[cleanup_id] = replace(item, lease_owner=None, lease_expires_at=None)


class ArtifactCleanupService:
    def __init__(self, queue: CleanupQueueStore, deleter: ObjectDeleter):
        self.queue = queue
        self.deleter = deleter

    async def run_once(
        self, now: datetime, owner: str, limit: int = 100, lease_seconds: int = 300
    ) -> CleanupRun:
        rows = await self.queue.claim_pending(now, owner, lease_seconds, limit)
        resolved = 0
        failed = 0
        for row in rows:
            try:
                await self.deleter.delete(row.object_path)
            except FileNotFoundError:
                await self.queue.finalize_cleanup(row.cleanup_id, owner, True, now)
                resolved += 1
            except Exception:  # noqa: BLE001
                await self.queue.finalize_cleanup(row.cleanup_id, owner, False, now)
                failed += 1
            else:
                await self.queue.finalize_cleanup(row.cleanup_id, owner, True, now)
                resolved += 1
        return CleanupRun(claimed=len(rows), resolved=resolved, failed=failed)
