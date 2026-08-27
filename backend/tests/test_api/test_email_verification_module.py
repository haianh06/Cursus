import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.security.tokens import hash_opaque_token
from tests.support.invite_helpers import create_direct_user


@pytest.mark.asyncio
async def test_email_verification_required_before_login(client, monkeypatch):
    email = f"verify.user.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    create_direct_user(email, password, full_name="Verify Test User", is_email_verified=False)

    blocked_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert blocked_login.status_code == 401

    resend_token = f"resend-token-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        "src.services.auth.email_verification_service.create_opaque_token",
        lambda: resend_token,
    )
    resend_response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert resend_response.status_code == 200

    verify_response = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": resend_token},
    )
    assert verify_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    assert login_response.json()["user"]["is_email_verified"] is True


@pytest.mark.asyncio
async def test_email_verification_stores_only_token_hash(client, monkeypatch):
    email = f"hash.only.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    user = create_direct_user(email, password, full_name="Hash Only User", is_email_verified=False)

    verification_token = f"verify-token-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        "src.services.auth.email_verification_service.create_opaque_token",
        lambda: verification_token,
    )
    response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert response.status_code == 200

    db = SessionLocal()
    try:
        stored_token = (
            db.query(models.VerificationToken)
            .filter_by(user_id=user.id, purpose="EMAIL_VERIFICATION")
            .first()
        )
        assert stored_token is not None
        assert stored_token.token_hash == hash_opaque_token(verification_token)
        assert stored_token.token_hash != verification_token
    finally:
        db.close()


@pytest.mark.asyncio
async def test_resend_invalidates_previous_email_verification_token(client, monkeypatch):
    email = f"resend.invalidates.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    create_direct_user(email, password, full_name="Resend Invalidates User", is_email_verified=False)

    first_token = f"first-token-{uuid.uuid4().hex}"
    second_token = f"second-token-{uuid.uuid4().hex}"
    tokens = iter([first_token, second_token])
    monkeypatch.setattr(
        "src.services.auth.email_verification_service.create_opaque_token",
        lambda: next(tokens),
    )

    first_resend = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert first_resend.status_code == 200

    second_resend = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert second_resend.status_code == 200

    stale_response = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": first_token},
    )
    assert stale_response.status_code == 400

    verify_response = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": second_token},
    )
    assert verify_response.status_code == 200


@pytest.mark.asyncio
async def test_expired_email_verification_token_is_rejected(client, monkeypatch):
    email = f"expired.verify.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    create_direct_user(email, password, full_name="Expired Verify User", is_email_verified=False)

    verification_token = f"expired-token-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        "src.services.auth.email_verification_service.create_opaque_token",
        lambda: verification_token,
    )
    resend_response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert resend_response.status_code == 200
    _expire_email_verification_token(verification_token)

    verify_response = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": verification_token},
    )

    assert verify_response.status_code == 400


@pytest.mark.asyncio
async def test_email_verification_token_is_single_use(client, monkeypatch):
    email = f"single.use.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    create_direct_user(email, password, full_name="Single Use User", is_email_verified=False)

    verification_token = f"single-use-token-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        "src.services.auth.email_verification_service.create_opaque_token",
        lambda: verification_token,
    )
    resend_response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert resend_response.status_code == 200

    first_verify = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": verification_token},
    )
    assert first_verify.status_code == 200

    replay_verify = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": verification_token},
    )
    assert replay_verify.status_code == 400


@pytest.mark.asyncio
async def test_verify_endpoint_does_not_create_session(client, monkeypatch):
    email = f"verify.no.session.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    create_direct_user(email, password, full_name="No Session User", is_email_verified=False)

    verification_token = f"no-session-token-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        "src.services.auth.email_verification_service.create_opaque_token",
        lambda: verification_token,
    )
    resend_response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert resend_response.status_code == 200

    verify_response = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": verification_token},
    )

    assert verify_response.status_code == 200
    assert "token" not in verify_response.json()
    assert "session" not in verify_response.json()
    assert "set-cookie" not in verify_response.headers


@pytest.mark.asyncio
async def test_email_verification_writes_audit_events(client, monkeypatch):
    email = f"audit.verify.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"
    create_direct_user(email, password, full_name="Audit Verify User", is_email_verified=False)

    verification_token = f"audit-token-{uuid.uuid4().hex}"
    monkeypatch.setattr(
        "src.services.auth.email_verification_service.create_opaque_token",
        lambda: verification_token,
    )
    resend_response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": email},
    )
    assert resend_response.status_code == 200

    verify_response = await client.post(
        "/api/v1/auth/email/verify",
        json={"token": verification_token},
    )
    assert verify_response.status_code == 200

    # Registration no longer issues a verification token itself (invited
    # users start pre-verified), so the "a token was issued" audit trail
    # now comes from the resend endpoint instead of EMAIL_VERIFICATION_ISSUED.
    assert _audit_event_exists("EMAIL_VERIFICATION_RESEND_REQUESTED", "ALLOW")
    assert _audit_event_exists("EMAIL_VERIFICATION_SUCCESS", "ALLOW")


@pytest.mark.asyncio
async def test_resend_response_does_not_enumerate_email(client):
    existing_response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": "student.demo@example.test"},
    )
    missing_response = await client.post(
        "/api/v1/auth/email/resend",
        json={"email": f"missing.{uuid.uuid4().hex}@example.test"},
    )

    assert existing_response.status_code == 200
    assert missing_response.status_code == 200
    assert existing_response.json() == missing_response.json()


def _expire_email_verification_token(raw_token: str) -> None:
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
