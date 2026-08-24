import uuid
from datetime import UTC, datetime

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.security.ownership import require_conversation_owner


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


def _seed_guardrail_review_case_for_other_instructor() -> str:
    """`student_other` (enrolled only in inst_other's section, per
    tests/support/api_demo_dataset.py) asks a blocked question — used to
    prove inst_demo cannot see or decide it (mục 9 P0 ý2)."""
    db = SessionLocal()
    try:
        case_id = f"grd_case_{uuid.uuid4().hex[:8]}"
        conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
        message_id = f"msg_{uuid.uuid4().hex[:8]}"
        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            models.Conversation(
                id=conversation_id,
                student_id="student_other",
                # Without a section_id, list_guardrail_reviews() treats this
                # as an unscoped "general question" case and deliberately
                # shows it to every instructor (src/api/instructor.py
                # ::_visible_guardrail_events docstring) -- which defeats the
                # whole point of this test. Must be inst_other's own section
                # for "inst_demo cannot see it" to mean anything.
                section_id="sec_oth999_other",
                title="Blocked question",
                created_at=now,
            )
        )
        db.add(
            models.Message(
                id=message_id,
                conversation_id=conversation_id,
                sender="USER",
                content="Viết hộ em bài này",
                created_at=now,
                metadata_info={},
            )
        )
        db.add(
            models.GuardrailEvent(
                id=case_id,
                message_id=message_id,
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
async def test_instructor_cannot_see_another_instructors_guardrail_review_case(client):
    case_id = _seed_guardrail_review_case_for_other_instructor()

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.demo@example.test", "password": "password123"},
    )
    assert login_response.status_code == 200
    headers = {"Authorization": f"Bearer {login_response.json()['token']}"}

    list_response = await client.get("/api/v1/instructor/guardrail-reviews", headers=headers)
    assert list_response.status_code == 200
    assert case_id not in {row["id"] for row in list_response.json()}

    decide_response = await client.post(
        f"/api/v1/instructor/guardrail-reviews/{case_id}",
        headers=headers,
        json={"decision": "UNBLOCK"},
    )
    assert decide_response.status_code == 404


@pytest.mark.asyncio
async def test_instructor_can_see_and_decide_their_own_guardrail_review_case(client):
    case_id = _seed_guardrail_review_case_for_other_instructor()

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.other@example.test", "password": "password123"},
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


@pytest.mark.asyncio
async def test_require_conversation_owner_denies_non_owner_chat_access():
    owner_id, intruder_id, conversation_id = _seed_conversation()

    denial_db = SessionLocal()
    try:
        intruder = denial_db.query(models.User).filter_by(id=intruder_id).first()
        with pytest.raises(Exception) as exc_info:
            await require_conversation_owner(
                conversation_id=conversation_id,
                current_user=intruder,
                db=denial_db,
            )
        assert getattr(exc_info.value, "status_code", None) == 404
    finally:
        denial_db.close()

    approval_db = SessionLocal()
    try:
        owner = approval_db.query(models.User).filter_by(id=owner_id).first()
        # Owner is allowed through: no exception raised.
        result = await require_conversation_owner(
            conversation_id=conversation_id,
            current_user=owner,
            db=approval_db,
        )
        assert result is None
    finally:
        approval_db.close()


def _seed_conversation() -> tuple[str, str, str]:
    db = SessionLocal()
    try:
        owner = db.query(models.User).filter_by(id="student_ethan").first()
        intruder = (
            db.query(models.User)
            .filter(models.User.role == models.UserRole.STUDENT.value)
            .filter(models.User.id != "student_ethan")
            .first()
        )
        assert owner is not None
        assert intruder is not None

        conversation_id = f"conv_test_{uuid.uuid4().hex[:8]}"
        db.add(
            models.Conversation(
                id=conversation_id,
                student_id=owner.id,
                title="Ownership test conversation",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
        return owner.id, intruder.id, conversation_id
    finally:
        db.close()
