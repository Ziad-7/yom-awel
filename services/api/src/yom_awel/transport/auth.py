import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import PyJWKClient

from yom_awel.domain.errors import DomainError
from yom_awel.transport.settings import Settings


@dataclass(frozen=True)
class Identity:
    provider: str
    subject: str


class Authenticator:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.jwks = (
            PyJWKClient(
                settings.supabase_url + "/auth/v1/.well-known/jwks.json",
                cache_jwk_set=True,
                lifespan=300,
                timeout=5,
            )
            if settings.mode == "cloud"
            else None
        )

    def local_session(self) -> str:
        if self.settings.mode != "local":
            raise DomainError("not_found", "Local sessions are disabled")
        now = datetime.now(UTC)
        return jwt.encode(
            {
                "sub": str(uuid4()),
                "iat": now,
                "exp": now + timedelta(days=7),
                "iss": "yom-awel-local",
                "aud": "authenticated",
            },
            self.settings.secret,
            algorithm="HS256",
        )

    async def verify(self, authorization: str | None) -> Identity:
        if (
            not authorization
            or not authorization.startswith("Bearer ")
            or len(authorization) > 8192
        ):
            raise DomainError("unauthorized", "Sign in required")
        token = authorization[7:]
        try:
            if self.jwks is not None:
                header = jwt.get_unverified_header(token)
                if header.get("alg") not in ("RS256", "ES256") or not header.get("kid"):
                    raise jwt.InvalidTokenError()
                key = await asyncio.to_thread(self.jwks.get_signing_key_from_jwt, token)
                claims = jwt.decode(
                    token,
                    key.key,
                    algorithms=["RS256", "ES256"],
                    issuer=self.settings.supabase_url + "/auth/v1",
                    audience="authenticated",
                    options={"require": ["exp", "sub", "iss", "aud"]},
                )
                if claims.get("role") != "authenticated" or claims.get("is_anonymous") is not True:
                    raise jwt.InvalidTokenError()
                provider = "supabase"
            else:
                claims = jwt.decode(
                    token,
                    self.settings.secret,
                    algorithms=["HS256"],
                    issuer="yom-awel-local",
                    audience="authenticated",
                    options={"require": ["exp", "sub", "iss", "aud"]},
                )
                provider = "local"
            subject = str(UUID(claims["sub"]))
            return Identity(provider, subject)
        except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
            raise DomainError("unauthorized", "Sign in required") from exc
