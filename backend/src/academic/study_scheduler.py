"""Pack self-study tasks into free gaps around a locked FPT timetable.

Lectures / exams stay fixed. Tasks prefer empty campus slots, then evenings,
then rest days (no class, weekend). Prep sits before the lecture when a gap
exists; otherwise the block becomes a review after class.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from src.academic.slots import CLASS_SLOT_TIMES

logger = logging.getLogger(__name__)

Interval = tuple[datetime, datetime]

STEP = timedelta(minutes=15)
BREAK_AFTER_CLASS = timedelta(minutes=10)
MIN_DURATION = 30
CLASS_DAY_CAP = 120
REST_DAY_CAP = 210
CAMPUS_SLOT_STARTS = {(h, m) for h, m, _, _ in CLASS_SLOT_TIMES.values()}


@dataclass(frozen=True)
class StudyTaskRequest:
    task_id: str
    duration_minutes: int
    phase: str = "generic"
    anchor: datetime | None = None
    priority: str = "MEDIUM"


@dataclass(frozen=True)
class Placement:
    task_id: str
    start: datetime
    end: datetime


@dataclass
class _DayLoad:
    minutes: int = 0
    blocks: int = 0


def pack_study_tasks(
    *,
    monday: date,
    occupied: list[Interval],
    locked: list[Interval] | None = None,
    tasks: list[StudyTaskRequest],
    budget_minutes: int | None = None,
) -> list[Placement]:
    """Return one non-overlapping placement per task, spread across the week."""
    if not tasks:
        return []

    busy: list[Interval] = [_naive(start, end) for start, end in occupied]
    locked_busy = [_naive(start, end) for start, end in (locked or occupied)]
    rest_days = _rest_days(monday, locked_busy)
    sized = _fit_budget(tasks, budget_minutes)
    ordered = sorted(sized, key=_task_sort_key)
    load = {monday + timedelta(days=offset): _DayLoad() for offset in range(7)}
    placements: list[Placement] = []

    for task in ordered:
        duration = max(MIN_DURATION, int(task.duration_minutes))
        placed = _place_one(
            monday=monday,
            task=task,
            duration=duration,
            busy=busy,
            rest_days=rest_days,
            load=load,
            respect_cap=True,
        )
        if placed is None:
            placed = _place_one(
                monday=monday,
                task=task,
                duration=min(duration, 45),
                busy=busy,
                rest_days=rest_days,
                load=load,
                respect_cap=False,
            )
        if placed is None:
            logger.warning("study_scheduler_unplaced task=%s", task.task_id)
            continue
        busy.append((placed.start, placed.end))
        day_load = load[placed.start.date()]
        day_load.minutes += _minutes(placed.start, placed.end)
        day_load.blocks += 1
        placements.append(placed)

    logger.info(
        "study_scheduler_packed tasks=%s placed=%s rest_days=%s",
        len(tasks),
        len(placements),
        sorted(day.isoformat() for day in rest_days),
    )
    return placements


def _place_one(
    *,
    monday: date,
    task: StudyTaskRequest,
    duration: int,
    busy: list[Interval],
    rest_days: set[date],
    load: dict[date, _DayLoad],
    respect_cap: bool,
) -> Placement | None:
    best: tuple[float, datetime, datetime] | None = None
    for start, end in _candidates(monday, duration, busy):
        day = start.date()
        if day < monday or day > monday + timedelta(days=6):
            continue
        added = _minutes(start, end)
        cap = REST_DAY_CAP if day in rest_days else CLASS_DAY_CAP
        if respect_cap and load[day].minutes + added > cap:
            continue
        score = _score(
            start=start,
            end=end,
            task=task,
            rest_days=rest_days,
            load=load[day],
        )
        if best is None or score > best[0]:
            best = (score, start, end)
    if best is None:
        return None
    _, start, end = best
    return Placement(task_id=task.task_id, start=start, end=end)


def _candidates(
    monday: date,
    duration: int,
    busy: list[Interval],
) -> Iterable[Interval]:
    span = timedelta(minutes=duration)
    padded = _pad_busy(busy)
    for offset in range(7):
        day = monday + timedelta(days=offset)
        rest = day.weekday() >= 5 or _day_is_idle(day, busy)
        for gap_start, gap_end in subtract_busy(_day_windows(day, rest), padded):
            cursor = _snap_up(gap_start)
            latest = gap_end
            while cursor + span <= latest:
                yield cursor, cursor + span
                cursor += STEP


def _day_windows(day: date, rest_day: bool) -> list[Interval]:
    if rest_day or day.weekday() >= 5:
        return [
            (_at(day, 8, 0), _at(day, 12, 0)),
            (_at(day, 13, 30), _at(day, 17, 30)),
            (_at(day, 18, 0), _at(day, 21, 30)),
        ]
    return [
        (_at(day, 7, 30), _at(day, 12, 20)),
        (_at(day, 12, 50), _at(day, 17, 40)),
        (_at(day, 18, 0), _at(day, 21, 30)),
    ]


def subtract_busy(windows: list[Interval], busy: list[Interval]) -> list[Interval]:
    """Return windows with busy intervals removed."""
    remaining = list(windows)
    for busy_start, busy_end in busy:
        next_remaining: list[Interval] = []
        for win_start, win_end in remaining:
            if busy_end <= win_start or busy_start >= win_end:
                next_remaining.append((win_start, win_end))
                continue
            if win_start < busy_start:
                next_remaining.append((win_start, busy_start))
            if busy_end < win_end:
                next_remaining.append((busy_end, win_end))
        remaining = next_remaining
    return [(start, end) for start, end in remaining if end - start >= timedelta(minutes=MIN_DURATION)]


def _score(
    *,
    start: datetime,
    end: datetime,
    task: StudyTaskRequest,
    rest_days: set[date],
    load: _DayLoad,
) -> float:
    phase = (task.phase or "generic").lower()
    score = 0.0
    if start.weekday() < 5 and (start.hour, start.minute) in CAMPUS_SLOT_STARTS:
        score += 28.0
    if start.date() in rest_days:
        score += 18.0
        if 8 <= start.hour < 18:
            score += 8.0
    elif start.hour < 18:
        score += 14.0
    else:
        score += 6.0
    if start.hour >= 21:
        score -= 22.0

    score -= load.minutes / 4.0
    score -= load.blocks * 12.0

    anchor = task.anchor
    if anchor is not None:
        if phase in {"prep", "exam"}:
            if end <= anchor:
                hours_before = (anchor - end).total_seconds() / 3600.0
                score += 55.0 - min(hours_before, 30.0)
                if phase == "exam" and 12 <= hours_before <= 48:
                    score += 12.0
            else:
                score -= 70.0
        elif phase == "review":
            if start >= anchor:
                hours_after = (start - anchor).total_seconds() / 3600.0
                score += 42.0 - min(hours_after, 24.0)
            else:
                score -= 35.0
        elif end <= anchor:
            score += 20.0
    return score


def _fit_budget(
    tasks: list[StudyTaskRequest],
    budget_minutes: int | None,
) -> list[StudyTaskRequest]:
    if not budget_minutes or budget_minutes <= 0:
        return tasks
    total = sum(max(MIN_DURATION, int(task.duration_minutes)) for task in tasks)
    if total <= budget_minutes:
        return tasks
    factor = budget_minutes / total
    fitted: list[StudyTaskRequest] = []
    for task in tasks:
        minutes = max(MIN_DURATION, int(round(task.duration_minutes * factor / 15) * 15))
        fitted.append(
            StudyTaskRequest(
                task_id=task.task_id,
                duration_minutes=minutes,
                phase=task.phase,
                anchor=task.anchor,
                priority=task.priority,
            )
        )
    return fitted


def _task_sort_key(task: StudyTaskRequest) -> tuple[int, datetime, str]:
    phase = (task.phase or "generic").lower()
    rank = 0 if phase == "exam" else 1 if task.priority.upper() == "HIGH" else 2
    anchor = task.anchor or datetime.max.replace(microsecond=0)
    return (rank, anchor, task.task_id)


def _rest_days(monday: date, locked: list[Interval]) -> set[date]:
    busy_days = {start.date() for start, _ in locked}
    days = {monday + timedelta(days=offset) for offset in range(7)}
    return {day for day in days if day.weekday() >= 5 or day not in busy_days}


def _day_is_idle(day: date, busy: list[Interval]) -> bool:
    return all(start.date() != day for start, _ in busy)


def _pad_busy(busy: list[Interval]) -> list[Interval]:
    padded: list[Interval] = []
    for start, end in busy:
        padded.append((start, end + BREAK_AFTER_CLASS))
    return padded


def _snap_up(value: datetime) -> datetime:
    minutes = value.minute
    extra = (15 - minutes % 15) % 15
    snapped = value.replace(second=0, microsecond=0) + timedelta(minutes=extra)
    return snapped


def _at(day: date, hour: int, minute: int) -> datetime:
    return datetime.combine(day, time(hour, minute))


def _minutes(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def _naive(start: datetime, end: datetime) -> Interval:
    return (start.replace(tzinfo=None), end.replace(tzinfo=None))
