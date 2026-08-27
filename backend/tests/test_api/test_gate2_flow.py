"""End-to-end Gate-2 vertical slice.

Covers the two demo journeys the mentor will actually be walked through:

    Plan → Do → Reflect → Next-week plan
    Do   → deterministic alert → lecturer intervention + audit

Assertions deliberately target the *contract* (provenance labels, citation
ids, defer reason enforcement, before/after diff) rather than prose, so
copy changes do not break the suite but a broken guarantee does.
"""

from __future__ import annotations

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
    """`POST /demo/reset` (see _reset_demo) always assigns the gate2 demo
    section to `demo.instructor@cursusdemo.local` inside whatever org
    `gate2_demo.py::_ensure_instructor` resolves at reset time (a different
    account than any password-login constant, and not necessarily inside an
    org named "cursus-demo" in a fresh test DB, so POST /auth/demo-session's
    `DEMO_ORG_SLUG` check can't be relied on here either). Mint a real access
    token for that exact row directly instead of going through any login
    endpoint -- same JWT the app itself would issue, just without needing a
    password or a specific org slug to exist first."""
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
    # The shared httpx client still carries the STUDENT's access_token cookie
    # from _login() above, and _extract_access_token() (src/api/auth.py)
    # checks the cookie *before* the Authorization header -- so without
    # clearing it here every "instructor" request would silently keep
    # authenticating as the student instead.
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_demo_seed_declares_simulated_assignment(client):
    headers = await _login(client, STUDENT)
    resp = await client.get("/api/v1/demo/seed", headers=headers)
    assert resp.status_code == 200, resp.text
    seed = resp.json()

    assert seed["fixtureVersion"] == "gate2_demo_v1"
    assert seed["assignment"]["title"] == "SSA101 Group Project — Part 1"
    # The four deliverables must never be presented as syllabus fact.
    assert seed["assignment"]["provenance"]["source_type"] == "simulated"
    assert len(seed["assignment"]["deliverables"]) == 4
    for item in seed["assignment"]["deliverables"]:
        assert item["provenance"]["source_type"] == "simulated"
    # ... while the source refs that *are* real point at real syllabus chunks.
    assert seed["assignment"]["sourceRefs"] == [
        "SSA101-session-13",
        "SSA101-session-14",
        "SSA101-session-15",
    ]
    assert seed["course"]["officialChunks"] >= 70


@pytest.mark.asyncio
async def test_plan_do_reflect_next_plan(client, monkeypatch):
    # This test's actual intent is "the student's own defer reason surfaces
    # verbatim in the drafted summary" -- a property of the deterministic
    # `build_summary` template, not of LLM paraphrasing fidelity. Force the
    # deterministic path so this doesn't depend on network/a real API key
    # (previously "passed" only by accident: the model_name config value was
    # broken/404-ing until 22/08 -- see src/config.py's comment on that
    # field and eval/results/report.md's P0#5 section for the full story --
    # so build_summary_llm always fell back to build_summary anyway).
    from src.services.ai import reflection_engine

    monkeypatch.setattr(reflection_engine, "has_configured_llm", lambda: False)

    headers = await _login(client, STUDENT)
    reset = await _reset_demo(client, headers)
    assignment_id = reset["assignmentId"]

    # ── PLAN ─────────────────────────────────────────────────────────
    resp = await client.post(
        "/api/v1/plans/generate",
        headers=headers,
        json={
            "assignment_id": assignment_id,
            "available_hours": 8.0,
            "preferred_sessions": ["EVENING"],
        },
    )
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    assert plan["status"] == "DRAFT"
    assert 4 <= len(plan["tasks"]) <= 6
    assert plan["capacityMinutes"] == 480
    assert plan["plannedMinutes"] == sum(t["estimatedMinutes"] for t in plan["tasks"])

    # Every task carries an estimate and an explicit AI-estimate provenance.
    for task in plan["tasks"]:
        assert task["estimatedMinutes"] > 0
        assert task["estimateProvenance"]["source_type"] == "ai_suggested"
        assert task["estimateProvenance"]["label_vi"] == "Ước tính của Curi"
    # At least one task is grounded in a real syllabus chunk with an excerpt.
    grounded = [task for task in plan["tasks"] if task["sourceRefs"]]
    assert grounded, "expected at least one task grounded in a syllabus chunk"
    ref = grounded[0]["sourceRefs"][0]
    assert ref["chunkId"].startswith("SSA101-")
    assert ref["excerpt"]
    assert ref["provenance"]["source_type"] == "official_document"

    plan_id = plan["id"]

    # AI proposes only — the plan is not active until the student confirms.
    resp = await client.post(
        "/api/v1/plans/accept", headers=headers, json={"plan_id": plan_id}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ACTIVE"
    assert resp.json()["plan"]["status"] == "IN_PROGRESS"

    # ── DO ───────────────────────────────────────────────────────────
    tasks = plan["tasks"]
    resp = await client.patch(
        f"/api/v1/plans/tasks/{tasks[0]['id']}",
        headers=headers,
        json={"status": "COMPLETED", "actual_minutes": 55},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "COMPLETED"
    assert resp.json()["actualMinutes"] == 55

    # Defer without a reason must be rejected.
    resp = await client.patch(
        f"/api/v1/plans/tasks/{tasks[2]['id']}",
        headers=headers,
        json={"status": "DEFERRED"},
    )
    assert resp.status_code == 400
    assert "reason" in resp.json()["detail"].lower()

    # A bogus reason code is rejected too — free text is not a reason.
    resp = await client.patch(
        f"/api/v1/plans/tasks/{tasks[2]['id']}",
        headers=headers,
        json={"status": "DEFERRED", "reason_code": "because"},
    )
    assert resp.status_code == 400

    resp = await client.patch(
        f"/api/v1/plans/tasks/{tasks[2]['id']}",
        headers=headers,
        json={
            "status": "DEFERRED",
            "reason_code": "underestimated_time",
            "reason_note": "Sơ đồ mất nhiều thời gian hơn dự tính.",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["reasonCode"] == "underestimated_time"
    assert resp.json()["deferCount"] == 1

    # Same state store: the plan read back shows the new statuses.
    resp = await client.get("/api/v1/plans/weekly", headers=headers)
    assert resp.status_code == 200
    weekly = resp.json()
    assert weekly["id"] == plan_id
    statuses = {task["id"]: task["status"] for task in weekly["tasks"]}
    assert statuses[tasks[0]["id"]] == "COMPLETED"
    assert statuses[tasks[2]["id"]] == "DEFERRED"

    # ── REFLECT ──────────────────────────────────────────────────────
    resp = await client.get("/api/v1/student/reflections/preview", headers=headers)
    assert resp.status_code == 200, resp.text
    preview = resp.json()
    assert preview["facts"]["completedTasks"] == 1
    assert preview["facts"]["deferredTasks"] == 1
    # Completion 1/6 -> low band; the same fixed 6-question catalog (5
    # single-choice self-feedback scales + 1 free-text note) is always asked.
    assert preview["band"] == "low"
    assert preview["questions"][-1]["id"] == "self_notes"
    assert preview["facts"]["provenance"]["source_type"] == "system_derived"

    # Memory preview is drafted without being stored.
    resp = await client.post(
        "/api/v1/student/reflections/preview-summary",
        headers=headers,
        json={
            "plan_id": plan_id,
            "answers": [{"questionId": "q_obstacle", "answer": "Sơ đồ khó hơn tưởng."}],
            "adjustments": ["split_diagram_tasks", "increase_diagram_estimate"],
        },
    )
    assert resp.status_code == 200, resp.text
    drafted = resp.json()
    assert drafted["editable"] is True
    assert "Sơ đồ khó hơn tưởng." in drafted["summary"]

    resp = await client.get("/api/v1/student/reflections", headers=headers)
    assert resp.json() == [], "preview-summary must not persist anything"

    # Confirm — the student edits the summary before it is stored.
    resp = await client.post(
        "/api/v1/student/reflections",
        headers=headers,
        json={
            "plan_id": plan_id,
            "answers": [
                {
                    "questionId": "q_obstacle",
                    "answer": "Sơ đồ use-case mất gấp đôi thời gian.",
                    "reasonCode": "underestimated_time",
                },
                {"questionId": "q_next_priority", "answer": "Nộp sớm một ngày."},
            ],
            "adjustments": [
                "split_diagram_tasks",
                "increase_diagram_estimate",
                "keep_buffer_day",
            ],
            "summary": "Bản tóm tắt tôi tự sửa.",
            "student_confirmed": True,
            "share_with_advisor": False,
        },
    )
    assert resp.status_code == 200, resp.text
    reflection = resp.json()
    assert reflection["studentConfirmed"] is True
    assert reflection["summary"] == "Bản tóm tắt tôi tự sửa."
    assert set(reflection["adjustments"]) == {
        "split_diagram_tasks",
        "increase_diagram_estimate",
        "keep_buffer_day",
    }

    # ── NEXT PLAN ────────────────────────────────────────────────────
    resp = await client.post(
        "/api/v1/plans/from-reflection",
        headers=headers,
        json={"reflection_id": reflection["id"]},
    )
    assert resp.status_code == 200, resp.text
    next_plan = resp.json()

    assert next_plan["createdFromReflectionId"] == reflection["id"]
    assert next_plan["id"] != plan_id
    # The reflection visibly changed the plan: the diagram task was split.
    split_tasks = [t for t in next_plan["tasks"] if t["derivedFrom"] == "use_case"]
    assert len(split_tasks) == 4, [t["title"] for t in next_plan["tasks"]]
    assert sum(t["estimatedMinutes"] for t in split_tasks) == 225
    changes = {item["adjustment"] for item in next_plan["reflectionChanges"]}
    assert "split_diagram_tasks" in changes
    assert "increase_diagram_estimate" in changes
    # Before/after evidence is returned so the UI does not have to guess.
    assert next_plan["previousPlan"]["id"] == plan_id


@pytest.mark.asyncio
async def test_unconfirmed_reflection_cannot_drive_next_plan(client):
    headers = await _login(client, STUDENT)
    reset = await _reset_demo(client, headers)

    resp = await client.post(
        "/api/v1/plans/generate",
        headers=headers,
        json={
            "assignment_id": reset["assignmentId"],
            "available_hours": 8.0,
            "preferred_sessions": ["EVENING"],
        },
    )
    plan_id = resp.json()["id"]

    await client.post(
        "/api/v1/student/reflections",
        headers=headers,
        json={
            "plan_id": plan_id,
            "answers": [],
            "adjustments": ["split_diagram_tasks"],
            "student_confirmed": False,
        },
    )
    resp = await client.post(
        "/api/v1/plans/from-reflection", headers=headers, json={"plan_id": plan_id}
    )
    assert resp.status_code == 400
    assert "xác nhận" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_alert_queue_and_intervention_audit(client):
    # Superseded contract note: this originally targeted a since-retired
    # /instructor/alerts + /instructor/audit surface (additive risk_engine.py
    # scoring: score/severity/signals, rulesVersion "risk_rules_v1"). That was
    # replaced by GET/POST /instructor/risks backed by risk_signal_service.py
    # (risk_type/risk_level, no numeric score) -- see
    # src/api/instructor.py::_serialize_risk_row and
    # tests/test_api/test_instructor.py for the current contract's own
    # dedicated coverage. Rewritten here to exercise the same journey
    # (queue -> detail -> intervention -> reflected in queue) against the
    # endpoints that actually exist today, rather than resurrecting a
    # deprecated response shape.
    student_headers = await _login(client, STUDENT)
    await _reset_demo(client, student_headers)

    headers = await _login_gate2_instructor(client)
    resp = await client.get("/api/v1/instructor/risks", headers=headers)
    assert resp.status_code == 200, resp.text
    risks = resp.json()
    assert risks, "demo reset must leave at least one risk case for the instructor"

    case = risks[0]
    for key in ("id", "studentId", "riskLevel", "riskType", "status", "evidence"):
        assert key in case, case

    # Detail view must expose evidence but no raw reflection/chat content.
    resp = await client.get(f"/api/v1/instructor/risks/{case['id']}", headers=headers)
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == case["id"]
    assert "reflection" not in str(detail).lower()

    # Record the human decision.
    resp = await client.post(
        f"/api/v1/instructor/risks/{case['id']}/intervention",
        headers=headers,
        json={"decision": "APPROVE", "note": "Đã mời trao đổi sau giờ học."},
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["decision"] == "APPROVE"
    assert result["status"] == "INTERVENTION_APPROVED"
    assert result["auditMetadata"]["previousState"] == "INTERVENTION_PENDING"

    # The decision is reflected back in the queue, and the F10 timeline
    # (instructor_interventions) has the audit entry.
    resp = await client.get("/api/v1/instructor/risks", headers=headers)
    updated = next(r for r in resp.json() if r["id"] == case["id"])
    assert updated["status"] == "INTERVENTION_APPROVED"

    resp = await client.get(f"/api/v1/instructor/risks/{case['id']}/interventions", headers=headers)
    assert resp.status_code == 200, resp.text
    entries = resp.json()
    assert entries, "intervention must leave an audit entry"
    assert entries[0]["decision"] == "APPROVE"


@pytest.mark.asyncio
async def test_invalid_intervention_action_rejected(client):
    student_headers = await _login(client, STUDENT)
    await _reset_demo(client, student_headers)
    headers = await _login_gate2_instructor(client)
    risks = (await client.get("/api/v1/instructor/risks", headers=headers)).json()
    risk_id = risks[0]["id"]

    resp = await client.post(
        f"/api/v1/instructor/risks/{risk_id}/intervention",
        headers=headers,
        json={"decision": "delete_student"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_demo_reset_is_idempotent(client):
    headers = await _login(client, STUDENT)
    first = await _reset_demo(client, headers)
    second = await _reset_demo(client, headers)
    assert first["assignmentId"] == second["assignmentId"]
    assert first["sectionId"] == second["sectionId"]
    assert first["officialChunks"] == second["officialChunks"]

    # After a reset the student starts with no plan for the current week.
    resp = await client.get("/api/v1/plans/weekly", headers=headers)
    assert resp.status_code == 404
