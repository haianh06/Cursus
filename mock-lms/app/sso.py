"""Web-viewer identity for Mock LMS -- borrowed from Cursus, not a parallel
account system (mục 6.6). Replaces the old single shared HTTP Basic Auth
admin credential (22/08 patch) with the real per-user identity of whoever is
logged into Cursus, via the scoped OIDC-style code exchange implemented on
the Cursus side (`src/api/mock_lms_sso.py`).

Three pieces:
  - `build_authorize_redirect`: bounce an unauthenticated browser to Cursus.
  - `/sso/callback`: exchange the one-time code for identity, mint our own
    short-lived session cookie (JWT signed with THIS app's existing
    `security.SIGNING_SECRET` -- never Cursus's).
  - `require_identity` / `require_admin`: FastAPI dependencies used by
    `web.py` in place of the old `require_web_admin`.
"""
from __future__ import annotations

import base64
import os
import secrets
import time
from urllib.parse import quote, urlencode

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.security import SIGNING_SECRET

# This is the browser-visible Cursus URL. Must be "localhost", not
# "127.0.0.1" -- the browser treats them as different hosts for cookie
# purposes, and Cursus's frontend logs in via "localhost:8000".
CURSUS_BASE_URL = os.environ.get("CURSUS_BASE_URL", "http://localhost:8000")
# In Docker, the browser must be redirected to localhost while this container
# must call Cursus over the Compose network. Keep those concerns separate so
# SSO works both from a host process and from the edusync container.
CURSUS_INTERNAL_BASE_URL = os.environ.get("CURSUS_INTERNAL_BASE_URL", CURSUS_BASE_URL)
MOCK_LMS_PUBLIC_URL = os.environ.get("MOCK_LMS_PUBLIC_URL", "http://localhost:9000")
# Must match Cursus's MOCK_LMS_SSO_SHARED_SECRET -- proves the /token caller
# is really this app's backend, not a random client guessing codes.
SSO_SHARED_SECRET = os.environ.get("MOCK_LMS_SSO_SHARED_SECRET", "dev-only-mock-lms-sso-secret")

SESSION_COOKIE_NAME = "mock_lms_session"
STATE_COOKIE_NAME = "mock_lms_sso_state"
SESSION_TTL_SECONDS = 3600


def _sign_session(identity: dict) -> str:
    claims = {**identity, "iat": int(time.time()), "exp": int(time.time()) + SESSION_TTL_SECONDS}
    return jwt.encode(claims, SIGNING_SECRET, algorithm="HS256")


def _read_session(token: str) -> dict | None:
    try:
        return jwt.decode(token, SIGNING_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def build_authorize_redirect(return_to: str) -> RedirectResponse:
    """Sends the browser to Cursus's SSO authorize endpoint. `return_to` is
    the Mock LMS path the user actually wanted (e.g. `/courses/CEA201`) --
    round-tripped inside the opaque `state` value, not as its own query
    param, so Cursus's generic authorize endpoint doesn't need to know
    anything about Mock LMS's URL shape."""
    nonce = secrets.token_urlsafe(16)
    state_payload = f"{nonce}|{return_to}".encode()
    state = base64.urlsafe_b64encode(state_payload).decode()

    callback = f"{MOCK_LMS_PUBLIC_URL}/sso/callback"
    query = urlencode({"redirect_uri": callback, "state": state})
    authorize_url = f"{CURSUS_BASE_URL}/api/v1/auth/sso/mock-lms/authorize?{query}"

    response = RedirectResponse(url=authorize_url)
    response.set_cookie(
        STATE_COOKIE_NAME, nonce, max_age=300, httponly=True, samesite="lax"
    )
    return response


async def exchange_code(code: str) -> dict:
    """Server-to-server call to Cursus -- never done from the browser."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            f"{CURSUS_INTERNAL_BASE_URL}/api/v1/auth/sso/mock-lms/token",
            json={"code": code},
            headers={"X-Mock-Lms-Sso-Secret": SSO_SHARED_SECRET},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="cursus_sso_exchange_failed")
    return resp.json()


def decode_state(state: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(state.encode()).decode()
        nonce, return_to = raw.split("|", 1)
        return nonce, return_to
    except Exception as exc:  # noqa: BLE001 -- any malformed state is just invalid
        raise HTTPException(status_code=400, detail="invalid_state") from exc


def require_identity(request: Request):
    """Any logged-in Cursus user (Student/Instructor/Admin) -- gates the
    *page* routes in web.py (GET /courses, GET /courses/{code}). A missing/
    expired session there raises _NeedsLogin, which main.py's exception
    handler turns into a redirect to Cursus's login -- correct for a real
    browser navigation, which follows redirects across origins fine."""
    identity = _read_identity_cookie(request)
    if not identity:
        return_to = str(request.url.path)
        if request.url.query:
            return_to += f"?{request.url.query}"
        raise _NeedsLogin(return_to)
    return identity


def require_identity_json(request: Request):
    """Same check as require_identity, for the /web-api/* JSON routes the
    SPA calls with fetch() -- those must never trigger _NeedsLogin's
    cross-origin redirect. `fetch()` doesn't navigate the browser on a
    redirect: it either fails outright (opaque redirect to another origin)
    or, if it somehow succeeded, would hand back Cursus's *login page HTML*
    as if it were the JSON payload the SPA asked for. A plain 401 lets the
    SPA's own fetch wrapper (frontend/src/lib/api.ts) detect it and force a
    real top-level navigation back to this same page instead, which *does*
    follow the SSO redirect correctly."""
    identity = _read_identity_cookie(request)
    if not identity:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")
    return identity


def _read_identity_cookie(request: Request) -> dict | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    return _read_session(token) if token else None


def require_admin(identity: dict = Depends(require_identity)):
    if identity.get("role") != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
    return identity


def require_admin_json(identity: dict = Depends(require_identity_json)):
    if identity.get("role") != "ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
    return identity


class _NeedsLogin(Exception):
    def __init__(self, return_to: str):
        self.return_to = return_to
