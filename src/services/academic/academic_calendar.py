"""Campus slot times + academic-term/week math shared by semester setup,
academic terms/exams, and practice-set week resolution.

Adapted from develop's `src/academic/slots.py` + `src/academic/practice.py`
(read via `git show origin/develop:...`) — kept as plain functions in
`src/services/` rather than a new top-level `src/academic` package, since
this branch has no such package and the schema/migration for this checkpoint
is meant to be final (no new modules outside repositories/services/schemas/api).
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

# slot_id -> (start_h, start_m, end_h, end_m)
SLOT_TIMES: dict[int, tuple[int, int, int, int]] = {
    1: (7, 30, 9, 0),
    2: (9, 10, 10, 40),
    3: (10, 50, 12, 20),
    4: (12, 50, 14, 20),
    5: (14, 30, 16, 0),
    6: (16, 10, 17, 40),
}


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def slot_datetimes(day: date, slot_id: int) -> tuple[datetime, datetime]:
    if slot_id not in SLOT_TIMES:
        raise ValueError("Invalid slot_id")
    start_h, start_m, end_h, end_m = SLOT_TIMES[slot_id]
    return datetime.combine(day, time(start_h, start_m)), datetime.combine(day, time(end_h, end_m))


def term_bounds(start_date: date, study_weeks: int, exam_weeks: int) -> tuple[date, date]:
    start = monday_of(start_date)
    total = max(1, study_weeks) + max(0, exam_weeks)
    end = start + timedelta(days=total * 7 - 1)
    return start, end


def exam_week_bounds(start_date: date, study_weeks: int, exam_weeks: int) -> tuple[date, date] | None:
    if exam_weeks <= 0:
        return None
    start, end = term_bounds(start_date, study_weeks, exam_weeks)
    exam_start = start + timedelta(weeks=max(0, study_weeks))
    return exam_start, end


# ── Practice-set week resolution ─────────────────────────────────────────
STUDY_WEEK_MIN = 1
STUDY_WEEK_MAX = 10
_SLOT_RE = re.compile(r"slot\s*0*(\d+)", re.IGNORECASE)


def clamp_study_week(week_number: int) -> int:
    return max(STUDY_WEEK_MIN, min(STUDY_WEEK_MAX, int(week_number)))


def semester_week_number(semester_start: date, today: date | None = None) -> int:
    """1-based week number of `today` relative to a semester's Monday-aligned
    start — the single definition of "current week" shared by the topbar,
    planner, reflection and practice screens. Do not recompute this inline
    with `date.today().isocalendar()`: that's the student's real-world
    calendar week, not the week of their semester, and the two drift apart
    within days of the semester starting.
    """
    reference = today if today is not None else date.today()
    return max(1, ((monday_of(reference) - monday_of(semester_start)).days // 7) + 1)


def get_active_semester_start(db: Session, student_id: str) -> date | None:
    """The one query for "does this student have an active semester, and
    when did it start" — every week-number helper below goes through this
    instead of re-querying `SemesterSetup`/`semester_setups` inline."""
    from src.repositories.semester_repository import SemesterRepository

    semester = SemesterRepository(db).get_active(student_id)
    return semester.start_date if semester is not None else None


def academic_week_number(db: Session, student_id: str, week_start: date) -> int:
    """Week number of `week_start` relative to the student's active semester
    when one exists, else the plain ISO week of that date. The one place
    that answers "what week is this for this student" — every read (plans,
    reflections, practice defaults) and every write (plan/timetable
    creation) must go through this, or a read using one fallback policy
    will never find a row a write created under another.
    """
    semester_start = get_active_semester_start(db, student_id)
    if semester_start is not None:
        return semester_week_number(semester_start, week_start)
    return monday_of(week_start).isocalendar().week


def current_week_for_student(db: Session, student_id: str, today: date | None = None) -> int:
    """`academic_week_number` for "today" — the one place `/plans`,
    `/student` and friends should ask "what week is it for this student
    right now", instead of each re-deriving it from
    `date.today().isocalendar()` directly.
    """
    return academic_week_number(db, student_id, today if today is not None else date.today())


def slide_key_for_week(week_number: int) -> str:
    return f"slot_{clamp_study_week(week_number):02d}"


def slot_number(value: str | int) -> int | None:
    if isinstance(value, int):
        return value if STUDY_WEEK_MIN <= value <= STUDY_WEEK_MAX else None
    match = _SLOT_RE.search(str(value or ""))
    if match is None:
        return None
    number = int(match.group(1))
    if number < STUDY_WEEK_MIN:
        return None
    return min(number, STUDY_WEEK_MAX)
