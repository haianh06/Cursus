from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import AuditLog, SelfStudySession, User, UserRole
from src.repositories.audit_repository import AuditRepository
from src.security.passwords import hash_password
from tests.support.api_demo_dataset import DEMO_PASSWORD

# student_ethan (seeded by ensure_api_demo_dataset via the `client` fixture)
# has no organization_id, so the admin used here must also have none --
# _require_student() in admin_student360.py 404s on any org mismatch,
# including None vs a real org id.
ADMIN_EMAIL = "admin.student360.test@example.test"
STUDENT_ID = "student_ethan"


def _ensure_orgless_admin() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email=ADMIN_EMAIL).first() is None:
            db.add(
                User(
                    id="admin_student360_test",
                    email=ADMIN_EMAIL,
                    password_hash=hash_password(DEMO_PASSWORD),
                    full_name="Admin Student360 Test",
                    role=UserRole.ADMIN.value,
                    organization_id=None,
                    is_email_verified=True,
                    is_active=True,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            db.commit()
    finally:
        db.close()


async def _login(client, email: str, password: str = DEMO_PASSWORD) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _admin_headers(client) -> dict[str, str]:
    _ensure_orgless_admin()
    return await _login(client, ADMIN_EMAIL)


@pytest.mark.asyncio
async def test_admin_can_read_student_plans_and_it_is_audited(client):
    headers = await _admin_headers(client)

    response = await client.get(f"/api/v1/admin/students/{STUDENT_ID}/plans", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True

    db = SessionLocal()
    try:
        events = (
            db.query(AuditLog)
            .filter_by(event_type="ADMIN_SENSITIVE_READ", resource_type="PLAN")
            .filter(AuditLog.resource_id.like(f"%{STUDENT_ID}%"))
            .all()
        )
        assert len(events) >= 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_instructor_cannot_read_student_raw_data(client):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.demo@example.test", "password": DEMO_PASSWORD},
    )
    if response.status_code != 200:
        pytest.skip("no seeded instructor.demo account in this dataset")
    headers = {"Authorization": f"Bearer {response.json()['token']}"}

    response = await client.get(f"/api/v1/admin/students/{STUDENT_ID}/plans", headers=headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_student_cannot_read_their_own_raw_data_via_admin_route(client):
    headers = await _login(client, "student.demo@example.test")

    response = await client.get(f"/api/v1/admin/students/{STUDENT_ID}/plans", headers=headers)

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unknown_student_returns_404(client):
    headers = await _admin_headers(client)

    response = await client.get("/api/v1/admin/students/not_a_real_id/plans", headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_admin_can_read_all_raw_tabs(client):
    """One representative check per resource-type mapping added to the
    permission matrix, not just PLAN -- confirms the new per-route
    READ_SENSITIVE/READ dependencies don't 403 the role that's supposed to
    pass them."""
    headers = await _admin_headers(client)

    for path in (
        "tasks",
        "progress-events",
        "reminders",
        "assignments",
        "submissions",
        "reflections",
        "documents",
        "risk",
        "interventions",
        "sessions",
    ):
        response = await client.get(f"/api/v1/admin/students/{STUDENT_ID}/{path}", headers=headers)
        assert response.status_code == 200, f"{path} -> {response.status_code}: {response.text}"


@pytest.mark.asyncio
async def test_student_sessions_are_audited_before_release(client):
    headers = await _admin_headers(client)

    db = SessionLocal()
    try:
        if db.get(SelfStudySession, "session_student360_test") is None:
            started_at = datetime.now(UTC).replace(tzinfo=None)
            db.add(
                SelfStudySession(
                    id="session_student360_test",
                    student_id=STUDENT_ID,
                    schedule_block_id="sb_plan_ethan_w6",
                    title="Admin 360 focus session",
                    planned_minutes=50,
                    started_at=started_at,
                    scheduled_end_at=started_at,
                    ended_at=None,
                    actual_minutes=None,
                    pomodoros_completed=1,
                    status="IN_PROGRESS",
                )
            )
            db.commit()
    finally:
        db.close()

    response = await client.get(f"/api/v1/admin/students/{STUDENT_ID}/sessions", headers=headers)

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"][0]["id"] == "session_student360_test"
    assert response.json()["data"][0]["pomodorosCompleted"] == 1

    db = SessionLocal()
    try:
        events = (
            db.query(AuditLog)
            .filter_by(event_type="ADMIN_SENSITIVE_READ", resource_type="SELF_STUDY_SESSION")
            .filter(AuditLog.resource_id.like(f"%{STUDENT_ID}%"))
            .all()
        )
        assert len(events) >= 1
        assert events[-1].metadata_info["subjectStudentId"] == STUDENT_ID
    finally:
        db.close()


@pytest.mark.asyncio
async def test_student_sessions_fail_closed_when_audit_write_fails(client, monkeypatch):
    headers = await _admin_headers(client)

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditRepository, "add", fail_audit)
    response = await client.get(f"/api/v1/admin/students/{STUDENT_ID}/sessions", headers=headers)

    assert response.status_code == 503
    assert response.json()["detail"] == "sensitive_audit_unavailable"
