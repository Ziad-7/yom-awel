"""Server-only signed operations for the private Supabase submissions bucket."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from pydantic import ValidationError

from yom_awel.domain.entities import Artifact
from yom_awel.domain.errors import ArtifactIntegrityFailure, ArtifactNotReady, PersistenceError
from yom_awel.persistence.retention import CleanupArtifact, CleanupQueueStore
from yom_awel.persistence.supabase import SupabaseRpcClient
from yom_awel.ports.artifacts import ArtifactUploadAuthorization

MAX_ARTIFACT_BYTES = 5 * 1024 * 1024
PRIVATE_BUCKET = "submissions"


class SupabaseArtifactError(PersistenceError):
    def __init__(self, code: str, message: str = "Supabase artifact operation failed") -> None:
        super().__init__(code, message)


@dataclass(frozen=True)
class ArtifactReservation:
    """Result of the server-side metadata reservation RPC.

    The discriminator is part of the RPC contract: callers must never infer
    creation from the shape of a returned row, because doing so can overwrite
    an object during a duplicate or retry.
    """

    row: Mapping[str, object]
    created: bool


class SignedUpload(Protocol):
    url: str
    token: str


class SignedDownload(Protocol):
    url: str


class SupabaseArtifactMetadata(Protocol):
    async def select_artifact(
        self, artifact_id: UUID, learner_id: UUID
    ) -> Mapping[str, object] | None: ...

    async def reserve_artifact_v2(self, row: Mapping[str, object]) -> ArtifactReservation: ...

    async def enqueue_cleanup(self, row: Mapping[str, object]) -> None: ...

    async def resolve_cleanup(self, learner_id: UUID, artifact_id: UUID) -> None: ...

    async def prepare_delete(self, row: Mapping[str, object]) -> None: ...

    async def activate_artifact(
        self, learner_id: UUID, artifact_id: UUID, upload_owner: str
    ) -> None: ...


class SupabaseSignedStorage(Protocol):
    async def object_metadata(self, bucket: str, path: str) -> Mapping[str, object]: ...

    async def create_signed_upload_url(
        self, bucket: str, path: str, expires_in: int, metadata: Mapping[str, str]
    ) -> SignedUpload: ...

    async def upload_with_signed_url(
        self, signed: SignedUpload, content: bytes, metadata: Mapping[str, str]
    ) -> None: ...

    async def create_signed_download_url(
        self, bucket: str, path: str, expires_in: int
    ) -> SignedDownload: ...

    async def download_with_signed_url(self, signed: SignedDownload) -> bytes: ...

    async def delete_object(self, bucket: str, path: str) -> None: ...


class SupabaseCleanupQueue(CleanupQueueStore):
    """Service-role queue adapter consumed by the daily retention worker."""

    def __init__(self, rpc: SupabaseRpcClient) -> None:
        self._rpc = rpc
        self._claimed: dict[UUID, CleanupArtifact] = {}

    async def claim_pending(
        self, now: datetime, owner: str, lease_seconds: int, limit: int
    ) -> list[CleanupArtifact]:
        try:
            response = await self._rpc.rpc(
                "claim_artifact_cleanup",
                {
                    "p_limit": limit,
                    "p_lease_owner": owner,
                    "p_lease_seconds": lease_seconds,
                },
            )
            if response.error is not None:
                raise SupabaseArtifactError("supabase_provider_error")
            rows = response.data
            if rows is None:
                return []
            if not isinstance(rows, list):
                raise SupabaseArtifactError("provider_payload_invalid")
            claimed = [self._map_cleanup_row(row) for row in rows if isinstance(row, Mapping)]
            if len(claimed) != len(rows):
                raise SupabaseArtifactError("provider_payload_invalid")
            self._claimed.update({item.cleanup_id: item for item in claimed})
            return claimed
        except SupabaseArtifactError:
            raise
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc

    async def finalize_cleanup(
        self, cleanup_id: UUID, owner: str, deleted: bool, now: datetime
    ) -> None:
        item = self._claimed.get(cleanup_id)
        if item is None:
            raise SupabaseArtifactError("cleanup_not_claimed")
        try:
            if deleted:
                response = await self._rpc.rpc(
                    "finalize_artifact_cleanup",
                    {"p_cleanup_id": str(cleanup_id), "p_lease_owner": owner},
                )
            else:
                response = await self._rpc.rpc(
                    "release_artifact_cleanup",
                    {"p_cleanup_id": str(cleanup_id), "p_lease_owner": owner},
                )
            if response.error is not None:
                raise SupabaseArtifactError("supabase_provider_error")
        except SupabaseArtifactError:
            raise
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        finally:
            self._claimed.pop(cleanup_id, None)

    @staticmethod
    def _map_cleanup_row(value: Mapping[str, object]) -> CleanupArtifact:
        required = {
            "cleanup_id",
            "learner_id",
            "artifact_id",
            "object_path",
            "attempts",
            "lease_owner",
            "lease_expires_at",
        }
        if not required.issubset(value):
            raise SupabaseArtifactError("provider_payload_invalid")
        try:
            lease_value = value["lease_expires_at"]
            lease = (
                None
                if lease_value is None
                else datetime.fromisoformat(str(lease_value)).astimezone(UTC)
            )
            attempts = value["attempts"]
            if type(attempts) is not int or attempts < 1:
                raise ValueError("invalid attempts")
            return CleanupArtifact(
                cleanup_id=UUID(str(value["cleanup_id"])),
                learner_id=UUID(str(value["learner_id"])),
                artifact_id=UUID(str(value["artifact_id"])),
                object_path=str(value["object_path"]),
                attempts=attempts,
                lease_owner=str(value["lease_owner"]) if value["lease_owner"] else None,
                lease_expires_at=lease,
            )
        except (TypeError, ValueError) as exc:
            raise SupabaseArtifactError("provider_payload_invalid") from exc


def generated_object_path(learner_id: UUID, artifact_id: UUID) -> str:
    """Generate, rather than accept, the only storage path this adapter uses."""

    return f"{learner_id}/{artifact_id}"


def _validate_path(path: object, learner_id: UUID, artifact_id: UUID) -> str:
    if not isinstance(path, str) or path.count("/") != 1:
        raise SupabaseArtifactError("provider_payload_invalid", "Artifact path is not UUID-only")
    learner_part, artifact_part = path.split("/")
    try:
        parsed_learner = UUID(learner_part)
        parsed_artifact = UUID(artifact_part)
    except ValueError as exc:
        raise SupabaseArtifactError(
            "provider_payload_invalid", "Artifact path is not UUID-only"
        ) from exc
    if (
        str(parsed_learner) != learner_part
        or str(parsed_artifact) != artifact_part
        or parsed_learner != learner_id
        or parsed_artifact != artifact_id
    ):
        raise SupabaseArtifactError("learner_scope_violation", "Artifact path is out of scope")
    return path


_ARTIFACT_KEYS = {
    "artifact_id",
    "learner_id",
    "object_path",
    "filename",
    "content_type",
    "size_bytes",
    "sha256",
    "retention_expires_at",
    "purge_status",
    "purge_lease_owner",
    "purge_lease_expires_at",
    "purged_at",
    "created_at",
}


def map_artifact_row(value: Mapping[str, object], learner_id: UUID) -> Artifact:
    if set(value) != _ARTIFACT_KEYS:
        raise SupabaseArtifactError("provider_payload_invalid", "Unexpected artifact columns")
    artifact_id = value.get("artifact_id")
    row_learner = value.get("learner_id")
    if artifact_id is None or row_learner is None or value.get("object_path") is None:
        raise SupabaseArtifactError("provider_payload_invalid", "Required artifact value is null")
    if value.get("purge_status") not in {
        "ACTIVE",
        "UPLOADING",
        "CLAIMED",
        "PURGE_FAILED",
        "PURGED",
    }:
        raise SupabaseArtifactError("provider_payload_invalid", "Invalid artifact lifecycle status")
    try:
        parsed_artifact = UUID(str(artifact_id))
        parsed_learner = UUID(str(row_learner))
    except (TypeError, ValueError) as exc:
        raise SupabaseArtifactError("provider_payload_invalid", "Invalid artifact UUID") from exc
    if parsed_learner != learner_id:
        raise SupabaseArtifactError(
            "learner_scope_violation", "Artifact does not belong to learner"
        )
    _validate_path(value["object_path"], learner_id, parsed_artifact)
    try:
        return Artifact.model_validate(
            {
                "artifact_id": parsed_artifact,
                "learner_id": parsed_learner,
                "filename": value["filename"],
                "content_type": value["content_type"],
                "size_bytes": value["size_bytes"],
                "sha256": value["sha256"],
            }
        )
    except (ValidationError, TypeError, ValueError) as exc:
        raise SupabaseArtifactError("provider_payload_invalid", "Invalid artifact row") from exc


class SupabaseArtifactStore:
    """Private-bucket ArtifactStore using short-lived signed URLs internally."""

    def __init__(
        self,
        metadata: SupabaseArtifactMetadata,
        storage: SupabaseSignedStorage,
        *,
        upload_expiry_seconds: int = 300,
        download_expiry_seconds: int = 120,
        upload_owner: str = "artifact-uploader",
        upload_lease_seconds: int = 600,
    ) -> None:
        if not 1 <= upload_expiry_seconds <= 900 or not 1 <= download_expiry_seconds <= 900:
            raise ValueError("signed URL expiry must be between one and 900 seconds")
        if (
            not upload_owner
            or not 1 <= upload_lease_seconds <= 900
            or upload_lease_seconds < upload_expiry_seconds
        ):
            raise ValueError("upload owner and lease must cover signed upload expiry")
        self._metadata = metadata
        self._storage = storage
        self._upload_expiry = upload_expiry_seconds
        self._download_expiry = download_expiry_seconds
        self._upload_owner = upload_owner
        self._upload_lease_seconds = upload_lease_seconds

    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None:
        try:
            row = await self._metadata.select_artifact(artifact_id, learner_id)
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        if row is None:
            return None
        if row.get("purge_status") != "ACTIVE":
            return None
        return map_artifact_row(row, learner_id)

    async def authorize_upload(
        self, artifact: Artifact, *, expires_in_seconds: int | None = None
    ) -> ArtifactUploadAuthorization:
        """Reserve metadata and mint a short-lived one-object signed URL.

        The browser performs the actual object upload with this URL.  The
        metadata row is created before that mutation, so a subsequent
        submission can resolve the artifact by learner/id and independently
        verify size and SHA-256 through ``download``.
        """

        expiry = self._upload_expiry if expires_in_seconds is None else expires_in_seconds
        if not 1 <= expiry <= 900:
            raise ValueError("signed upload expiry must be between one and 900 seconds")
        path = generated_object_path(artifact.learner_id, artifact.artifact_id)
        metadata = {
            "content_type": artifact.content_type,
            "sha256": artifact.sha256,
            "size_bytes": str(artifact.size_bytes),
            "upsert": "false",
        }
        cleanup_row = self._cleanup_row(artifact, "UPLOAD_FAILED", path)
        try:
            await self._metadata.enqueue_cleanup(cleanup_row)
            reservation = await self._metadata.reserve_artifact_v2(
                {
                    "artifact_id": str(artifact.artifact_id),
                    "learner_id": str(artifact.learner_id),
                    "object_path": path,
                    "filename": artifact.filename,
                    "content_type": artifact.content_type,
                    "size_bytes": artifact.size_bytes,
                    "sha256": artifact.sha256,
                    "upload_owner": self._upload_owner,
                    "upload_lease_seconds": self._upload_lease_seconds,
                }
            )
            if not isinstance(reservation, ArtifactReservation):
                raise SupabaseArtifactError("provider_payload_invalid")
            row = reservation.row
            status = row.get("purge_status")
            if status in {"PURGED", "CLAIMED"}:
                raise SupabaseArtifactError("artifact_unavailable")
            signed = await self._storage.create_signed_upload_url(
                PRIVATE_BUCKET, path, expiry, metadata
            )
            if not isinstance(signed.url, str) or not signed.url:
                raise SupabaseArtifactError("provider_payload_invalid")
            if not isinstance(signed.token, str) or not signed.token:
                raise SupabaseArtifactError("provider_payload_invalid")
            return ArtifactUploadAuthorization(
                artifact=map_artifact_row(row, artifact.learner_id),
                upload_url=signed.url,
                upload_token=signed.token,
                expires_in_seconds=expiry,
                headers={"x-upsert": "false"},
            )
        except SupabaseArtifactError:
            raise
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc

    async def complete_upload(self, artifact_id: UUID, learner_id: UUID) -> Artifact:
        """Verify the browser-uploaded object before activating its metadata."""

        try:
            row = await self._metadata.select_artifact(artifact_id, learner_id)
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        if row is None:
            raise ArtifactNotReady()
        status = row.get("purge_status")
        artifact = map_artifact_row(row, learner_id)
        if status == "ACTIVE":
            return artifact
        if status != "UPLOADING":
            raise ArtifactNotReady()

        path = generated_object_path(learner_id, artifact_id)
        try:
            object_metadata = await self._storage.object_metadata(PRIVATE_BUCKET, path)
            if not self._metadata_matches(artifact, object_metadata):
                raise ArtifactIntegrityFailure()
            signed = await self._storage.create_signed_download_url(
                PRIVATE_BUCKET, path, self._download_expiry
            )
            content = await self._storage.download_with_signed_url(signed)
        except ArtifactIntegrityFailure:
            raise
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        if (
            len(content) != artifact.size_bytes
            or hashlib.sha256(content).hexdigest() != artifact.sha256
        ):
            raise ArtifactIntegrityFailure()
        try:
            await self._metadata.activate_artifact(learner_id, artifact_id, self._upload_owner)
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        await self._best_effort_resolve(learner_id, artifact_id)
        activated_row = dict(row)
        activated_row["purge_status"] = "ACTIVE"
        activated_row["purge_lease_owner"] = None
        activated_row["purge_lease_expires_at"] = None
        return map_artifact_row(activated_row, learner_id)

    async def put(self, artifact: Artifact, content: bytes) -> Artifact:
        if len(content) != artifact.size_bytes or len(content) > MAX_ARTIFACT_BYTES:
            raise SupabaseArtifactError("artifact_size_mismatch", "Artifact size is invalid")
        digest = hashlib.sha256(content).hexdigest()
        if digest != artifact.sha256:
            raise SupabaseArtifactError("artifact_hash_mismatch", "Artifact hash is invalid")
        path = generated_object_path(artifact.learner_id, artifact.artifact_id)
        metadata = {
            "content_type": artifact.content_type,
            "sha256": digest,
            "size_bytes": str(len(content)),
            "upsert": "false",
        }
        cleanup_row = self._cleanup_row(artifact, "UPLOAD_FAILED", path)
        try:
            await self._metadata.enqueue_cleanup(cleanup_row)
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        try:
            reservation = await self._metadata.reserve_artifact_v2(
                {
                    "artifact_id": str(artifact.artifact_id),
                    "learner_id": str(artifact.learner_id),
                    "object_path": path,
                    "filename": artifact.filename,
                    "content_type": artifact.content_type,
                    "size_bytes": artifact.size_bytes,
                    "sha256": artifact.sha256,
                    "upload_owner": self._upload_owner,
                    "upload_lease_seconds": self._upload_lease_seconds,
                }
            )
            if not isinstance(reservation, ArtifactReservation):
                raise SupabaseArtifactError("provider_payload_invalid")
        except SupabaseArtifactError:
            raise
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        row, created = reservation.row, reservation.created
        if not created:
            # Do not resolve a queue entry for another caller's unfinished
            # reservation. The cleanup worker owns reconciliation of UPLOADING
            # metadata; ACTIVE duplicates can safely resolve their retry entry.
            status = row.get("purge_status")
            if status in {"UPLOADING", "CLAIMED"}:
                raise SupabaseArtifactError(
                    "artifact_upload_in_progress", "Artifact upload is still in progress"
                )
            if status == "PURGED":
                raise SupabaseArtifactError(
                    "artifact_unavailable", "Artifact is no longer available"
                )
            await self._best_effort_resolve(artifact.learner_id, artifact.artifact_id)
            return map_artifact_row(row, artifact.learner_id)
        try:
            signed = await self._storage.create_signed_upload_url(
                PRIVATE_BUCKET, path, self._upload_expiry, metadata
            )
            await self._storage.upload_with_signed_url(signed, content, metadata)
        except SupabaseArtifactError:
            await self._best_effort_tombstone(self._cleanup_row(artifact, "UPLOAD_FAILED", path))
            raise
        except Exception as exc:
            await self._best_effort_tombstone(self._cleanup_row(artifact, "UPLOAD_FAILED", path))
            raise SupabaseArtifactError("supabase_provider_error") from exc
        return await self.complete_upload(artifact.artifact_id, artifact.learner_id)

    @staticmethod
    def _metadata_matches(artifact: Artifact, metadata: Mapping[str, object]) -> bool:
        return (
            set(metadata) == {"content_type", "size_bytes", "sha256"}
            and metadata["content_type"] == artifact.content_type
            and type(metadata["size_bytes"]) is int
            and metadata["size_bytes"] == artifact.size_bytes
            and isinstance(metadata["sha256"], str)
            and metadata["sha256"] == artifact.sha256
        )

    @staticmethod
    def _cleanup_row(artifact: Artifact, reason: str, path: str) -> Mapping[str, object]:
        return {
            "learner_id": str(artifact.learner_id),
            "artifact_id": str(artifact.artifact_id),
            "object_path": path,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
            "reason": reason,
        }

    async def _best_effort_delete(self, path: str) -> None:
        try:
            await self._storage.delete_object(PRIVATE_BUCKET, path)
        except Exception as _cleanup_error:  # noqa: BLE001
            # Preserve the metadata/provider failure; retention can reconcile
            # an object if a provider cleanup request itself fails.
            return

    async def _best_effort_enqueue(self, row: Mapping[str, object]) -> None:
        try:
            await self._metadata.enqueue_cleanup(row)
        except Exception as _enqueue_error:  # noqa: BLE001
            return

    async def _best_effort_resolve(self, learner_id: UUID, artifact_id: UUID) -> None:
        try:
            await self._metadata.resolve_cleanup(learner_id, artifact_id)
        except Exception as _resolve_error:  # noqa: BLE001
            return

    async def _best_effort_tombstone(self, row: Mapping[str, object]) -> None:
        try:
            await self._metadata.prepare_delete(row)
        except Exception as _tombstone_error:  # noqa: BLE001
            return

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None:
        artifact = await self.get(artifact_id, learner_id)
        if artifact is None:
            return None
        path = generated_object_path(learner_id, artifact_id)
        try:
            signed = await self._storage.create_signed_download_url(
                PRIVATE_BUCKET, path, self._download_expiry
            )
            content = await self._storage.download_with_signed_url(signed)
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        if (
            len(content) != artifact.size_bytes
            or hashlib.sha256(content).hexdigest() != artifact.sha256
        ):
            raise SupabaseArtifactError("artifact_integrity_failure")
        return content

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None:
        artifact = await self.get(artifact_id, learner_id)
        if artifact is None:
            return
        path = generated_object_path(learner_id, artifact_id)
        try:
            await self._metadata.prepare_delete(self._cleanup_row(artifact, "DELETE_FAILED", path))
            await self._storage.delete_object(PRIVATE_BUCKET, path)
        except Exception as exc:
            raise SupabaseArtifactError("supabase_provider_error") from exc
        await self._best_effort_resolve(learner_id, artifact_id)
