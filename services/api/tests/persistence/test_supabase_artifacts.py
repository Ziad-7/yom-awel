from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import UUID, uuid4

import pytest

from yom_awel.domain.entities import Artifact
from yom_awel.persistence.retention import CleanupArtifact
from yom_awel.persistence.supabase_artifacts import (
    MAX_ARTIFACT_BYTES,
    PRIVATE_BUCKET,
    ArtifactReservation,
    SupabaseArtifactError,
    SupabaseArtifactStore,
    SupabaseCleanupQueue,
    generated_object_path,
    map_artifact_row,
)


@dataclass
class Signed:
    url: str
    token: str = "opaque"


class MetadataFake:
    def __init__(
        self,
        row: Mapping[str, object] | None = None,
        *,
        insert_error: Exception | None = None,
        created: bool = True,
        created_sequence: list[bool] | None = None,
    ) -> None:
        self.row = row
        self.insert_error = insert_error
        self.created = created
        self.created_sequence = list(created_sequence or [])
        self.inserted: Mapping[str, object] | None = None
        self.cleanup_rows: list[Mapping[str, object]] = []
        self.resolved: list[tuple[UUID, UUID]] = []
        self.reserved: list[Mapping[str, object]] = []
        self.prepare_delete_calls: list[Mapping[str, object]] = []
        self.activated: list[tuple[UUID, UUID, str]] = []

    async def select_artifact(
        self, artifact_id: UUID, learner_id: UUID
    ) -> Mapping[str, object] | None:
        return self.row

    async def reserve_artifact(self, row: Mapping[str, object]) -> ArtifactReservation:
        self.inserted = row
        self.reserved.append(row)
        if self.insert_error is not None:
            raise self.insert_error
        assert self.row is not None
        created = self.created_sequence.pop(0) if self.created_sequence else self.created
        return ArtifactReservation(self.row, created)

    async def enqueue_cleanup(self, row: Mapping[str, object]) -> None:
        self.cleanup_rows.append(row)

    async def resolve_cleanup(self, learner_id: UUID, artifact_id: UUID) -> None:
        self.resolved.append((learner_id, artifact_id))

    async def prepare_delete(self, row: Mapping[str, object]) -> None:
        self.prepare_delete_calls.append(row)
        if self.row is not None:
            self.row = dict(self.row)
            self.row["purge_status"] = "PURGED"

    async def activate_artifact(
        self, learner_id: UUID, artifact_id: UUID, upload_owner: str
    ) -> None:
        self.activated.append((learner_id, artifact_id, upload_owner))


class StorageFake:
    def __init__(
        self,
        content: bytes = b"",
        *,
        upload_error: Exception | None = None,
        delete_error: Exception | None = None,
    ) -> None:
        self.content = content
        self.upload_error = upload_error
        self.delete_error = delete_error
        self.upload_calls: list[tuple[str, str, int, Mapping[str, str]]] = []
        self.download_calls: list[tuple[str, str, int]] = []
        self.delete_calls: list[tuple[str, str]] = []

    async def create_signed_upload_url(
        self, bucket: str, path: str, expires_in: int, metadata: Mapping[str, str]
    ) -> Signed:
        self.upload_calls.append((bucket, path, expires_in, metadata))
        return Signed("https://signed.invalid/upload")

    async def upload_with_signed_url(
        self, signed: Signed, content: bytes, metadata: Mapping[str, str]
    ) -> None:
        if self.upload_error is not None:
            raise self.upload_error
        self.content = content

    async def create_signed_download_url(self, bucket: str, path: str, expires_in: int) -> Signed:
        self.download_calls.append((bucket, path, expires_in))
        return Signed("https://signed.invalid/download")

    async def download_with_signed_url(self, signed: Signed) -> bytes:
        return self.content

    async def delete_object(self, bucket: str, path: str) -> None:
        self.delete_calls.append((bucket, path))
        if self.delete_error is not None:
            raise self.delete_error


@dataclass
class RpcResponse:
    data: object
    error: object | None = None


class CleanupRpcFake:
    def __init__(self, row: Mapping[str, object]) -> None:
        self.row = row
        self.calls: list[tuple[str, Mapping[str, object]]] = []

    async def rpc(self, function: str, params: Mapping[str, object]) -> RpcResponse:
        self.calls.append((function, params))
        if function == "claim_artifact_cleanup":
            return RpcResponse([self.row])
        return RpcResponse(None)


@dataclass
class LocalSigned:
    url: str
    token: str


class LocalArtifactMetadata:
    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key

    async def _rpc(self, function: str, params: Mapping[str, object]) -> object:
        def request() -> object:
            http_request = Request(
                f"{self.base_url}/rest/v1/rpc/{function}",
                data=json.dumps(params).encode("utf-8"),
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(http_request, timeout=5) as response:
                body = response.read()
            # PostgREST returns an empty body for successful void RPCs when
            # callers request the default response representation.
            return None if not body else json.loads(body.decode("utf-8"))

        return await asyncio.to_thread(request)

    async def insert(self, table: str, row: Mapping[str, object]) -> None:
        def request() -> None:
            http_request = Request(
                f"{self.base_url}/rest/v1/{table}",
                data=json.dumps(row).encode("utf-8"),
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/json",
                    "Prefer": "return=minimal",
                },
                method="POST",
            )
            with urlopen(http_request, timeout=5):
                return

        await asyncio.to_thread(request)

    async def select_artifact(
        self, artifact_id: UUID, learner_id: UUID
    ) -> Mapping[str, object] | None:
        def request() -> Mapping[str, object] | None:
            url = (
                f"{self.base_url}/rest/v1/artifacts?artifact_id=eq.{artifact_id}"
                f"&learner_id=eq.{learner_id}"
            )
            http_request = Request(
                url,
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                },
            )
            with urlopen(http_request, timeout=5) as response:
                rows = json.loads(response.read().decode("utf-8"))
            return rows[0] if isinstance(rows, list) and rows else None

        return await asyncio.to_thread(request)

    async def reserve_artifact(self, row: Mapping[str, object]) -> ArtifactReservation:
        value = await self._rpc(
            "reserve_artifact",
            {
                "p_learner_id": row["learner_id"],
                "p_artifact_id": row["artifact_id"],
                "p_object_path": row["object_path"],
                "p_filename": row["filename"],
                "p_size_bytes": row["size_bytes"],
                "p_sha256": row["sha256"],
                "p_upload_owner": row["upload_owner"],
                "p_upload_lease_seconds": row["upload_lease_seconds"],
            },
        )
        if isinstance(value, Mapping) and isinstance(value.get("artifact"), Mapping):
            created = value.get("created")
            if type(created) is not bool:
                raise RuntimeError("local reserve_artifact returned invalid discriminator")
            return ArtifactReservation(value["artifact"], created)
        raise RuntimeError("local reserve_artifact returned no row/discriminator")

    async def enqueue_cleanup(self, row: Mapping[str, object]) -> None:
        await self._rpc(
            "enqueue_artifact_cleanup",
            {
                "p_learner_id": row["learner_id"],
                "p_artifact_id": row["artifact_id"],
                "p_object_path": row["object_path"],
                "p_sha256": row["sha256"],
                "p_size_bytes": row["size_bytes"],
                "p_reason": row["reason"],
            },
        )

    async def resolve_cleanup(self, learner_id: UUID, artifact_id: UUID) -> None:
        await self._rpc(
            "resolve_artifact_cleanup",
            {"p_learner_id": str(learner_id), "p_artifact_id": str(artifact_id)},
        )

    async def prepare_delete(self, row: Mapping[str, object]) -> None:
        await self._rpc(
            "prepare_artifact_delete",
            {
                "p_learner_id": row["learner_id"],
                "p_artifact_id": row["artifact_id"],
                "p_object_path": row["object_path"],
                "p_sha256": row["sha256"],
                "p_size_bytes": row["size_bytes"],
                "p_reason": row["reason"],
            },
        )

    async def activate_artifact(
        self, learner_id: UUID, artifact_id: UUID, upload_owner: str
    ) -> None:
        await self._rpc(
            "activate_artifact",
            {
                "p_learner_id": str(learner_id),
                "p_artifact_id": str(artifact_id),
                "p_upload_owner": upload_owner,
            },
        )


class LocalArtifactStorage:
    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key

    def _url(self, bucket: str, path: str) -> str:
        return f"{self.base_url}/storage/v1/object/{bucket}/{quote(path, safe='/')}"

    async def create_signed_upload_url(
        self, bucket: str, path: str, expires_in: int, metadata: Mapping[str, str]
    ) -> LocalSigned:
        return LocalSigned(self._url(bucket, path), path)

    async def upload_with_signed_url(
        self, signed: LocalSigned, content: bytes, metadata: Mapping[str, str]
    ) -> None:
        def request() -> None:
            http_request = Request(
                signed.url,
                data=content,
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                    "Content-Type": "application/octet-stream",
                    "x-upsert": "false",
                },
                method="POST",
            )
            with urlopen(http_request, timeout=5):
                return

        await asyncio.to_thread(request)

    async def create_signed_download_url(
        self, bucket: str, path: str, expires_in: int
    ) -> LocalSigned:
        return LocalSigned(self._url(bucket, path), path)

    async def download_with_signed_url(self, signed: LocalSigned) -> bytes:
        def request() -> bytes:
            http_request = Request(
                signed.url,
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                },
            )
            with urlopen(http_request, timeout=5) as response:
                return response.read()

        return await asyncio.to_thread(request)

    async def delete_object(self, bucket: str, path: str) -> None:
        def request() -> None:
            http_request = Request(
                self._url(bucket, path),
                headers={
                    "apikey": self.service_key,
                    "Authorization": f"Bearer {self.service_key}",
                },
                method="DELETE",
            )
            with urlopen(http_request, timeout=5):
                return

        await asyncio.to_thread(request)


@pytest.mark.asyncio
async def test_local_artifact_rpc_helper_accepts_empty_success_body(monkeypatch) -> None:
    class EmptyResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return b""

    monkeypatch.setattr(
        sys.modules[__name__],
        "urlopen",
        lambda request, timeout: EmptyResponse(),
    )
    metadata = LocalArtifactMetadata("http://supabase.invalid", "service-key")
    assert await metadata._rpc("resolve_artifact_cleanup", {}) is None


def artifact(learner_id: UUID, artifact_id: UUID, content: bytes) -> Artifact:
    import hashlib

    return Artifact(
        artifact_id=artifact_id,
        learner_id=learner_id,
        filename="answer.txt",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )


def artifact_row(value: Artifact) -> dict[str, object]:
    return {
        "artifact_id": str(value.artifact_id),
        "learner_id": str(value.learner_id),
        "object_path": generated_object_path(value.learner_id, value.artifact_id),
        "filename": value.filename,
        "size_bytes": value.size_bytes,
        "sha256": value.sha256,
        "retention_expires_at": "2030-01-01T00:00:00+00:00",
        "purge_status": "ACTIVE",
        "purge_lease_owner": None,
        "purge_lease_expires_at": None,
        "purged_at": None,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_put_and_download_use_private_signed_uuid_path_and_hash_metadata() -> None:
    learner_id, artifact_id, content = uuid4(), uuid4(), b"hello"
    value = artifact(learner_id, artifact_id, content)
    metadata = MetadataFake(artifact_row(value))
    storage = StorageFake(content)
    store = SupabaseArtifactStore(metadata, storage)
    assert await store.put(value, content) == value
    assert storage.upload_calls == [
        (
            PRIVATE_BUCKET,
            generated_object_path(learner_id, artifact_id),
            300,
            {"sha256": value.sha256, "size_bytes": "5", "upsert": "false"},
        )
    ]
    assert await store.download(artifact_id, learner_id) == content
    assert storage.download_calls == [
        (PRIVATE_BUCKET, generated_object_path(learner_id, artifact_id), 120)
    ]
    assert metadata.resolved == [(learner_id, artifact_id)]
    assert metadata.activated == [(learner_id, artifact_id, "artifact-uploader")]
    assert metadata.reserved[0]["upload_owner"] == "artifact-uploader"
    assert metadata.reserved[0]["upload_lease_seconds"] == 600


@pytest.mark.asyncio
async def test_artifact_size_hash_scope_and_delete_boundaries() -> None:
    learner_id, artifact_id = uuid4(), uuid4()
    content = b"safe"
    value = artifact(learner_id, artifact_id, content)
    metadata = MetadataFake(artifact_row(value))
    storage = StorageFake(content)
    store = SupabaseArtifactStore(metadata, storage)
    with pytest.raises(SupabaseArtifactError) as size_error:
        await store.put(value.model_copy(update={"size_bytes": len(content) + 1}), content)
    assert size_error.value.code == "artifact_size_mismatch"
    with pytest.raises(SupabaseArtifactError) as hash_error:
        await store.put(value.model_copy(update={"sha256": "a" * 64}), content)
    assert hash_error.value.code == "artifact_hash_mismatch"
    await store.delete(artifact_id, learner_id)
    assert await store.get(artifact_id, learner_id) is None
    assert storage.delete_calls == [
        (PRIVATE_BUCKET, generated_object_path(learner_id, artifact_id))
    ]
    assert metadata.prepare_delete_calls[0]["reason"] == "DELETE_FAILED"
    assert metadata.resolved == [(learner_id, artifact_id)]
    assert MAX_ARTIFACT_BYTES == 5 * 1024 * 1024


@pytest.mark.asyncio
async def test_metadata_reservation_failure_happens_before_object_mutation() -> None:
    learner_id, artifact_id, content = uuid4(), uuid4(), b"orphan-risk"
    value = artifact(learner_id, artifact_id, content)
    metadata = MetadataFake(insert_error=RuntimeError("database details"))
    storage = StorageFake(content)
    store = SupabaseArtifactStore(metadata, storage)
    with pytest.raises(SupabaseArtifactError) as error:
        await store.put(value, content)
    assert error.value.code == "supabase_provider_error"
    assert "database details" not in str(error.value)
    assert storage.upload_calls == []
    assert storage.delete_calls == []
    assert metadata.cleanup_rows[0]["reason"] == "UPLOAD_FAILED"


@pytest.mark.asyncio
async def test_upload_failure_does_not_attempt_cleanup_before_successful_upload() -> None:
    learner_id, artifact_id, content = uuid4(), uuid4(), b"upload-fails"
    value = artifact(learner_id, artifact_id, content)
    storage = StorageFake(content, upload_error=RuntimeError("upload details"))
    metadata = MetadataFake(artifact_row(value))
    store = SupabaseArtifactStore(metadata, storage)
    with pytest.raises(SupabaseArtifactError) as error:
        await store.put(value, content)
    assert error.value.code == "supabase_provider_error"
    assert storage.delete_calls == []
    assert metadata.prepare_delete_calls == [
        {
            "learner_id": str(learner_id),
            "artifact_id": str(artifact_id),
            "object_path": generated_object_path(learner_id, artifact_id),
            "sha256": value.sha256,
            "size_bytes": len(content),
            "reason": "UPLOAD_FAILED",
        }
    ]


@pytest.mark.asyncio
async def test_duplicate_retry_returns_existing_metadata_without_uploading() -> None:
    learner_id, artifact_id, content = uuid4(), uuid4(), b"retry-safe"
    value = artifact(learner_id, artifact_id, content)
    metadata = MetadataFake(artifact_row(value), created=False)
    storage = StorageFake(content)
    store = SupabaseArtifactStore(metadata, storage)
    assert await store.put(value, content) == value
    assert storage.upload_calls == []
    assert storage.delete_calls == []
    assert metadata.resolved == [(learner_id, artifact_id)]


@pytest.mark.asyncio
async def test_unfinished_duplicate_does_not_tombstone_another_upload() -> None:
    learner_id, artifact_id, content = uuid4(), uuid4(), b"unfinished"
    value = artifact(learner_id, artifact_id, content)
    row = artifact_row(value)
    row["purge_status"] = "UPLOADING"
    metadata = MetadataFake(row, created=False)
    storage = StorageFake(content)
    store = SupabaseArtifactStore(metadata, storage)
    with pytest.raises(SupabaseArtifactError) as error:
        await store.put(value, content)
    assert error.value.code == "artifact_upload_in_progress"
    assert storage.upload_calls == []
    assert metadata.resolved == []


def test_upload_lease_must_cover_signed_url() -> None:
    with pytest.raises(ValueError):
        SupabaseArtifactStore(
            MetadataFake(artifact_row(artifact(uuid4(), uuid4(), b"x"))),
            StorageFake(),
            upload_expiry_seconds=300,
            upload_lease_seconds=299,
        )


@pytest.mark.asyncio
async def test_duplicate_purged_artifact_is_not_reported_as_usable() -> None:
    learner_id, artifact_id, content = uuid4(), uuid4(), b"gone"
    value = artifact(learner_id, artifact_id, content)
    row = artifact_row(value)
    row["purge_status"] = "PURGED"
    metadata = MetadataFake(row, created=False)
    with pytest.raises(SupabaseArtifactError) as error:
        await SupabaseArtifactStore(metadata, StorageFake(content)).put(value, content)
    assert error.value.code == "artifact_unavailable"


@pytest.mark.asyncio
async def test_racing_reservations_allow_only_one_storage_mutation() -> None:
    learner_id, artifact_id, content = uuid4(), uuid4(), b"race-safe"
    value = artifact(learner_id, artifact_id, content)
    metadata = MetadataFake(artifact_row(value), created_sequence=[True, False])
    storage = StorageFake(content)
    first = SupabaseArtifactStore(metadata, storage)
    second = SupabaseArtifactStore(metadata, storage)
    assert await first.put(value, content) == value
    assert await second.put(value, content) == value
    assert len(storage.upload_calls) == 1
    assert storage.delete_calls == []


@pytest.mark.asyncio
async def test_cleanup_finalization_uses_owner_lease_cas_rpc() -> None:
    learner_id, artifact_id, cleanup_id = uuid4(), uuid4(), uuid4()
    rpc = CleanupRpcFake(
        {
            "cleanup_id": str(cleanup_id),
            "learner_id": str(learner_id),
            "artifact_id": str(artifact_id),
            "object_path": f"{learner_id}/{artifact_id}",
            "attempts": 1,
            "lease_owner": "worker-one",
            "lease_expires_at": "2030-01-01T00:00:00+00:00",
        }
    )
    queue = SupabaseCleanupQueue(rpc)
    claimed = await queue.claim_pending(datetime(2029, 1, 1, tzinfo=UTC), "worker-one", 60, 1)
    assert claimed == [
        CleanupArtifact(
            cleanup_id,
            learner_id,
            artifact_id,
            f"{learner_id}/{artifact_id}",
            attempts=1,
            lease_owner="worker-one",
            lease_expires_at=datetime(2030, 1, 1, tzinfo=UTC),
        )
    ]
    await queue.finalize_cleanup(cleanup_id, "worker-one", True, datetime(2029, 1, 1, tzinfo=UTC))
    assert rpc.calls[-1] == (
        "finalize_artifact_cleanup",
        {"p_cleanup_id": str(cleanup_id), "p_lease_owner": "worker-one"},
    )


def test_artifact_mapper_rejects_path_effects_and_unknown_rows() -> None:
    learner_id, artifact_id = uuid4(), uuid4()
    value = artifact(learner_id, artifact_id, b"x")
    row = artifact_row(value)
    row["object_path"] = "../escape"
    with pytest.raises(SupabaseArtifactError) as path_error:
        map_artifact_row(row, learner_id)
    assert path_error.value.code == "provider_payload_invalid"
    row = artifact_row(value)
    row["extra"] = "unknown"
    with pytest.raises(SupabaseArtifactError) as unknown_error:
        map_artifact_row(row, learner_id)
    assert unknown_error.value.code == "provider_payload_invalid"
    row = artifact_row(value)
    row["learner_id"] = str(uuid4())
    with pytest.raises(SupabaseArtifactError) as owner_error:
        map_artifact_row(row, learner_id)
    assert owner_error.value.code == "learner_scope_violation"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_storage_contract_is_opt_in() -> None:
    base_url = os.getenv("SUPABASE_LOCAL_URL")
    if not base_url:
        pytest.skip("set SUPABASE_LOCAL_URL to run local Supabase integration tests")
    service_key = os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    if not service_key:
        pytest.skip("set SUPABASE_LOCAL_SERVICE_ROLE_KEY to run local Supabase integration tests")

    def request_bucket() -> dict[str, object]:
        request = Request(
            f"{base_url.rstrip('/')}/storage/v1/bucket/submissions",
            headers={
                "apikey": service_key,
                "Authorization": f"Bearer {service_key}",
            },
        )
        try:
            with urlopen(request, timeout=5) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            pytest.fail(f"local Supabase storage request failed with status {error.code}")

    bucket = await asyncio.to_thread(request_bucket)
    assert bucket["id"] == PRIVATE_BUCKET
    assert bucket["public"] is False
    assert bucket["file_size_limit"] in {MAX_ARTIFACT_BYTES, str(MAX_ARTIFACT_BYTES)}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_local_artifact_upload_download_delete_flow() -> None:
    base_url = os.getenv("SUPABASE_LOCAL_URL")
    if not base_url:
        pytest.skip("set SUPABASE_LOCAL_URL to run local Supabase integration tests")
    service_key = os.getenv("SUPABASE_LOCAL_SERVICE_ROLE_KEY")
    if not service_key:
        pytest.skip("set SUPABASE_LOCAL_SERVICE_ROLE_KEY to run local Supabase integration tests")
    learner_id, artifact_id, content = uuid4(), uuid4(), b"x"
    metadata = LocalArtifactMetadata(base_url, service_key)
    await metadata.insert(
        "learners",
        {
            "learner_id": str(learner_id),
            "display_name": "local-artifact",
            "preferred_language": "en",
            "status": "ONBOARDING",
            "state_machine_version": "1",
        },
    )
    value = Artifact(
        artifact_id=artifact_id,
        learner_id=learner_id,
        filename="local.txt",
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
    )
    store = SupabaseArtifactStore(metadata, LocalArtifactStorage(base_url, service_key))
    assert await store.put(value, content) == value
    assert await store.download(artifact_id, learner_id) == content
    await store.delete(artifact_id, learner_id)
    assert await store.get(artifact_id, learner_id) is None
    assert await store.download(artifact_id, learner_id) is None
