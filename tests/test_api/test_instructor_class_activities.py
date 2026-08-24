"""Instructor class-activity CRUD (src/api/instructor.py's /class-activities
routes + ClassActivityService).

No test coverage existed for this feature at all before this file --
AcademicTermRepository.get_active()/.list_courses()/.get_course() had all
been changed to require a mandatory `organization_id` argument (fail-closed
org-scoping), but ClassActivityService's calls to them were never updated
to match. Every one of these routes 500'd on every request as a result --
confirmed live against a running dev server, not just here.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

STUDENT = {"email": "student.demo@example.test", "password": "password123"}


async def _login(client, credentials: dict) -> dict:
    resp = await client.post("/api/v1/auth/login", json=credentials)
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


async def _reset_demo(client, headers: dict) -> dict:
    resp = await client.post("/api/v1/demo/reset", json={"confirm": True}, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _login_gate2_instructor(client) -> dict:
    """Same pattern as tests/test_api/test_gate2_flow.py."""
    from src.config import get_settings
    from src.db import models
    from src.db.connection import SessionLocal
    from src.security.tokens import create_access_token

    db = SessionLocal()
    try:
        instructor = db.query(models.User).filter_by(email="demo.instructor@cursusdemo.local").first()
        assert instructor is not None, "gate2_demo.py should have created this row on reset"
        token = create_access_token(subject=instructor.id, settings=get_settings())
    finally:
        db.close()
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


def _next_weekday(start: date) -> date:
    day = start
    while day.weekday() > 4:
        day += timedelta(days=1)
    return day


async def _setup_instructor(client) -> tuple[dict, str]:
    """Returns (instructor_headers, course_id) with the gate2 demo class set up."""
    student_headers = await _login(client, STUDENT)
    await _reset_demo(client, student_headers)
    instructor_headers = await _login_gate2_instructor(client)

    dashboard = await client.get("/api/v1/instructor/dashboard", headers=instructor_headers)
    assert dashboard.status_code == 200, dashboard.text
    courses = dashboard.json()["courses"]
    assert courses, "gate2 demo should assign the instructor at least one course"
    return instructor_headers, courses[0]["id"]


@pytest.mark.asyncio
async def test_list_class_activities_does_not_500(client):
    instructor_headers, _course_id = await _setup_instructor(client)

    response = await client.get("/api/v1/instructor/class-activities", headers=instructor_headers)

    assert response.status_code == 200
    data = response.json()
    assert "activities" in data
    assert "window" in data


@pytest.mark.asyncio
async def test_create_list_update_delete_class_activity(client):
    instructor_headers, course_id = await _setup_instructor(client)
    activity_date = _next_weekday(date.today() + timedelta(days=14))

    created = await client.post(
        "/api/v1/instructor/class-activities",
        json={
            "course_id": course_id,
            "activity_date": activity_date.isoformat(),
            "kind": "LAB",
            "title": "Buổi lab kiểm tra",
        },
        headers=instructor_headers,
    )
    assert created.status_code == 201, created.text
    activity_id = created.json()["id"]

    listed = await client.get("/api/v1/instructor/class-activities", headers=instructor_headers)
    assert listed.status_code == 200
    assert any(item["id"] == activity_id for item in listed.json()["activities"])

    updated = await client.patch(
        f"/api/v1/instructor/class-activities/{activity_id}",
        json={"title": "Buổi lab đã đổi tên"},
        headers=instructor_headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["title"] == "Buổi lab đã đổi tên"

    deleted = await client.delete(
        f"/api/v1/instructor/class-activities/{activity_id}", headers=instructor_headers
    )
    assert deleted.status_code == 204

    listed_after = await client.get("/api/v1/instructor/class-activities", headers=instructor_headers)
    assert not any(item["id"] == activity_id for item in listed_after.json()["activities"])


@pytest.mark.asyncio
async def test_weekend_activity_date_rejected(client):
    instructor_headers, course_id = await _setup_instructor(client)
    saturday = date.today() + timedelta(days=(5 - date.today().weekday()) % 7 + 7)
    assert saturday.weekday() == 5

    response = await client.post(
        "/api/v1/instructor/class-activities",
        json={
            "course_id": course_id,
            "activity_date": saturday.isoformat(),
            "kind": "OTHER",
            "title": "Weekend activity",
        },
        headers=instructor_headers,
    )

    assert response.status_code == 400
