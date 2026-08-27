import uuid

import pytest

from src.db import models
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_org,
    ensure_user,
    login,
)


@pytest.mark.asyncio
async def test_admin_can_trigger_a_password_reset_for_a_member(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"pwd-{suffix}", name="Password Org")
    admin_email = f"admin.pwd.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    target_id = ensure_user(
        email=f"stu.pwd.{suffix}@test.local", org_id=org_id, role=models.UserRole.STUDENT
    )

    token = await login(client, admin_email)
    response = await client.post(
        f"/api/v1/admin/users/{target_id}/reset-password", headers=auth_headers(token)
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_cannot_reset_a_password_in_another_organization(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"pwd-a-{suffix}", name="Org A")
    admin_email = f"admin.a.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    outsider = ensure_user(
        email=f"stu.b.{suffix}@test.local",
        org_id=ensure_org(slug=f"pwd-b-{suffix}", name="Org B"),
        role=models.UserRole.STUDENT,
    )

    token = await login(client, admin_email)
    response = await client.post(
        f"/api/v1/admin/users/{outsider}/reset-password", headers=auth_headers(token)
    )

    assert response.status_code == 404
