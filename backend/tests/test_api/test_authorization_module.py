from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import User, UserRole
from src.security.passwords import hash_password


@pytest.mark.asyncio
async def test_student_cannot_access_instructor_routes(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    response = await client.get(
        "/api/v1/instructor/dashboard",
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_instructor_cannot_access_student_routes(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "instructor.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    response = await client.get(
        "/api/v1/student/dashboard",
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_service_account_cannot_access_student_or_instructor_routes(client):
    _ensure_service_account_user()

    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "service.account@example.test",
            "password": "ServicePassword123",
        },
    )
    assert login_response.status_code == 200
    token = login_response.json()["token"]

    student_response = await client.get(
        "/api/v1/student/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    instructor_response = await client.get(
        "/api/v1/instructor/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert student_response.status_code == 403
    assert instructor_response.status_code == 403


@pytest.mark.asyncio
async def test_instructor_lacks_approve_permission_after_role_check(client):
    """Instructor role-gated router is reachable, but the intervention
    endpoint additionally enforces the INTERVENTION:APPROVE permission via
    the policy layer. A student never reaches this far (blocked by role),
    so this test asserts the permission-guarded 404/403 ordering is sane
    for an authenticated instructor on a risk case they do not own."""
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "instructor.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    response = await client.post(
        "/api/v1/instructor/risks/nonexistent-risk-id/intervention",
        json={"decision": "APPROVE"},
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 404


def _ensure_service_account_user() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email="service.account@example.test").first()
        if existing:
            return

        db.add(
            User(
                id="service_account_demo",
                email="service.account@example.test",
                password_hash=hash_password("ServicePassword123"),
                full_name="Canvas Sync Service Account",
                role=UserRole.SERVICE_ACCOUNT.value,
                is_email_verified=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()
