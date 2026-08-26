"""Deterministic risk-rule fixtures (Blueprint §4.1, Data Contract §6).

These assert the exact score for hand-built task/event sets, so a refactor
that silently changes a weight fails CI instead of changing what a lecturer
sees mid-demo.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.services.ai.risk_engine import RiskEngine, severity_for

NOW = datetime(2026, 8, 20, 12, 0, 0)
SECTION_ID = "sec_risk_fixture"


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _make_student(db, suffix: str, *, created_at: datetime | None = None) -> str:
    """`created_at` defaults to a well-established account (90 days old) --
    every existing fixture here is a "healthy, long-tracked student" in
    spirit even though `_build_week` only ever builds one week of task rows,
    so account age must not default to `NOW` (that would make every one of
    them look brand-new to RiskEngine's mục 14.1 missingness check). Pass
    `created_at=NOW` explicitly to build an actually-new-student fixture."""
    student_id = f"stu_risk_{suffix}_{uuid.uuid4().hex[:6]}"
    db.add(
        models.User(
            id=student_id,
            email=f"{student_id}@risk.test",
            password_hash="x",
            full_name=f"Risk Fixture {suffix}",
            role=models.UserRole.STUDENT.value,
            is_email_verified=True,
            is_active=True,
            created_at=created_at if created_at is not None else NOW - timedelta(days=90),
        )
    )
    db.flush()
    return student_id


def _build_week(
    db,
    student_id: str,
    tasks: list[tuple[str, int, str]],
    *,
    events: list[tuple[int, str, str]] | None = None,
) -> None:
    """tasks: (title, day_offset_from_NOW, status). Negative offset = past."""
    plan_id = f"plan_{uuid.uuid4().hex[:8]}"
    db.add(
        models.WeeklyPlan(
            id=plan_id,
            student_id=student_id,
            week_number=NOW.isocalendar().week,
            goals={"statement": "fixture"},
            study_hours_allocated=8.0,
        )
    )
    db.flush()
    task_ids: list[str] = []
    for index, (title, offset, status) in enumerate(tasks):
        when = NOW + timedelta(days=offset)
        daily_id = f"dp_{uuid.uuid4().hex[:8]}"
        block_id = f"sb_{uuid.uuid4().hex[:8]}"
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        db.add(models.DailyPlan(id=daily_id, weekly_plan_id=plan_id, date=when, status="TODO"))
        db.add(
            models.ScheduleBlock(
                id=block_id,
                daily_plan_id=daily_id,
                start_time=when,
                end_time=when + timedelta(minutes=60),
                activity_description="fixture",
            )
        )
        db.add(
            models.StudyTask(
                id=task_id,
                schedule_block_id=block_id,
                assignment_id=None,
                title=f"{title} {index}",
                planned_minutes=60,
                actual_minutes=60 if status == "COMPLETED" else None,
                priority="MEDIUM",
                status=status,
                difficulty="MEDIUM",
                rescheduled_count=0,
            )
        )
        task_ids.append(task_id)

    for offset, event_type, task_ref in events or []:
        index = int(task_ref)
        db.add(
            models.ProgressEvent(
                id=f"evt_{uuid.uuid4().hex[:8]}",
                student_id=student_id,
                task_id=task_ids[index],
                event_type=event_type,
                payload={"reason_code": "underestimated_time"},
                occurred_at=NOW + timedelta(days=offset),
            )
        )
    db.flush()


def test_severity_bands_are_exactly_the_documented_thresholds():
    assert severity_for(0) == ("normal", "LOW")
    assert severity_for(2) == ("normal", "LOW")
    assert severity_for(3) == ("watch", "MEDIUM")
    assert severity_for(4) == ("watch", "MEDIUM")
    assert severity_for(5) == ("needs_support", "HIGH")
    assert severity_for(9) == ("needs_support", "HIGH")


def test_healthy_student_scores_zero(db):
    student_id = _make_student(db, "healthy")
    _build_week(
        db,
        student_id,
        [("done", -3, "COMPLETED"), ("done", -2, "COMPLETED"), ("todo", 2, "TODO")],
        events=[(-3, "TASK_COMPLETED", "0"), (-2, "TASK_COMPLETED", "1")],
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    assert result.score == 0
    assert result.severity == "normal"
    assert result.signals == []


def test_two_overdue_plus_low_completion_scores_four(db):
    student_id = _make_student(db, "overdue")
    _build_week(
        db,
        student_id,
        [
            ("late", -3, "TODO"),
            ("late", -2, "TODO"),
            ("late", -1, "TODO"),
            ("done", -4, "COMPLETED"),
        ],
        events=[(-4, "TASK_COMPLETED", "3")],
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code for signal in result.signals}
    assert "OVERDUE_TASKS_2_PLUS" in codes
    assert "COMPLETION_BELOW_40" in codes
    assert result.score == 4
    assert result.severity == "watch"


def test_repeated_defer_adds_exactly_one_point(db):
    student_id = _make_student(db, "defer")
    _build_week(
        db,
        student_id,
        [("a", -3, "DEFERRED"), ("b", -2, "COMPLETED"), ("c", 3, "TODO")],
        events=[
            (-3, "TASK_DEFERRED", "0"),
            (-2, "TASK_DEFERRED", "0"),
            (-2, "TASK_COMPLETED", "1"),
        ],
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code: signal.points for signal in result.signals}
    assert codes.get("TASK_DEFERRED_2_PLUS") == 1


def test_inactive_seven_days_adds_two(db):
    student_id = _make_student(db, "inactive")
    _build_week(db, student_id, [("a", -9, "TODO"), ("b", -8, "TODO")], events=[])
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code for signal in result.signals}
    assert "INACTIVE_7_DAYS" in codes
    # 2 overdue (+2) + completion 0% (+2) + inactive (+2)
    assert result.score == 6
    assert result.severity == "needs_support"


def _save_reflection(
    db, student_id: str, *, stress_code: str | None, confirmed: bool, week_number: int
) -> None:
    answers = [{"questionId": "stress_level", "selectedCodes": [stress_code]}] if stress_code else []
    db.add(
        models.WeeklyReflection(
            id=f"ref_{uuid.uuid4().hex[:8]}",
            student_id=student_id,
            week_number=week_number,
            content="fixture reflection",
            generated_at=NOW,
            metrics={"answers": answers, "studentConfirmed": confirmed},
        )
    )
    db.flush()


def test_self_reported_high_stress_adds_two(db):
    student_id = _make_student(db, "stressed")
    _build_week(db, student_id, [("done", -1, "COMPLETED")], events=[(-1, "TASK_COMPLETED", "0")])
    _save_reflection(
        db, student_id, stress_code="very_high", confirmed=True, week_number=NOW.isocalendar().week
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code: signal.points for signal in result.signals}
    assert codes.get("SELF_REPORTED_HIGH_STRESS") == 2
    assert result.score == 2


def test_self_reported_high_stress_ignored_when_reflection_not_confirmed(db):
    """A draft/preview reflection must never contribute to the score — only
    a `studentConfirmed` one the student actually chose to save."""
    student_id = _make_student(db, "draftstress")
    _build_week(db, student_id, [("done", -1, "COMPLETED")], events=[(-1, "TASK_COMPLETED", "0")])
    _save_reflection(
        db, student_id, stress_code="very_high", confirmed=False, week_number=NOW.isocalendar().week
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code for signal in result.signals}
    assert "SELF_REPORTED_HIGH_STRESS" not in codes
    assert result.score == 0


def test_self_reported_low_stress_does_not_trigger(db):
    student_id = _make_student(db, "calm")
    _build_week(db, student_id, [("done", -1, "COMPLETED")], events=[(-1, "TASK_COMPLETED", "0")])
    _save_reflection(
        db, student_id, stress_code="very_low", confirmed=True, week_number=NOW.isocalendar().week
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code for signal in result.signals}
    assert "SELF_REPORTED_HIGH_STRESS" not in codes
    assert result.score == 0


def test_self_reported_high_stress_uses_only_the_latest_reflection(db):
    """An old confirmed "very_high" week must not haunt the score forever
    once a newer reflection exists — even if the newer one has no stress
    answer at all."""
    student_id = _make_student(db, "recovered")
    _build_week(db, student_id, [("done", -1, "COMPLETED")], events=[(-1, "TASK_COMPLETED", "0")])
    _save_reflection(
        db, student_id, stress_code="very_high", confirmed=True, week_number=1
    )
    _save_reflection(
        db, student_id, stress_code=None, confirmed=True, week_number=NOW.isocalendar().week
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code for signal in result.signals}
    assert "SELF_REPORTED_HIGH_STRESS" not in codes


def test_self_reported_high_stress_also_works_through_preload(db):
    """`preload()` batch-fetches reflections for the instructor dashboard —
    must pick the same latest-per-student row as the unpreloaded path."""
    student_id = _make_student(db, "preloadstress")
    _build_week(db, student_id, [("done", -1, "COMPLETED")], events=[(-1, "TASK_COMPLETED", "0")])
    _save_reflection(
        db, student_id, stress_code="very_high", confirmed=True, week_number=NOW.isocalendar().week
    )
    engine = RiskEngine(db, now=NOW)
    engine.preload([student_id])
    result = engine.assess(student_id=student_id, section_id=SECTION_ID)
    codes = {signal.code for signal in result.signals}
    assert "SELF_REPORTED_HIGH_STRESS" in codes


def test_score_is_reproducible_across_runs(db):
    student_id = _make_student(db, "stable")
    _build_week(
        db,
        student_id,
        [("a", -3, "TODO"), ("b", -2, "TODO"), ("c", -1, "COMPLETED")],
        events=[(-1, "TASK_COMPLETED", "2")],
    )
    engine = RiskEngine(db, now=NOW)
    first = engine.assess(student_id=student_id, section_id=SECTION_ID)
    second = engine.assess(student_id=student_id, section_id=SECTION_ID)
    assert first.score == second.score
    assert [s.as_dict() for s in first.signals] == [s.as_dict() for s in second.signals]


def test_score_equals_sum_of_signal_points(db):
    student_id = _make_student(db, "sum")
    _build_week(
        db,
        student_id,
        [("a", -5, "TODO"), ("b", -4, "TODO"), ("c", -3, "TODO")],
        events=[],
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    assert result.score == sum(signal.points for signal in result.signals)


# mục 14.1 "Missingness" — a student who has never used Cursus, or whose
# account is younger than the 7-day assessment window, must not silently
# read as "normal" (observed, fine). See RiskEngine._insufficient_data.


def test_zero_tasks_ever_is_insufficient_data(db):
    student_id = _make_student(db, "notasks")
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    assert result.score == 0
    assert result.severity == "insufficient_data"


def test_brand_new_student_with_no_signals_is_insufficient_data(db):
    student_id = _make_student(db, "brandnew", created_at=NOW - timedelta(days=2))
    _build_week(
        db,
        student_id,
        [("done", -1, "COMPLETED"), ("todo", 1, "TODO")],
        events=[(-1, "TASK_COMPLETED", "0")],
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    assert result.score == 0
    assert result.severity == "insufficient_data"


def test_brand_new_student_with_a_real_signal_keeps_the_real_severity(db):
    """Missingness only relabels an already-lowest-band (score 0) result --
    it must never suppress a genuine finding just because the account is
    new. A 2-day-old account with real overdue tasks stays "watch", exactly
    like test_two_overdue_plus_low_completion_scores_four's older account."""
    student_id = _make_student(db, "brandnewrisk", created_at=NOW - timedelta(days=2))
    _build_week(
        db,
        student_id,
        [
            ("late", -2, "TODO"),
            ("late", -1, "TODO"),
            ("done", -1, "COMPLETED"),
        ],
        events=[(-1, "TASK_COMPLETED", "2")],
    )
    result = RiskEngine(db, now=NOW).assess(student_id=student_id, section_id=SECTION_ID)
    assert "OVERDUE_TASKS_2_PLUS" in {signal.code for signal in result.signals}
    assert result.severity == "watch"


def test_insufficient_data_is_never_persisted_as_an_open_alert(db):
    student_id = _make_student(db, "notaskspersist")
    engine = RiskEngine(db, now=NOW)
    result = engine.assess(student_id=student_id, section_id=SECTION_ID)
    assert result.severity == "insufficient_data"
    saved = engine.persist_assessment(result)
    assert saved is None
    assert (
        db.query(models.RiskSignal).filter_by(student_id=student_id, section_id=SECTION_ID).first()
        is None
    )
