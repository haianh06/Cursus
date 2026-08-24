"""Tests for the lecture-driven weekly plan flow (`src/api/lecture_plan.py`).

Second, independent plan-generation flow — must never collide with Gate 2's
assignment-driven planner (`src/api/plans.py`). See
`src/services/lecture_plan_service.py` module docstring for the collision
analysis this suite checks.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from src.db.connection import SessionLocal
from src.db.models import UserRole
from src.services.academic.timetable_service import monday_of
from src.services.ai.plan_builder import PlanBuilder
from src.services.mock.gate2_demo import PART1_ASSIGNMENT_ID, Gate2DemoService
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


def _unique_code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


def _next_week_monday() -> date:
    # A week comfortably in the future so it never collides with any
    # week-specific Gate2 fixture data.
    return monday_of(date.today() + timedelta(days=21))


async def _setup_semester_with_class_slot(client, *, org_id: str, token: str, course_id: str, weekday: int):
    monday = _next_week_monday()
    resp = await client.post(
        "/api/v1/student/semesters",
        headers=auth_headers(token),
        json={
            "name": "Lecture Plan Test Term",
            "start_date": (monday - timedelta(days=7)).isoformat(),
            "end_date": (monday + timedelta(days=28)).isoformat(),
            "course_ids": [course_id],
            "weekly_slots": [{"weekday": weekday, "slot_id": 1, "course_id": course_id}],
            "exceptions": [],
        },
    )
    assert resp.status_code == 201, resp.text
    return monday


@pytest.mark.asyncio
async def test_generate_lecture_plan_succeeds_with_active_semester(client):
    org_id = ensure_org("lecplan-org-a", "Lecture Plan Org A")
    student_email = f"lecplan.student.a.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    ensure_user(
        email=f"lecplan.instr.a.{uuid.uuid4().hex}@example.test", org_id=org_id, role=UserRole.INSTRUCTOR
    )
    code = _unique_code("LPA")
    course_id = ensure_course(code=code, org_id=org_id, name="Lecture Plan Course A")

    token = await login(client, student_email)
    monday = await _setup_semester_with_class_slot(
        client, org_id=org_id, token=token, course_id=course_id, weekday=1  # Tuesday
    )

    resp = await client.post(
        "/api/v1/student/lecture-plan/generate",
        headers=auth_headers(token),
        json={"week_start": monday.isoformat(), "available_hours": 8.0, "language": "vi"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["tasks"]) > 0
    assert data["assignmentId"] == ""
    assert data["weekStart"] == monday.isoformat()

    # Persisted goals carry the lecture_plan tag and never an assignment_id key.
    db = SessionLocal()
    try:
        from src.db.models import WeeklyPlan

        plan = db.query(WeeklyPlan).filter_by(id=data["id"]).first()
        assert plan is not None
        assert plan.goals["source"] == "lecture_plan"
        assert "assignment_id" not in plan.goals
    finally:
        db.close()


@pytest.mark.asyncio
async def test_generate_lecture_plan_fails_without_active_semester(client):
    org_id = ensure_org("lecplan-org-b", "Lecture Plan Org B")
    student_email = f"lecplan.student.b.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)

    token = await login(client, student_email)
    resp = await client.post(
        "/api/v1/student/lecture-plan/generate",
        headers=auth_headers(token),
        json={"available_hours": 6.0},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_generate_lecture_plan_fails_with_no_sessions_in_week(client):
    org_id = ensure_org("lecplan-org-c", "Lecture Plan Org C")
    student_email = f"lecplan.student.c.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    ensure_user(
        email=f"lecplan.instr.c.{uuid.uuid4().hex}@example.test", org_id=org_id, role=UserRole.INSTRUCTOR
    )
    code = _unique_code("LPC")
    course_id = ensure_course(code=code, org_id=org_id, name="Lecture Plan Course C")

    token = await login(client, student_email)
    monday = _next_week_monday()
    # Semester term with no weekly_slots at all -> no sessions any week.
    resp = await client.post(
        "/api/v1/student/semesters",
        headers=auth_headers(token),
        json={
            "name": "Empty Term",
            "start_date": (monday - timedelta(days=7)).isoformat(),
            "end_date": (monday + timedelta(days=28)).isoformat(),
            "course_ids": [course_id],
            "weekly_slots": [],
            "exceptions": [],
        },
    )
    assert resp.status_code == 201, resp.text

    resp = await client.post(
        "/api/v1/student/lecture-plan/generate",
        headers=auth_headers(token),
        json={"week_start": monday.isoformat(), "available_hours": 6.0},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_lecture_plan_never_touches_gate2_plan_data(client):
    """Generating a lecture plan for the same student/week as a Gate2 plan
    must leave the Gate2 plan's shape and content completely unaffected, and
    the two must never be confused by either app's "current plan" lookups."""
    org_id = ensure_org("lecplan-org-d", "Lecture Plan Org D")
    student_email = f"lecplan.student.d.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    ensure_user(
        email=f"lecplan.instr.d.{uuid.uuid4().hex}@example.test", org_id=org_id, role=UserRole.INSTRUCTOR
    )
    code = _unique_code("LPD")
    course_id = ensure_course(code=code, org_id=org_id, name="Lecture Plan Course D")

    token = await login(client, student_email)
    monday = await _setup_semester_with_class_slot(
        client, org_id=org_id, token=token, course_id=course_id, weekday=2  # Wednesday
    )
    week_number = monday.isocalendar().week

    # Build a Gate2 (assignment-driven) plan directly for the exact same
    # student + week_number, mirroring what plan_builder.PlanBuilder.generate
    # does for the demo assignment.
    db = SessionLocal()
    try:
        Gate2DemoService(db).ensure_student(student_id)
    finally:
        db.close()

    db = SessionLocal()
    try:
        from src.db.models import Assignment, WeeklyPlan

        assignment = db.query(Assignment).filter_by(id=PART1_ASSIGNMENT_ID).first()
        assert assignment is not None
        gate2_plan = PlanBuilder(db).generate(
            student_id=student_id,
            assignment=assignment,
            available_hours=10.0,
            week_start=monday,
        )
        db.commit()
        gate2_plan_id = gate2_plan.id
        gate2_goals_before = dict(gate2_plan.goals)
        gate2_task_count_before = (
            db.query(WeeklyPlan).filter_by(id=gate2_plan_id).first()
        )
        assert gate2_task_count_before is not None
    finally:
        db.close()

    # Now generate the lecture plan for the identical week.
    resp = await client.post(
        "/api/v1/student/lecture-plan/generate",
        headers=auth_headers(token),
        json={"week_start": monday.isoformat(), "available_hours": 8.0},
    )
    assert resp.status_code == 200, resp.text
    lecture_plan_id = resp.json()["id"]
    assert lecture_plan_id != gate2_plan_id

    # 1. Gate2's own WeeklyPlan row is byte-for-byte unchanged.
    db = SessionLocal()
    try:
        from src.db.models import WeeklyPlan

        gate2_plan_after = db.query(WeeklyPlan).filter_by(id=gate2_plan_id).first()
        assert gate2_plan_after is not None
        assert gate2_plan_after.goals == gate2_goals_before
    finally:
        db.close()

    # 2. Gate2's own "current plan" resolution (GET /plans/weekly) still
    # returns the Gate2 plan, not the lecture plan, for this week.
    resp = await client.get(
        f"/api/v1/plans/weekly?week_number={week_number}", headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    weekly = resp.json()
    assert weekly["id"] == gate2_plan_id
    assert weekly["assignmentId"] == PART1_ASSIGNMENT_ID
    # 2b. This IS a silent override (a real lecture_plan for this exact week
    # lost to the Gate2 plan) -- the response must say so instead of leaving
    # the student with no way to know the lecture plan exists at all.
    assert any("kế hoạch theo lịch học" in warning for warning in weekly["warnings"])

    # 3. Gate2's timetable/self-study view never shows the lecture plan's
    # blocks (timetable_service._self_study_blocks skips source=lecture_plan).
    resp = await client.get(
        f"/api/v1/plans/timetable?week_start={monday.isoformat()}", headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    blocks = resp.json()["blocks"]
    lecture_titles = {"Ôn bài trước", "Luyện tập sau"}
    for block in blocks:
        title = block.get("title") or ""
        assert not any(title.startswith(prefix) for prefix in lecture_titles)

    # 4. The lecture plan itself is fetchable through its own endpoint and
    # correctly tagged.
    resp = await client.get(
        f"/api/v1/student/lecture-plan/{lecture_plan_id}", headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["assignmentId"] == ""


@pytest.mark.asyncio
async def test_gate2_plan_alone_has_no_superseded_warning(client):
    """The new "your lecture plan was overridden" warning must only fire
    when a real lecture_plan for the same week actually lost -- a lone Gate2
    plan (the common case, no lecture plan generated at all) must not."""
    org_id = ensure_org("lecplan-org-e", "Lecture Plan Org E")
    student_email = f"lecplan.student.e.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    token = await login(client, student_email)
    monday = _next_week_monday()
    week_number = monday.isocalendar().week

    db = SessionLocal()
    try:
        Gate2DemoService(db).ensure_student(student_id)
    finally:
        db.close()

    db = SessionLocal()
    try:
        from src.db.models import Assignment

        assignment = db.query(Assignment).filter_by(id=PART1_ASSIGNMENT_ID).first()
        PlanBuilder(db).generate(
            student_id=student_id, assignment=assignment, available_hours=10.0, week_start=monday
        )
        db.commit()
    finally:
        db.close()

    resp = await client.get(
        f"/api/v1/plans/weekly?week_number={week_number}", headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    warnings = resp.json()["warnings"]
    assert not any("kế hoạch theo lịch học" in warning for warning in warnings)
