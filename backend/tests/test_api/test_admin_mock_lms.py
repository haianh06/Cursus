"""Integration tests for the /admin/mock-lms/* routes -- real HTTP requests through
the FastAPI app, real DB writes, but the Mock LMS *client* is swapped for a fixture
via dependency override (no real network call, no dependency on a running Mock LMS
dev server -- this suite must pass on any machine/CI)."""
from datetime import UTC, datetime

import pytest
from fastapi import Depends
from sqlalchemy.orm import Session

from src.api.admin_mock_lms import get_mock_lms_sync_service
from src.db.connection import SessionLocal, get_db
from src.db.models import User, UserRole
from src.main import app
from src.security.passwords import hash_password
from src.services.core.mock_lms_sync_service import MockLmsSyncService


def _ensure_admin_user() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email="mocklms.admin@example.test").first():
            return
        db.add(
            User(
                id="mocklms_admin",
                email="mocklms.admin@example.test",
                password_hash=hash_password("AdminPassword123"),
                full_name="Mock LMS Admin",
                role=UserRole.ADMIN.value,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()


async def _login(client, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _admin_headers(client) -> dict[str, str]:
    _ensure_admin_user()
    return await _login(client, "mocklms.admin@example.test", "AdminPassword123")


class FakeMockLmsClient:
    def __init__(self, courses, assignments_by_code):
        self._courses = courses
        self._assignments_by_code = assignments_by_code

    def list_courses(self):
        return self._courses

    def list_assignments(self, course_code):
        return self._assignments_by_code.get(course_code, [])


def _override_with_fixture_client(code: str, name: str, assignment_name: str, due_at: str) -> None:
    """Override `get_mock_lms_sync_service` with a variant that still resolves its
    DB session through the app's own `get_db` dependency (same session the request's
    other route code uses) -- constructing a second, separate SessionLocal() here
    instead caused `sqlite3.OperationalError: database is locked` (two independent
    write transactions against one SQLite file)."""
    client = FakeMockLmsClient(
        courses=[{"id": "c1", "course_code": code, "name": name, "semester": "1", "credit": 3}],
        assignments_by_code={
            code: [
                {
                    "id": "route_test_a1", "name": assignment_name, "description": "",
                    "due_at": due_at, "points_possible": 15, "updated_at": "2026-08-21T00:00:00",
                }
            ]
        },
    )

    def _get_service(db: Session = Depends(get_db)) -> MockLmsSyncService:
        return MockLmsSyncService(db, client=client)

    app.dependency_overrides[get_mock_lms_sync_service] = _get_service


@pytest.mark.asyncio
async def test_preview_requires_authentication(client):
    response = await client.post("/api/v1/admin/mock-lms/sync/preview")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_preview_returns_a_diff(client):
    headers = await _admin_headers(client)
    _override_with_fixture_client("ZZROUTE1", "Route Test Course", "Assignment 1", "2026-09-30T00:00:00")
    try:
        response = await client.post("/api/v1/admin/mock-lms/sync/preview", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["changedCount"] == 1
        assert body["changes"][0]["courseCode"] == "ZZROUTE1"
    finally:
        app.dependency_overrides.pop(get_mock_lms_sync_service, None)


@pytest.mark.asyncio
async def test_publish_without_reason_is_rejected(client):
    headers = await _admin_headers(client)
    _override_with_fixture_client("ZZROUTE2", "Route Test Course 2", "Assignment 1", "2026-09-30T00:00:00")
    try:
        response = await client.post(
            "/api/v1/admin/mock-lms/sync/publish", headers=headers, json={"reason": ""}
        )
        assert response.status_code in (400, 422)
    finally:
        app.dependency_overrides.pop(get_mock_lms_sync_service, None)


@pytest.mark.asyncio
async def test_publish_then_history_then_rollback_end_to_end(client):
    headers = await _admin_headers(client)
    _override_with_fixture_client("ZZROUTE3", "Route Test Course 3", "Assignment 1", "2026-09-30T00:00:00")
    try:
        publish_resp = await client.post(
            "/api/v1/admin/mock-lms/sync/publish",
            headers=headers,
            json={"reason": "Route-level integration test"},
        )
        assert publish_resp.status_code == 200, publish_resp.text
        version = publish_resp.json()
        assert version["reason"] == "Route-level integration test"
        assert version["rolledBackFrom"] is None
        assert len(version["payload"]) == 1

        history_resp = await client.get("/api/v1/admin/mock-lms/history", headers=headers)
        assert history_resp.status_code == 200
        history = history_resp.json()
        assert any(v["syncVersion"] == version["syncVersion"] for v in history)

        rollback_resp = await client.post(
            f"/api/v1/admin/mock-lms/sync/{version['syncVersion']}/rollback",
            headers=headers,
            json={"reason": "Undo for test"},
        )
        assert rollback_resp.status_code == 200, rollback_resp.text
        rolled_back = rollback_resp.json()
        assert rolled_back["rolledBackFrom"] == version["syncVersion"]
    finally:
        app.dependency_overrides.pop(get_mock_lms_sync_service, None)


@pytest.mark.asyncio
async def test_non_admin_cannot_access_mock_lms_routes(client):
    db = SessionLocal()
    try:
        if not db.query(User).filter_by(email="mocklms.student@example.test").first():
            db.add(
                User(
                    id="mocklms_student",
                    email="mocklms.student@example.test",
                    password_hash=hash_password("StudentPassword123"),
                    full_name="Mock LMS Student",
                    role=UserRole.STUDENT.value,
                    is_email_verified=True,
                    is_active=True,
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            db.commit()
    finally:
        db.close()
    headers = await _login(client, "mocklms.student@example.test", "StudentPassword123")

    response = await client.post("/api/v1/admin/mock-lms/sync/preview", headers=headers)
    assert response.status_code == 403
