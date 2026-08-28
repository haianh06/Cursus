from datetime import datetime, timedelta

import pytest


async def _login_student(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_timetable_crud_self_study_block(client):
    headers = await _login_student(client)

    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date().isoformat()

    start = monday.replace(hour=18, minute=0)
    end = monday.replace(hour=19, minute=30)

    create_response = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={
            "title": "Review PRF192 notes",
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["kind"] == "SELF_STUDY"
    assert created["locked"] is False
    block_id = created["id"]

    get_response = await client.get(
        f"/api/v1/plans/timetable?week_start={week_start}",
        headers=headers,
    )
    assert get_response.status_code == 200
    blocks = get_response.json()["blocks"]
    assert any(block["id"] == block_id for block in blocks)

    moved_start = start.replace(hour=20)
    moved_end = end.replace(hour=21, minute=30)
    patch_response = await client.patch(
        f"/api/v1/plans/timetable/blocks/{block_id}",
        headers=headers,
        json={
            "title": "Review PRF192 + exercises",
            "start": moved_start.isoformat(),
            "end": moved_end.isoformat(),
        },
    )
    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["title"] == "Review PRF192 + exercises"

    delete_response = await client.delete(
        f"/api/v1/plans/timetable/blocks/{block_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    after_delete = await client.get(
        f"/api/v1/plans/timetable?week_start={week_start}",
        headers=headers,
    )
    assert after_delete.status_code == 200
    assert all(block["id"] != block_id for block in after_delete.json()["blocks"])


@pytest.mark.asyncio
async def test_timetable_bootstrap_creates_class_and_self_study(client):
    headers = await _login_student(client)
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date().isoformat()

    response = await client.post(
        f"/api/v1/plans/timetable/bootstrap?week_start={week_start}",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    kinds = {block["kind"] for block in payload["blocks"]}
    assert "CLASS" in kinds
    assert "SELF_STUDY" in kinds


@pytest.mark.asyncio
async def test_timetable_rejects_self_study_overlap_with_class(client):
    headers = await _login_student(client)
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date().isoformat()

    bootstrap = await client.post(
        f"/api/v1/plans/timetable/bootstrap?week_start={week_start}",
        headers=headers,
    )
    assert bootstrap.status_code == 200
    class_block = next(
        block for block in bootstrap.json()["blocks"] if block["kind"] == "CLASS"
    )
    class_start = datetime.fromisoformat(class_block["start"])
    overlap_end = class_start + timedelta(minutes=45)

    response = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={
            "title": "Illegal overlap",
            "start": class_start.isoformat(),
            "end": overlap_end.isoformat(),
        },
    )
    assert response.status_code == 400
    assert "overlap" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_recurring_self_study_block_create_and_delete_all(client):
    """a46db63 §6.3.8: repeatWeeklyUntil creates one occurrence per week
    sharing a recurrence_series_id; scope=all deletes every occurrence."""
    headers = await _login_student(client)
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date().isoformat()
    next_week_start = (monday + timedelta(days=7)).date().isoformat()

    start = monday.replace(hour=6, minute=0)
    end = monday.replace(hour=7, minute=0)
    until = (monday + timedelta(days=8)).date().isoformat()

    create_response = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={
            "title": "Recurring morning review",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "repeatWeeklyUntil": until,
        },
    )
    assert create_response.status_code == 201, create_response.text
    first = create_response.json()
    series_id = first["recurrenceSeriesId"]
    assert series_id

    week1 = await client.get(f"/api/v1/plans/timetable?week_start={week_start}", headers=headers)
    week2 = await client.get(
        f"/api/v1/plans/timetable?week_start={next_week_start}", headers=headers
    )
    week1_series = [b for b in week1.json()["blocks"] if b.get("recurrenceSeriesId") == series_id]
    week2_series = [b for b in week2.json()["blocks"] if b.get("recurrenceSeriesId") == series_id]
    assert len(week1_series) == 1
    assert len(week2_series) == 1

    delete_response = await client.delete(
        f"/api/v1/plans/timetable/blocks/{first['id']}?scope=all",
        headers=headers,
    )
    assert delete_response.status_code == 204

    week1_after = await client.get(
        f"/api/v1/plans/timetable?week_start={week_start}", headers=headers
    )
    week2_after = await client.get(
        f"/api/v1/plans/timetable?week_start={next_week_start}", headers=headers
    )
    assert all(b.get("recurrenceSeriesId") != series_id for b in week1_after.json()["blocks"])
    assert all(b.get("recurrenceSeriesId") != series_id for b in week2_after.json()["blocks"])


@pytest.mark.asyncio
async def test_started_self_study_plan_can_be_changed_or_removed_without_losing_session(client):
    """Plans are flexible; Pomodoro evidence survives their removal."""
    headers = await _login_student(client)

    start = datetime.now() + timedelta(minutes=1)
    end = start + timedelta(minutes=40)
    create_response = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={"title": "Tự học", "start": start.isoformat(), "end": end.isoformat()},
    )
    assert create_response.status_code == 201, create_response.text
    block_id = create_response.json()["id"]

    start_session = await client.post(
        "/api/v1/student/self-study/sessions",
        headers=headers,
        json={"blockId": block_id},
    )
    assert start_session.status_code == 200, start_session.text
    assert start_session.json()["status"] == "IN_PROGRESS"

    update_response = await client.patch(
        f"/api/v1/plans/timetable/blocks/{block_id}",
        headers=headers,
        json={"title": "Edited after starting"},
    )
    assert update_response.status_code == 200, update_response.text

    delete_response = await client.delete(
        f"/api/v1/plans/timetable/blocks/{block_id}", headers=headers,
    )
    assert delete_response.status_code == 204, delete_response.text

    monday = start.date() - timedelta(days=start.weekday())
    timetable = await client.get(
        f"/api/v1/plans/timetable?week_start={monday.isoformat()}", headers=headers,
    )
    assert all(block["id"] != block_id for block in timetable.json()["blocks"])

    session_response = await client.get(
        f"/api/v1/student/self-study/sessions/{start_session.json()['id']}", headers=headers,
    )
    assert session_response.status_code == 200, session_response.text


@pytest.mark.asyncio
async def test_timetable_rejects_overlap_between_self_study_plans(client):
    headers = await _login_student(client)
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)

    first = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={"title": "Focus A", "start": monday.replace(hour=18).isoformat(), "end": monday.replace(hour=19).isoformat()},
    )
    assert first.status_code == 201, first.text

    overlap = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={"title": "Focus B", "start": monday.replace(hour=18, minute=30).isoformat(), "end": monday.replace(hour=19, minute=30).isoformat()},
    )
    assert overlap.status_code == 400, overlap.text
    assert "overlap" in overlap.json()["detail"].lower()

    second = await client.post(
        "/api/v1/plans/timetable/blocks",
        headers=headers,
        json={"title": "Focus B", "start": monday.replace(hour=19).isoformat(), "end": monday.replace(hour=20).isoformat()},
    )
    assert second.status_code == 201, second.text
    move_into_conflict = await client.patch(
        f"/api/v1/plans/timetable/blocks/{second.json()['id']}",
        headers=headers,
        json={"start": monday.replace(hour=18, minute=30).isoformat(), "end": monday.replace(hour=19, minute=30).isoformat()},
    )
    assert move_into_conflict.status_code == 400, move_into_conflict.text


@pytest.mark.asyncio
async def test_timetable_shows_exam_block_and_semester_meta(client):
    """a46db63 exam-block/semester-meta parity — exam sessions scheduled
    against the student's active semester's courses render as locked EXAM
    blocks, and get_week() reports which semester week is being viewed."""
    import uuid

    from src.db import models
    from src.db.connection import SessionLocal

    headers = await _login_student(client)
    monday = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    while monday.weekday() != 0:
        monday += timedelta(days=1)
    week_start = monday.date()

    db = SessionLocal()
    try:
        student = db.query(models.User).filter_by(email="student.demo@example.test").first()
        course = db.query(models.Course).first()
        assert student is not None and course is not None

        org_id = student.organization_id
        if org_id is None:
            org_id = f"org_{uuid.uuid4().hex[:10]}"
            db.add(models.Organization(id=org_id, name="Test Org", slug=f"test-org-{org_id[-6:]}"))
            db.flush()
            student.organization_id = org_id

        db.query(models.SemesterSetup).filter_by(student_id=student.id).update(
            {"is_active": False}
        )
        semester = models.SemesterSetup(
            id=f"sem_{uuid.uuid4().hex[:10]}",
            student_id=student.id,
            name="Test Term",
            start_date=week_start - timedelta(weeks=1),
            end_date=week_start + timedelta(weeks=10),
            is_active=True,
        )
        db.add(semester)
        db.flush()
        db.add(
            models.SemesterCourse(
                id=f"semc_{uuid.uuid4().hex[:10]}",
                semester_id=semester.id,
                course_id=course.id,
            )
        )
        term = models.AcademicTerm(
            id=f"term_{uuid.uuid4().hex[:10]}",
            organization_id=org_id,
            name="Test Academic Term",
            start_date=week_start - timedelta(weeks=1),
            is_active=True,
        )
        db.add(term)
        db.flush()
        exam = models.CourseExam(
            id=f"exam_{uuid.uuid4().hex[:10]}",
            term_id=term.id,
            course_id=course.id,
            kind="FINAL",
        )
        db.add(exam)
        db.flush()
        db.add(
            models.CourseExamSession(
                id=f"exs_{uuid.uuid4().hex[:10]}",
                exam_id=exam.id,
                exam_date=week_start + timedelta(days=2),
                slot_id=1,
                label="Ca 1",
            )
        )
        db.commit()
    finally:
        db.close()

    resp = await client.get(
        f"/api/v1/plans/timetable?week_start={week_start.isoformat()}", headers=headers
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    exam_blocks = [b for b in payload["blocks"] if b["kind"] == "EXAM"]
    assert len(exam_blocks) == 1
    assert exam_blocks[0]["locked"] is True
    assert payload["semesterMeta"] is not None
    assert payload["semesterMeta"]["weekNumber"] == 2
