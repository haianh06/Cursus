import uuid
from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import Organization, User, UserRole
from src.security.passwords import hash_password


def _ensure_org_and_admin() -> tuple[str, str]:
    """Returns (email, organization_id) for a dedicated admin — this
    endpoint is organization-scoped, so it needs an admin whose
    organization_id is actually set (the shared admin.demo@example.test
    fixture used elsewhere does not set one)."""
    db = SessionLocal()
    try:
        email = "settings.admin@example.test"
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            return email, existing.organization_id

        org_id = f"org_settings_test_{uuid.uuid4().hex[:8]}"
        db.add(Organization(id=org_id, name="Settings Test Org", slug=org_id, kind="production", created_at=datetime.now(UTC).replace(tzinfo=None)))
        db.add(
            User(
                id="settings_admin",
                email=email,
                password_hash=hash_password("AdminPassword123"),
                full_name="Settings Admin",
                role=UserRole.ADMIN.value,
                organization_id=org_id,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
        return email, org_id
    finally:
        db.close()


async def _login(client, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _admin_headers(client) -> dict[str, str]:
    email, _org_id = _ensure_org_and_admin()
    return await _login(client, email, "AdminPassword123")


@pytest.mark.asyncio
async def test_get_settings_creates_documented_defaults_on_first_read(client):
    headers = await _admin_headers(client)
    response = await client.get("/api/v1/admin/settings", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["demoModeEnabled"] is False
    assert body["autoRiskAlertsEnabled"] is True
    assert body["defaultSemester"] == "Fall2026"


@pytest.mark.asyncio
async def test_get_settings_requires_authentication(client):
    response = await client.get("/api/v1/admin/settings")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_cannot_read_settings(client):
    headers = await _login(client, "student.demo@example.test", "password123")
    response = await client.get("/api/v1/admin/settings", headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_updates_only_provided_fields_and_persists(client):
    headers = await _admin_headers(client)

    patch_resp = await client.patch(
        "/api/v1/admin/settings",
        headers=headers,
        json={"demoModeEnabled": True},
    )
    assert patch_resp.status_code == 200
    body = patch_resp.json()
    assert body["demoModeEnabled"] is True
    assert body["autoRiskAlertsEnabled"] is True  # untouched field kept its value
    assert body["updatedBy"] == "settings_admin"

    get_resp = await client.get("/api/v1/admin/settings", headers=headers)
    assert get_resp.json()["demoModeEnabled"] is True


@pytest.mark.asyncio
async def test_patch_default_semester(client):
    headers = await _admin_headers(client)
    response = await client.patch(
        "/api/v1/admin/settings",
        headers=headers,
        json={"defaultSemester": "Spring2027"},
    )
    assert response.status_code == 200
    assert response.json()["defaultSemester"] == "Spring2027"
