from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from yom_awel.domain.errors import DomainError
from yom_awel.transport.settings import Settings

SESSION_COOKIE = "yom_session"
SESSION_SECONDS = 7 * 24 * 3600
ISSUER = "yom-awel"
AUDIENCE = "learner"
PROVIDER = "web"
MAX_TOKEN_LENGTH = 4096


@dataclass(frozen=True)
class Identity:
    provider: str
    subject: str


class Authenticator:
    """Anonymous learner sessions signed by the API; the token lives in an HttpOnly cookie."""

    def __init__(self, settings: Settings) -> None:
        self._secret = settings.secret

    def issue(self) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(uuid4()),
                "iat": now,
                "exp": now + timedelta(seconds=SESSION_SECONDS),
                "iss": ISSUER,
                "aud": AUDIENCE,
            },
            self._secret,
            algorithm="HS256",
        )

    def verify(self, token: str | None) -> Identity:
        if not token or len(token) > MAX_TOKEN_LENGTH:
            raise DomainError("unauthorized", "Sign in required")
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                issuer=ISSUER,
                audience=AUDIENCE,
                options={"require": ["exp", "sub", "iss", "aud"]},
            )
            return Identity(PROVIDER, str(UUID(claims["sub"])))
        except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
            raise DomainError("unauthorized", "Sign in required") from exc
