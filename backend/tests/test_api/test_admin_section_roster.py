import uuid

import pytest

from src.db import models
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


@pytest.fixture
def roster_setup():
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"ros-org-{suffix}", name="Roster Org")
    admin_email = f"admin.ros.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    student_id = ensure_user(
        email=f"stu.ros.{suffix}@test.local", org_id=org_id, role=models.UserRole.STUDENT
    )
    course_id = ensure_course(code=f"ZZROS{suffix[:3].upper()}", org_id=org_id)
    return {
        "org_id": org_id,
        "admin_email": admin_email,
        "student_id": student_id,
        "course_id": course_id,
    }


@pytest.mark.asyncio
async def test_admin_adds_and_removes_a_student_from_a_section(client, roster_setup):
    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)
    section_id = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1900",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()["id"]

    added = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": roster_setup["student_id"]},
    )
    assert added.status_code == 201, added.text

    listed = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert listed.status_code == 200
    assert [item["studentId"] for item in listed.json()["items"]] == [
        roster_setup["student_id"]
    ]

    removed = await client.delete(
        f"/api/v1/admin/sections/{section_id}/roster/{roster_setup['student_id']}",
        headers=headers,
    )
    assert removed.status_code == 204

    after = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert after.json()["items"] == []


@pytest.mark.asyncio
async def test_adding_the_same_student_twice_is_idempotent(client, roster_setup):
    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)
    section_id = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1901",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()["id"]

    body = {"studentId": roster_setup["student_id"]}
    first = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers, json=body
    )
    second = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers, json=body
    )

    assert first.status_code == 201
    assert second.status_code == 201
    listed = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert len(listed.json()["items"]) == 1


@pytest.mark.asyncio
async def test_cannot_enrol_a_student_from_another_organization(client, roster_setup):
    outsider = ensure_user(
        email=f"out.{uuid.uuid4().hex[:6]}@test.local",
        org_id=ensure_org(slug=f"out-{uuid.uuid4().hex[:6]}", name="Out"),
        role=models.UserRole.STUDENT,
    )
    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)
    section_id = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1902",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()["id"]

    response = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": outsider},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_removed_student_does_not_appear_in_roster(client, roster_setup):
    """Test Finding 1 & 2: remove_from_roster soft-deletes (DROPPED status),
    list_roster filters out DROPPED students."""
    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)
    section_id = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1903",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()["id"]

    # Add student
    await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": roster_setup["student_id"]},
    )

    # Verify student appears in roster
    roster = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert len(roster.json()["items"]) == 1
    assert roster.json()["items"][0]["studentId"] == roster_setup["student_id"]

    # Remove student (soft-delete to DROPPED)
    await client.delete(
        f"/api/v1/admin/sections/{section_id}/roster/{roster_setup['student_id']}",
        headers=headers,
    )

    # Verify student no longer appears in roster (filtered out because status=DROPPED)
    roster_after = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert roster_after.json()["items"] == []


@pytest.mark.asyncio
async def test_dropped_student_cannot_access_course_material(client, roster_setup):
    """Test Finding 3 regression: a DROPPED enrollment must not pass the
    course-access gate (student_enrolled_in_course). Without this filter,
    a dropped student can access material but cannot be bound to a section,
    creating unbound conversations visible to all instructors."""
    from src.db.connection import SessionLocal
    from src.repositories.chunk_repository import ChunkRepository

    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)

    # Create section and add student
    section_response = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1904",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()
    section_id = section_response["id"]
    course_code = section_response["courseCode"]

    await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": roster_setup["student_id"]},
    )

    # Verify gate allows access when ENROLLED
    db = SessionLocal()
    try:
        chunk_repo = ChunkRepository(db)
        assert chunk_repo.student_enrolled_in_course(
            student_id=roster_setup["student_id"], subject_code=course_code
        ), "Student should be able to access course when ENROLLED"
    finally:
        db.close()

    # Remove student (sets status to DROPPED)
    await client.delete(
        f"/api/v1/admin/sections/{section_id}/roster/{roster_setup['student_id']}",
        headers=headers,
    )

    # Verify gate blocks access when DROPPED
    db = SessionLocal()
    try:
        chunk_repo = ChunkRepository(db)
        assert not chunk_repo.student_enrolled_in_course(
            student_id=roster_setup["student_id"], subject_code=course_code
        ), "DROPPED student must not access course material (Finding 3 regression)"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_dropped_student_cannot_access_quiz(client, roster_setup):
    """Test that quiz access gate blocks DROPPED students. The quiz_repository
    is_enrolled() method must filter for ENROLLED status, or a dropped student
    can open quiz questions and submit answers."""
    from src.db.connection import SessionLocal
    from src.db import models as db_models

    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)

    # Create section with student enrolled
    section_response = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1905",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()
    section_id = section_response["id"]

    # Add student to section
    await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": roster_setup["student_id"]},
    )

    # Create a published quiz in this section via database
    db = SessionLocal()
    try:
        quiz = db_models.Quiz(
            id=f"quiz_{uuid.uuid4().hex[:12]}",
            section_id=section_id,
            title="Test Quiz",
            description="Test",
            is_published=True,
            time_limit_minutes=15,
            max_points=100,
        )
        db.add(quiz)
        db.commit()  # Commit so the quiz is visible to the test client
        quiz_id = quiz.id
    finally:
        db.close()

    # Verify enrolled student CAN access quiz
    response_enrolled = await client.get(
        f"/api/v1/student/quizzes/{quiz_id}",
        headers=await auth_headers_for_student(client, roster_setup["student_id"]),
    )
    assert response_enrolled.status_code == 200, (
        f"Enrolled student should access quiz, got {response_enrolled.status_code}: {response_enrolled.text}"
    )

    # Remove student (soft-delete to DROPPED)
    await client.delete(
        f"/api/v1/admin/sections/{section_id}/roster/{roster_setup['student_id']}",
        headers=headers,
    )

    # Verify dropped student CANNOT access quiz
    response_dropped_get = await client.get(
        f"/api/v1/student/quizzes/{quiz_id}",
        headers=await auth_headers_for_student(client, roster_setup["student_id"]),
    )
    assert response_dropped_get.status_code == 403, (
        f"DROPPED student should not access quiz (get), got {response_dropped_get.status_code}"
    )

    # Verify dropped student CANNOT submit quiz
    response_dropped_submit = await client.post(
        f"/api/v1/student/quizzes/{quiz_id}/submit",
        headers=await auth_headers_for_student(client, roster_setup["student_id"]),
        json={"answers": {}},
    )
    assert response_dropped_submit.status_code == 403, (
        f"DROPPED student should not submit quiz, got {response_dropped_submit.status_code}"
    )


async def auth_headers_for_student(client, student_id: str) -> dict[str, str]:
    """Get auth headers for a student. Uses password login with the student's email."""
    from src.db.connection import SessionLocal
    from src.db import models

    db = SessionLocal()
    try:
        student = db.get(models.User, student_id)
        assert student is not None
        email = student.email
    finally:
        db.close()

    # Login as student
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "TestPassword123"},
    )
    assert response.status_code == 200, response.text
    client.cookies.clear()
    return auth_headers(response.json()["token"])
