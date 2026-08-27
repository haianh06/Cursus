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

from src.api.auth import _extract_access_token, _extract_refresh_token, _set_auth_cookies, get_auth_service
from src.config import Settings, get_settings
from src.db import models
from src.db.connection import get_db
from src.services.auth.auth_service import AuthService
from src.services.auth.session_service import SessionError
from src.services.auth_exceptions import InactiveUserError, UnauthorizedError

router = APIRouter(prefix="/auth/sso/mock-lms", tags=["mock-lms-sso"])

# Shown by authorize() below when the browser has no valid Cursus session --
# was a bare two-line HTMLResponse with no way out (deliberately no
# auto-redirect-with-return, see authorize()'s docstring), which left a
# visitor on a dead-end page with nothing to click. Styled to match Cursus's
# own auth screens and given an actual way forward: log in, then reopen
# Mock LMS from wherever they got this link (Admin Console's EduSync link,
# or the Student/Instructor sidebar if that's ever wired up).
_LOGIN_REQUIRED_PAGE = """<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cần đăng nhập — EduSync</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root {{ color-scheme: light; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
    background: #f8fafc; font-family: 'Inter', -apple-system, "Segoe UI", Roboto, system-ui, sans-serif;
    color: #0f172a; padding: 24px;
  }}
  .card {{
    max-width: 420px; width: 100%; background: #fff; border: 1px solid #e2e8f0; border-radius: 16px;
    padding: 32px 28px; box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  }}
  .icon {{
    width: 44px; height: 44px; border-radius: 10px; background: #2468C9;
    display: flex; align-items: center; justify-content: center; margin-bottom: 16px;
  }}
  .icon svg {{ width: 22px; height: 22px; }}
  h1 {{
    font-family: 'Sora', 'Inter', sans-serif; font-size: 18px; font-weight: 700;
    margin: 0 0 8px; letter-spacing: -0.02em;
  }}
  p {{ font-size: 13.5px; line-height: 1.6; color: #475569; margin: 0 0 24px; }}
  a.cta {{
    display: inline-flex; align-items: center; gap: 6px; background: #2468C9; color: #fff;
    text-decoration: none; font-size: 13.5px; font-weight: 600; padding: 10px 18px; border-radius: 10px;
    transition: background-color 0.15s ease;
  }}
  a.cta:hover {{ background: #1B57A8; }}
</style>
</head>
<body>
  <div class="card">
    <div class="icon">
      <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M12 3L2 8l10 5 10-5-10-5z" fill="#fff"/>
        <path d="M6 12v5c0 1.5 2.5 3.5 6 3.5s6-2 6-3.5v-5" stroke="#fff" stroke-width="1.6" stroke-linecap="round"/>
      </svg>
    </div>
    <h1>Cần đăng nhập Cursus trước</h1>
    <p>
      EduSync dùng chung danh tính với Cursus — không có tài khoản riêng.
      Đăng nhập Cursus xong, quay lại mở EduSync lần nữa (từ Admin Console, hoặc link đã đưa bạn tới đây).
    </p>
    <a class="cta" href="{login_url}">Đăng nhập Cursus &rarr;</a>
  </div>
</body>
</html>"""

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

    refreshed_cookies: tuple[str, str, bool] | None = None  # (access, refresh, remember_me)
    try:
        token = _extract_access_token(authorization, request, settings)
        user = await auth_service.get_current_user(token)
    except (HTTPException, UnauthorizedError, InactiveUserError):
        # The access-token cookie is short-lived (jwt_access_token_minutes,
        # 15 min by default) and this link is a plain cross-origin <a href>
        # navigation (App.jsx's EduSync Topbar link), so it never goes
        # through the SPA's own fetch-level 401-retry (frontend/src/lib/
        # api.js refreshSession()). Without this fallback, a session that's
        # still perfectly valid -- just idle a few minutes -- dead-ends here
        # instead of transparently refreshing, same as any other Cursus page
        # would on the next API call.
        refresh_token = _extract_refresh_token(request, settings)
        if not refresh_token:
            login_url = f"{settings.cursus_frontend_url.rstrip('/')}/login"
            return HTMLResponse(_LOGIN_REQUIRED_PAGE.format(login_url=login_url), status_code=status.HTTP_401_UNAUTHORIZED)
        try:
            result = await auth_service.refresh_access_token(refresh_token)
        except (UnauthorizedError, InactiveUserError, SessionError):
            login_url = f"{settings.cursus_frontend_url.rstrip('/')}/login"
            return HTMLResponse(_LOGIN_REQUIRED_PAGE.format(login_url=login_url), status_code=status.HTTP_401_UNAUTHORIZED)
        user = result.user
        refreshed_cookies = (result.access_token, result.refresh_token, result.session.remember_me)

    code = secrets.token_urlsafe(32)
    _pending_codes[code] = {"user_id": user.id, "expires_at": time.time() + _CODE_TTL_SECONDS}
    response = RedirectResponse(url=f"{redirect_uri}?code={code}&state={state}")
    if refreshed_cookies:
        access_token, refresh_token, remember_me = refreshed_cookies
        _set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_token,
            settings=settings,
            remember_me=remember_me,
        )
    return response


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
