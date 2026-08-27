"""`admin_announcements` is read by `GET /instructor/announcements` and shown
on the instructor dashboard, but no route ever wrote to it -- the panel was
permanently empty. Adding the writer also makes the reader's missing
organization filter matter for the first time, so both are covered here.
"""

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
async def test_an_admin_announcement_reaches_the_instructor_panel(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"ann-{suffix}", name="Announcement Org")
    admin_email = f"admin.ann.{suffix}@test.local"
    inst_email = f"inst.ann.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    ensure_user(email=inst_email, org_id=org_id, role=models.UserRole.INSTRUCTOR)

    admin_token = await login(client, admin_email)
    created = await client.post(
        "/api/v1/admin/announcements",
        headers=auth_headers(admin_token),
        json={"title": f"Lịch nghỉ lễ {suffix}", "content": "Nghỉ từ 02/09."},
    )
    assert created.status_code == 201, created.text

    inst_token = await login(client, inst_email)
    listed = await client.get(
        "/api/v1/instructor/announcements", headers=auth_headers(inst_token)
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["announcements"]
    mine = [row for row in rows if row["title"] == f"Lịch nghỉ lễ {suffix}"]
    assert len(mine) == 1
    assert mine[0]["content"] == "Nghỉ từ 02/09."
    # The reader resolves `created_by` to a display name, so an announcement
    # with no resolvable author would silently read as a bare "Admin".
    assert mine[0]["authorName"]


@pytest.mark.asyncio
async def test_an_announcement_does_not_leak_to_another_organization(client):
    suffix = uuid.uuid4().hex[:6]
    mine = ensure_org(slug=f"annx-a-{suffix}", name="Org A")
    theirs = ensure_org(slug=f"annx-b-{suffix}", name="Org B")
    admin_email = f"admin.annx.{suffix}@test.local"
    outsider_email = f"inst.annx.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=mine, role=models.UserRole.ADMIN)
    ensure_user(email=outsider_email, org_id=theirs, role=models.UserRole.INSTRUCTOR)

    admin_token = await login(client, admin_email)
    title = f"Noi bo Org A {suffix}"
    created = await client.post(
        "/api/v1/admin/announcements",
        headers=auth_headers(admin_token),
        json={"title": title, "content": "Chi danh cho Org A."},
    )
    assert created.status_code == 201, created.text

    outsider_token = await login(client, outsider_email)
    listed = await client.get(
        "/api/v1/instructor/announcements", headers=auth_headers(outsider_token)
    )
    assert listed.status_code == 200, listed.text
    assert all(row["title"] != title for row in listed.json()["announcements"])


@pytest.mark.asyncio
async def test_an_instructor_cannot_publish_an_announcement(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"annr-{suffix}", name="Announcement Roles")
    inst_email = f"inst.annr.{suffix}@test.local"
    ensure_user(email=inst_email, org_id=org_id, role=models.UserRole.INSTRUCTOR)

    token = await login(client, inst_email)
    response = await client.post(
        "/api/v1/admin/announcements",
        headers=auth_headers(token),
        json={"title": "Khong duoc phep", "content": "..."},
    )

    assert response.status_code == 403
