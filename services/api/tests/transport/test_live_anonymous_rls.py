"""Opt-in read-only cloud release gate using isolated, preseeded test identities.

M5_LIVE_AUTH_TESTS=1 requires every value below. Missing credentials fail the gate;
ordinary local CI skips it. Tokens must be issued by the configured test Supabase
project (including the missing-claim token); never use production identities.
"""

import os

import httpx
import jwt
import pytest

from yom_awel.domain.errors import DomainError
from yom_awel.transport.auth import Authenticator
from yom_awel.transport.settings import Settings

pytestmark = pytest.mark.integration


@pytest.fixture
def live():
    if os.getenv("M5_LIVE_AUTH_TESTS") != "1":
        pytest.skip("live anonymous/RLS gate not enabled; see issue #26")
    names = [
        "SUPABASE_URL",
        "SUPABASE_PUBLISHABLE_KEY",
        "M5_OWNER_JWT",
        "M5_OTHER_JWT",
        "M5_NON_ANONYMOUS_JWT",
        "M5_MISSING_ANONYMOUS_JWT",
        "M5_OWNER_ARTIFACT_ID",
        "M5_OWNER_OBJECT_PATH",
    ]
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        pytest.fail("Missing live test configuration: " + ", ".join(missing), pytrace=False)
    return {name: os.environ[name] for name in names}


@pytest.mark.asyncio
async def test_live_jwks_requires_anonymous_claim(live):
    auth = Authenticator(Settings(mode="cloud", supabase_url=live["SUPABASE_URL"].rstrip("/")))
    owner = await auth.verify("Bearer " + live["M5_OWNER_JWT"])
    other = await auth.verify("Bearer " + live["M5_OTHER_JWT"])
    assert owner.subject != other.subject
    for name in ["M5_NON_ANONYMOUS_JWT", "M5_MISSING_ANONYMOUS_JWT"]:
        assert auth.jwks is not None
        key = auth.jwks.get_signing_key_from_jwt(live[name])
        claims = jwt.decode(
            live[name],
            key.key,
            algorithms=["RS256", "ES256"],
            issuer=live["SUPABASE_URL"].rstrip("/") + "/auth/v1",
            audience="authenticated",
        )
        # Same owner subject with altered policy claims is essential: unrelated
        # identities would only exercise ownership, not the anonymous-only rule.
        assert claims["sub"] == owner.subject
        assert claims["role"] == "authenticated"
        if name == "M5_NON_ANONYMOUS_JWT":
            assert claims.get("is_anonymous") is False
        else:
            assert "is_anonymous" not in claims
        with pytest.raises(DomainError, match="Sign in required"):
            await auth.verify("Bearer " + live[name])


def test_live_rls_and_private_storage_reject_foreign_and_non_anonymous(live):
    # Positive owner reads prevent a missing fixture or blanket denial from
    # falsely passing the negative assertions.
    artifact_id = live["M5_OWNER_ARTIFACT_ID"]
    paths = [
        "/rest/v1/artifacts?select=artifact_id&artifact_id=eq." + artifact_id,
        "/storage/v1/object/authenticated/submissions/" + live["M5_OWNER_OBJECT_PATH"],
    ]
    with httpx.Client(
        base_url=live["SUPABASE_URL"].rstrip("/"), timeout=10, follow_redirects=False
    ) as client:
        for path in paths:
            response = client.get(
                path,
                headers={
                    "apikey": live["SUPABASE_PUBLISHABLE_KEY"],
                    "Authorization": "Bearer " + live["M5_OWNER_JWT"],
                },
            )
            assert response.status_code == 200
            if path.startswith("/rest/"):
                assert response.json() == [{"artifact_id": artifact_id}]
            for name in ["M5_OTHER_JWT", "M5_NON_ANONYMOUS_JWT", "M5_MISSING_ANONYMOUS_JWT"]:
                denied = client.get(
                    path,
                    headers={
                        "apikey": live["SUPABASE_PUBLISHABLE_KEY"],
                        "Authorization": "Bearer " + live[name],
                    },
                )
                if path.startswith("/rest/"):
                    assert denied.status_code in (200, 401, 403)
                    if denied.status_code == 200:
                        assert denied.json() == []
                else:
                    assert denied.status_code in (400, 401, 403, 404)
