"""Draft weekly study tasks from a student's timetable sessions (lecture-driven).

Second, independent plan-generation flow that coexists with Gate 2's
assignment-driven ``PlanBuilder`` (`src/services/plan_builder.py`). It must
never be confused for a Gate 2 plan:

* ``WeeklyPlan.goals`` is tagged ``{"source": "lecture_plan", ...}`` — no
  ``assignment_id`` key at all, so `plan_builder.is_study_plan` still returns
  ``True`` for these rows but every place that *ranks* candidate plans for "the
  current plan" (`src/api/plans.py::_resolve_plan`,
  `src/api/student.py::_resolve_plan_for_reflection`) scores an
  ``assignment_id``-bearing Gate 2 plan higher, so a lecture plan can never
  outrank a real Gate 2 plan for the same week.
* `src/services/timetable_service.py`'s self-study block queries explicitly
  skip rows tagged ``source == "lecture_plan"`` so these tasks never bleed
  into Gate 2's timetable/self-study rendering.

Adapted from develop's `src/services/lecture_plan_service.py` (see
``git show origin/develop:src/services/lecture_plan_service.py``), but ported
to this branch's semester/timetable data model:

* develop resolved the active semester via ``TimetableService._active_semester``
  (a private method that does not exist on this branch) — here it comes from
  ``SemesterRepository.get_active(student_id)``.
* develop built the week from ``TimetableService.get_week()`` blocks — here
  the week is built directly from ``SemesterWeekSlot`` (recurring weekly
  class blocks) plus ``CourseExamSession`` rows whose date falls in the
  target week, using the shared date/time helpers in
  ``src/services/academic_calendar.py``.
* develop's task generator grounded titles in retrieved syllabus chunks via
  RAG. This simplified version skips retrieval and just generates a "review
  before" + "practice after" task pair per class session (a single "revise"
  task per exam session), which keeps the feature self-contained and cheap.
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.academic_term_repository import AcademicTermRepository
from src.repositories.semester_repository import SemesterRepository
from src.services.academic.academic_calendar import (
    SLOT_TIMES,
    monday_of,
    semester_week_number,
    slot_datetimes,
)
from src.services.core import provenance as prov

LECTURE_PLAN_SOURCE = "lecture_plan"
"""``WeeklyPlan.goals["source"]`` tag for plans this service creates. Was a
bare string literal repeated in 5 call sites across this file, api/lecture_plan.py,
and services/academic/timetable_service.py -- now imported everywhere instead
so a future rename/typo can't silently split into "two different sources"."""

logger = logging.getLogger(__name__)

PLANNER_VERSION = "lecture_plan_v1"
MAX_TASKS = 7
REVIEW_BEFORE_MINUTES = 30
PRACTICE_AFTER_MINUTES = 30
EXAM_REVISE_MINUTES = 60


class LecturePlanService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._semesters = SemesterRepository(db)
        self._terms = AcademicTermRepository(db)

    def generate(
        self,
        *,
        student_id: str,
        organization_id: str | None,
        week_start: date | None,
        available_hours: float,
        language: str = "vi",
    ) -> models.WeeklyPlan:
        semester = self._semesters.get_active(student_id)
        if semester is None:
            raise LookupError(
                "No active semester set up yet. Set up your semester schedule first."
            )

        monday = monday_of(week_start or date.today())
        week_end = monday + timedelta(days=6)

        sessions = self._week_sessions(semester, organization_id, monday, week_end)
        if not sessions:
            raise ValueError("No class or exam sessions found in this week")

        specs = self._task_specs(sessions, language)
        warnings: list[str] = []
        if len(specs) > MAX_TASKS:
            warnings.append("More tasks than the 7-task cap; extra sessions were dropped.")
        specs = specs[:MAX_TASKS]

        vi = language.lower().startswith("vi")
        week_number = semester_week_number(semester.start_date, monday)
        course_count = len({item["course_code"] for item in sessions})
        statement = (
            f"Ôn và chuẩn bị theo {len(sessions)} buổi học/thi tuần {week_number}"
            if vi
            else f"Prep and review for {len(sessions)} class/exam sessions in week {week_number}"
        )

        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        capacity_minutes = int(round(max(0.0, float(available_hours or 0)) * 60))
        planned_minutes = sum(spec["minutes"] for spec in specs)

        plan = models.WeeklyPlan(
            id=plan_id,
            student_id=student_id,
            week_number=int(week_number),
            goals={
                "source": LECTURE_PLAN_SOURCE,
                "status": "DRAFT",
                "week_start": monday.isoformat(),
                "semester_id": semester.id,
                "planner_version": PLANNER_VERSION,
                "statement": statement,
                "capacity_minutes": capacity_minutes,
                "planned_minutes": planned_minutes,
                "language": language,
                "course_count": course_count,
                "provenance": prov.ai_suggested(PLANNER_VERSION),
                "task_meta": {},
            },
            study_hours_allocated=round(capacity_minutes / 60.0, 2),
        )
        self._db.add(plan)
        self._db.flush()

        task_meta: dict[str, dict] = {}
        for spec in specs:
            daily_id = f"dp_{uuid.uuid4().hex[:8]}"
            block_id = f"sb_{uuid.uuid4().hex[:8]}"
            task_id = f"task_{uuid.uuid4().hex[:8]}"

            self._db.add(
                models.DailyPlan(
                    id=daily_id,
                    weekly_plan_id=plan_id,
                    date=datetime.combine(spec["day"], datetime.min.time()),
                    status="TODO",
                )
            )
            self._db.add(
                models.ScheduleBlock(
                    id=block_id,
                    daily_plan_id=daily_id,
                    start_time=spec["start"],
                    end_time=spec["start"] + timedelta(minutes=spec["minutes"]),
                    activity_description=spec["title"],
                )
            )
            self._db.add(
                models.StudyTask(
                    id=task_id,
                    schedule_block_id=block_id,
                    assignment_id=None,
                    title=spec["title"],
                    planned_minutes=spec["minutes"],
                    actual_minutes=None,
                    priority=spec["priority"],
                    status="TODO",
                    difficulty="MEDIUM",
                    rescheduled_count=0,
                )
            )
            task_meta[task_id] = {
                "key": spec["key"],
                "scheduled_date": spec["day"].isoformat(),
                "course_code": spec["course_code"],
                "phase": spec["phase"],
                "suggestion_reason": spec["reason"],
                "provenance": prov.ai_suggested(PLANNER_VERSION),
                "estimate_provenance": prov.ai_suggested(PLANNER_VERSION),
            }

        goals = dict(plan.goals)
        goals["task_meta"] = task_meta
        plan.goals = goals
        self._db.commit()

        logger.info(
            "lecture_plan_drafted id=%s student=%s semester=%s sessions=%s tasks=%s",
            plan_id,
            student_id,
            semester.id,
            len(sessions),
            len(specs),
        )
        return plan

    # ── week assembly ─────────────────────────────────────────────────
    def _week_sessions(
        self,
        semester: models.SemesterSetup,
        organization_id: str | None,
        monday: date,
        week_end: date,
    ) -> list[dict[str, Any]]:
        course_ids = [link.course_id for link in self._semesters.list_course_links(semester.id)]
        courses: dict[str, models.Course] = {}
        if course_ids:
            # A course could have been removed from the org catalog since the
            # student linked it; fall back to the raw id as the display code
            # rather than raising, since a missing course must never block
            # plan generation for the rest of the week's sessions.
            try:
                resolved = self._semesters.get_courses_by_ids(course_ids, organization_id)
            except LookupError:
                resolved = (
                    self._db.query(models.Course)
                    .filter(models.Course.id.in_(course_ids))
                    .all()
                )
            courses = {course.id: course for course in resolved}

        sessions: list[dict[str, Any]] = []

        for slot in self._semesters.list_week_slots(semester.id):
            if slot.slot_id not in SLOT_TIMES:
                continue
            day = monday + timedelta(days=slot.weekday)
            if day < monday or day > week_end:
                continue
            if day < semester.start_date or day > semester.end_date:
                continue
            start, end = slot_datetimes(day, slot.slot_id)
            course = courses.get(slot.course_id)
            sessions.append(
                {
                    "kind": "CLASS",
                    "course_id": slot.course_id,
                    "course_code": course.code if course else slot.course_id,
                    "day": day,
                    "slot_start": start,
                    "slot_end": end,
                }
            )

        exam_rows = self._terms.sessions_in_range_for_courses(course_ids, monday, week_end)
        for exam_session, exam in exam_rows:
            if exam_session.slot_id not in SLOT_TIMES:
                continue
            start, end = slot_datetimes(exam_session.exam_date, exam_session.slot_id)
            course = courses.get(exam.course_id)
            sessions.append(
                {
                    "kind": f"EXAM_{exam.kind}",
                    "course_id": exam.course_id,
                    "course_code": course.code if course else exam.course_id,
                    "day": exam_session.exam_date,
                    "slot_start": start,
                    "slot_end": end,
                }
            )

        sessions.sort(key=lambda item: (item["day"], item["slot_start"]))
        return sessions

    def _task_specs(
        self, sessions: list[dict[str, Any]], language: str
    ) -> list[dict[str, Any]]:
        vi = language.lower().startswith("vi")
        specs: list[dict[str, Any]] = []
        for session in sessions:
            code = session["course_code"]
            day_label = session["day"].strftime("%d/%m")
            if session["kind"].startswith("EXAM"):
                revise_day = session["day"] - timedelta(days=1)
                specs.append(
                    {
                        "key": f"exam_{code}_{session['day'].isoformat()}",
                        "course_code": code,
                        "day": revise_day,
                        "start": datetime.combine(revise_day, datetime.min.time()).replace(
                            hour=19, minute=0
                        ),
                        "minutes": EXAM_REVISE_MINUTES,
                        "priority": "HIGH",
                        "phase": "review",
                        "title": (
                            f"Ôn thi {code} · {day_label}"
                            if vi
                            else f"Revise for {code} exam · {day_label}"
                        ),
                        "reason": (
                            "Ôn tập trước kỳ thi giúp giảm áp lực phút chót."
                            if vi
                            else "Reviewing ahead of the exam avoids last-minute cramming."
                        ),
                    }
                )
                continue

            specs.append(
                {
                    "key": f"prep_{code}_{session['day'].isoformat()}",
                    "course_code": code,
                    "day": session["day"],
                    "start": session["slot_start"] - timedelta(minutes=REVIEW_BEFORE_MINUTES),
                    "minutes": REVIEW_BEFORE_MINUTES,
                    "priority": "MEDIUM",
                    "phase": "prep",
                    "title": (
                        f"Ôn bài trước buổi {code} · {day_label}"
                        if vi
                        else f"Review before {code} class · {day_label}"
                    ),
                    "reason": (
                        "Ôn nhanh trước buổi học giúp theo kịp bài giảng."
                        if vi
                        else "A quick review before class makes the lecture easier to follow."
                    ),
                }
            )
            specs.append(
                {
                    "key": f"practice_{code}_{session['day'].isoformat()}",
                    "course_code": code,
                    "day": session["day"],
                    "start": session["slot_end"] + timedelta(minutes=15),
                    "minutes": PRACTICE_AFTER_MINUTES,
                    "priority": "MEDIUM",
                    "phase": "practice",
                    "title": (
                        f"Luyện tập sau buổi {code} · {day_label}"
                        if vi
                        else f"Practice after {code} class · {day_label}"
                    ),
                    "reason": (
                        "Luyện tập ngay sau buổi học giúp củng cố kiến thức."
                        if vi
                        else "Practicing right after class reinforces what you just learned."
                    ),
                }
            )
        return specs
