"""Access token (JWT) and opaque refresh-token primitives.

JWT signing/verification is delegated to PyJWT rather than hand-rolled HMAC
code. PyJWT is chosen over python-jose because it is more actively
maintained, has a smaller dependency surface (no bundled crypto backends to
keep in sync), and defaults to an explicit `algorithms=[...]` allow-list on
decode, which is the primary defense against algorithm-confusion attacks.

JWT creation, validation, and parsing are kept as separate functions so each
concern can be tested and evolved independently:
  - `create_access_token`        -> Creation
  - `_decode_and_validate`       -> Validation (signature, exp, iss, aud)
  - `parse_access_token_claims`  -> Parsing (validated payload -> typed claims)

Refresh tokens remain opaque random strings (not JWTs); their creation and
hashing are unrelated to JWT hardening and are left as-is for the Session
module.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from src.config import Settings
from src.security.token_exceptions import (
    InvalidTokenError,
    MalformedTokenError,
    TokenError,
    TokenExpiredError,
)
from src.services.auth.refresh_token_service import RefreshTokenService

REQUIRED_CLAIMS = ["sub", "jti", "iat", "exp", "iss", "aud"]

__all__ = [
    "AccessTokenClaims",
    "TokenError",
    "InvalidTokenError",
    "TokenExpiredError",
    "MalformedTokenError",
    "create_access_token",
    "decode_access_token",
    "parse_access_token_claims",
    "create_refresh_token",
    "hash_refresh_token",
    "create_opaque_token",
    "hash_opaque_token",
]


@dataclass(frozen=True)
class AccessTokenClaims:
    """Typed view of a validated access token payload."""

    subject: str
    jti: str
    issued_at: int
    expires_at: int
    issuer: str
    audience: str
    session_id: str | None = None


def create_access_token(
    *,
    subject: str,
    settings: Settings,
    session_id: str | None = None,
) -> str:
    """JWT Creation.

    Only the claims required to identify and verify the token are included:
    `sub`, `jti`, `iat`, `exp`, `iss`, `aud`. `sid` is the one additional
    claim kept, because the existing Session module links access tokens to a
    session id for logout/rotation; role is intentionally *not* embedded
    here because authorization always re-reads the current role from the
    database, so a cached role claim would be a stale-privilege risk.
    """
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "sub": subject,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_access_token_minutes),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    if session_id:
        payload["sid"] = session_id

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_and_validate(token: str, settings: Settings) -> dict[str, object]:
    """JWT Validation.

    Verifies signature, expiry, issuer, and audience, and requires all
    mandatory claims to be present. Raises domain-specific token exceptions
    instead of leaking the underlying PyJWT exception types to callers.
    """
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": REQUIRED_CLAIMS},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Access token is invalid") from exc


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    """Backward-compatible dict-shaped decode (validated payload)."""
    return _decode_and_validate(token, settings)


def parse_access_token_claims(token: str, settings: Settings) -> AccessTokenClaims:
    """Token Parsing.

    Validates the token, then maps the raw payload into a typed
    `AccessTokenClaims` object so callers never deal with untyped dict
    lookups for security-sensitive values.
    """
    payload = _decode_and_validate(token, settings)
    try:
        return AccessTokenClaims(
            subject=str(payload["sub"]),
            jti=str(payload["jti"]),
            issued_at=int(payload["iat"]),
            expires_at=int(payload["exp"]),
            issuer=str(payload["iss"]),
            audience=str(payload["aud"]),
            session_id=str(payload["sid"]) if "sid" in payload else None,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MalformedTokenError(
            "Access token payload is missing or has malformed required claims"
        ) from exc


def create_refresh_token() -> str:
    return RefreshTokenService().create_token()


def hash_refresh_token(token: str) -> str:
    return RefreshTokenService().hash_token(token)


def create_opaque_token() -> str:
    return RefreshTokenService().create_token()


def hash_opaque_token(token: str) -> str:
    return RefreshTokenService().hash_token(token)
