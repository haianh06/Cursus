"""Minimal deterministic dataset for API tests (H7).

Avoids the full 600-user seed.py pipeline while covering demo logins,
enrollment ownership, instructor risks, and planner fixtures.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.db import models
from src.security.passwords import hash_password

DEMO_PASSWORD = "password123"
DEMO_PASSWORD_HASH = hash_password(DEMO_PASSWORD)


def ensure_api_demo_dataset(db: Session) -> None:
    """Idempotent: create the demo rows, and re-create the plan/risk fixtures
    if a previous test removed them (e.g. POST /demo/reset clears the demo
    student's plan state). Keeping this repairable is what makes the suite
    order-independent."""
    if db.query(models.User).filter_by(id="student_ethan").first() is not None:
        _ensure_plan_fixtures(db)
        return

    now = datetime.now(UTC).replace(tzinfo=None)

    ethan = models.User(
        id="student_ethan",
        email="student.demo@example.test",
        password_hash=DEMO_PASSWORD_HASH,
        full_name="Ethan Nguyen",
        role=models.UserRole.STUDENT.value,
        is_email_verified=True,
        is_active=True,
        created_at=now - timedelta(days=30),
    )
    other_student = models.User(
        id="student_other",
        email="student.other@example.test",
        password_hash=DEMO_PASSWORD_HASH,
        full_name="Other Student",
        role=models.UserRole.STUDENT.value,
        is_email_verified=True,
        is_active=True,
        created_at=now - timedelta(days=30),
    )
    instructor = models.User(
        id="inst_demo",
        email="instructor.demo@example.test",
        password_hash=DEMO_PASSWORD_HASH,
        full_name="Demo Instructor",
        role=models.UserRole.INSTRUCTOR.value,
        is_email_verified=True,
        is_active=True,
        created_at=now - timedelta(days=60),
    )
    other_instructor = models.User(
        id="inst_other",
        email="instructor.other@example.test",
        password_hash=DEMO_PASSWORD_HASH,
        full_name="Other Instructor",
        role=models.UserRole.INSTRUCTOR.value,
        is_email_verified=True,
        is_active=True,
        created_at=now - timedelta(days=60),
    )
    db.add_all([ethan, other_student, instructor, other_instructor])

    course_ssa = models.Course(
        id="SSA101",
        code="SSA101",
        name="Study Skills & Academic Success",
        description="Demo course for Study Assistant and planner tests.",
    )
    course_other = models.Course(
        id="OTH999",
        code="OTH999",
        name="Other Course",
        description="Course Ethan is not enrolled in.",
    )
    db.add_all([course_ssa, course_other])

    section_ethan = models.CourseSection(
        id="sec_ssa101_demo",
        course_id="SSA101",
        instructor_id="inst_demo",
        term="Fall2026",
        section_code="SE1801",
    )
    section_other = models.CourseSection(
        id="sec_oth999_other",
        course_id="OTH999",
        instructor_id="inst_other",
        term="Fall2026",
        section_code="SE1901",
    )
    db.add_all([section_ethan, section_other])

    db.add_all(
        [
            models.Enrollment(
                id="enr_ethan_ssa",
                student_id="student_ethan",
                section_id="sec_ssa101_demo",
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=now - timedelta(days=20),
            ),
            models.Enrollment(
                id="enr_other_oth",
                student_id="student_other",
                section_id="sec_oth999_other",
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=now - timedelta(days=20),
            ),
        ]
    )

    asg_ethan = models.Assignment(
        id="asg_ssa101_demo",
        section_id="sec_ssa101_demo",
        title="SSA101 Weekly Lab",
        description="Demo assignment for Ethan.",
        due_date=now + timedelta(days=7),
        max_points=100,
        assessment_type="ASSIGNMENT",
    )
    asg_other = models.Assignment(
        id="asg_oth999_other",
        section_id="sec_oth999_other",
        title="Other Course Project",
        description="Assignment Ethan must not access.",
        due_date=now + timedelta(days=10),
        max_points=100,
        assessment_type="ASSIGNMENT",
    )
    db.add_all([asg_ethan, asg_other])

    def _add_plan_tree(
        *,
        plan_id: str,
        student_id: str,
        assignment_id: str,
        task_id: str,
    ) -> None:
        from datetime import date, timedelta

        # POST /plans/accept schedules the plan into declared free gaps
        # (TimetableService.schedule_plan_into_gaps) and 409s without at
        # least one declared day -- give the whole current week generous
        # room so any test that accepts this fixture plan can.
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        availability = [
            {"date": (monday + timedelta(days=offset)).isoformat(), "availableMinutes": 180}
            for offset in range(7)
        ]
        db.add(
            models.WeeklyPlan(
                id=plan_id,
                student_id=student_id,
                week_number=today.isocalendar().week,
                goals={"statement": "Demo weekly plan", "availability": availability},
                study_hours_allocated=10.0,
            )
        )
        daily_id = f"dp_{plan_id}"
        db.add(
            models.DailyPlan(
                id=daily_id,
                weekly_plan_id=plan_id,
                date=now,
                status="TODO",
            )
        )
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
        db.add(
            models.StudyTask(
                id=task_id,
                schedule_block_id=block_id,
                assignment_id=assignment_id,
                title="Demo study task",
                planned_minutes=60,
                actual_minutes=None,
                priority="MEDIUM",
                status="TODO",
                difficulty="MEDIUM",
            )
        )

    _add_plan_tree(
        plan_id="plan_ethan_w6",
        student_id="student_ethan",
        assignment_id="asg_ssa101_demo",
        task_id="task_ethan_1",
    )
    _add_plan_tree(
        plan_id="plan_other_w6",
        student_id="student_other",
        assignment_id="asg_oth999_other",
        task_id="task_other_1",
    )

    db.add(
        models.RiskSignal(
            id="risk_ethan_demo",
            student_id="student_ethan",
            section_id="sec_ssa101_demo",
            assignment_id="asg_ssa101_demo",
            risk_type="LATE_SUBMISSION",
            risk_level="MEDIUM",
            triggered_rules={"rule": "demo"},
            evidence={"note": "demo risk for instructor.demo"},
            recommended_action="Reach out to student",
            generated_at=now - timedelta(days=2),
            resolved_at=None,
            resolution_type=None,
        )
    )
    db.add(
        models.RiskSignal(
            id="risk_other_instructor",
            student_id="student_other",
            section_id="sec_oth999_other",
            assignment_id="asg_oth999_other",
            risk_type="ABANDONMENT",
            risk_level="HIGH",
            triggered_rules={"rule": "demo"},
            evidence={"note": "owned by inst_other"},
            recommended_action="Escalate",
            generated_at=now - timedelta(days=1),
            resolved_at=None,
            resolution_type=None,
        )
    )

    db.commit()


def _ensure_plan_fixtures(db: Session) -> None:
    """Re-create the weekly-plan / risk fixtures if they were cleared."""
    now = datetime.now(UTC).replace(tzinfo=None)
    specs = (
        ("plan_ethan_w6", "student_ethan", "asg_ssa101_demo", "task_ethan_1"),
        ("plan_other_w6", "student_other", "asg_oth999_other", "task_other_1"),
    )
    changed = False
    for plan_id, student_id, assignment_id, task_id in specs:
        if db.query(models.WeeklyPlan).filter_by(id=plan_id).first() is not None:
            continue
        changed = True
        from datetime import date, timedelta

        today = date.today()
        monday = today - timedelta(days=today.weekday())
        availability = [
            {"date": (monday + timedelta(days=offset)).isoformat(), "availableMinutes": 180}
            for offset in range(7)
        ]
        db.add(
            models.WeeklyPlan(
                id=plan_id,
                student_id=student_id,
                week_number=today.isocalendar().week,
                goals={"statement": "Demo weekly plan", "availability": availability},
                study_hours_allocated=10.0,
            )
        )
        daily_id = f"dp_{plan_id}"
        db.add(
            models.DailyPlan(
                id=daily_id, weekly_plan_id=plan_id, date=now, status="TODO"
            )
        )
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
        db.add(
            models.StudyTask(
                id=task_id,
                schedule_block_id=block_id,
                assignment_id=assignment_id,
                title="Demo study task",
                planned_minutes=60,
                actual_minutes=None,
                priority="MEDIUM",
                status="TODO",
                difficulty="MEDIUM",
            )
        )

    if db.query(models.RiskSignal).filter_by(id="risk_ethan_demo").first() is None:
        changed = True
        db.add(
            models.RiskSignal(
                id="risk_ethan_demo",
                student_id="student_ethan",
                section_id="sec_ssa101_demo",
                assignment_id="asg_ssa101_demo",
                risk_type="LATE_SUBMISSION",
                risk_level="MEDIUM",
                triggered_rules={"rule": "demo"},
                evidence={"note": "demo risk for instructor.demo"},
                recommended_action="Reach out to student",
                generated_at=now - timedelta(days=2),
            )
        )
    if changed:
        db.commit()
