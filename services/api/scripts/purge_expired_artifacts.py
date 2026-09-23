"""Bounded production entry point for artifact retention and orphan cleanup.

The workflow supplies credentials only through the process environment. This
module never prints them and performs a safe no-op when server-only
configuration is absent (for local development and forked CI).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

from yom_awel.persistence.retention import (
    ArtifactCleanupService,
    CleanupRun,
    RetentionService,
    SupabaseAuthAdminClient,
    SupabaseObjectDeleter,
    SupabaseRetentionStore,
)
from yom_awel.persistence.supabase_artifacts import SupabaseCleanupQueue


@dataclass(frozen=True)
class _HttpResponse:
    data: object
    error: object | None = None


class _HttpRpc:
    def __init__(self, base_url: str, service_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_key = service_key

    async def rpc(self, function: str, params: Mapping[str, object]) -> _HttpResponse:
        def request() -> _HttpResponse:
            http_request = Request(
                f"{self._base_url}/rest/v1/rpc/{function}",
                data=json.dumps(params).encode("utf-8"),
                headers={
                    "apikey": self._service_key,
                    "Authorization": f"Bearer {self._service_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urlopen(http_request, timeout=15) as response:
                    return _HttpResponse(json.loads(response.read().decode("utf-8")))
            except HTTPError as error:
                error.read()
                return _HttpResponse(None, {"status": error.code})
            except (OSError, ValueError, json.JSONDecodeError):
                return _HttpResponse(None, {"status": "transport"})

        return await asyncio.to_thread(request)


async def _run_cleanup(
    base_url: str, service_key: str, owner: str, limit: int, lease: int
) -> CleanupRun:
    rpc = _HttpRpc(base_url, service_key)
    queue = SupabaseCleanupQueue(rpc)
    object_deleter = SupabaseObjectDeleter(base_url, service_key)
    now = datetime.now(UTC)

    # Keep the order explicit: orphan queue first, then normal expired rows.
    orphan_result = await ArtifactCleanupService(queue, object_deleter).run_once(
        now, owner, limit, lease
    )
    retention = SupabaseRetentionStore(rpc)
    expired_result = await RetentionService(
        retention, object_deleter
    ).run_once(now, owner, limit, lease)

    # Auth deletion is deliberately last.  The RPC erases application data
    # only after locking the request/identity and proving no unresolved rows.
    auth = SupabaseAuthAdminClient(base_url, service_key)
    auth_failed = 0
    claims = await retention.claim_deletion_requests(owner, limit)
    for request_id, learner_id, auth_user_id in claims:
        try:
            reconciled = await retention.reconcile_anonymous(learner_id, owner, now)
            if not reconciled:
                auth_failed += 1
                await retention.finalize_deletion_request(request_id, owner, False)
                continue
            await auth.delete_user(auth_user_id)
            await retention.finalize_deletion_request(request_id, owner, True)
        except Exception:  # noqa: BLE001
            auth_failed += 1
            try:
                await retention.finalize_deletion_request(request_id, owner, False)
            except Exception:  # noqa: BLE001
                pass

    return CleanupRun(
        claimed=orphan_result.claimed + expired_result.claimed,
        resolved=orphan_result.resolved + expired_result.purged,
        failed=orphan_result.failed + expired_result.failed + auth_failed,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purge expired submission artifacts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cleanup-queue", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--lease-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    if args.limit < 1 or args.limit > 100 or args.lease_seconds < 1:
        parser.error("--limit must be between 1 and 100; --lease-seconds must be positive")
    if not args.cleanup_queue:
        print("retention cleanup: no cleanup queue requested; no objects deleted")
        return 0
    base_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if args.dry_run or not base_url or not service_key:
        print("retention cleanup: safe no-op; server-only backend is not configured")
        return 0
    configured_owner = os.getenv("RETENTION_WORKER_ID")
    try:
        owner = str(UUID(configured_owner)) if configured_owner else str(uuid4())
    except ValueError:
        parser.error("RETENTION_WORKER_ID must be a UUID")
    try:
        result = asyncio.run(
            _run_cleanup(base_url, service_key, owner, args.limit, args.lease_seconds)
        )
    except Exception:  # noqa: BLE001
        # Keep provider details and credentials out of CI logs; the non-zero
        # status is the operational alert and causes a retry/manual recovery.
        print("retention cleanup failed")
        return 1
    print(
        "retention cleanup completed: "
        f"claimed={result.claimed} resolved={result.resolved} failed={result.failed}"
    )
    return 1 if result.failed else 0


if __name__ == "__main__":
    sys.exit(main())
