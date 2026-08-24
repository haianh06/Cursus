"""OAuth2 client_credentials (RFC 6749 4.4) -- own signing key, independent of Cursus's.

Deliberately does NOT reuse Cursus's `src/security/tokens.py` signing secret: the whole
point of this app is to be a genuinely separate system, so if Cursus's key rotated, this
app's tokens must be unaffected, and vice versa.
"""
from __future__ import annotations

import os
import secrets
import time
import uuid

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
ISSUER = "mock-lms"
AUDIENCE = "cursus"
ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 3600

# Dev-only fallback so `uvicorn app.main:app` works out of the box; override via env for
# anything beyond local dev.
SIGNING_SECRET = os.environ.get("MOCK_LMS_JWT_SECRET", "dev-only-mock-lms-secret-do-not-use-in-prod")

_hasher = PasswordHasher()


def hash_secret(raw_secret: str) -> str:
    return _hasher.hash(raw_secret)


def verify_secret(raw_secret: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw_secret)
    except VerifyMismatchError:
        return False


def issue_access_token(client_id: str) -> tuple[str, int]:
    now = int(time.time())
    claims = {
        "sub": client_id,
        "jti": uuid.uuid4().hex,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    token = jwt.encode(claims, SIGNING_SECRET, algorithm=ALGORITHM)
    return token, TOKEN_TTL_SECONDS


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError on any invalid/expired/mis-audienced token."""
    return jwt.decode(
        token,
        SIGNING_SECRET,
        algorithms=[ALGORITHM],
        audience=AUDIENCE,
        issuer=ISSUER,
    )


# ── Human-facing web UI auth ────────────────────────────────────────────────
# [SỬA 23/08] The single shared HTTP Basic Auth admin account (22/08 patch,
# MOCK_LMS_ADMIN_USER/MOCK_LMS_ADMIN_PASSWORD_HASH) is gone -- replaced by
# real Cursus identity via a scoped SSO code-exchange (see `app/sso.py` +
# `src/api/mock_lms_sso.py` on the Cursus side). No parallel credential to
# manage here anymore; `require_identity`/`require_admin` in `app/sso.py` are
# what `web.py` uses now.
