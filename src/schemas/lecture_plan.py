"""Pydantic schemas for the lecture-driven weekly plan endpoint.

Independent of Gate 2's plan schemas (`src/schemas/plan.py`) — this backs
`src/services/lecture_plan_service.py` / `src/api/lecture_plan.py`, a second
plan-generation flow keyed off a student's timetable sessions rather than an
assignment. The response reuses `plan_builder.serialize_plan`'s generic
``WeeklyPlan``/``DailyPlan``/``ScheduleBlock``/``StudyTask`` shape, so no
separate response schema is declared here — routes return that dict as-is.
"""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class LecturePlanGenerateRequest(BaseModel):
    week_start: date | None = Field(
        default=None, description="Monday of the target week; defaults to the current week."
    )
    available_hours: float = Field(default=6.0, ge=0, le=80)
    language: str = Field(default="vi", max_length=8)
