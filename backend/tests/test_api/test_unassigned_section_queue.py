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


@pytest.mark.asyncio
async def test_a_section_without_an_instructor_shows_up_in_the_work_queue(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"unassigned-{suffix}", name="Unassigned Org")
    admin_email = f"admin.un.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    course_id = ensure_course(code=f"ZZUN{suffix[:3].upper()}", org_id=org_id)

    db = SessionLocal()
    try:
        db.add(
            models.CourseSection(
                id=f"sec_un_{suffix}",
                course_id=course_id,
                instructor_id=None,
                term="Fall2026",
                section_code="SE-UN",
            )
        )
        db.commit()
    finally:
        db.close()

    token = await login(client, admin_email)
    response = await client.get("/api/v1/admin/work-queue", headers=auth_headers(token))

    assert response.status_code == 200
    items = response.json()["items"]
    # NOTE: the task-8 brief's own test snippet asserted `item["subject_id"]`,
    # but the four pre-existing work-queue sources in build_work_queue all key
    # their own row id as `trigger_id` (see RISK_SIGNAL/GUARDRAIL_EVENT/
    # DATA_REQUEST/INGEST_JOB below in admin_overview_service.py) and the
    # frontend uses `item.trigger_id` as the React list key
    # (AdminOverview.jsx: `key={`${item.trigger_type}:${item.trigger_id}`}`).
    # A `subject_id`-only item would collide under an undefined React key for
    # every unassigned section, so this asserts the real, load-bearing key.
    assert any(
        item["trigger_type"] == "UNASSIGNED_SECTION" and item["trigger_id"] == f"sec_un_{suffix}"
        for item in items
    ), items


def test_semester_repository_no_longer_guesses_an_instructor():
    from src.repositories import semester_repository

    assert not hasattr(semester_repository.SemesterRepository, "first_instructor_id"), (
        "first_instructor_id gán lớp cho một giảng viên bất kỳ — đã được thay "
        "bằng lớp chưa gán + việc trong Work Queue"
    )
