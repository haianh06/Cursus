"""Tests for student semester setup (courses + weekly slots), org-scoped."""

from __future__ import annotations

import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.db.models import UserRole
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


def _unique_code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


@pytest.mark.asyncio
async def test_catalog_shows_shared_courses_regardless_of_org(client):
    """`Course.code` has a database-wide unique constraint (src/db/models.py)
    — this schema only ever supports one shared course catalog, not a
    per-org duplicate one (matches src/api/admin.py's AdminReadService,
    which never filtered the catalog by org either). Verified live against
    real seed data: Gate2's demo accounts (org_cursus_demo) and its demo
    courses (org_fpt_university) sit in different orgs, so a strict
    catalog filter here made the Semester feature's catalog empty for the
    actual demo student — this test locks in the corrected behavior."""
    org_a = ensure_org("sem-org-a", "Semester Org A")
    org_b = ensure_org("sem-org-b", "Semester Org B")
    student_email = f"sem.student.a.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_a, role=UserRole.STUDENT)
    ensure_user(email=f"sem.instr.a.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.INSTRUCTOR)

    code_a = _unique_code("SMA")
    code_b = _unique_code("SMB")
    ensure_course(code=code_a, org_id=org_a, name="Org A Course")
    ensure_course(code=code_b, org_id=org_b, name="Org B Course")

    token = await login(client, student_email)
    response = await client.get("/api/v1/student/semesters/catalog", headers=auth_headers(token))
    assert response.status_code == 200
    codes = {c["code"] for c in response.json()["courses"]}
    assert code_a in codes
    assert code_b in codes


@pytest.mark.asyncio
async def test_create_semester_rejects_nonexistent_course_id(client):
    """The catalog is shared (see test above), but a made-up/nonexistent
    course_id must still be rejected — that boundary is "does this course
    exist at all", not "does it belong to my org"."""
    org_a = ensure_org("sem-org-a2", "Semester Org A2")
    student_email = f"sem.student.b.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_a, role=UserRole.STUDENT)
    ensure_user(email=f"sem.instr.b.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.INSTRUCTOR)
    bogus_course_id = f"course_does_not_exist_{uuid.uuid4().hex}"

    token = await login(client, student_email)
    response = await client.post(
        "/api/v1/student/semesters",
        headers=auth_headers(token),
        json={
            "name": "Fall Test",
            "start_date": "2026-08-31",
            "end_date": "2026-12-20",
            "course_ids": [bogus_course_id],
            "weekly_slots": [],
            "exceptions": [],
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_semester_with_own_course(client):
    org_a = ensure_org("sem-org-a3", "Semester Org A3")
    student_email = f"sem.student.c.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_a, role=UserRole.STUDENT)
    ensure_user(email=f"sem.instr.c.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.INSTRUCTOR)
    code = _unique_code("OWN")
    course_id = ensure_course(code=code, org_id=org_a, name="Own course")

    token = await login(client, student_email)
    create_resp = await client.post(
        "/api/v1/student/semesters",
        headers=auth_headers(token),
        json={
            "name": "Fall Test",
            "start_date": "2026-08-31",
            "end_date": "2026-09-13",
            "course_ids": [course_id],
            "weekly_slots": [{"weekday": 0, "slot_id": 1, "course_id": course_id}],
            "exceptions": [],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    body = create_resp.json()
    assert body["course_ids"] == [course_id]
    assert len(body["events"]) > 0

    semester_id = body["id"]
    get_resp = await client.get(f"/api/v1/student/semesters/{semester_id}", headers=auth_headers(token))
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == semester_id

    status_resp = await client.get("/api/v1/student/semesters/status", headers=auth_headers(token))
    assert status_resp.status_code == 200
    assert status_resp.json()["required"] is False
    assert status_resp.json()["activeSemesterId"] == semester_id


@pytest.mark.asyncio
async def test_another_student_cannot_read_semester(client):
    org_a = ensure_org("sem-org-a4", "Semester Org A4")
    student_email = f"sem.student.d.{uuid.uuid4().hex}@example.test"
    other_email = f"sem.student.e.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_a, role=UserRole.STUDENT)
    ensure_user(email=other_email, org_id=org_a, role=UserRole.STUDENT)
    ensure_user(email=f"sem.instr.d.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.INSTRUCTOR)
    code = _unique_code("SHR")
    course_id = ensure_course(code=code, org_id=org_a)

    token = await login(client, student_email)
    create_resp = await client.post(
        "/api/v1/student/semesters",
        headers=auth_headers(token),
        json={
            "name": "Fall Test",
            "start_date": "2026-08-31",
            "end_date": "2026-09-06",
            "course_ids": [course_id],
            "weekly_slots": [],
            "exceptions": [],
        },
    )
    assert create_resp.status_code == 201
    semester_id = create_resp.json()["id"]

    other_token = await login(client, other_email)
    resp = await client.get(f"/api/v1/student/semesters/{semester_id}", headers=auth_headers(other_token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_semester_setup_completes_with_zero_instructors_in_the_org(client):
    """The headline behaviour Task 8 exists for: an org with *no* instructor
    account at all used to make `first_instructor_id()` raise `LookupError`,
    blocking the student out of semester setup entirely (see the removed
    method in src/repositories/semester_repository.py). Setup must now
    complete, the created section must be unassigned (not guessing an
    instructor from nowhere), and it must surface in the admin Work Queue
    so a human can pick a real instructor -- closing the loop end to end.

    Goes through the real `/api/v1/student/semesters` route (SemesterService
    -> SemesterRepository.get_or_create_section), unlike
    test_unassigned_section_queue.py's direct-row-insert test, so this is
    the one place that actually exercises the wizard code path this task
    changed."""
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(f"sem-noinstr-{suffix}", "No Instructor Org")
    student_email = f"sem.student.noinstr.{suffix}@example.test"
    admin_email = f"sem.admin.noinstr.{suffix}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    ensure_user(email=admin_email, org_id=org_id, role=UserRole.ADMIN)
    # Deliberately no ensure_user(..., role=UserRole.INSTRUCTOR) here -- this
    # org has zero instructor accounts, which is exactly the case that used
    # to raise LookupError out of first_instructor_id() before this task.
    code = _unique_code("NOI")
    course_id = ensure_course(code=code, org_id=org_id, name="No Instructor Course")

    token = await login(client, student_email)
    create_resp = await client.post(
        "/api/v1/student/semesters",
        headers=auth_headers(token),
        json={
            "name": "Fall Test",
            "start_date": "2026-08-31",
            "end_date": "2026-09-13",
            "course_ids": [course_id],
            "weekly_slots": [{"weekday": 0, "slot_id": 1, "course_id": course_id}],
            "exceptions": [],
        },
    )
    assert create_resp.status_code == 201, create_resp.text
    body = create_resp.json()
    assert body["course_ids"] == [course_id]
    assert len(body["events"]) > 0

    db = SessionLocal()
    try:
        sections = db.query(models.CourseSection).filter_by(course_id=course_id).all()
    finally:
        db.close()
    assert sections, "SemesterService should have created a section for the course"
    assert all(section.instructor_id is None for section in sections), (
        "a section created in an org with zero instructors must stay "
        "unassigned, not silently pick one from nowhere"
    )

    admin_token = await login(client, admin_email)
    queue_resp = await client.get("/api/v1/admin/work-queue", headers=auth_headers(admin_token))
    assert queue_resp.status_code == 200
    section_ids = {section.id for section in sections}
    items = queue_resp.json()["items"]
    assert any(
        item["trigger_type"] == "UNASSIGNED_SECTION" and item["trigger_id"] in section_ids
        for item in items
    ), items
