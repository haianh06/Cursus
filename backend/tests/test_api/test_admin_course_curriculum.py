import uuid
from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import Organization, User, UserRole
from src.security.passwords import hash_password


def _ensure_admin() -> None:
    """Same shared `id="admin_demo"` fixture pattern as the other admin test
    files -- gets an organization_id too, matching the org-scoped audit-log
    fail-closed check added mục 9 ý2."""
    db = SessionLocal()
    try:
        if db.query(User).filter_by(id="admin_demo").first() is None:
            org_id = f"org_admin_test_{uuid.uuid4().hex[:8]}"
            db.add(Organization(
                id=org_id, name="Admin Test Org", slug=org_id, kind="production",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ))
            db.add(User(
                id="admin_demo",
                email="admin.demo@example.test",
                password_hash=hash_password("AdminPassword123"),
                full_name="Admin Demo",
                role=UserRole.ADMIN.value,
                organization_id=org_id,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ))
            db.commit()
    finally:
        db.close()


async def _headers(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def admin_headers(client):
    _ensure_admin()
    return await _headers(client, "admin.demo@example.test", "AdminPassword123")


@pytest.mark.asyncio
async def test_curriculum_detail_for_a_real_course_returns_clos_and_sessions(client):
    headers = await admin_headers(client)
    response = await client.get("/api/v1/admin/courses/SSA101/curriculum", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["clo_count"] == len(data["clos"])
    assert data["session_count"] == len(data["sessions"])
    assert data["clos"][0]["code"] == "CLO1"
    assert data["meta"]["NoCredit"] == "3"


@pytest.mark.asyncio
async def test_curriculum_detail_for_a_lowercase_suffixed_code_still_resolves(client):
    # 7 of the 44 real catalog codes have a significant lowercase suffix
    # (e.g. SWE202c) matching their exact chunks_<CODE>.json filename --
    # this is the regression the route's docstring warns against.
    headers = await admin_headers(client)
    response = await client.get("/api/v1/admin/courses/SWE202c/curriculum", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["clo_count"] > 0


@pytest.mark.asyncio
async def test_curriculum_detail_404s_for_a_course_with_no_real_syllabus(client):
    headers = await admin_headers(client)
    response = await client.get(
        "/api/v1/admin/courses/NOT_A_REAL_SUBJECT_CODE/curriculum", headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_curriculum_detail_requires_admin_role(client):
    response = await client.post(
        "/api/v1/auth/login", json={"email": "student.demo@example.test", "password": "password123"}
    )
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['token']}"}

    response = await client.get("/api/v1/admin/courses/SSA101/curriculum", headers=headers)
    assert response.status_code == 403
