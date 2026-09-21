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
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID

from yom_awel.persistence.retention import ArtifactCleanupService, CleanupRun, ObjectDeleter
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


class _HttpStorageDeleter(ObjectDeleter):
    def __init__(self, base_url: str, service_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._service_key = service_key

    async def delete(self, object_path: str) -> None:
        # Queue rows are server-produced UUID/UUID paths. Revalidate before
        # constructing a URL so a compromised row cannot target another key.
        parts = object_path.split("/")
        if len(parts) != 2:
            raise ValueError("invalid queued artifact path")
        UUID(parts[0])
        UUID(parts[1])

        def request() -> None:
            http_request = Request(
                f"{self._base_url}/storage/v1/object/submissions/{quote(object_path, safe='/')}",
                headers={
                    "apikey": self._service_key,
                    "Authorization": f"Bearer {self._service_key}",
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
                raise OSError("storage deletion failed") from error

        await asyncio.to_thread(request)


async def _run_cleanup(
    base_url: str, service_key: str, owner: str, limit: int, lease: int
) -> CleanupRun:
    queue = SupabaseCleanupQueue(_HttpRpc(base_url, service_key))
    worker = ArtifactCleanupService(queue, _HttpStorageDeleter(base_url, service_key))
    return await worker.run_once(datetime.now(UTC), owner, limit, lease)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Purge expired submission artifacts")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--cleanup-queue", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--lease-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    if args.limit < 1 or args.lease_seconds < 1:
        parser.error("--limit and --lease-seconds must be positive")
    if not args.cleanup_queue:
        print("retention cleanup: no cleanup queue requested; no objects deleted")
        return 0
    base_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if args.dry_run or not base_url or not service_key:
        print("retention cleanup: safe no-op; server-only backend is not configured")
        return 0
    owner = os.getenv("RETENTION_WORKER_ID", "github-retention")
    result = asyncio.run(_run_cleanup(base_url, service_key, owner, args.limit, args.lease_seconds))
    print(
        "retention cleanup completed: "
        f"claimed={result.claimed} resolved={result.resolved} failed={result.failed}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
