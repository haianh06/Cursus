"""Map semester study weeks onto ingested lecture-slide slots."""

from __future__ import annotations

import re

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
