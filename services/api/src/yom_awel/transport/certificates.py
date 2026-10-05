"""Tamper-evident public links to a learner's skills certificate.

A token is the learner id followed by an HMAC tag, keyed off the server secret with its own
domain label, so it cannot be guessed, forged, or edited into another learner's link. Nothing
is stored: the verify page always reads the learner's live graded records.
"""

import base64
import binascii
import hashlib
import hmac
from uuid import UUID

from yom_awel.domain.errors import DomainError

TAG_BYTES = 16
TOKEN_LENGTH = 43  # base64url of 16 id bytes + 16 tag bytes, unpadded
TOKEN_PATTERN = rf"^[A-Za-z0-9_-]{{{TOKEN_LENGTH}}}$"
_LABEL = b"yom-awel/certificate/v1"


def _tag(secret: str, learner_id: UUID) -> bytes:
    key = hmac.new(secret.encode(), _LABEL, hashlib.sha256).digest()
    return hmac.new(key, learner_id.bytes, hashlib.sha256).digest()[:TAG_BYTES]


def issue(secret: str, learner_id: UUID) -> str:
    raw = learner_id.bytes + _tag(secret, learner_id)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def verify(secret: str, token: str) -> UUID:
    try:
        raw = base64.urlsafe_b64decode(token + "=")
    except (binascii.Error, ValueError):
        raise DomainError("not_found", "Certificate not found") from None
    if len(token) != TOKEN_LENGTH or len(raw) != 16 + TAG_BYTES:
        raise DomainError("not_found", "Certificate not found")
    learner_id = UUID(bytes=raw[:16])
    if not hmac.compare_digest(raw[16:], _tag(secret, learner_id)):
        raise DomainError("not_found", "Certificate not found")
    return learner_id
