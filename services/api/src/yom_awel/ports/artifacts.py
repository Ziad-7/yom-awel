from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from yom_awel.domain.entities import Artifact


@dataclass(frozen=True)
class ArtifactUploadAuthorization:
    """Short-lived authorization for one generated artifact object.

    The application layer only sees this typed value.  Provider adapters may
    use a signed URL/token pair, while local adapters can expose their own
    development endpoint without importing a transport framework.
    """

    artifact: Artifact
    upload_url: str
    upload_token: str | None
    expires_in_seconds: int
    headers: Mapping[str, str] = field(default_factory=dict)


class ArtifactStore(Protocol):
    async def get(self, artifact_id: UUID, learner_id: UUID) -> Artifact | None: ...

    async def authorize_upload(
        self, artifact: Artifact, *, expires_in_seconds: int = 300
    ) -> ArtifactUploadAuthorization: ...

    async def complete_upload(self, artifact_id: UUID, learner_id: UUID) -> Artifact: ...

    async def put(self, artifact: Artifact, content: bytes) -> Artifact: ...

    async def download(self, artifact_id: UUID, learner_id: UUID) -> bytes | None: ...

    async def delete(self, artifact_id: UUID, learner_id: UUID) -> None: ...
