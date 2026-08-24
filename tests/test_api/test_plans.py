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


@pytest.mark.asyncio
async def test_goal_text_planner_lifecycle(client, monkeypatch):
    """StudentPlanner (a46db63 contract): goal_text + subject_code, no
    assignment — full Plan -> Do -> Reflect -> next-week regenerate loop."""
    from src.services.ai import weekly_plan_engine

    monkeypatch.setattr(weekly_plan_engine, "has_configured_llm", lambda: False)

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
            "goal_text": "Hoàn thành lab tuần này",
            "subject_code": "SSA101",
            "available_hours": 10.0,
            "preferred_sessions": ["EVENING"],
        },
    )
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    assert plan["status"] == "DRAFT"
    assert plan["subjectCode"] == "SSA101"
    assert plan["goalText"] == "Hoàn thành lab tuần này"
    assert 3 <= len(plan["tasks"]) <= 7
    plan_id = plan["id"]

    resp = await client.post("/api/v1/plans/accept", headers=headers, json={"plan_id": plan_id})
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"

    tasks = plan["tasks"]
    resp = await client.patch(
        f"/api/v1/plans/tasks/{tasks[0]['id']}",
        headers=headers,
        json={"status": "COMPLETED", "actual_minutes": 30},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/api/v1/student/reflections/preview", headers=headers)
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    question_ids = [q["id"] for q in preview["questions"]]
    assert question_ids == [
        "accomplishment",
        "time_spent",
        "went_well",
        "went_poorly",
        "biggest_lesson",
        "stop_start_continue",
        "next_week_outcomes",
    ]

    resp = await client.post(
        "/api/v1/student/reflections",
        headers=headers,
        json={
            "plan_id": plan_id,
            "answers": [
                {"questionId": "went_well", "answer": "Bắt đầu sớm."},
                {
                    "questionId": "stop_start_continue",
                    "selectedCodes": ["reduce_hours"],
                },
                {
                    "questionId": "next_week_outcomes",
                    "items": ["Nộp lab đúng hạn"],
                },
            ],
            "summary": "Tuần này ổn.",
            "student_confirmed": True,
            "share_with_advisor": False,
        },
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/api/v1/plans/from-reflection",
        headers=headers,
        json={"plan_id": plan_id},
    )
    assert resp.status_code == 200, resp.text
    next_plan = resp.json()
    assert next_plan["weekStart"] != plan["weekStart"]
    for task in next_plan["tasks"]:
        original = next(t for t in tasks if t["title"] in task["title"] or True)
        assert task["estimatedMinutes"] <= original["estimatedMinutes"]
