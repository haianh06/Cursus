"""Pomodoro self-study sessions -- one per self-study ScheduleBlock.

A self-study block on the timetable (see TimetableService) is just a
ScheduleBlock reached through DailyPlan -> WeeklyPlan for the student; this
service owns the separate SelfStudySession row that tracks actually *running*
a Pomodoro timer against one of those blocks. The server is authoritative on
the clock/phase -- the frontend only ticks a cosmetic display between
periodic resyncs (see SelfStudySession.jsx).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db import models
from src.services import pomodoro
from src.services.academic.timetable_service import monday_of, week_bounds

REMINDER_LEAD = timedelta(minutes=10)
_TERMINAL = {"COMPLETED", "ABANDONED"}

# ScheduleBlock.start_time/end_time are naive datetimes written by the
# frontend as local wall-clock time (see Timetable.jsx's toIsoLocal(), which
# never includes a UTC offset) -- there is no per-user timezone anywhere in
# this app, only this one fixed Vietnam offset. Comparing them against
# datetime.utcnow() would shift every window check by 7 hours, so "now" for
# this service must be computed the same naive-local way.
_APP_TZ_OFFSET = timedelta(hours=7)


def _now() -> datetime:
    return datetime.utcnow() + _APP_TZ_OFFSET


class SelfStudyWindowError(ValueError):
    """The reminder window for this block hasn't opened yet, or has closed."""


class SelfStudyConflictError(ValueError):
    """This block already has a finished (terminal) session."""


@dataclass(frozen=True)
class _OwnedBlock:
    id: str
    title: str
    start: datetime
    end: datetime


class SelfStudyService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upcoming(self, *, student_id: str, now: datetime | None = None) -> list[dict]:
        moment = now or _now()
        monday = monday_of(moment.date())
        start, end = week_bounds(monday)
        blocks = self._self_study_blocks_in_range(student_id=student_id, start=start, end=end)

        items: list[dict] = []
        for block in blocks:
            open_at = block.start - REMINDER_LEAD
            if not (open_at <= moment < block.end):
                continue
            session = self._session_for_block(student_id=student_id, block_id=block.id)
            items.append(
                {
                    "blockId": block.id,
                    "title": block.title,
                    "start": block.start.isoformat(),
                    "end": block.end.isoformat(),
                    "canStart": session is None or session.status not in _TERMINAL,
                    "sessionId": session.id if session else None,
                }
            )
        return items

    def weekly_stats(self, *, student_id: str, week_start: date | None = None, now: datetime | None = None) -> dict:
        moment = now or _now()
        monday = monday_of(week_start or moment.date())
        start, end = week_bounds(monday)
        sessions = (
            self._db.query(models.SelfStudySession)
            .filter(
                models.SelfStudySession.student_id == student_id,
                models.SelfStudySession.started_at >= start,
                models.SelfStudySession.started_at < end,
            )
            .all()
        )
        daily_minutes = {(monday + timedelta(days=i)).isoformat(): 0 for i in range(7)}
        for session in sessions:
            self._finalize_if_due(session, moment)
            if session.status not in _TERMINAL:
                continue
            day_key = session.started_at.date().isoformat()
            if day_key in daily_minutes:
                daily_minutes[day_key] += session.actual_minutes or 0
        self._db.commit()
        return {"dailyMinutes": [{"date": d, "minutes": m} for d, m in daily_minutes.items()]}

    def active(self, *, student_id: str, now: datetime | None = None) -> dict | None:
        session = (
            self._db.query(models.SelfStudySession)
            .filter_by(student_id=student_id, status="IN_PROGRESS")
            .order_by(models.SelfStudySession.started_at.desc())
            .first()
        )
        if not session:
            return None
        self._finalize_if_due(session, now or _now())
        self._db.commit()
        return self._to_payload(session, now or _now())

    def start(self, *, student_id: str, block_id: str, now: datetime | None = None) -> dict:
        moment = now or _now()
        block = self._owned_block(student_id=student_id, block_id=block_id)

        existing = self._session_for_block(student_id=student_id, block_id=block_id)
        if existing:
            self._finalize_if_due(existing, moment)
            self._db.commit()
            if existing.status in _TERMINAL:
                raise SelfStudyConflictError("This block already has a finished session")
            return self._to_payload(existing, moment)

        if moment < block.start - REMINDER_LEAD:
            raise SelfStudyWindowError("This session hasn't opened yet")
        if moment >= block.end:
            raise SelfStudyWindowError("This session has ended")

        planned = max(1, int((block.end - block.start).total_seconds() // 60))
        scheduled_end = min(moment + timedelta(minutes=planned), block.end)
        session = models.SelfStudySession(
            id=f"sss_{uuid.uuid4().hex[:10]}",
            student_id=student_id,
            schedule_block_id=block.id,
            title=block.title,
            planned_minutes=planned,
            started_at=moment,
            scheduled_end_at=scheduled_end,
            status="IN_PROGRESS",
            pomodoros_completed=0,
        )
        self._db.add(session)
        try:
            self._db.commit()
        except IntegrityError:
            # Two concurrent "start" calls raced on the unique
            # schedule_block_id constraint -- adopt whichever row won.
            self._db.rollback()
            winner = self._session_for_block(student_id=student_id, block_id=block_id)
            if not winner:
                raise
            self._finalize_if_due(winner, moment)
            self._db.commit()
            if winner.status in _TERMINAL:
                raise SelfStudyConflictError("This block already has a finished session") from None
            return self._to_payload(winner, moment)

        self._db.refresh(session)
        return self._to_payload(session, moment)

    def get_session(self, *, student_id: str, session_id: str, now: datetime | None = None) -> dict:
        moment = now or _now()
        session = self._owned_session(student_id=student_id, session_id=session_id)
        self._finalize_if_due(session, moment)
        self._db.commit()
        return self._to_payload(session, moment)

    def abandon(self, *, student_id: str, session_id: str, now: datetime | None = None) -> dict:
        moment = now or _now()
        session = self._owned_session(student_id=student_id, session_id=session_id)
        if session.status not in _TERMINAL:
            if moment >= session.scheduled_end_at:
                self._close(session, status="COMPLETED", ended_at=session.scheduled_end_at)
            else:
                self._close(session, status="ABANDONED", ended_at=moment)
        self._db.commit()
        return self._to_payload(session, moment)

    # ── internals ────────────────────────────────────────────────────────

    def _owned_block(self, *, student_id: str, block_id: str) -> _OwnedBlock:
        row = (
            self._db.query(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(
                models.ScheduleBlock.id == block_id,
                models.WeeklyPlan.student_id == student_id,
            )
            .first()
        )
        if not row:
            raise LookupError("Self-study block not found")
        return _OwnedBlock(id=row.id, title=row.activity_description, start=row.start_time, end=row.end_time)

    def _owned_session(self, *, student_id: str, session_id: str) -> models.SelfStudySession:
        session = (
            self._db.query(models.SelfStudySession)
            .filter_by(id=session_id, student_id=student_id)
            .first()
        )
        if not session:
            raise LookupError("Self-study session not found")
        return session

    def _session_for_block(self, *, student_id: str, block_id: str) -> models.SelfStudySession | None:
        return (
            self._db.query(models.SelfStudySession)
            .filter_by(student_id=student_id, schedule_block_id=block_id)
            .first()
        )

    def _self_study_blocks_in_range(self, *, student_id: str, start: datetime, end: datetime) -> list[_OwnedBlock]:
        rows = (
            self._db.query(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(
                models.WeeklyPlan.student_id == student_id,
                models.ScheduleBlock.cancelled_at.is_(None),
                models.ScheduleBlock.start_time >= start,
                models.ScheduleBlock.start_time < end,
            )
            .all()
        )
        return [
            _OwnedBlock(id=row.id, title=row.activity_description, start=row.start_time, end=row.end_time)
            for row in rows
        ]

    def _finalize_if_due(self, session: models.SelfStudySession, moment: datetime) -> None:
        if session.status == "IN_PROGRESS" and moment >= session.scheduled_end_at:
            self._close(session, status="COMPLETED", ended_at=session.scheduled_end_at)

    def _close(self, session: models.SelfStudySession, *, status: str, ended_at: datetime) -> None:
        remaining = (session.scheduled_end_at - session.started_at).total_seconds()
        elapsed = min((ended_at - session.started_at).total_seconds(), remaining)
        session.status = status
        session.ended_at = ended_at
        session.actual_minutes = int(elapsed // 60)
        snapshot = pomodoro.snapshot_at(elapsed, max(0.0, remaining - elapsed))
        session.pomodoros_completed = snapshot.pomodoros_completed

    def _to_payload(self, session: models.SelfStudySession, moment: datetime) -> dict:
        if session.status in _TERMINAL:
            end_ref = session.ended_at or session.scheduled_end_at
            elapsed = max(0.0, (end_ref - session.started_at).total_seconds())
            session_remaining = 0.0
            snapshot = pomodoro.PomodoroSnapshot(
                phase="done", phase_remaining_seconds=0, pomodoros_completed=session.pomodoros_completed
            )
        else:
            elapsed = max(0.0, (moment - session.started_at).total_seconds())
            session_remaining = max(0.0, (session.scheduled_end_at - moment).total_seconds())
            snapshot = pomodoro.snapshot_at(elapsed, session_remaining)
            session.pomodoros_completed = snapshot.pomodoros_completed

        return {
            "id": session.id,
            "status": session.status,
            "phase": snapshot.phase,
            "phaseRemainingSeconds": snapshot.phase_remaining_seconds,
            "sessionRemainingSeconds": int(session_remaining),
            "title": session.title,
            "pomodorosCompleted": session.pomodoros_completed,
            "actualMinutes": session.actual_minutes,
        }
