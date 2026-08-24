from datetime import UTC, datetime, timedelta

import pytest

from src.db.connection import SessionLocal
from src.db.models import AuthSession

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


def _refresh_set_cookie(response) -> str:
    for value in response.headers.get_list("set-cookie"):
        if value.startswith(f"{REFRESH_COOKIE_NAME}="):
            return value
    return ""
