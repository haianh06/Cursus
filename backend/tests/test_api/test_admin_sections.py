import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


@pytest.fixture
def org_setup():
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"sec-org-{suffix}", name="Section Org")
    admin_email = f"admin.sec.{suffix}@test.local"
    inst_email = f"inst.sec.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    instructor_id = ensure_user(
        email=inst_email, org_id=org_id, role=models.UserRole.INSTRUCTOR
    )
    course_id = ensure_course(code=f"ZZSEC{suffix[:3].upper()}", org_id=org_id)
    return {
        "org_id": org_id,
        "admin_email": admin_email,
        "instructor_id": instructor_id,
        "course_id": course_id,
    }


@pytest.mark.asyncio
async def test_admin_lists_available_courses_for_the_section_form(client, org_setup):
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)

    response = await client.get("/api/v1/admin/sections/courses", headers=headers)

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert any(item["id"] == org_setup["course_id"] for item in items)


@pytest.mark.asyncio
async def test_admin_creates_a_section_and_assigns_an_instructor(client, org_setup):
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)

    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1801",
            "term": "Fall2026",
            "instructorId": org_setup["instructor_id"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["sectionCode"] == "SE1801"
    assert body["instructorId"] == org_setup["instructor_id"]
    assert body["enrolledCount"] == 0

    listed = await client.get("/api/v1/admin/sections", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json()["items"])


@pytest.mark.asyncio
async def test_admin_can_reassign_the_instructor_of_a_section(client, org_setup):
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)

    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1802",
            "term": "Fall2026",
            "instructorId": None,
        },
    )
    section_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/admin/sections/{section_id}",
        headers=headers,
        json={"instructorId": org_setup["instructor_id"]},
    )
    assert updated.status_code == 200
    assert updated.json()["instructorId"] == org_setup["instructor_id"]


@pytest.mark.asyncio
async def test_cannot_assign_an_instructor_from_another_organization(client, org_setup):
    other_org = ensure_org(slug=f"other-{uuid.uuid4().hex[:6]}", name="Other Org")
    outsider = ensure_user(
        email=f"outsider.{uuid.uuid4().hex[:6]}@test.local",
        org_id=other_org,
        role=models.UserRole.INSTRUCTOR,
    )
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)

    response = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1803",
            "term": "Fall2026",
            "instructorId": outsider,
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_a_section_with_enrolled_students_is_refused(client, org_setup):
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)
    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1804",
            "term": "Fall2026",
            "instructorId": org_setup["instructor_id"],
        },
    )
    section_id = created.json()["id"]

    db = SessionLocal()
    try:
        student_id = ensure_user(
            email=f"stu.{uuid.uuid4().hex[:6]}@test.local",
            org_id=org_setup["org_id"],
            role=models.UserRole.STUDENT,
        )
        db.add(
            models.Enrollment(
                id=f"enr_{uuid.uuid4().hex[:10]}",
                student_id=student_id,
                section_id=section_id,
                status=models.EnrollmentStatus.ENROLLED.value,
            )
        )
        db.commit()
    finally:
        db.close()

    response = await client.delete(
        f"/api/v1/admin/sections/{section_id}", headers=headers
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_admin_deletes_an_empty_section(client, org_setup):
    """The happy delete path -- the browser check for Task 9 caught this
    returning 500 (and therefore no CORS header, so the SPA saw a bare
    network error) while the 409 refusal above was fine."""
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)
    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1805",
            "term": "Fall2026",
            "instructorId": org_setup["instructor_id"],
        },
    )
    section_id = created.json()["id"]

    response = await client.delete(
        f"/api/v1/admin/sections/{section_id}", headers=headers
    )

    assert response.status_code == 204, response.text
    listed = await client.get("/api/v1/admin/sections", headers=headers)
    assert all(row["id"] != section_id for row in listed.json()["items"])


@pytest.mark.asyncio
async def test_admin_deletes_a_section_whose_only_student_was_removed(client, org_setup):
    """`remove_from_roster` soft-deletes (status=DROPPED) so grade/enrolled_at
    survive, which leaves an `enrollments` row pointing at the section. The
    409 guard counts only ENROLLED, so this reaches `db.delete(section)` --
    and `CourseSection.enrollments` declares no delete cascade, so the ORM
    tried to NULL out the non-nullable `enrollments.section_id` and the
    delete blew up with a 500 instead of a 204.
    """
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)
    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1806",
            "term": "Fall2026",
            "instructorId": org_setup["instructor_id"],
        },
    )
    section_id = created.json()["id"]
    student_id = ensure_user(
        email=f"stu.{uuid.uuid4().hex[:6]}@test.local",
        org_id=org_setup["org_id"],
        role=models.UserRole.STUDENT,
    )
    added = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": student_id},
    )
    assert added.status_code == 201, added.text
    removed = await client.delete(
        f"/api/v1/admin/sections/{section_id}/roster/{student_id}", headers=headers
    )
    assert removed.status_code == 204, removed.text

    response = await client.delete(
        f"/api/v1/admin/sections/{section_id}", headers=headers
    )

    assert response.status_code == 204, response.text
    listed = await client.get("/api/v1/admin/sections", headers=headers)
    assert all(row["id"] != section_id for row in listed.json()["items"])


@pytest.mark.asyncio
async def test_admin_deletes_a_section_that_carries_course_content(client, org_setup):
    """Same missing-cascade shape as the enrollment case, one table over:
    `CourseSection.modules` (and `Module.lessons` under it) declared no delete
    cascade while `modules.section_id` / `lessons.module_id` are NOT NULL with
    `ondelete="CASCADE"`, so the ORM tried to NULL them out and the delete
    500'd. Reachable for any ingested section -- admin-created ones have no
    modules, which is why Task 9's browser pass never hit it.

    Course-level material is untouched: `documents.course_id` points at
    `courses`, not at the section, so only the section's own module/lesson
    structure goes with it.
    """
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)
    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1807",
            "term": "Fall2026",
            "instructorId": org_setup["instructor_id"],
        },
    )
    section_id = created.json()["id"]

    db = SessionLocal()
    try:
        module_id = f"mod_{uuid.uuid4().hex[:10]}"
        db.add(
            models.Module(
                id=module_id,
                section_id=section_id,
                title="Week 1",
                description=None,
                week_number=1,
                sequence_order=1,
            )
        )
        db.add(
            models.Lesson(
                id=f"les_{uuid.uuid4().hex[:10]}",
                module_id=module_id,
                title="Intro",
                content="body",
                sequence_order=1,
            )
        )
        db.commit()
    finally:
        db.close()

    response = await client.delete(
        f"/api/v1/admin/sections/{section_id}", headers=headers
    )

    assert response.status_code == 204, response.text
    db = SessionLocal()
    try:
        assert db.get(models.CourseSection, section_id) is None
        assert db.query(models.Module).filter_by(section_id=section_id).count() == 0
        assert db.query(models.Lesson).filter_by(module_id=module_id).count() == 0
    finally:
        db.close()
