"""Tests for admin/instructor academic term + course exam + class activity
endpoints added to `src/api/admin.py`, org-scoped throughout."""

from __future__ import annotations

import uuid

import pytest

from src.db.models import UserRole
from tests.support.semester_practice_fixtures import (
    auth_headers,
    enroll_student,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


def _code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


@pytest.mark.asyncio
async def test_admin_upserts_term_scoped_to_own_org(client):
    org_a = ensure_org("term-org-a", "Term Org A")
    org_b = ensure_org("term-org-b", "Term Org B")
    admin_a = f"term.admin.a.{uuid.uuid4().hex}@example.test"
    admin_b = f"term.admin.b.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_a, org_id=org_a, role=UserRole.ADMIN)
    ensure_user(email=admin_b, org_id=org_b, role=UserRole.ADMIN)

    token_a = await login(client, admin_a)
    resp = await client.put(
        "/api/v1/admin/academic-terms/active",
        headers=auth_headers(token_a),
        json={"name": "Fall 2026 A", "startDate": "2026-08-31", "studyWeeks": 10, "examWeeks": 2},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Fall 2026 A"

    # Org B never configured a term — must see none, not org A's.
    token_b = await login(client, admin_b)
    resp_b = await client.get("/api/v1/admin/academic-terms/active", headers=auth_headers(token_b))
    assert resp_b.status_code == 200
    assert resp_b.json() is None


@pytest.mark.asyncio
async def test_instructor_cannot_manage_terms_but_can_log_class_activity(client):
    org_a = ensure_org("term-org-c", "Term Org C")
    admin_email = f"term.admin.c.{uuid.uuid4().hex}@example.test"
    instr_email = f"term.instr.c.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_email, org_id=org_a, role=UserRole.ADMIN)
    instructor_id = ensure_user(email=instr_email, org_id=org_a, role=UserRole.INSTRUCTOR)
    code = _code("ACT")
    course_id = ensure_course(code=code, org_id=org_a)
    enroll_student(
        student_id=ensure_user(email=f"term.stu.c.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.STUDENT),
        course_id=course_id,
        instructor_id=instructor_id,
    )
    # Make the instructor actually teach the course (section instructor_id).
    from src.db.connection import SessionLocal
    from src.db.models import CourseSection

    db = SessionLocal()
    try:
        db.query(CourseSection).filter_by(course_id=course_id).update({"instructor_id": instructor_id})
        db.commit()
    finally:
        db.close()

    instr_token = await login(client, instr_email)

    # Instructor is blocked from the ADMIN-only term endpoint.
    term_resp = await client.put(
        "/api/v1/admin/academic-terms/active",
        headers=auth_headers(instr_token),
        json={"name": "Should Fail", "startDate": "2026-08-31"},
    )
    assert term_resp.status_code == 403

    # But CAN log a class activity for a course they teach.
    activity_resp = await client.post(
        "/api/v1/admin/class-activities",
        headers=auth_headers(instr_token),
        json={
            "courseId": course_id,
            "activityDate": "2026-09-01",
            "kind": "LECTURE_HELD",
            "title": "Intro lecture",
        },
    )
    assert activity_resp.status_code == 201, activity_resp.text
    assert activity_resp.json()["kind"] == "LECTURE_HELD"

    list_resp = await client.get(
        f"/api/v1/admin/class-activities?course_id={course_id}", headers=auth_headers(instr_token)
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


@pytest.mark.asyncio
async def test_instructor_cannot_log_activity_for_course_they_do_not_teach(client):
    org_a = ensure_org("term-org-d", "Term Org D")
    instr_email = f"term.instr.d.{uuid.uuid4().hex}@example.test"
    other_instr_email = f"term.instr.d2.{uuid.uuid4().hex}@example.test"
    ensure_user(email=instr_email, org_id=org_a, role=UserRole.INSTRUCTOR)
    other_instructor_id = ensure_user(email=other_instr_email, org_id=org_a, role=UserRole.INSTRUCTOR)
    code = _code("NOTEACH")
    course_id = ensure_course(code=code, org_id=org_a)
    enroll_student(
        student_id=ensure_user(email=f"term.stu.d.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.STUDENT),
        course_id=course_id,
        instructor_id=other_instructor_id,
    )

    instr_token = await login(client, instr_email)
    resp = await client.post(
        "/api/v1/admin/class-activities",
        headers=auth_headers(instr_token),
        json={"courseId": course_id, "activityDate": "2026-09-01", "kind": "LECTURE_HELD", "title": "x"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_instructor_cannot_read_class_activities_for_course_they_do_not_teach(client):
    """IDOR regression test (found 22/08 via RBAC sweep, same bug shape as the
    guardrail-reviews fix from 21/08): the GET sibling of the POST tested
    above had no `instructor_teaches_course` check at all -- any instructor
    could read another instructor's class-activity log for a course they
    have zero relationship to."""
    org_a = ensure_org("term-org-idor", "Term Org IDOR")
    owner_email = f"term.instr.idor-owner.{uuid.uuid4().hex}@example.test"
    outsider_email = f"term.instr.idor-outsider.{uuid.uuid4().hex}@example.test"
    owner_id = ensure_user(email=owner_email, org_id=org_a, role=UserRole.INSTRUCTOR)
    ensure_user(email=outsider_email, org_id=org_a, role=UserRole.INSTRUCTOR)
    code = _code("IDOR")
    course_id = ensure_course(code=code, org_id=org_a)
    enroll_student(
        student_id=ensure_user(email=f"term.stu.idor.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.STUDENT),
        course_id=course_id,
        instructor_id=owner_id,
    )

    owner_token = await login(client, owner_email)
    post_resp = await client.post(
        "/api/v1/admin/class-activities",
        headers=auth_headers(owner_token),
        json={"courseId": course_id, "activityDate": "2026-09-01", "kind": "LECTURE_HELD", "title": "Owner's lecture"},
    )
    assert post_resp.status_code == 201, post_resp.text

    # The actual owner can read it back.
    owner_read = await client.get(
        f"/api/v1/admin/class-activities?course_id={course_id}", headers=auth_headers(owner_token)
    )
    assert owner_read.status_code == 200
    assert len(owner_read.json()) == 1

    # An instructor with NO relationship to this course must be rejected, not
    # handed the log.
    outsider_token = await login(client, outsider_email)
    outsider_read = await client.get(
        f"/api/v1/admin/class-activities?course_id={course_id}", headers=auth_headers(outsider_token)
    )
    assert outsider_read.status_code == 403, outsider_read.text


@pytest.mark.asyncio
async def test_course_exam_conflict_detection(client):
    org_a = ensure_org("term-org-e", "Term Org E")
    admin_email = f"term.admin.e.{uuid.uuid4().hex}@example.test"
    instr_email = f"term.instr.e.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_email, org_id=org_a, role=UserRole.ADMIN)
    ensure_user(email=instr_email, org_id=org_a, role=UserRole.INSTRUCTOR)
    course_1 = ensure_course(code=_code("EX1"), org_id=org_a)
    course_2 = ensure_course(code=_code("EX2"), org_id=org_a)

    token = await login(client, admin_email)
    term_resp = await client.put(
        "/api/v1/admin/academic-terms/active",
        headers=auth_headers(token),
        json={"name": "Exam Term", "startDate": "2026-08-31", "studyWeeks": 2, "examWeeks": 2},
    )
    assert term_resp.status_code == 200
    exam_start = term_resp.json()["exam_start"]

    exam1_resp = await client.put(
        "/api/v1/admin/course-exams",
        headers=auth_headers(token),
        json={
            "courseId": course_1,
            "kind": "FINAL",
            "sessions": [{"examDate": exam_start, "slotId": 1, "label": "Ca 1"}],
        },
    )
    assert exam1_resp.status_code == 200, exam1_resp.text

    exam2_resp = await client.put(
        "/api/v1/admin/course-exams",
        headers=auth_headers(token),
        json={
            "courseId": course_2,
            "kind": "FINAL",
            "sessions": [{"examDate": exam_start, "slotId": 1, "label": "Ca 1"}],
        },
    )
    assert exam2_resp.status_code == 200, exam2_resp.text
