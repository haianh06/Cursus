import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.security.passwords import verify_password
from src.security.tokens import hash_opaque_token
from tests.support.invite_helpers import create_test_invite


@pytest.mark.asyncio
async def test_forgot_password_returns_generic_response(client):
    response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": "does-not-exist@example.test"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_password_reset_updates_password_and_revokes_sessions(client, monkeypatch):
    email = f"reset.user.{uuid.uuid4().hex}@example.test"
    old_password = "StrongPassword123"
    new_password = "NewStrongPassword456"
    reset_token = f"reset-token-{uuid.uuid4().hex}"
    await _register_verified_user(client, monkeypatch, email, old_password)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password, "remember_me": True},
    )
    assert login_response.status_code == 200
    old_access_token = login_response.json()["token"]

    monkeypatch.setattr(
        "src.services.auth.password_reset_service.create_opaque_token",
        lambda: reset_token,
    )
    forgot_response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )
    assert forgot_response.status_code == 200

    reset_response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": new_password},
    )
    assert reset_response.status_code == 200

    old_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login_response.status_code == 401

    refresh_response = await client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401

    sessions_response = await client.get(
        "/api/v1/auth/sessions",
        headers={"Authorization": f"Bearer {old_access_token}"},
    )
    assert sessions_response.status_code == 200
    assert sessions_response.json() == []

    new_login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login_response.status_code == 200

    assert _password_reset_audit_event_exists("PASSWORD_RESET_REQUESTED", "ALLOW")
    assert _password_reset_audit_event_exists("PASSWORD_RESET_SUCCESS", "ALLOW")


@pytest.mark.asyncio
async def test_password_reset_stores_only_token_hash(client, monkeypatch):
    email = f"reset.hash.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    reset_token = f"hash-reset-token-{uuid.uuid4().hex}"
    await _register_verified_user(client, monkeypatch, email, password)

    monkeypatch.setattr(
        "src.services.auth.password_reset_service.create_opaque_token",
        lambda: reset_token,
    )
    response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )

    assert response.status_code == 200
    stored_token = _get_password_reset_token(reset_token)
    assert stored_token is not None
    assert stored_token.token_hash == hash_opaque_token(reset_token)
    assert stored_token.token_hash != reset_token


@pytest.mark.asyncio
async def test_expired_password_reset_token_is_rejected(client, monkeypatch):
    email = f"reset.expired.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    reset_token = f"expired-reset-token-{uuid.uuid4().hex}"
    await _register_verified_user(client, monkeypatch, email, password)
    await _request_password_reset(client, monkeypatch, email, reset_token)
    _expire_password_reset_token(reset_token)

    response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": "NewStrongPassword456"},
    )

    assert response.status_code == 400
    assert _password_reset_audit_event_exists("PASSWORD_RESET_FAILED", "DENY")


@pytest.mark.asyncio
async def test_reused_password_reset_token_is_rejected(client, monkeypatch):
    email = f"reset.replay.{uuid.uuid4().hex}@example.test"
    old_password = "StrongPassword123"
    new_password = "NewStrongPassword456"
    reset_token = f"replay-reset-token-{uuid.uuid4().hex}"
    await _register_verified_user(client, monkeypatch, email, old_password)
    await _request_password_reset(client, monkeypatch, email, reset_token)

    first_response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": new_password},
    )
    assert first_response.status_code == 200

    replay_response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": "AnotherStrongPassword789"},
    )
    assert replay_response.status_code == 400


@pytest.mark.asyncio
async def test_invalid_password_reset_token_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/password/reset",
        json={
            "token": f"invalid-reset-token-{uuid.uuid4().hex}",
            "new_password": "NewStrongPassword456",
        },
    )

    assert response.status_code == 400
    assert _password_reset_audit_event_exists("PASSWORD_RESET_FAILED", "DENY")


@pytest.mark.asyncio
async def test_inactive_user_password_reset_token_is_rejected(client, monkeypatch):
    email = f"reset.inactive.{uuid.uuid4().hex}@example.test"
    old_password = "StrongPassword123"
    reset_token = f"inactive-reset-token-{uuid.uuid4().hex}"
    await _register_verified_user(client, monkeypatch, email, old_password)
    await _request_password_reset(client, monkeypatch, email, reset_token)
    _deactivate_user(email)

    response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": reset_token, "new_password": "NewStrongPassword456"},
    )

    assert response.status_code == 400
    assert _stored_password_matches(email, old_password) is True


@pytest.mark.asyncio
async def test_already_used_password_reset_token_is_rejected(client, monkeypatch):
    email = f"reset.used.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    used_token = f"used-reset-token-{uuid.uuid4().hex}"
    await _register_verified_user(client, monkeypatch, email, password)
    _insert_used_password_reset_token(email, used_token)

    response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": used_token, "new_password": "NewStrongPassword456"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_for_inactive_user_does_not_issue_token(client, monkeypatch):
    email = f"reset.inactive.request.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    reset_token = f"inactive-request-token-{uuid.uuid4().hex}"
    await _register_verified_user(client, monkeypatch, email, password)
    _deactivate_user(email)

    monkeypatch.setattr(
        "src.services.auth.password_reset_service.create_opaque_token",
        lambda: reset_token,
    )
    response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )

    assert response.status_code == 200
    assert _get_password_reset_token(reset_token) is None


@pytest.mark.asyncio
async def test_new_password_reset_request_invalidates_previous_token(client, monkeypatch):
    email = f"reset.invalidate.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    first_token = f"first-reset-token-{uuid.uuid4().hex}"
    second_token = f"second-reset-token-{uuid.uuid4().hex}"
    tokens = iter([first_token, second_token])
    await _register_verified_user(client, monkeypatch, email, password)
    monkeypatch.setattr(
        "src.services.auth.password_reset_service.create_opaque_token",
        lambda: next(tokens),
    )

    first_response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )
    assert first_response.status_code == 200
    second_response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )
    assert second_response.status_code == 200

    stale_response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": first_token, "new_password": "NewStrongPassword456"},
    )
    assert stale_response.status_code == 400

    valid_response = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": second_token, "new_password": "NewStrongPassword456"},
    )
    assert valid_response.status_code == 200


async def _register_verified_user(
    client,
    monkeypatch,
    email: str,
    password: str,
) -> None:
    invite_token = create_test_invite(email, role="STUDENT")
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Password Reset User",
            "invite_token": invite_token,
        },
    )
    assert register_response.status_code == 201
    # Invited users are pre-verified, so no /auth/email/verify step is needed.


async def _request_password_reset(
    client,
    monkeypatch,
    email: str,
    token: str,
) -> None:
    monkeypatch.setattr(
        "src.services.auth.password_reset_service.create_opaque_token",
        lambda: token,
    )
    forgot_response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )
    assert forgot_response.status_code == 200


def _get_password_reset_token(raw_token: str) -> models.VerificationToken | None:
    db = SessionLocal()
    try:
        return (
            db.query(models.VerificationToken)
            .filter_by(
                token_hash=hash_opaque_token(raw_token),
                purpose="PASSWORD_RESET",
            )
            .first()
        )
    finally:
        db.close()


def _expire_password_reset_token(raw_token: str) -> None:
    db = SessionLocal()
    try:
        token = (
            db.query(models.VerificationToken)
            .filter_by(token_hash=hash_opaque_token(raw_token))
            .first()
        )
        assert token is not None
        token.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()


def _deactivate_user(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        assert user is not None
        user.is_active = False
        db.commit()
    finally:
        db.close()


def _stored_password_matches(email: str, password: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        assert user is not None
        return verify_password(password, user.password_hash)
    finally:
        db.close()


def _insert_used_password_reset_token(email: str, raw_token: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        assert user is not None
        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            models.VerificationToken(
                id=f"vrt_{uuid.uuid4().hex}",
                user_id=user.id,
                token_hash=hash_opaque_token(raw_token),
                purpose="PASSWORD_RESET",
                used_at=now,
                expires_at=now + timedelta(minutes=30),
                created_at=now,
            )
        )
        db.commit()
    finally:
        db.close()


def _password_reset_audit_event_exists(event_type: str, decision: str) -> bool:
    db = SessionLocal()
    try:
        return (
            db.query(models.AuditLog)
            .filter_by(event_type=event_type, decision=decision)
            .first()
            is not None
        )
    finally:
        db.close()
