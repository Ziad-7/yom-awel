"""Private, zero-cloud artifact storage for local mode."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from uuid import UUID

from yom_awel.domain.entities import Artifact
from yom_awel.domain.errors import LearnerScopeViolation, UniqueConstraintViolation


class LocalArtifactStore:
    """Store bytes below generated UUID paths, never user-controlled paths.

    Metadata is kept in a generated sidecar next to the bytes.  The original
    filename is metadata only and can therefore contain path separators or
    Unicode characters without changing the storage location.
    """

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _learner_dir(self, learner_id: UUID) -> Path:
        return self.root / str(learner_id)

    def _data_path(self, artifact: Artifact | UUID, learner_id: UUID | None = None) -> Path:
        if isinstance(artifact, Artifact):
            learner_id = artifact.learner_id
            artifact_id = artifact.artifact_id
        else:
            if learner_id is None:
                raise ValueError("learner_id is required")
            artifact_id = artifact
        return self._learner_dir(learner_id) / str(artifact_id)

    def _meta_path(self, data_path: Path) -> Path:
        return data_path.with_name(f".{data_path.name}.metadata.json")

    @staticmethod
    def _metadata(artifact: Artifact) -> bytes:
        return json.dumps(
            artifact.model_dump(mode="json"), sort_keys=True, ensure_ascii=False
        ).encode()

    @staticmethod
    def _read_metadata(path: Path) -> Artifact:
        return Artifact.model_validate(json.loads(path.read_text(encoding="utf-8")))

    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None:
        data_path = self._data_path(artifact_id, learner_id)
        meta_path = self._meta_path(data_path)
        if not data_path.is_file() or not meta_path.is_file():
            return None
        try:
            artifact = self._read_metadata(meta_path)
        except (OSError, ValueError, TypeError):
            return None
        if artifact.learner_id != learner_id or artifact.artifact_id != artifact_id:
            return None
        return artifact

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None:
        artifact = await self.get(artifact_id, learner_id)
        if artifact is None:
            return None
        try:
            return self._data_path(artifact).read_bytes()
        except OSError:
            return None

    async def put(self, artifact: Artifact, content: bytes) -> Artifact:
        if len(content) != artifact.size_bytes:
            raise ValueError("content size does not match artifact metadata")
        digest = hashlib.sha256(content).hexdigest()
        if digest != artifact.sha256:
            raise ValueError("content sha256 does not match artifact metadata")

        learner_dir = self._learner_dir(artifact.learner_id)
        learner_dir.mkdir(parents=True, exist_ok=True)
        data_path = self._data_path(artifact)
        meta_path = self._meta_path(data_path)
        if data_path.exists() or meta_path.exists():
            raise UniqueConstraintViolation("artifacts.id")

        temporary_paths: list[Path] = []
        try:
            temp_fd, temp_name = tempfile.mkstemp(
                prefix=f".{artifact.artifact_id}.", dir=learner_dir
            )
            temp_path = Path(temp_name)
            temporary_paths.append(temp_path)
            with os.fdopen(temp_fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            if hashlib.sha256(temp_path.read_bytes()).hexdigest() != artifact.sha256:
                raise ValueError("temporary content sha256 does not match metadata")
            os.replace(temp_path, data_path)
            temporary_paths.remove(temp_path)

            meta_fd, meta_name = tempfile.mkstemp(
                prefix=f".{artifact.artifact_id}.metadata.", dir=learner_dir
            )
            meta_temp = Path(meta_name)
            temporary_paths.append(meta_temp)
            with os.fdopen(meta_fd, "wb") as handle:
                handle.write(self._metadata(artifact))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(meta_temp, meta_path)
            temporary_paths.remove(meta_temp)
            return artifact
        except Exception:
            for path in temporary_paths:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            # If data was atomically installed but metadata failed, remove the
            # new object; no pre-existing destination was allowed above.
            if data_path.exists() and not meta_path.exists():
                data_path.unlink()
            try:
                learner_dir.rmdir()
            except OSError:
                pass
            raise

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None:
        data_path = self._data_path(artifact_id, learner_id)
        meta_path = self._meta_path(data_path)
        existing: Artifact | None = None
        if not meta_path.is_file():
            # A caller with the wrong learner scope must not be able to infer
            # the object through the normal read API, but deletion still
            # enforces ownership like the repository adapter does.
            for candidate in self.root.glob(f"*/{artifact_id}"):
                candidate_meta = self._meta_path(candidate)
                if candidate_meta.is_file():
                    try:
                        candidate_artifact = self._read_metadata(candidate_meta)
                    except (OSError, ValueError, TypeError):
                        continue
                    if candidate_artifact.artifact_id == artifact_id:
                        raise LearnerScopeViolation("artifact.learner_id")
        if meta_path.is_file():
            try:
                existing = self._read_metadata(meta_path)
            except (OSError, ValueError, TypeError):
                existing = None
        if existing is not None and existing.learner_id != learner_id:
            raise LearnerScopeViolation("artifact.learner_id")
        for path in (data_path, meta_path):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


# Short alias for callers that prefer the adapter's storage-oriented name.
LocalArtifacts = LocalArtifactStore
