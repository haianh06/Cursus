import uuid
from datetime import datetime, time

import pytest

from src.services.mock.student_mock_data_service import SLOTS, StudentMockDataService
from tests.support.invite_helpers import create_test_invite


@pytest.mark.asyncio
async def test_register_student_gets_four_course_mock_semester(client, monkeypatch):
    email = f"mock.student.{uuid.uuid4().hex}@example.test"
    password = "StrongPassword123"

    invite_token = create_test_invite(email, role="STUDENT")
    register_response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Mock Student",
            "invite_token": invite_token,
        },
    )
    assert register_response.status_code == 201
    # Invited users are pre-verified, so no /auth/email/verify step is needed.

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['token']}"}

    dashboard = await client.get("/api/v1/student/dashboard", headers=headers)
    assert dashboard.status_code == 200
    data = dashboard.json()
    codes = {course["code"] for course in data["courses"]}
    assert {"SSA101", "PRF192", "CEA201", "CSI106"}.issubset(codes)
    assert len(data["upcomingAssignments"]) >= 4

    timetable = await client.get("/api/v1/plans/timetable", headers=headers)
    assert timetable.status_code == 200
    blocks = timetable.json()["blocks"]
    class_blocks = [block for block in blocks if block["kind"] == "CLASS"]
    assert len(class_blocks) == 8  # 4 study days * 2 slots

    # Validate slot boundaries and morning/afternoon-only rule.
    by_day: dict[str, list] = {}
    for block in class_blocks:
        start = datetime.fromisoformat(block["start"])
        end = datetime.fromisoformat(block["end"])
        day_key = start.date().isoformat()
        by_day.setdefault(day_key, []).append((start, end))
        slot_ok = any(
            start.time() == slot_start and end.time() == slot_end
            for slot_start, slot_end in SLOTS.values()
        )
        assert slot_ok

    assert len(by_day) == 4
    for sessions in by_day.values():
        assert len(sessions) == 2
        morning = all(start.time() <= time(12, 20) for start, _ in sessions)
        afternoon = all(start.time() >= time(12, 50) for start, _ in sessions)
        assert morning or afternoon


def test_rest_day_is_stable_per_student():
    student_id = "user_demo_rest_day"
    first = StudentMockDataService.rest_day_for_student(student_id)
    second = StudentMockDataService.rest_day_for_student(student_id)
    assert first == second
    assert 0 <= first <= 4
