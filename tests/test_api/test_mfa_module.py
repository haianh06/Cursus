import time
import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.services.auth.mfa_service import generate_totp
from tests.support.invite_helpers import create_test_invite


@pytest.mark.asyncio
async def test_totp_setup_enable_and_login_challenge(client, monkeypatch):
    email = f"mfa.user.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    token = await _register_verified_and_login(client, monkeypatch, email, password)

    setup = await client.post(
        "/api/v1/auth/mfa/totp/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert setup.status_code == 200
    setup_data = setup.json()
    assert setup_data["secret"]
    assert setup_data["secret"] in setup_data["otpauth_uri"]
    assert setup_data["otpauth_uri"].startswith("otpauth://totp/")
    assert setup_data["qr_code_uri"] == setup_data["otpauth_uri"]
    assert _stored_mfa_secret_is_encrypted(email, setup_data["secret"]) is True

    enable_code = _totp(setup_data["secret"])
    enable = await client.post(
        "/api/v1/auth/mfa/totp/enable",
        json={"code": enable_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enable.status_code == 200
    assert len(enable.json()["recovery_codes"]) >= 5

    challenged = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert challenged.status_code == 200
    assert challenged.json()["mfa_required"] is True
    assert challenged.json()["token"] is None

    future_time = time.time() + 60
    monkeypatch.setattr("src.services.auth.mfa_service.time.time", lambda: future_time)
    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "mfa_code": _totp(setup_data["secret"], now=future_time),
        },
    )
    assert login.status_code == 200
    assert login.json()["token"]
    assert _audit_event_exists("MFA_TOTP_ENABLED", "ALLOW")


@pytest.mark.asyncio
async def test_recovery_code_login_is_single_use(client, monkeypatch):
    email = f"mfa.recovery.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    token = await _register_verified_and_login(client, monkeypatch, email, password)
    recovery_code = await _enable_mfa_and_get_recovery_code(client, token)

    first_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "recovery_code": recovery_code,
        },
    )
    assert first_login.status_code == 200
    assert first_login.json()["token"]

    replay_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "recovery_code": recovery_code,
        },
    )
    assert replay_login.status_code == 401


@pytest.mark.asyncio
async def test_trusted_device_bypasses_future_mfa_prompt(client, monkeypatch):
    email = f"mfa.trusted.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    token = await _register_verified_and_login(client, monkeypatch, email, password)
    recovery_code = await _enable_mfa_and_get_recovery_code(client, token)

    trusted_login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "recovery_code": recovery_code,
            "remember_device": True,
        },
    )
    assert trusted_login.status_code == 200
    assert "mfa_trusted_device" in trusted_login.headers.get("set-cookie", "")

    password_only_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert password_only_login.status_code == 200
    assert password_only_login.json()["token"]


@pytest.mark.asyncio
async def test_mfa_brute_force_lockout_blocks_valid_code(client, monkeypatch):
    email = f"mfa.lockout.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    token = await _register_verified_and_login(client, monkeypatch, email, password)
    setup_data = await _setup_mfa(client, token)
    enable = await client.post(
        "/api/v1/auth/mfa/totp/enable",
        json={"code": _totp(setup_data["secret"])},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enable.status_code == 200

    for _ in range(5):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": email,
                "password": password,
                "mfa_code": "000000",
            },
        )
        assert response.status_code == 401

    future_time = time.time() + 60
    monkeypatch.setattr("src.services.auth.mfa_service.time.time", lambda: future_time)
    locked_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
            "mfa_code": _totp(setup_data["secret"], now=future_time),
        },
    )
    assert locked_response.status_code == 401


@pytest.mark.asyncio
async def test_disable_mfa_with_recovery_code_removes_login_challenge(client, monkeypatch):
    email = f"mfa.disable.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    token = await _register_verified_and_login(client, monkeypatch, email, password)
    recovery_code = await _enable_mfa_and_get_recovery_code(client, token)

    disable = await client.post(
        "/api/v1/auth/mfa/disable",
        json={"recovery_code": recovery_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert disable.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    assert login.json()["token"]


async def _register_verified_and_login(client, monkeypatch, email: str, password: str) -> str:
    invite_token = create_test_invite(email, role="STUDENT")
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "MFA User",
            "invite_token": invite_token,
        },
    )
    assert register.status_code == 201
    # Invited users are pre-verified, so no /auth/email/verify step is needed.
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()["token"]


async def _setup_mfa(client, token: str) -> dict:
    setup = await client.post(
        "/api/v1/auth/mfa/totp/setup",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert setup.status_code == 200
    return setup.json()


async def _enable_mfa_and_get_recovery_code(client, token: str) -> str:
    setup_data = await _setup_mfa(client, token)
    enable = await client.post(
        "/api/v1/auth/mfa/totp/enable",
        json={"code": _totp(setup_data["secret"])},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert enable.status_code == 200
    return enable.json()["recovery_codes"][0]


def _totp(secret: str, now: float | None = None) -> str:
    timestamp = time.time() if now is None else now
    return generate_totp(secret, int(timestamp) // 30)


def _stored_mfa_secret_is_encrypted(email: str, secret: str) -> bool:
    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).first()
        assert user is not None
        credential = db.query(models.MfaTotpCredential).filter_by(user_id=user.id).first()
        assert credential is not None
        return credential.secret_encrypted != secret and secret not in credential.secret_encrypted
    finally:
        db.close()


def _audit_event_exists(event_type: str, decision: str) -> bool:
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
