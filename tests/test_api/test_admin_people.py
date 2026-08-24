import pytest

from tests.test_api.test_admin import _ensure_admin_user


@pytest.mark.asyncio
async def test_admin_people_requires_admin_role(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student.demo@example.test", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/people", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_people_lists_org_users_with_academic_summary(client):
    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/people", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "items" in data
    assert "meta" in data
    for item in data["items"]:
        assert set(item.keys()) >= {"id", "full_name", "email", "role", "is_active", "academic_summary"}


@pytest.mark.asyncio
async def test_admin_people_role_filter(client):
    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/people?role=ADMIN", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_admin_people_search_filter(client):
    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/people?search=nobody-matches-this-xyz", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["items"] == []
