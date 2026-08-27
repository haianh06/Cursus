"""Tests for the Self-Study Pomodoro feature (src/services/academic/self_study_service.py)."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from src.db.models import UserRole
from src.services.academic.self_study_service import _now
from tests.support.semester_practice_fixtures import auth_headers, ensure_org, ensure_user, login


def _now_naive() -> datetime:
    # ScheduleBlock.start_time/end_time are naive local wall-clock time, not
    # naive UTC -- see Timetable.jsx's parseLocal()/toIsoLocal(), which both
    # deliberately round-trip local Y/M/D/H/M components with no timezone
    # conversion. Building fixtures from true UTC here would silently drift
    # by the app's fixed +7h offset from whatever self_study_service.py
    # actually compares against, so this reuses that same helper.
    return _now()


async def _create_self_study_block(client, token, *, start: datetime, end: datetime) -> str:
    response = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=auth_headers(token),
        json={"title": "Ôn SSA101", "start": start.isoformat(), "end": end.isoformat()},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_upcoming_lists_a_block_inside_its_reminder_window(client):
    org = ensure_org("ss-org-a", "Self Study Org A")
    email = f"ss.student.a.{uuid.uuid4().hex}@example.test"
    ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    start = _now_naive() + timedelta(minutes=5)
    end = start + timedelta(minutes=30)
    block_id = await _create_self_study_block(client, token, start=start, end=end)

    response = await client.get("/api/v1/student/self-study/upcoming", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    items = response.json()
    assert any(item["blockId"] == block_id and item["canStart"] for item in items)


@pytest.mark.asyncio
async def test_start_before_window_opens_is_a_400_not_403(client):
    org = ensure_org("ss-org-b", "Self Study Org B")
    email = f"ss.student.b.{uuid.uuid4().hex}@example.test"
    ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    start = _now_naive() + timedelta(hours=2)
    end = start + timedelta(minutes=30)
    block_id = await _create_self_study_block(client, token, start=start, end=end)

    response = await client.post(
        "/api/v1/student/self-study/sessions", headers=auth_headers(token), json={"blockId": block_id}
    )
    assert response.status_code == 400, response.text


@pytest.mark.asyncio
async def test_start_within_window_creates_an_in_progress_session(client):
    org = ensure_org("ss-org-c", "Self Study Org C")
    email = f"ss.student.c.{uuid.uuid4().hex}@example.test"
    ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    start = _now_naive() - timedelta(minutes=2)
    end = start + timedelta(minutes=30)
    block_id = await _create_self_study_block(client, token, start=start, end=end)

    response = await client.post(
        "/api/v1/student/self-study/sessions", headers=auth_headers(token), json={"blockId": block_id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "IN_PROGRESS"
    assert body["phase"] == "work"
    assert body["pomodorosCompleted"] == 0

    again = await client.post(
        "/api/v1/student/self-study/sessions", headers=auth_headers(token), json={"blockId": block_id}
    )
    assert again.status_code == 200, again.text
    assert again.json()["id"] == body["id"]  # idempotent re-start returns the same session


@pytest.mark.asyncio
async def test_abandon_marks_session_ended_early(client):
    org = ensure_org("ss-org-d", "Self Study Org D")
    email = f"ss.student.d.{uuid.uuid4().hex}@example.test"
    ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    start = _now_naive() - timedelta(minutes=1)
    end = start + timedelta(minutes=30)
    block_id = await _create_self_study_block(client, token, start=start, end=end)

    started = await client.post(
        "/api/v1/student/self-study/sessions", headers=auth_headers(token), json={"blockId": block_id}
    )
    session_id = started.json()["id"]

    response = await client.post(
        f"/api/v1/student/self-study/sessions/{session_id}/abandon", headers=auth_headers(token)
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ABANDONED"


@pytest.mark.asyncio
async def test_starting_a_finished_block_again_is_a_409(client):
    org = ensure_org("ss-org-e", "Self Study Org E")
    email = f"ss.student.e.{uuid.uuid4().hex}@example.test"
    ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    start = _now_naive() - timedelta(minutes=1)
    end = start + timedelta(minutes=30)
    block_id = await _create_self_study_block(client, token, start=start, end=end)

    started = await client.post(
        "/api/v1/student/self-study/sessions", headers=auth_headers(token), json={"blockId": block_id}
    )
    session_id = started.json()["id"]
    await client.post(f"/api/v1/student/self-study/sessions/{session_id}/abandon", headers=auth_headers(token))

    response = await client.post(
        "/api/v1/student/self-study/sessions", headers=auth_headers(token), json={"blockId": block_id}
    )
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_student_cannot_start_another_students_block(client):
    org = ensure_org("ss-org-f", "Self Study Org F")
    owner_email = f"ss.student.f.owner.{uuid.uuid4().hex}@example.test"
    other_email = f"ss.student.f.other.{uuid.uuid4().hex}@example.test"
    ensure_user(email=owner_email, org_id=org, role=UserRole.STUDENT)
    ensure_user(email=other_email, org_id=org, role=UserRole.STUDENT)

    owner_token = await login(client, owner_email)
    start = _now_naive() - timedelta(minutes=1)
    end = start + timedelta(minutes=30)
    block_id = await _create_self_study_block(client, owner_token, start=start, end=end)

    other_token = await login(client, other_email)
    response = await client.post(
        "/api/v1/student/self-study/sessions", headers=auth_headers(other_token), json={"blockId": block_id}
    )
    assert response.status_code == 404, response.text
