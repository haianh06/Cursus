"""Self-study Pomodoro window check must use the app's fixed local offset.

ScheduleBlock.start_time/end_time are naive datetimes written by the
frontend as local wall-clock time (Timetable.jsx's toIsoLocal() never
includes a UTC offset). A block created for "1 minute from now" therefore
lands in the DB as naive-local, not naive-UTC. If the service compared that
against `datetime.utcnow()` directly, every real request would be off by the
app's fixed +7h offset and `start()` would always say "hasn't opened yet" or
"has ended" -- this pinned the regression found during production QA.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.services.academic.self_study_service import (
    SelfStudyService,
    SelfStudyWindowError,
    _now,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_block(db, *, start: datetime, end: datetime) -> tuple[str, str]:
    student_id = f"stu_selfstudy_{uuid.uuid4().hex[:6]}"
    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    daily_id = f"dp_{uuid.uuid4().hex[:8]}"
    block_id = f"sb_{uuid.uuid4().hex[:8]}"
    db.add(
        models.User(
            id=student_id,
            email=f"{student_id}@selfstudy.test",
            password_hash="x",
            full_name="Self Study Fixture",
            role=models.UserRole.STUDENT.value,
            is_email_verified=True,
            is_active=True,
        )
    )
    db.add(
        models.WeeklyPlan(
            id=plan_id,
            student_id=student_id,
            week_number=start.isocalendar().week,
            goals={"statement": "fixture"},
            study_hours_allocated=8.0,
        )
    )
    db.add(models.DailyPlan(id=daily_id, weekly_plan_id=plan_id, date=start.date(), status="TODO"))
    db.add(
        models.ScheduleBlock(
            id=block_id,
            daily_plan_id=daily_id,
            start_time=start,
            end_time=end,
            activity_description="Tự học",
        )
    )
    db.flush()
    return student_id, block_id


def test_now_is_naive_local_not_naive_utc():
    # _now() must diverge from a bare datetime.utcnow() by the app's fixed
    # offset -- if this ever collapses back to utcnow(), the window check
    # regresses to comparing UTC "now" against local-wall-clock block times.
    delta = _now() - datetime.utcnow()
    assert timedelta(hours=6, minutes=59) < delta < timedelta(hours=7, minutes=1)


def test_start_succeeds_for_a_block_starting_one_minute_from_local_now(db):
    # Mirrors exactly what the frontend sends: a block whose start_time is
    # "local wall-clock now + 1 minute", naive, with no UTC offset.
    start = _now() + timedelta(minutes=1)
    end = start + timedelta(minutes=40)
    student_id, block_id = _make_block(db, start=start, end=end)

    result = SelfStudyService(db).start(student_id=student_id, block_id=block_id)

    assert result["status"] == "IN_PROGRESS"


def test_start_rejects_a_block_more_than_ten_minutes_in_the_future(db):
    start = _now() + timedelta(minutes=30)
    end = start + timedelta(minutes=40)
    student_id, block_id = _make_block(db, start=start, end=end)

    with pytest.raises(SelfStudyWindowError):
        SelfStudyService(db).start(student_id=student_id, block_id=block_id)
