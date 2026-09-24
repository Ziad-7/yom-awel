from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from yom_awel.domain.contracts import artifact_content_type
from yom_awel.domain.entities import Artifact
from yom_awel.domain.errors import UniqueConstraintViolation
from yom_awel.persistence import local_artifacts
from yom_awel.persistence.local_artifacts import LocalArtifactStore


def _artifact(root_name: str) -> tuple[Artifact, bytes]:
    content = b"safe local content"
    return (
        Artifact(
            artifact_id=uuid4(),
            learner_id=uuid4(),
            filename=root_name,
            content_type=artifact_content_type(root_name),
            size_bytes=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        ),
        content,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename",
    [
        "../escape.csv",
        "/absolute/escape.csv",
        "nested\\..\\escape.csv",
        "unicode∕separator.csv",
        "same.csv",
    ],
)
async def test_generated_paths_ignore_original_filename(tmp_path: Path, filename: str) -> None:
    store = LocalArtifactStore(tmp_path)
    artifact, content = _artifact(filename)
    await store.put(artifact, content)

    expected = tmp_path / str(artifact.learner_id) / str(artifact.artifact_id)
    assert expected.is_file()
    assert filename not in str(expected)
    assert await store.get(artifact.artifact_id, artifact.learner_id) == artifact
    assert await store.download(artifact.artifact_id, artifact.learner_id) == content

    await store.delete(artifact.artifact_id, artifact.learner_id)
    assert not expected.exists()
    assert await store.get(artifact.artifact_id, artifact.learner_id) is None


@pytest.mark.asyncio
async def test_repeated_artifact_id_is_unique(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    artifact, content = _artifact("same.csv")
    await store.put(artifact, content)
    with pytest.raises(UniqueConstraintViolation):
        await store.put(artifact, content)


@pytest.mark.asyncio
async def test_failed_hash_write_leaves_no_files(tmp_path: Path) -> None:
    store = LocalArtifactStore(tmp_path)
    artifact, content = _artifact("failed.csv")
    invalid = artifact.model_copy(update={"sha256": "0" * 64})
    with pytest.raises(ValueError):
        await store.put(invalid, content)
    assert list(tmp_path.rglob("*")) == []


@pytest.mark.asyncio
async def test_failed_metadata_rename_cleans_data_and_temp_files(
    tmp_path: Path, monkeypatch
) -> None:
    store = LocalArtifactStore(tmp_path)
    artifact, content = _artifact("rename-failure.csv")
    original_replace = local_artifacts.os.replace
    calls = 0

    def fail_metadata_replace(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated metadata failure")
        return original_replace(source, destination)

    monkeypatch.setattr(local_artifacts.os, "replace", fail_metadata_replace)
    with pytest.raises(OSError):
        await store.put(artifact, content)
    assert list(tmp_path.rglob("*.metadata.json")) == []
    assert list(tmp_path.rglob(str(artifact.artifact_id))) == []
