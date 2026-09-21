from typing import Protocol
from uuid import UUID

from yom_awel.domain.entities import Artifact


class ArtifactStore(Protocol):
    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None: ...

    async def put(self, artifact: Artifact, content: bytes) -> Artifact: ...

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None: ...

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None: ...
