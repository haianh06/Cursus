"""SSO handoff for Mock LMS's web viewer (mục 6.6).

Mock LMS and Cursus are genuinely separate origins (ADR-016) -- a browser
visiting Mock LMS directly cannot present Cursus's HttpOnly session cookie,
and the two apps deliberately do not share a JWT signing secret. This module
is a thin, scoped-down OIDC-authorization-code-style handoff: Cursus mints a
short-lived, single-use code for the *already logged in* user, Mock LMS
exchanges that code server-to-server for identity + role, then issues its
own session -- no parallel account system, no shared secret material besides
the one exchange-call credential below.

Not full LTI 1.3 (mục 15 already scopes that as a separate stretch goal never
built) -- no JWKS, no deployment IDs, no NRPS/AGS. Just enough to answer
"who is this, what role" once, safely.
"""
from __future__ import annotations

import secrets
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth import _extract_access_token, get_auth_service
from src.config import Settings, get_settings
from src.db.connection import get_db
from src.db import models
from src.services.auth.auth_service import AuthService
from src.services.auth_exceptions import InactiveUserError, UnauthorizedError

router = APIRouter(prefix="/auth/sso/mock-lms", tags=["mock-lms-sso"])

_CODE_TTL_SECONDS = 60
# In-memory, single-process store -- proportionate to this app's existing
# scope (same reasoning as the OAuth client store not needing Redis): codes
# live seconds, single-use, and a Cursus backend restart mid-handoff just
# means the user clicks the Mock LMS link again.
_pending_codes: dict[str, dict] = {}


def _cleanup_expired() -> None:
    now = time.time()
    for code in [c for c, v in _pending_codes.items() if v["expires_at"] < now]:
        _pending_codes.pop(code, None)


@router.get("/authorize")
async def authorize(
    request: Request,
    redirect_uri: str,
    state: str,
    authorization: str | None = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
):
    """Redirect target for Mock LMS's login-required pages. If the browser's
    Cursus cookie is valid, mints a one-time code and bounces back to
    `redirect_uri`. If not logged into Cursus, shows a plain blocking page
    (no auto-redirect-with-return -- the real usage path is: log into Cursus
    normally first, then open Mock LMS from Admin Console)."""
    _cleanup_expired()

    allowed_prefixes = tuple(
        p.strip() for p in settings.mock_lms_sso_allowed_redirect_prefixes.split(",") if p.strip()
    )
    if not redirect_uri.startswith(allowed_prefixes):
        raise HTTPException(status_code=400, detail="redirect_uri not allowed")

    try:
        token = _extract_access_token(authorization, request, settings)
        user = await auth_service.get_current_user(token)
    except (HTTPException, UnauthorizedError, InactiveUserError):
        return HTMLResponse(
            "<h3>Cần đăng nhập Cursus trước khi mở Mock LMS.</h3>"
            "<p>Đây là LMS mô phỏng, dùng chung danh tính với Cursus (không có "
            "tài khoản riêng). Đăng nhập Cursus trước, rồi mở lại Mock LMS.</p>",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    code = secrets.token_urlsafe(32)
    _pending_codes[code] = {"user_id": user.id, "expires_at": time.time() + _CODE_TTL_SECONDS}
    return RedirectResponse(url=f"{redirect_uri}?code={code}&state={state}")


class ExchangeRequest(BaseModel):
    code: str


class ExchangeResponse(BaseModel):
    user_id: str
    role: str
    name: str
    email: str


@router.post("/token", response_model=ExchangeResponse)
async def exchange_code(
    payload: ExchangeRequest,
    x_mock_lms_sso_secret: str | None = Header(default=None, alias="X-Mock-Lms-Sso-Secret"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ExchangeResponse:
    """Server-to-server only (called by Mock LMS's backend, never a browser).
    `X-Mock-Lms-Sso-Secret` is not a user credential -- it just proves the
    caller is really Mock LMS's server, not a random client guessing codes."""
    _cleanup_expired()

    if not settings.mock_lms_sso_shared_secret or not secrets.compare_digest(
        x_mock_lms_sso_secret or "", settings.mock_lms_sso_shared_secret
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_sso_secret")

    entry = _pending_codes.pop(payload.code, None)
    if not entry or entry["expires_at"] < time.time():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_or_expired_code")

    user = db.get(models.User, entry["user_id"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_not_found_or_inactive")

    return ExchangeResponse(
        user_id=user.id,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        name=user.full_name,
        email=user.email,
    )
