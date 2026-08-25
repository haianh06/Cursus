"""Seed a real weekly plan + self-study session history for one student
account, so the Student Home dashboard has actual data to inspect end to end
(week progress, next best action, daily study-hours chart) instead of the
empty "no plan yet" state. Every number seeded here is a real DB row read
back through the real endpoints — not a frontend-only fake.

Usage:
  python scripts/seed_dashboard_demo.py --email someone@example.com
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import get_settings  # noqa: E402
from src.db import models  # noqa: E402
from src.db.connection import SessionLocal  # noqa: E402
from src.services.mock.student_mock_data_service import StudentMockDataService  # noqa: E402
from src.services.academic.timetable_service import TimetableService, monday_of  # noqa: E402
from src.services.weekly_plan_service import WeeklyPlanService  # noqa: E402


def _student_course_code(db, student_id: str) -> str | None:
    enrollment = (
        db.query(models.Enrollment)
        .filter_by(student_id=student_id)
        .order_by(models.Enrollment.enrolled_at.desc())
        .first()
    )
    if enrollment is None:
        return None
    section = db.query(models.CourseSection).filter_by(id=enrollment.section_id).first()
    if section is None:
        return None
    course = db.query(models.Course).filter_by(id=section.course_id).first()
    return course.code if course else None


def _seed_weekly_plan(db, student) -> dict | None:
    code = _student_course_code(db, student.id)
    if not code:
        StudentMockDataService(db).ensure_for_student(student.id)
        code = _student_course_code(db, student.id)
    if not code:
        print("No enrolled course found — cannot seed a weekly plan")
        return None

    service = WeeklyPlanService(db)
    plan = service.generate(
        student_id=student.id,
        goal_text="On tap va hoan thanh bai tap tuan nay",
        subject_code=code,
        available_hours=10,
    )
    tasks = plan["tasks"]
    for index, task in enumerate(tasks[:2]):
        delta = 10 if index == 0 else -10
        actual = max(15, int(task["estimatedMinutes"]) + delta)
        service.update_task(
            student_id=student.id,
            task_id=task["id"],
            status="COMPLETED",
            actual_minutes=actual,
        )
    if len(tasks) > 2:
        service.update_task(
            student_id=student.id,
            task_id=tasks[2]["id"],
            status="DEFERRED",
            reason_code="low_energy",
        )
    return plan


def _seed_self_study_sessions(db, student) -> int:
    timetable = TimetableService(db)
    today = date.today()
    monday = monday_of(today)
    created = 0
    for offset in range(7):
        day = monday + timedelta(days=offset)
        if day >= today:
            break
        start = datetime.combine(day, time(19, 0))
        end = start + timedelta(minutes=90)
        try:
            block_payload = timetable.create_self_study_block(
                student_id=student.id,
                title="Tu hoc buoi toi",
                start=start,
                end=end,
            )
        except ValueError:
            continue  # overlaps a class this day — skip, not fatal
        actual_minutes = 60 + (offset * 5) % 40
        session = models.SelfStudySession(
            id=f"sss_{uuid.uuid4().hex[:10]}",
            student_id=student.id,
            schedule_block_id=block_payload["id"],
            title="Tu hoc buoi toi",
            planned_minutes=90,
            started_at=start,
            scheduled_end_at=end,
            ended_at=start + timedelta(minutes=actual_minutes),
            actual_minutes=actual_minutes,
            pomodoros_completed=max(1, actual_minutes // 25),
            status="COMPLETED",
        )
        db.add(session)
        created += 1
    db.commit()
    return created


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed real dashboard data for a student account")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()

    get_settings.cache_clear()
    db = SessionLocal()
    try:
        student = db.query(models.User).filter_by(email=args.email.lower().strip()).first()
        if not student:
            print(f"User not found: {args.email}")
            return 1
        role_value = student.role if isinstance(student.role, str) else student.role.value
        if role_value != "STUDENT":
            print("Not a STUDENT account")
            return 1

        plan = _seed_weekly_plan(db, student)
        if plan:
            print(f"Weekly plan: {plan['id']} ({len(plan['tasks'])} tasks)")

        sessions = _seed_self_study_sessions(db, student)
        print(f"Self-study sessions created: {sessions}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
