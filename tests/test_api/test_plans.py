import pytest


@pytest.mark.asyncio
async def test_planner_lifecycle_endpoints(client):
    # 1. Login
    payload = {
        "email": "student.demo@example.test",
        "password": "password123"
    }
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get assignments to use for planner
    resp = await client.get("/api/v1/student/dashboard", headers=headers)
    assert resp.status_code == 200
    dash_data = resp.json()
    asg_id = dash_data["upcomingAssignments"][0]["id"]

    # 3. Generate draft plan
    gen_payload = {
        "assignment_id": asg_id,
        "available_hours": 10.0,
        "preferred_sessions": ["MORNING", "EVENING"]
    }
    resp = await client.post("/api/v1/plans/generate", json=gen_payload, headers=headers)
    assert resp.status_code == 200
    plan_data = resp.json()
    assert plan_data["status"] == "DRAFT"
    assert len(plan_data["tasks"]) > 0
    plan_id = plan_data["id"]

    # 4. Accept/Approve plan
    resp = await client.post("/api/v1/plans/accept", json={"plan_id": plan_id}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ACTIVE"

    # 5. Fetch weekly plan for the current Monday-based ISO week
    resp = await client.get("/api/v1/plans/weekly", headers=headers)
    assert resp.status_code == 200
    weekly = resp.json()
    assert "id" in weekly
    assert weekly["id"] == plan_id
    assert weekly["status"] == "IN_PROGRESS"

    # 6. Update study task status
    task_id = weekly["tasks"][0]["id"]
    resp = await client.patch(
        f"/api/v1/plans/tasks/{task_id}",
        json={"status": "COMPLETED", "actual_minutes": 45},
        headers=headers
    )
    assert resp.status_code == 200
    task_res = resp.json()
    assert task_res["status"] == "COMPLETED"
    assert task_res["actualMinutes"] == 45


@pytest.mark.asyncio
async def test_generate_plan_rejects_unenrolled_assignment(client):
    """M3: students must not generate plans for foreign assignments."""
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "student.demo@example.test", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.post(
        "/api/v1/plans/generate",
        headers=headers,
        json={
            "assignment_id": "asg_oth999_other",
            "available_hours": 8.0,
            "preferred_sessions": ["EVENING"],
        },
    )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Assignment not found"
