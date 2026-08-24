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
