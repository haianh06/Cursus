"""FPT campus slots: class (2h20) vs exam (90 minutes). Never mix the two."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Literal

SlotKind = Literal["class", "exam"]

# Ca học — 4 tiết / ~2h20, nghỉ trưa 12:20–12:50.
CLASS_SLOT_TIMES: dict[int, tuple[int, int, int, int]] = {
    1: (7, 30, 9, 50),
    2: (10, 0, 12, 20),
    3: (12, 50, 15, 10),
    4: (15, 20, 17, 40),
}

# Ca thi — 90 phút, nghỉ 10 phút, nghỉ trưa giữa ca 3 và 4.
EXAM_SLOT_TIMES: dict[int, tuple[int, int, int, int]] = {
    1: (7, 30, 9, 0),
    2: (9, 10, 10, 40),
    3: (10, 50, 12, 20),
    4: (12, 50, 14, 20),
    5: (14, 30, 16, 0),
    6: (16, 10, 17, 40),
}


def slot_table(kind: SlotKind) -> dict[int, tuple[int, int, int, int]]:
    if kind == "exam":
        return EXAM_SLOT_TIMES
    if kind == "class":
        return CLASS_SLOT_TIMES
    raise ValueError("kind must be 'class' or 'exam'")


def slot_labels(kind: SlotKind) -> list[dict[str, str | int]]:
    return [
        {
            "id": slot_id,
            "start": f"{times[0]:02d}:{times[1]:02d}",
            "end": f"{times[2]:02d}:{times[3]:02d}",
        }
        for slot_id, times in slot_table(kind).items()
    ]


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def slot_datetimes(day: date, slot_id: int, *, kind: SlotKind) -> tuple[datetime, datetime]:
    table = slot_table(kind)
    if slot_id not in table:
        raise ValueError("Invalid slot_id")
    start_h, start_m, end_h, end_m = table[slot_id]
    start = datetime.combine(day, time(start_h, start_m))
    end = datetime.combine(day, time(end_h, end_m))
    return start, end


def wall_clock_iso(value: datetime) -> str:
    """Serialize as Asia/Ho_Chi_Minh wall clock — never append Z / UTC offset."""
    naive = value.replace(tzinfo=None) if value.tzinfo is not None else value
    return naive.strftime("%Y-%m-%dT%H:%M:%S")


def campus_now() -> datetime:
    """Current time as naive Asia/Ho_Chi_Minh wall clock (matches timetable storage)."""
    from zoneinfo import ZoneInfo

    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).replace(tzinfo=None)


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
