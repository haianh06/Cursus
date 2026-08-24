"""P0#8 trace (mục 9 ý8, Option B, docs/PENDING_DECISIONS.md #1) —
confirms llm_attempted/llm_success/fallback_used/retrieval_empty land in
`WeeklyReflection.metrics` (existing JSON column, zero migration) after
`ReflectionEngine.save()` runs. `save()` never calls the LLM itself (by
design — see its own comment), so these fields are always False/False
here except `fallback_used`, which reflects whether the caller supplied
summary text or not.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.db import models
from src.db.connection import SessionLocal
from src.security.passwords import hash_password
from src.services.ai import plan_builder
from src.services.ai.reflection_engine import ReflectionEngine

COURSE_CODE = "TRACER101"


def _ensure_student(db):
    if db.query(models.User).filter_by(id="trace_reflect_student").first() is None:
        db.add(
            models.User(
                id="trace_reflect_student",
                email="trace.reflect@example.test",
                password_hash=hash_password("TracePassword123"),
                full_name="Trace Reflect Student",
                role=models.UserRole.STUDENT.value,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()


def _clean(db):
    db.query(models.WeeklyReflection).filter_by(student_id="trace_reflect_student").delete()
    db.query(models.StudyTask).filter(
        models.StudyTask.schedule_block_id.in_(
            db.query(models.ScheduleBlock.id).filter(
                models.ScheduleBlock.daily_plan_id.in_(
                    db.query(models.DailyPlan.id).filter(
                        models.DailyPlan.weekly_plan_id.in_(
                            db.query(models.WeeklyPlan.id).filter_by(student_id="trace_reflect_student")
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
                    db.query(models.WeeklyPlan.id).filter_by(student_id="trace_reflect_student")
                )
            )
        )
    ).delete(synchronize_session=False)
    db.query(models.DailyPlan).filter(
        models.DailyPlan.weekly_plan_id.in_(
            db.query(models.WeeklyPlan.id).filter_by(student_id="trace_reflect_student")
        )
    ).delete(synchronize_session=False)
    db.query(models.WeeklyPlan).filter_by(student_id="trace_reflect_student").delete()
    db.query(models.Assignment).filter_by(section_id="sec_tracer101").delete()
    db.query(models.CourseSection).filter_by(id="sec_tracer101").delete()
    db.query(models.Course).filter_by(id=COURSE_CODE).delete()
    db.commit()


def _make_plan(db, monkeypatch) -> models.WeeklyPlan:
    db.add(models.Course(id=COURSE_CODE, code=COURSE_CODE, name="Tracer Course", description=""))
    db.add(
        models.CourseSection(
            id="sec_tracer101",
            course_id=COURSE_CODE,
            instructor_id="inst_tracer",
            term="Fall2026",
            section_code="TR02",
        )
    )
    assignment = models.Assignment(
        id="asg_tracer101",
        section_id="sec_tracer101",
        title="Tracer Assignment",
        description="Used only to exercise ReflectionEngine trace fields.",
        due_date=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=7),
        max_points=100,
        assessment_type="ASSIGNMENT",
    )
    db.add(assignment)
    db.flush()

    monkeypatch.setattr(
        plan_builder, "_llm_generated_tasks",
        lambda db, a: (None, {"retrieval_empty": True, "llm_success": False}),
    )
    return plan_builder.PlanBuilder(db).generate(
        student_id="trace_reflect_student", assignment=assignment, available_hours=10,
    )


def test_save_with_client_summary_marks_fallback_not_used(monkeypatch):
    db = SessionLocal()
    try:
        _clean(db)
        _ensure_student(db)
        plan = _make_plan(db, monkeypatch)

        row = ReflectionEngine(db).save(
            plan=plan, answers=[], adjustments=[], summary="Tuần này ổn.",
            student_confirmed=True, share_with_advisor=False,
        )

        assert row.metrics["llm_attempted"] is False
        assert row.metrics["llm_success"] is False
        assert row.metrics["fallback_used"] is False
        assert row.metrics["retrieval_empty"] is False
    finally:
        _clean(db)
        db.close()


def test_save_without_client_summary_marks_fallback_used(monkeypatch):
    db = SessionLocal()
    try:
        _clean(db)
        _ensure_student(db)
        plan = _make_plan(db, monkeypatch)

        row = ReflectionEngine(db).save(
            plan=plan, answers=[], adjustments=[], summary=None,
            student_confirmed=True, share_with_advisor=False,
        )

        assert row.metrics["llm_attempted"] is False
        assert row.metrics["llm_success"] is False
        assert row.metrics["fallback_used"] is True
        assert row.metrics["retrieval_empty"] is False
        # The deterministic template still produced real saved content.
        assert row.content
    finally:
        _clean(db)
        db.close()
