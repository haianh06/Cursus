import uuid
from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import User, UserRole
from src.security.passwords import hash_password
from tests.support.semester_practice_fixtures import auth_headers, ensure_org, ensure_user, login


@pytest.mark.asyncio
async def test_student_cannot_read_audit_events(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    response = await client.get(
        "/api/v1/audit/events",
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_query_own_organizations_login_events(client):
    """mục 9 ý2: org-scoped now, so both accounts here need an explicit,
    matching organization -- LOGIN_SUCCESS carries actor_user_id (unlike
    LOGIN_FAILED, which is intentionally anonymous/unattributable and stays
    org-less, see src/api/auth.py), so it backfills to the student's own org
    and the admin in that same org can see it."""
    org_id = ensure_org("audit-org-a", "Audit Org A")
    student_email = f"audit.student.a.{uuid.uuid4().hex}@example.test"
    admin_email = f"audit.admin.a.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    ensure_user(email=admin_email, org_id=org_id, role=UserRole.ADMIN)

    await login(client, student_email)

    admin_token = await login(client, admin_email)
    response = await client.get(
        "/api/v1/audit/events?event_type=LOGIN_SUCCESS&limit=500",
        headers=auth_headers(admin_token),
    )

    assert response.status_code == 200
    events = response.json()
    assert any(event["actor_user_id"] == student_id for event in events)


@pytest.mark.asyncio
async def test_admin_cannot_see_another_organizations_audit_events(client):
    """The actual gap this migration fixes: before it, any ADMIN saw every
    organization's audit log mixed together."""
    org_a = ensure_org("audit-org-b1", "Audit Org B1")
    org_b = ensure_org("audit-org-b2", "Audit Org B2")
    student_a_email = f"audit.student.b1.{uuid.uuid4().hex}@example.test"
    admin_b_email = f"audit.admin.b2.{uuid.uuid4().hex}@example.test"
    student_a_id = ensure_user(email=student_a_email, org_id=org_a, role=UserRole.STUDENT)
    ensure_user(email=admin_b_email, org_id=org_b, role=UserRole.ADMIN)

    # A distinctive login for org_a's student.
    await login(client, student_a_email)

    # org_b's admin must not see org_a's event.
    admin_b_token = await login(client, admin_b_email)
    response = await client.get(
        "/api/v1/audit/events?event_type=LOGIN_SUCCESS&limit=500",
        headers=auth_headers(admin_b_token),
    )
    assert response.status_code == 200
    seen_actors = {event["actor_user_id"] for event in response.json()}
    assert student_a_id not in seen_actors


@pytest.mark.asyncio
async def test_org_less_admin_gets_404_not_every_organizations_log(client):
    """Fail closed (same choice already made for update_user_status()/
    get_analytics()): an ADMIN with no organization_id must never fall
    through to "the filter is empty, show everything"."""
    db = SessionLocal()
    try:
        orgless_email = f"audit.orgless.{uuid.uuid4().hex}@example.test"
        db.add(
            User(
                id=f"user_{uuid.uuid4().hex}",
                email=orgless_email,
                password_hash=hash_password("TestPassword123"),
                full_name="Org-less Admin",
                role=UserRole.ADMIN.value,
                is_email_verified=True,
                is_active=True,
                organization_id=None,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()

    token = await login(client, orgless_email, password="TestPassword123")
    response = await client.get("/api/v1/audit/events", headers=auth_headers(token))
    assert response.status_code == 404
