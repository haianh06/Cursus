import uuid

import pytest

from tests.support.invite_helpers import create_test_invite


@pytest.mark.asyncio
async def test_change_password_updates_password_and_keeps_current_session(client, monkeypatch):
    email = f"change.password.{uuid.uuid4().hex}@example.test"
    old_password = "OldPassword123!"
    new_password = "NewPassword123!"

    invite_token = create_test_invite(email, role="STUDENT")
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": old_password,
            "full_name": "Change Password User",
            "invite_token": invite_token,
        },
    )
    assert register.status_code == 201
    # Invited users are pre-verified, so no /auth/email/verify step is needed.

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    changed = await client.post(
        "/api/v1/auth/password/change",
        json={
            "current_password": old_password,
            "new_password": new_password,
        },
        headers=headers,
    )
    assert changed.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert old_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert new_login.status_code == 200
