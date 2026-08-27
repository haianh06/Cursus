import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal


@pytest.mark.asyncio
async def test_student_cannot_update_another_students_task(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        other_task = (
            db.query(models.StudyTask)
            .join(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(models.WeeklyPlan.student_id != "student_ethan")
            .first()
        )
    finally:
        db.close()

    assert other_task is not None

    response = await client.patch(
        f"/api/v1/plans/tasks/{other_task.id}",
        json={"status": "COMPLETED", "actual_minutes": 45},
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_read_unenrolled_course_detail(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        enrolled_course_ids = {
            course_id
            for (course_id,) in (
                db.query(models.CourseSection.course_id)
                .join(models.Enrollment)
                .filter(models.Enrollment.student_id == "student_ethan")
                .all()
            )
        }
        other_course = (
            db.query(models.Course)
            .filter(~models.Course.id.in_(enrolled_course_ids))
            .first()
        )
    finally:
        db.close()

    assert other_course is not None

    response = await client.get(
        f"/api/v1/student/courses/{other_course.id}",
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_student_cannot_read_unenrolled_assignment_detail(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        enrolled_section_ids = {
            section_id
            for (section_id,) in (
                db.query(models.Enrollment.section_id)
                .filter(models.Enrollment.student_id == "student_ethan")
                .all()
            )
        }
        other_assignment = (
            db.query(models.Assignment)
            .filter(~models.Assignment.section_id.in_(enrolled_section_ids))
            .first()
        )
    finally:
        db.close()

    assert other_assignment is not None

    response = await client.get(
        f"/api/v1/student/assignments/{other_assignment.id}",
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_instructor_cannot_read_another_instructors_risk(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "instructor.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        other_risk = (
            db.query(models.RiskSignal)
            .join(models.CourseSection)
            .filter(models.CourseSection.instructor_id != "inst_demo")
            .first()
        )
    finally:
        db.close()

    assert other_risk is not None

    response = await client.get(
        f"/api/v1/instructor/risks/{other_risk.id}",
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 404


def _seed_guardrail_review_case() -> str:
    """GuardrailEvent no longer links to a conversation/section (chat feature
    removed), so a blocked case can no longer be scoped to a specific
    instructor's class -- every instructor/admin can see and decide every
    case (see src/repositories/ownership_repository.py
    ::instructor_owns_guardrail_event)."""
    db = SessionLocal()
    try:
        case_id = f"grd_case_{uuid.uuid4().hex[:8]}"
        db.add(
            models.GuardrailEvent(
                id=case_id,
                classification="BLOCKED",
                safety_evaluation={},
                review_status="PENDING",
            )
        )
        db.commit()
        return case_id
    finally:
        db.close()


@pytest.mark.asyncio
async def test_any_instructor_can_see_and_decide_a_guardrail_review_case(client):
    case_id = _seed_guardrail_review_case()

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.demo@example.test", "password": "password123"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['token']}"}

    list_response = await client.get("/api/v1/instructor/guardrail-reviews", headers=headers)
    assert list_response.status_code == 200
    assert case_id in {row["id"] for row in list_response.json()}

    decide_response = await client.post(
        f"/api/v1/instructor/guardrail-reviews/{case_id}",
        headers=headers,
        json={"decision": "UNBLOCK"},
    )
    assert decide_response.status_code == 200


@pytest.mark.asyncio
async def test_student_cannot_accept_another_students_weekly_plan(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        other_plan = (
            db.query(models.WeeklyPlan)
            .filter(models.WeeklyPlan.student_id != "student_ethan")
            .first()
        )
    finally:
        db.close()

    assert other_plan is not None

    response = await client.post(
        "/api/v1/plans/accept",
        json={"plan_id": other_plan.id},
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_student_can_accept_own_weekly_plan(client):
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200

    db = SessionLocal()
    try:
        own_plan = (
            db.query(models.WeeklyPlan)
            .filter_by(student_id="student_ethan")
            .first()
        )
    finally:
        db.close()

    assert own_plan is not None

    response = await client.post(
        "/api/v1/plans/accept",
        json={"plan_id": own_plan.id},
        headers={"Authorization": f"Bearer {login_response.json()['token']}"},
    )

    assert response.status_code == 200


