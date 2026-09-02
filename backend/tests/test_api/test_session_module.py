import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI, Response
from httpx import ASGITransport, AsyncClient

from src.api.auth import _clear_auth_cookies
from src.config import Settings
from src.db.connection import SessionLocal
from src.db.models import AuthSession, UserRole

REFRESH_COOKIE_NAME = "refresh_token"


@pytest.mark.asyncio
async def test_login_creates_listable_session(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
            "remember_me": True,
        },
    )

    assert login_response.status_code == 200
    login_data = login_response.json()

    sessions_response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {login_data['token']}"},
    )

    assert sessions_response.status_code == 200
    sessions = sessions_response.json()
    assert any(session["id"] == login_data["session"]["id"] for session in sessions)
    assert login_data["session"]["remember_me"] is True


@pytest.mark.asyncio
async def test_refresh_rotates_session_token(client):
    login_response = await _login(client)
    assert login_response.status_code == 200
    original_session_id = login_response.json()["session"]["id"]

    refresh_response = await client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    refresh_data = refresh_response.json()
    assert refresh_data["token"]
    assert refresh_data["session"]["id"] != original_session_id


@pytest.mark.asyncio
async def test_refresh_reuse_revokes_token_family(client):
    login_response = await _login(client)
    assert login_response.status_code == 200
    original_session_id = login_response.json()["session"]["id"]
    original_refresh_token = client.cookies.get(REFRESH_COOKIE_NAME)
    assert original_refresh_token

    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    rotated_refresh_token = client.cookies.get(REFRESH_COOKIE_NAME)
    assert rotated_refresh_token and rotated_refresh_token != original_refresh_token

    client.cookies.set(REFRESH_COOKIE_NAME, original_refresh_token)
    reuse_response = await client.post("/api/v1/auth/refresh")
    assert reuse_response.status_code == 401

    family_id = _session_family_id(original_session_id)
    assert family_id is not None
    assert _all_family_sessions_revoked(family_id)

    client.cookies.set(REFRESH_COOKIE_NAME, rotated_refresh_token)
    revoked_family_response = await client.post("/api/v1/auth/refresh")
    assert revoked_family_response.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_current_session(client):
    login_response = await _login(client)
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    logout_response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_response.status_code == 200

    sessions_response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert sessions_response.status_code == 200
    session_ids = {session["id"] for session in sessions_response.json()}
    assert login_response.json()["session"]["id"] not in session_ids


@pytest.mark.asyncio
async def test_logout_all_revokes_all_current_user_sessions(client):
    first_login = await _login(client, user_agent="Device One")
    second_login = await _login(client, user_agent="Device Two")
    assert first_login.status_code == 200
    assert second_login.status_code == 200

    logout_response = await client.post(
        "/api/v1/auth/logout-all",
        headers={"Authorization": f"Bearer {second_login.json()['token']}"},
    )
    assert logout_response.status_code == 200

    sessions_response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {second_login.json()['token']}"},
    )
    assert sessions_response.status_code == 200
    assert sessions_response.json() == []


@pytest.mark.asyncio
async def test_expired_refresh_token_is_rejected(client):
    login_response = await _login(client)
    assert login_response.status_code == 200
    session_id = login_response.json()["session"]["id"]
    _expire_session(session_id)

    refresh_response = await client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 401
    assert _session_revoked_reason(session_id) == "EXPIRED"


@pytest.mark.asyncio
async def test_refresh_failure_clears_stale_auth_cookies(client):
    """A refresh token that fails for reasons *other than* a revoked/expired
    session (e.g. the user got deactivated) must still clear the auth
    cookies. Otherwise the browser keeps the dead access/refresh cookies
    forever, CsrfProtectionMiddleware keeps requiring a CSRF header on every
    mutating request because it sees those cookies, and the frontend can
    never repopulate its in-memory CSRF token because refresh keeps failing
    the same way -- a permanent "CSRF validation failed" lockout with no
    way out except manually clearing cookies (found via a live user report).

    Uses a throwaway user (not the shared `student.demo@example.test`
    fixture other tests in this file log in as) since it gets permanently
    deactivated below.
    """
    from tests.support.semester_practice_fixtures import PASSWORD, ensure_org, ensure_user

    org_id = ensure_org("refresh-lockout-org", "Refresh Lockout Org")
    email = f"refresh.lockout.{uuid.uuid4().hex}@example.test"
    user_id = ensure_user(email=email, org_id=org_id, role=UserRole.STUDENT, password=PASSWORD)

    login_response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": PASSWORD}
    )
    assert login_response.status_code == 200

    _deactivate_user(user_id)

    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401

    for cookie_name in (REFRESH_COOKIE_NAME, "access_token", "csrf_token"):
        cleared = _refresh_set_cookie(refresh_response, cookie_name)
        assert cleared, f"expected a Set-Cookie clearing {cookie_name}"
        assert "Max-Age=0" in cleared


@pytest.mark.asyncio
async def test_clear_auth_cookies_matches_secure_and_samesite_of_the_originals():
    """Per RFC 6265bis, a Set-Cookie that is not itself Secure can never
    overwrite/delete an existing Secure cookie of the same (name, domain,
    path) -- browsers silently drop the attempt even though the response
    itself arrived over HTTPS. `Response.delete_cookie()` defaults to
    secure=False, samesite="lax", so calling it without matching the
    original cookies' actual attributes is a *silent no-op* in any
    cross-domain production deployment using Secure + SameSite=None cookies
    (Vercel frontend, Render backend): POST /auth/logout returns 200, but
    the browser keeps the old cookies, and the next page load/refresh
    silently logs the user right back in. Reproduced live: production
    logout returned 200 with the cookies still present afterward, and a
    plain page reload landed the user back on /student, fully
    authenticated, with no login step at all.

    This asserts _clear_auth_cookies() emits Set-Cookie headers with the
    same Secure/SameSite attributes production actually uses (Secure=True,
    SameSite=None for cross-domain), not just default-attribute headers
    that happen to include Max-Age=0.
    """
    settings = Settings(
        jwt_secret_key="unit-test-secret-key-at-least-32-characters-long",
        app_env="production",
        access_token_cookie_secure=True,
        access_token_cookie_samesite="none",
        refresh_token_cookie_secure=True,
        refresh_token_cookie_samesite="none",
        google_api_key="test-google-key",
        openai_api_key="test-openai-key",
        crisis_escalation_email="crisis@example.test",
        database_url="postgresql://appuser:secret@db-host/appdb",
    )

    app = FastAPI()

    @app.post("/clear")
    async def clear_endpoint(response: Response):
        _clear_auth_cookies(response, settings)
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        response = await client.post("/clear")

    for cookie_name in ("access_token", "refresh_token", "csrf_token"):
        header = _refresh_set_cookie(response, cookie_name)
        assert header, f"expected a Set-Cookie clearing {cookie_name}"
        assert "secure" in header.lower(), f"{cookie_name} clear is missing Secure: {header}"
        assert "samesite=none" in header.lower(), f"{cookie_name} clear is missing SameSite=None: {header}"


def _deactivate_user(user_id: str) -> None:
    db = SessionLocal()
    try:
        from src.db.models import User

        user = db.query(User).filter_by(id=user_id).first()
        assert user is not None
        user.is_active = False
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_remember_me_extends_session_and_cookie_lifetime(client):
    login_response = await _login(client, remember_me=True)
    assert login_response.status_code == 200
    session = login_response.json()["session"]

    created_at = datetime.fromisoformat(session["created_at"])
    expires_at = datetime.fromisoformat(session["expires_at"])
    assert expires_at - created_at >= timedelta(days=29)

    refresh_set_cookie = _refresh_set_cookie(login_response)
    assert "Max-Age=2592000" in refresh_set_cookie
    assert "HttpOnly" in refresh_set_cookie
    assert "SameSite=strict" in refresh_set_cookie


@pytest.mark.asyncio
async def test_refresh_uses_sliding_session_expiration(client):
    login_response = await _login(client)
    assert login_response.status_code == 200
    session_id = login_response.json()["session"]["id"]
    old_expires_at = _shorten_session_expiry(session_id)

    refresh_response = await client.post("/api/v1/auth/refresh")

    assert refresh_response.status_code == 200
    new_expires_at = datetime.fromisoformat(refresh_response.json()["session"]["expires_at"])
    assert new_expires_at > old_expires_at + timedelta(days=5)


@pytest.mark.asyncio
async def test_multiple_devices_create_distinct_sessions(client):
    first_login = await _login(client, user_agent="Device One")
    second_login = await _login(client, user_agent="Device Two")
    assert first_login.status_code == 200
    assert second_login.status_code == 200

    sessions_response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {second_login.json()['token']}"},
    )

    assert sessions_response.status_code == 200
    session_ids = {session["id"] for session in sessions_response.json()}
    assert first_login.json()["session"]["id"] in session_ids
    assert second_login.json()["session"]["id"] in session_ids


async def _login(
    client,
    *,
    remember_me: bool = False,
    user_agent: str = "pytest-device",
):
    return await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
            "remember_me": remember_me,
        },
        headers={"user-agent": user_agent},
    )


def _session_family_id(session_id: str) -> str | None:
    db = SessionLocal()
    try:
        session = db.query(AuthSession).filter_by(id=session_id).first()
        return session.token_family_id if session else None
    finally:
        db.close()


def _all_family_sessions_revoked(token_family_id: str) -> bool:
    db = SessionLocal()
    try:
        sessions = db.query(AuthSession).filter_by(token_family_id=token_family_id).all()
        return bool(sessions) and all(session.revoked_at for session in sessions)
    finally:
        db.close()


def _expire_session(session_id: str) -> None:
    db = SessionLocal()
    try:
        session = db.query(AuthSession).filter_by(id=session_id).first()
        assert session is not None
        session.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()


def _session_revoked_reason(session_id: str) -> str | None:
    db = SessionLocal()
    try:
        session = db.query(AuthSession).filter_by(id=session_id).first()
        return session.revoked_reason if session else None
    finally:
        db.close()


def _shorten_session_expiry(session_id: str) -> datetime:
    db = SessionLocal()
    try:
        session = db.query(AuthSession).filter_by(id=session_id).first()
        assert session is not None
        now = datetime.now(UTC).replace(tzinfo=None)
        session.expires_at = now + timedelta(days=1)
        session.absolute_expires_at = now + timedelta(days=30)
        db.commit()
        return session.expires_at
    finally:
        db.close()


def _refresh_set_cookie(response, cookie_name: str = REFRESH_COOKIE_NAME) -> str:
    for value in response.headers.get_list("set-cookie"):
        if value.startswith(f"{cookie_name}="):
            return value
    return ""
