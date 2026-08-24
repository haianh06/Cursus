"""P0#8 trace (mục 9 ý8, Option B, docs/PENDING_DECISIONS.md #1) —
confirms llm_attempted/llm_success/fallback_used/retrieval_empty actually
land in `WeeklyPlan.goals` (the existing JSON column, zero migration) after
`PlanBuilder.generate()` runs, for each of: LLM success, LLM fallback
(retrieval empty), and the Gate-2 demo path (never calls the LLM at all).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.db import models
from src.db.connection import SessionLocal
from src.security.passwords import hash_password
from src.services.ai import plan_builder
from src.services.mock.gate2_demo import Gate2DemoService

COURSE_CODE = "TRACE101"


def _ensure_student(db):
    if db.query(models.User).filter_by(id="trace_student").first() is None:
        db.add(
            models.User(
                id="trace_student",
                email="trace.student@example.test",
                password_hash=hash_password("TracePassword123"),
                full_name="Trace Student",
                role=models.UserRole.STUDENT.value,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()


def _clean(db):
    db.query(models.StudyTask).filter(
        models.StudyTask.schedule_block_id.in_(
            db.query(models.ScheduleBlock.id).filter(
                models.ScheduleBlock.daily_plan_id.in_(
                    db.query(models.DailyPlan.id).filter(
                        models.DailyPlan.weekly_plan_id.in_(
                            db.query(models.WeeklyPlan.id).filter_by(student_id="trace_student")
                        )
                    )
                )
            )
        )
    ).delete(synchronize_session=False)
    db.query(models.ScheduleBlock).filter(
        models.ScheduleBlock.daily_plan_id.in_(
            db.query(models.DailyPlan.id).filter(
                models.DailyPlan.weekly_plan_id.in_(
                    db.query(models.WeeklyPlan.id).filter_by(student_id="trace_student")
                )
            )
        )
    ).delete(synchronize_session=False)
    db.query(models.DailyPlan).filter(
        models.DailyPlan.weekly_plan_id.in_(
            db.query(models.WeeklyPlan.id).filter_by(student_id="trace_student")
        )
    ).delete(synchronize_session=False)
    db.query(models.WeeklyPlan).filter_by(student_id="trace_student").delete()
    db.query(models.Assignment).filter_by(section_id="sec_trace101").delete()
    db.query(models.CourseSection).filter_by(id="sec_trace101").delete()
    db.query(models.Course).filter_by(id=COURSE_CODE).delete()
    db.commit()


def _make_assignment(db) -> models.Assignment:
    db.add(models.Course(id=COURSE_CODE, code=COURSE_CODE, name="Trace Course", description=""))
    db.add(
        models.CourseSection(
            id="sec_trace101",
            course_id=COURSE_CODE,
            instructor_id="inst_trace",
            term="Fall2026",
            section_code="TR01",
        )
    )
    assignment = models.Assignment(
        id="asg_trace101",
        section_id="sec_trace101",
        title="Trace Assignment",
        description="Used only to exercise PlanBuilder trace fields.",
        due_date=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
        max_points=100,
        assessment_type="ASSIGNMENT",
    )
    db.add(assignment)
    db.flush()
    return assignment


def test_llm_success_trace_lands_in_goals(monkeypatch):
    db = SessionLocal()
    try:
        _clean(db)
        _ensure_student(db)
        assignment = _make_assignment(db)

        fake_task = plan_builder.GeneratedTask(
            key="k1", title="Task 1", estimated_minutes=30, weekday=0, priority="HIGH",
            deliverable="", source_refs=(), source_fact=None, suggestion_reason="",
        )
        monkeypatch.setattr(
            plan_builder,
            "_llm_generated_tasks",
            lambda db, a: ([fake_task], {"retrieval_empty": False, "llm_success": True}),
        )

        plan = plan_builder.PlanBuilder(db).generate(
            student_id="trace_student", assignment=assignment, available_hours=10,
        )

        assert plan.goals["llm_attempted"] is True
        assert plan.goals["llm_success"] is True
        assert plan.goals["fallback_used"] is False
        assert plan.goals["retrieval_empty"] is False
    finally:
        _clean(db)
        db.close()


def test_llm_fallback_with_empty_retrieval_trace_lands_in_goals(monkeypatch):
    db = SessionLocal()
    try:
        _clean(db)
        _ensure_student(db)
        assignment = _make_assignment(db)

        monkeypatch.setattr(
            plan_builder,
            "_llm_generated_tasks",
            lambda db, a: (None, {"retrieval_empty": True, "llm_success": False}),
        )

        plan = plan_builder.PlanBuilder(db).generate(
            student_id="trace_student", assignment=assignment, available_hours=10,
        )

        assert plan.goals["llm_attempted"] is True
        assert plan.goals["llm_success"] is False
        assert plan.goals["fallback_used"] is True
        assert plan.goals["retrieval_empty"] is True
        # Fallback means the deterministic template still produced real tasks.
        assert len(plan.goals["task_meta"]) > 0
    finally:
        _clean(db)
        db.close()


def test_gate2_demo_assignment_never_attempts_llm(monkeypatch):
    db = SessionLocal()
    try:
        _clean(db)
        _ensure_student(db)
        called = {"llm_path": False}

        def _spy(*args, **kwargs):
            called["llm_path"] = True
            return None, {"retrieval_empty": False, "llm_success": False}

        monkeypatch.setattr(plan_builder, "_llm_generated_tasks", _spy)

        Gate2DemoService(db).ensure_student("trace_student")
        demo_assignment = db.get(models.Assignment, plan_builder.gate2_demo.PART1_ASSIGNMENT_ID)
        assert demo_assignment is not None, "Gate2DemoService.ensure_student must seed it"

        plan = plan_builder.PlanBuilder(db).generate(
            student_id="trace_student", assignment=demo_assignment, available_hours=10,
        )

        assert called["llm_path"] is False
        assert plan.goals["llm_attempted"] is False
        assert plan.goals["llm_success"] is False
        assert plan.goals["fallback_used"] is False
        assert plan.goals["retrieval_empty"] is False
    finally:
        _clean(db)
        db.close()
