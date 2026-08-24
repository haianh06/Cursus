"""Seed 4 named accounts (2 students, 1 instructor, 1 admin) with a small
mock dataset so each role has something to see on login — a shared course
section, enrollments, an assignment, a weekly plan per student, and one
risk signal for the instructor dashboard.

Idempotent: skips entirely once the first account (by email) already exists.
Called unconditionally from scripts/docker_entrypoint.py (like
_seed_curriculum/_ensure_academic_term) so it survives `docker compose down -v`
+ rebuild without depending on SEED_ON_START.

Usage: python scripts/seed_extra_users.py
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logger = logging.getLogger("seed-extra-users")

PASSWORD = "test123@"

ACCOUNTS = [
    {
        "id": "student_haianh",
        "email": "studenthaianh@example.com",
        "full_name": "Nguyễn Hải Anh",
        "role_key": "STUDENT",
    },
    {
        "id": "student_haidang",
        "email": "studenthaidang@example.com",
        "full_name": "Trịnh Hải Đăng",
        "role_key": "STUDENT",
    },
    {
        "id": "admin_chung",
        "email": "admin@example.com",
        "full_name": "Nguyễn Đức Chung",
        "role_key": "ADMIN",
    },
    {
        "id": "inst_binh",
        "email": "instructor@example.com",
        "full_name": "Nguyễn Thanh Bình",
        "role_key": "INSTRUCTOR",
    },
]


def _ensure_recent_academic_term(db) -> None:
    """Move the active term to start 3 weeks ago so "this week" has real classes.

    Only runs once, from the same first-run gate as the rest of this module —
    _ensure_academic_term() in docker_entrypoint.py always creates it with a
    fixed future date, which would leave every generated CalendarEvent in the
    future too (Timetable "this week" empty) unless nudged back like this.
    """
    from src.db import models
    from src.services.timetable_service import monday_of

    term = db.query(models.AcademicTerm).filter_by(is_active=True).first()
    if term is None:
        return
    today = datetime.now(UTC).date()
    term.start_date = monday_of(today) - timedelta(weeks=3)


def _setup_semester_for_student(db, student_id: str, course_codes: list[str]) -> None:
    """Give a student a real active semester (courses + weekly slots) so
    Timetable shows locked class blocks instead of being empty — this is
    the same backend flow SemesterSetupWizard drives from the frontend.
    """
    from src.db import models
    from src.repositories.semester_repository import SemesterRepository
    from src.services.semester_service import SemesterService

    courses = (
        db.query(models.Course)
        .filter(models.Course.code.in_(course_codes))
        .order_by(models.Course.code)
        .all()
    )
    course_ids = [course.id for course in courses]
    if len(course_ids) < len(course_codes):
        logger.warning("semester_setup_skipped_missing_courses codes=%s", course_codes)
        return

    weekly_slots = []
    for index, course_id in enumerate(course_ids):
        weekday_a = (index * 2) % 5
        weekday_b = (index * 2 + 1) % 5
        weekly_slots.append({"weekday": weekday_a, "slot_id": 1, "course_id": course_id})
        weekly_slots.append({"weekday": weekday_b, "slot_id": 2, "course_id": course_id})

    today = datetime.now(UTC).date()
    service = SemesterService(SemesterRepository(db))
    try:
        service.create(
            student_id=student_id,
            name="Fall 2026",
            start_date=today,
            end_date=today + timedelta(days=84),
            course_ids=course_ids,
            weekly_slots=weekly_slots,
            exceptions=[],
            require_term=False,
        )
    except ValueError:
        logger.exception("semester_setup_failed student_id=%s", student_id)


def ensure_extra_users(db) -> bool:
    """Create the 4 accounts + mock dataset. Returns True if it seeded anything."""
    from src.db import models
    from src.security.passwords import hash_password

    if db.query(models.User).filter_by(email=ACCOUNTS[0]["email"]).first() is not None:
        logger.info("extra_users_already_seeded")
        return False

    now = datetime.now(UTC).replace(tzinfo=None)
    password_hash = hash_password(PASSWORD)

    for account in ACCOUNTS:
        db.add(
            models.User(
                id=account["id"],
                email=account["email"],
                password_hash=password_hash,
                full_name=account["full_name"],
                role=getattr(models.UserRole, account["role_key"]).value,
                is_email_verified=True,
                is_active=True,
                created_at=now,
            )
        )
    db.flush()

    course = db.query(models.Course).filter_by(code="SSA101").first()
    if course is None:
        course = models.Course(
            id="SSA101",
            code="SSA101",
            name="Study Skills & Academic Success",
            description="Shared demo course for planner/QA testing.",
        )
        db.add(course)
        db.flush()

    section = models.CourseSection(
        id="sec_ssa101_custom",
        course_id=course.id,
        instructor_id="inst_binh",
        term="Fall2026",
        section_code="SE-CUSTOM01",
    )
    db.add(section)
    db.flush()

    db.add_all(
        [
            models.Enrollment(
                id="enr_student_haianh_custom",
                student_id="student_haianh",
                section_id=section.id,
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=now - timedelta(days=5),
            ),
            models.Enrollment(
                id="enr_student_haidang_custom",
                student_id="student_haidang",
                section_id=section.id,
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=now - timedelta(days=5),
            ),
        ]
    )
    db.flush()

    assignment = models.Assignment(
        id="asg_ssa101_custom",
        section_id=section.id,
        title="SSA101 Custom Weekly Lab",
        description="Demo assignment for the custom-seeded section.",
        due_date=now + timedelta(days=7),
        max_points=100,
        assessment_type="ASSIGNMENT",
    )
    db.add(assignment)
    db.flush()

    def _add_plan_tree(*, student_id: str) -> None:
        plan_id = f"plan_{student_id}_custom_w6"
        db.add(
            models.WeeklyPlan(
                id=plan_id,
                student_id=student_id,
                week_number=6,
                goals={"statement": "Custom demo weekly plan"},
                study_hours_allocated=10.0,
            )
        )
        db.flush()
        daily_id = f"dp_{plan_id}"
        db.add(
            models.DailyPlan(
                id=daily_id,
                weekly_plan_id=plan_id,
                date=now,
                status="TODO",
            )
        )
        db.flush()
        block_id = f"sb_{plan_id}"
        db.add(
            models.ScheduleBlock(
                id=block_id,
                daily_plan_id=daily_id,
                start_time=now.replace(hour=19, minute=0),
                end_time=now.replace(hour=21, minute=0),
                activity_description="Evening study",
            )
        )
        db.flush()
        db.add(
            models.StudyTask(
                id=f"task_{student_id}_custom_1",
                schedule_block_id=block_id,
                assignment_id=assignment.id,
                title="Demo study task",
                planned_minutes=60,
                actual_minutes=None,
                priority="MEDIUM",
                status="TODO",
                difficulty="MEDIUM",
            )
        )
        db.flush()

    _add_plan_tree(student_id="student_haianh")
    _add_plan_tree(student_id="student_haidang")

    db.add(
        models.RiskSignal(
            id="risk_student_haidang_custom",
            student_id="student_haidang",
            section_id=section.id,
            assignment_id=assignment.id,
            risk_type="LATE_SUBMISSION",
            risk_level="MEDIUM",
            triggered_rules={"rule": "demo"},
            evidence={"note": "demo risk for instructor@example.com"},
            recommended_action="Reach out to student",
            generated_at=now - timedelta(days=2),
            resolved_at=None,
            resolution_type=None,
            policy_version="v1",
        )
    )

    db.commit()

    # Separate course codes from SSA101 (used above for the inst_binh section)
    # so SemesterService doesn't create a second, duplicate SSA101 section.
    _ensure_recent_academic_term(db)
    db.commit()
    _setup_semester_for_student(db, "student_haianh", ["PRF192", "CSI106", "CEA201"])
    _setup_semester_for_student(db, "student_haidang", ["PRF192", "CSI106", "CEA201"])

    logger.info("extra_users_seeded count=%s", len(ACCOUNTS))
    return True


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from src.db.connection import SessionLocal

    db = SessionLocal()
    try:
        seeded = ensure_extra_users(db)
    finally:
        db.close()
    print("seeded" if seeded else "already_seeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
