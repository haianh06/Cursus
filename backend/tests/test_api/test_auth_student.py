from datetime import date

import pytest


@pytest.mark.asyncio
async def test_auth_and_student_dashboard_endpoints(client):
    # The mock semester is provisioned against the real current ISO week
    # (see student_mock_data_service.py), so reflection lookups must target
    # that same week rather than a fixed value the fixture may not have data
    # for.
    current_week = date.today().isocalendar().week
    # 1. Login with demo student
    payload = {
        "email": "student.demo@example.test",
        "password": "password123"
    }
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["email"] == "student.demo@example.test"
    assert data["user"]["role"] == "STUDENT"

    token = data["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get /me
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 200
    me_data = resp.json()
    assert me_data["id"] == data["user"]["id"]

    # 3. Get student dashboard
    resp = await client.get("/api/v1/student/dashboard", headers=headers)
    assert resp.status_code == 200
    dash_data = resp.json()
    assert "currentWeek" in dash_data
    assert "weeklyProgress" in dash_data
    assert "workload" in dash_data
    assert "riskStatus" in dash_data

    # 4. Get student courses
    resp = await client.get("/api/v1/student/courses", headers=headers)
    assert resp.status_code == 200
    courses = resp.json()
    assert len(courses) > 0

    # 5. Generate Weekly Reflection
    resp = await client.post(
        "/api/v1/student/reflections/generate", json={"week_number": current_week}, headers=headers
    )
    assert resp.status_code == 200
    reflection = resp.json()
    assert reflection["weekNumber"] == current_week
    assert "content" in reflection
    assert "metrics" in reflection

    # 6. Get Weekly Reflections.
    #    A reflection is now only stored once the student confirms it
    #    (POST /student/reflections with student_confirmed), so the list is
    #    legitimately empty until then — the system no longer writes a
    #    reflection on the student's behalf.
    resp = await client.get("/api/v1/student/reflections", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

    resp = await client.post(
        "/api/v1/student/reflections",
        json={
            "week_number": current_week,
            "answers": [{"questionId": "q_next_priority", "answer": "Ôn sớm hơn."}],
            "adjustments": ["keep_buffer_day"],
            "student_confirmed": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    resp = await client.get("/api/v1/student/reflections", headers=headers)
    refs = resp.json()
    assert len(refs) > 0

    # 7. Get Risks
    resp = await client.get("/api/v1/student/risks", headers=headers)
    assert resp.status_code == 200
    risks = resp.json()
    assert isinstance(risks, list)

