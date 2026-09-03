"""Executes Cursus Chat's tool calls (see ai_engine/chat_tools.py for the
tool schemas/decision step) -- the DB-touching half of that split, mirroring
how chat_cache_service.py/guardrail_service.py sit in this same package
next to the ai_engine layer that has no DB imports of its own.

Every wrapper below is a thin call into an EXISTING service already used by
a real student-facing route (TimetableService, resolve_current_plan/
serialize_plan, QuizService, SelfStudyService, and the same query
`/student/risks` already runs) -- no new business logic, just reshaping
each result into something compact enough to drop into an LLM prompt. Every
call is scoped by the `student_id` the caller passes in (always the asking
student's own id, never anyone else's -- see cursus_chat.py's call site),
and every wrapper swallows its own errors into `{"error": ...}` rather than
raising, so one broken tool never breaks the rest of the chat turn.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.quiz_repository import QuizRepository
from src.services.academic.academic_calendar import current_week_for_student
from src.services.academic.self_study_service import SelfStudyService
from src.services.academic.timetable_service import TimetableService, monday_of
from src.services.ai.plan_builder import resolve_current_plan, serialize_plan
from src.services.quiz_service import QuizService

logger = logging.getLogger(__name__)


def _week_start_for(offset: int):
    from datetime import date

    return monday_of(date.today()) + timedelta(weeks=offset)


def _get_weekly_timetable(db: Session, *, student_id: str, arguments: dict) -> dict:
    offset = int(arguments.get("weeks_from_now") or 0)
    week = TimetableService(db).get_week(student_id=student_id, week_start=_week_start_for(offset))
    return {
        "weekStart": week["weekStart"],
        "weekEnd": week["weekEnd"],
        "isEmpty": week["isEmpty"],
        "sessions": [
            {
                "title": block["title"],
                "start": block["start"],
                "end": block["end"],
                "kind": block["kind"],
                "courseCode": block["courseCode"],
                "description": block["description"],
            }
            for block in week["blocks"]
        ],
    }


def _get_current_plan_tasks(db: Session, *, student_id: str, arguments: dict) -> dict:
    offset = int(arguments.get("weeks_from_now") or 0)
    week_number = current_week_for_student(db, student_id) + offset
    plan = resolve_current_plan(db, student_id=student_id, week_number=week_number)
    if plan is None:
        return {"weekNumber": week_number, "hasPlan": False, "tasks": []}
    serialized = serialize_plan(db, plan)
    return {
        "weekNumber": week_number,
        "hasPlan": True,
        "status": serialized.get("status"),
        "completionRate": serialized.get("completionRate"),
        "tasks": [
            {
                "title": task["title"],
                "status": task["status"],
                "priority": task["priority"],
                "scheduledDate": task["scheduledDate"],
            }
            for task in serialized.get("tasks", [])
        ],
    }


def _get_quiz_results(db: Session, *, student_id: str, arguments: dict) -> dict:
    del arguments
    quizzes = QuizService(QuizRepository(db)).list_for_student(student_id=student_id)
    return {
        "quizzes": [
            {
                "title": quiz["title"],
                "courseCode": quiz.get("courseCode"),
                "dueDate": quiz.get("dueDate"),
                "maxPoints": quiz.get("maxPoints"),
                "myStatus": quiz.get("myStatus"),
                "myGrade": quiz.get("myGrade"),
            }
            for quiz in quizzes
        ]
    }


def _get_risk_signals(db: Session, *, student_id: str, arguments: dict) -> dict:
    """Same query as `GET /student/risks` (student.py) -- deliberately
    drops the raw `evidence` JSON blob (internal risk-engine detail, never
    authored to be read as prose) and the instructor-only fields, keeping
    only what's safe and useful to narrate to the student."""
    del arguments
    risks = (
        db.query(models.RiskSignal)
        .filter_by(student_id=student_id)
        .order_by(models.RiskSignal.generated_at.desc())
        .all()
    )
    items = []
    for risk in risks:
        section = db.query(models.CourseSection).filter_by(id=risk.section_id).first()
        course = db.query(models.Course).filter_by(id=section.course_id).first() if section else None
        items.append(
            {
                "courseCode": getattr(course, "code", None),
                "riskType": risk.risk_type,
                "riskLevel": risk.risk_level,
                "generatedAt": risk.generated_at.isoformat() if risk.generated_at else None,
                "resolvedAt": risk.resolved_at.isoformat() if risk.resolved_at else None,
                "resolutionType": risk.resolution_type,
            }
        )
    return {"riskSignals": items}


def _get_self_study_stats(db: Session, *, student_id: str, arguments: dict) -> dict:
    offset = int(arguments.get("weeks_from_now") or 0)
    stats = SelfStudyService(db).weekly_stats(student_id=student_id, week_start=_week_start_for(offset))
    total_minutes = sum(day["minutes"] for day in stats["dailyMinutes"])
    return {"dailyMinutes": stats["dailyMinutes"], "totalMinutes": total_minutes}


_TOOLS = {
    "get_weekly_timetable": _get_weekly_timetable,
    "get_current_plan_tasks": _get_current_plan_tasks,
    "get_quiz_results": _get_quiz_results,
    "get_risk_signals": _get_risk_signals,
    "get_self_study_stats": _get_self_study_stats,
}


def execute_chat_tool(db: Session, *, student_id: str, name: str, arguments: dict) -> dict:
    handler = _TOOLS.get(name)
    if handler is None:
        return {"error": f"unknown tool: {name}"}
    try:
        return handler(db, student_id=student_id, arguments=arguments or {})
    except Exception:
        logger.exception("chat_tool_execution_failed name=%s student_id=%s", name, student_id)
        return {"error": "could not fetch this data right now"}
