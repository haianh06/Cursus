"""Pomodoro timing constants + phase computation, shared by SelfStudyService
and the frontend timer display it feeds."""

from __future__ import annotations

from dataclasses import dataclass

WORK_SECONDS = 25 * 60
SHORT_BREAK_SECONDS = 5 * 60
LONG_BREAK_SECONDS = 15 * 60
LONG_BREAK_EVERY = 4  # every 4th work period gets the long break


@dataclass(frozen=True)
class PomodoroSnapshot:
    phase: str  # work | break | long_break | done
    phase_remaining_seconds: int
    pomodoros_completed: int


def snapshot_at(elapsed_seconds: float, session_remaining_seconds: float) -> PomodoroSnapshot:
    """Walk the work/break cycle from t=0 to figure out the current phase.

    `session_remaining_seconds` caps how far the cycle can run -- once the
    scheduled block itself is out of time, we report "done" regardless of
    where in the work/break cycle the elapsed time would otherwise land.
    """
    if session_remaining_seconds <= 0:
        return PomodoroSnapshot(phase="done", phase_remaining_seconds=0, pomodoros_completed=0)

    remaining = max(0.0, elapsed_seconds)
    pomodoros_completed = 0
    cycle_index = 0

    while True:
        work_remaining = WORK_SECONDS - remaining
        if work_remaining > 0:
            return PomodoroSnapshot(
                phase="work",
                phase_remaining_seconds=int(work_remaining),
                pomodoros_completed=pomodoros_completed,
            )
        remaining -= WORK_SECONDS
        pomodoros_completed += 1
        cycle_index += 1

        break_length = LONG_BREAK_SECONDS if cycle_index % LONG_BREAK_EVERY == 0 else SHORT_BREAK_SECONDS
        break_remaining = break_length - remaining
        if break_remaining > 0:
            phase = "long_break" if cycle_index % LONG_BREAK_EVERY == 0 else "break"
            return PomodoroSnapshot(
                phase=phase,
                phase_remaining_seconds=int(break_remaining),
                pomodoros_completed=pomodoros_completed,
            )
        remaining -= break_length
