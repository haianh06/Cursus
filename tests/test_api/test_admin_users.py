"""Admin Console 'Invites + Users' tab backend (mục 6.5): list org members
and lock/unlock accounts. `User.is_active` was already enforced at login
(auth_service.py) -- these routes were the only missing piece."""

from __future__ import annotations

import uuid

import pytest

from src.db.models import UserRole
from tests.support.semester_practice_fixtures import auth_headers, ensure_org, ensure_user, login


@pytest.mark.asyncio
async def test_admin_lists_only_users_in_their_own_org(client):
    org_a = ensure_org("users-org-a", "Users Org A")
    org_b = ensure_org("users-org-b", "Users Org B")
    admin_email = f"users.admin.a.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_email, org_id=org_a, role=UserRole.ADMIN)
    student_a_email = f"users.student.a.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_a_email, org_id=org_a, role=UserRole.STUDENT)
    other_org_email = f"users.student.b.{uuid.uuid4().hex}@example.test"
    ensure_user(email=other_org_email, org_id=org_b, role=UserRole.STUDENT)

    token = await login(client, admin_email)
    resp = await client.get("/api/v1/admin/users", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    emails = {row["email"] for row in resp.json()}
    assert admin_email in emails
    assert student_a_email in emails
    assert other_org_email not in emails


@pytest.mark.asyncio
async def test_admin_locks_and_unlocks_a_user_in_their_org(client):
    org = ensure_org("users-org-c", "Users Org C")
    admin_email = f"users.admin.c.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_email, org_id=org, role=UserRole.ADMIN)
    target_email = f"users.target.c.{uuid.uuid4().hex}@example.test"
    target_id = ensure_user(email=target_email, org_id=org, role=UserRole.STUDENT)

    admin_token = await login(client, admin_email)

    lock_resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        headers=auth_headers(admin_token),
        json={"is_active": False},
    )
    assert lock_resp.status_code == 200, lock_resp.text
    assert lock_resp.json()["is_active"] is False

    # A locked account cannot log in.
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": target_email, "password": "TestPassword123"},
    )
    assert login_resp.status_code in (401, 403), login_resp.text

    unlock_resp = await client.patch(
        f"/api/v1/admin/users/{target_id}/status",
        headers=auth_headers(admin_token),
        json={"is_active": True},
    )
    assert unlock_resp.status_code == 200
    assert unlock_resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_admin_cannot_lock_their_own_account(client):
    org = ensure_org("users-org-d", "Users Org D")
    admin_email = f"users.admin.d.{uuid.uuid4().hex}@example.test"
    admin_id = ensure_user(email=admin_email, org_id=org, role=UserRole.ADMIN)

    token = await login(client, admin_email)
    resp = await client.patch(
        f"/api/v1/admin/users/{admin_id}/status",
        headers=auth_headers(token),
        json={"is_active": False},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_admin_cannot_lock_a_user_in_a_different_org(client):
    org_a = ensure_org("users-org-e", "Users Org E")
    org_b = ensure_org("users-org-f", "Users Org F")
    admin_email = f"users.admin.e.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_email, org_id=org_a, role=UserRole.ADMIN)
    other_org_user_id = ensure_user(
        email=f"users.target.f.{uuid.uuid4().hex}@example.test", org_id=org_b, role=UserRole.STUDENT
    )

    token = await login(client, admin_email)
    resp = await client.patch(
        f"/api/v1/admin/users/{other_org_user_id}/status",
        headers=auth_headers(token),
        json={"is_active": False},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_user_status_fails_closed_for_a_caller_with_no_organization():
    """Defense-in-depth: found during a fresh adversarial re-sweep of this
    route (it postdates the earlier RBAC/IDOR sweep, which never covered
    it). No live path creates an org-less ADMIN today -- every route that
    creates a User sets organization_id -- but this must not fall through
    to an `organization_id IS NULL` filter (which could match other
    org-less users) if that ever changes. Calls the route function
    directly, bypassing FastAPI dependency injection, since an org-less
    admin can't be produced through the real invite/register flow."""
    from fastapi import HTTPException

    from src.api.admin import update_user_status
    from src.db.connection import SessionLocal
    from src.db.models import User
    from src.schemas.admin_schemas import UpdateUserStatusRequest

    caller = User(
        id=f"user_{uuid.uuid4().hex}",
        email=f"orgless.{uuid.uuid4().hex}@example.test",
        password_hash="x",
        full_name="Org-less Admin",
        role=UserRole.ADMIN.value,
        organization_id=None,
    )

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as exc_info:
            await update_user_status(
                user_id="any-user-id",
                payload=UpdateUserStatusRequest(is_active=False),
                current_user=caller,
                db=db,
            )
        assert exc_info.value.status_code == 404
    finally:
        db.close()
