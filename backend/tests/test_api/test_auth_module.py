import uuid

import pytest

from src.db.connection import SessionLocal
from src.db.models import User
from tests.support.invite_helpers import create_test_invite


@pytest.mark.asyncio
async def test_login_rejects_invalid_password(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_then_login_and_get_me(client):
    email = f"new.user.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"

    invite_token = create_test_invite(email, role="STUDENT")
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "New Test User",
            "invite_token": invite_token,
        },
    )

    assert register_response.status_code == 201
    registered = register_response.json()
    assert registered["user"]["email"] == email
    assert registered["user"]["role"] == "STUDENT"
    # AuthService.register marks invited users as email-verified up front
    # (the invite itself, sent to a known address, is the verification).
    assert registered["user"]["is_email_verified"] is True
    # No /auth/email/verify step needed: the user is already verified.

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200
    login_data = login_response.json()
    assert login_data["token_type"] == "bearer"
    assert login_data["token"]

    me_response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login_data['token']}"},
    )

    assert me_response.status_code == 200
    assert me_response.json()["email"] == email


@pytest.mark.asyncio
async def test_register_requires_invite_token(client):
    """Registration is invite-only: `invite_token` is a required field
    (Pydantic `Field(..., min_length=16)`), so a request without one never
    even reaches the auth service — it fails validation."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"no.invite.{uuid.uuid4().hex}@example.test",
            "password": "StrongPassword123",
            "full_name": "No Invite User",
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_rejects_invalid_invite_token(client):
    """A garbage/nonexistent invite_token is rejected with 400, not 422 —
    it passes Pydantic's shape validation but fails AuthService.register's
    invite lookup (`InvalidInviteError`)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"bad.invite.{uuid.uuid4().hex}@example.test",
            "password": "StrongPassword123",
            "full_name": "Bad Invite User",
            "invite_token": f"nonexistent-invite-token-{uuid.uuid4().hex}",
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_register_role_comes_from_invite_not_request(client):
    """There is no `role` field in the register request body at all — role
    can only ever come from the invite record. Prove it end to end: an
    INSTRUCTOR invite produces an INSTRUCTOR user."""
    email = f"instructor.invite.{uuid.uuid4().hex}@example.test"
    invite_token = create_test_invite(email, role="INSTRUCTOR")

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "full_name": "Instructor User",
            "invite_token": invite_token,
        },
    )

    assert response.status_code == 201
    registered = response.json()
    assert registered["user"]["role"] == "INSTRUCTOR"


@pytest.mark.asyncio
async def test_register_ignores_a_spoofed_role_in_the_request_body(client):
    """P0#1 (mục 9): register on a STUDENT invite but also send an extra
    'role': 'ADMIN' field in the body -- must be silently ignored (dropped
    by RegisterRequest, which has no `role` field at all), never honored.
    Found as a real test-coverage gap during a fresh P0 re-verification
    sweep: the sibling test above proves the happy path (invite role wins)
    but nothing had actually attempted a spoofed role before."""
    email = f"student.spoofed-role.{uuid.uuid4().hex}@example.test"
    invite_token = create_test_invite(email, role="STUDENT")

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "full_name": "Spoofed Role Attempt",
            "invite_token": invite_token,
            "role": "ADMIN",
        },
    )

    assert response.status_code == 201
    registered = response.json()
    assert registered["user"]["role"] == "STUDENT"


@pytest.mark.asyncio
async def test_login_rejects_inactive_user(client, monkeypatch):
    email = f"inactive.user.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"

    invite_token = create_test_invite(email, role="STUDENT")
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Inactive User",
            "invite_token": invite_token,
        },
    )
    assert register_response.status_code == 201
    # Invited users are pre-verified, so no /auth/email/verify step is needed.

    _deactivate_user(email)

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )

    assert login_response.status_code == 401


def _deactivate_user(email: str) -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        assert user is not None
        user.is_active = False
        db.commit()
    finally:
        db.close()
