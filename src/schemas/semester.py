"""Pydantic schemas for student semester setup."""

# ruff: noqa: N815 -- camelCase fields to match this branch's JSON convention.

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CatalogCourse(BaseModel):
    id: str
    code: str
    name: str


class CatalogResponse(BaseModel):
    courses: list[CatalogCourse]


class SemesterStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    required: bool
    activeSemesterId: str | None = None
    termConfigured: bool = False
    term: dict | None = None


class WeekSlotIn(BaseModel):
    weekday: int = Field(ge=0, le=4)
    slot_id: int = Field(ge=1, le=6)
    course_id: str = Field(min_length=1, max_length=64)


class ExceptionIn(BaseModel):
    kind: Literal["HOLIDAY", "EXAM_WEEK"]
    start_date: date
    end_date: date
    label: str = Field(default="", max_length=120)

    @model_validator(mode="after")
    def _end_not_before_start(self) -> ExceptionIn:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class CreateSemesterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    start_date: date
    end_date: date
    course_ids: list[str] = Field(min_length=1, max_length=8)
    weekly_slots: list[WeekSlotIn] = Field(default_factory=list)
    exceptions: list[ExceptionIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> CreateSemesterRequest:
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if len(set(self.course_ids)) != len(self.course_ids):
            raise ValueError("course_ids must be unique")
        seen: set[tuple[int, int]] = set()
        allowed = set(self.course_ids)
        for slot in self.weekly_slots:
            key = (slot.weekday, slot.slot_id)
            if key in seen:
                raise ValueError("Each weekday slot can hold only one course")
            seen.add(key)
            if slot.course_id not in allowed:
                raise ValueError("Slot course must be one of the selected courses")
        return self


class GeneratedEventOut(BaseModel):
    id: str
    course_code: str
    slot_id: int
    date: str
    weekday: int
    start: str
    end: str


class SemesterOut(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: str
    is_active: bool
    course_ids: list[str]
    weekly_slots: list[dict]
    exceptions: list[dict]


class CreateSemesterResponse(SemesterOut):
    events: list[GeneratedEventOut]


class SemesterListResponse(BaseModel):
    active_id: str | None
    semesters: list[SemesterOut]
