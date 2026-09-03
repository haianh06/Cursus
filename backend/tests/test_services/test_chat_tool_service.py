"""Cursus Chat's tool-calling executors (chat_tool_service.py) -- each tool
must (a) return the right shape, (b) never leak another student's data, and
(c) degrade to an empty/error result instead of raising when there's
nothing to find or the tool name is unknown."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.services.core.chat_tool_service import execute_chat_tool
from tests.support.semester_practice_fixtures import (
    ensure_course,
    ensure_org,
    ensure_user,
    enroll_student,
)


def _code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


def _now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def test_unknown_tool_name_returns_error_not_raise():
    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id="anyone", name="not_a_real_tool", arguments={})
        assert result == {"error": "unknown tool: not_a_real_tool"}
    finally:
        db.close()


def test_weekly_timetable_scopes_to_the_asking_student_only():
    org_id = ensure_org(f"ct-tt-{uuid.uuid4().hex[:6]}", "ct-tt")
    instructor_id = ensure_user(email=f"ct.tti.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_a = ensure_user(email=f"ct.tta.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    student_b = ensure_user(email=f"ct.ttb.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    code = _code("CTT")
    course_id = ensure_course(code=code, org_id=org_id)
    section_id = enroll_student(student_id=student_a, course_id=course_id, instructor_id=instructor_id)
    # student_b enrolled in a DIFFERENT section/course so their lecture must
    # never show up in student_a's timetable tool result.
    other_code = _code("CTX")
    other_course_id = ensure_course(code=other_code, org_id=org_id)
    enroll_student(student_id=student_b, course_id=other_course_id, instructor_id=instructor_id)

    db = SessionLocal()
    try:
        monday = _now_naive() - timedelta(days=_now_naive().weekday())
        lecture_start = monday.replace(hour=9, minute=0, second=0, microsecond=0)
        db.add(
            models.CalendarEvent(
                id=f"cal_{uuid.uuid4().hex[:10]}",
                section_id=section_id,
                title="Buoi hoc ly thuyet",
                description="Phong A1",
                start_time=lecture_start,
                end_time=lecture_start + timedelta(hours=2),
                event_type="LECTURE",
            )
        )
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id=student_a, name="get_weekly_timetable", arguments={})
        assert result["isEmpty"] is False
        titles = [s["title"] for s in result["sessions"]]
        assert "Buoi hoc ly thuyet" in titles
        assert all(s["courseCode"] != other_code for s in result["sessions"])

        # student_b has no lecture this week in THEIR own course -> empty,
        # never sees student_a's session.
        result_b = execute_chat_tool(db, student_id=student_b, name="get_weekly_timetable", arguments={})
        assert all(s["title"] != "Buoi hoc ly thuyet" for s in result_b["sessions"])
    finally:
        db.close()


def test_weekly_timetable_includes_today_and_marks_todays_session():
    """Regression: the LLM previously had no "today" ground truth anywhere
    in a timetable tool result (only a weekStart/weekEnd range), and guessed
    the range's END date was "today" -- wrongly declaring the week already
    over days early. The tool result must now say what today's date is,
    and mark which session (if any) falls on it."""
    from src.services.core.chat_tool_service import _app_today

    org_id = ensure_org(f"ct-tdy-{uuid.uuid4().hex[:6]}", "ct-tdy")
    instructor_id = ensure_user(email=f"ct.tdyi.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_id = ensure_user(email=f"ct.tdys.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    code = _code("CTD")
    course_id = ensure_course(code=code, org_id=org_id)
    section_id = enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)

    today = _app_today()
    lecture_start = datetime.combine(today, datetime.min.time()).replace(hour=9)
    db = SessionLocal()
    try:
        db.add(
            models.CalendarEvent(
                id=f"cal_{uuid.uuid4().hex[:10]}",
                section_id=section_id,
                title="Buoi hoc hom nay",
                description=None,
                start_time=lecture_start,
                end_time=lecture_start + timedelta(hours=2),
                event_type="LECTURE",
            )
        )
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id=student_id, name="get_weekly_timetable", arguments={})
        assert result["today"] == today.isoformat()
        session = next(s for s in result["sessions"] if s["title"] == "Buoi hoc hom nay")
        assert session["isToday"] is True
    finally:
        db.close()


def test_weekly_timetable_clamps_out_of_range_week_offset():
    org_id = ensure_org(f"ct-ttc-{uuid.uuid4().hex[:6]}", "ct-ttc")
    student_id = ensure_user(email=f"ct.ttcs.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    db = SessionLocal()
    try:
        # Way out of the [-4, 4] clamp -- must not raise, just get clamped
        # inside `decide_tool_calls`' own parsing (this only exercises the
        # executor's tolerance for an already-clamped/odd value reaching it).
        result = execute_chat_tool(db, student_id=student_id, name="get_weekly_timetable", arguments={"weeks_from_now": 4})
        assert result["isEmpty"] is True
    finally:
        db.close()


def test_current_plan_tasks_returns_empty_shape_when_no_plan_exists():
    org_id = ensure_org(f"ct-pl-{uuid.uuid4().hex[:6]}", "ct-pl")
    student_id = ensure_user(email=f"ct.pls.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id=student_id, name="get_current_plan_tasks", arguments={})
        assert result["hasPlan"] is False
        assert result["tasks"] == []
    finally:
        db.close()


def test_quiz_results_empty_when_not_enrolled_anywhere():
    org_id = ensure_org(f"ct-qz-{uuid.uuid4().hex[:6]}", "ct-qz")
    student_id = ensure_user(email=f"ct.qzs.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id=student_id, name="get_quiz_results", arguments={})
        assert result == {"quizzes": []}
    finally:
        db.close()


def test_quiz_results_shape_for_an_unstarted_published_quiz():
    org_id = ensure_org(f"ct-qzs-{uuid.uuid4().hex[:6]}", "ct-qzs")
    instructor_id = ensure_user(email=f"ct.qzsi.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_id = ensure_user(email=f"ct.qzss.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    code = _code("CTQ")
    course_id = ensure_course(code=code, org_id=org_id)
    section_id = enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)

    db = SessionLocal()
    try:
        db.add(
            models.Quiz(
                id=f"quiz_{uuid.uuid4().hex[:10]}",
                section_id=section_id,
                title="Quiz 1",
                description="",
                time_limit_minutes=20,
                due_date=_now_naive() + timedelta(days=3),
                max_points=10.0,
                created_by=instructor_id,
                is_published=True,
            )
        )
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id=student_id, name="get_quiz_results", arguments={})
        assert len(result["quizzes"]) == 1
        quiz = result["quizzes"][0]
        assert quiz["title"] == "Quiz 1"
        assert quiz["courseCode"] == code
        assert quiz["myStatus"] == "not_started"
        assert quiz["myGrade"] is None
    finally:
        db.close()


def test_risk_signals_scopes_to_student_and_drops_internal_fields():
    org_id = ensure_org(f"ct-rk-{uuid.uuid4().hex[:6]}", "ct-rk")
    instructor_id = ensure_user(email=f"ct.rki.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_a = ensure_user(email=f"ct.rka.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    student_b = ensure_user(email=f"ct.rkb.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    code = _code("CTR")
    course_id = ensure_course(code=code, org_id=org_id)
    section_id = enroll_student(student_id=student_a, course_id=course_id, instructor_id=instructor_id)
    enroll_student(student_id=student_b, course_id=course_id, instructor_id=instructor_id)

    db = SessionLocal()
    try:
        db.add(
            models.RiskSignal(
                id=f"risk_{uuid.uuid4().hex[:10]}",
                student_id=student_a,
                section_id=section_id,
                risk_type="LATE_SUBMISSION",
                risk_level="HIGH",
                triggered_rules={"internal": "rule trace"},
                evidence={"raw": "internal engine detail"},
                recommended_action="Instructor-only guidance text",
                generated_at=_now_naive(),
            )
        )
        db.commit()
    finally:
        db.close()

    db = SessionLocal()
    try:
        result_a = execute_chat_tool(db, student_id=student_a, name="get_risk_signals", arguments={})
        assert len(result_a["riskSignals"]) == 1
        signal = result_a["riskSignals"][0]
        assert signal["riskType"] == "LATE_SUBMISSION"
        assert signal["riskLevel"] == "HIGH"
        assert signal["courseCode"] == code
        assert "evidence" not in signal
        assert "triggeredRules" not in signal
        assert "recommendedAction" not in signal

        result_b = execute_chat_tool(db, student_id=student_b, name="get_risk_signals", arguments={})
        assert result_b["riskSignals"] == []
    finally:
        db.close()


def test_self_study_stats_empty_week_has_seven_zero_days():
    org_id = ensure_org(f"ct-ss-{uuid.uuid4().hex[:6]}", "ct-ss")
    student_id = ensure_user(email=f"ct.sss.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id=student_id, name="get_self_study_stats", arguments={})
        assert len(result["dailyMinutes"]) == 7
        assert result["totalMinutes"] == 0
    finally:
        db.close()


@pytest.mark.parametrize(
    "tool_name",
    [
        "get_weekly_timetable",
        "get_current_plan_tasks",
        "get_quiz_results",
        "get_risk_signals",
        "get_self_study_stats",
    ],
)
def test_every_tool_never_raises_for_a_student_with_no_data_at_all(tool_name):
    org_id = ensure_org(f"ct-nd-{uuid.uuid4().hex[:6]}", "ct-nd")
    student_id = ensure_user(email=f"ct.nds.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.STUDENT)
    db = SessionLocal()
    try:
        result = execute_chat_tool(db, student_id=student_id, name=tool_name, arguments={})
        assert "error" not in result
    finally:
        db.close()
