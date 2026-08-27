"""Pydantic schemas for course practice sets (MCQ + flashcards)."""

# ruff: noqa: N815 -- camelCase fields to match this branch's JSON convention
# (see src/schemas/qa.py).

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PracticeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    courseCode: str = Field(..., min_length=2, max_length=32)
    # No upper bound here: callers pass raw calendar/ISO week numbers (see
    # StudentPractice.jsx), and PracticeSetService.request_for_student()
    # already clamps into the valid study-week range via clamp_study_week().
    weekNumber: int = Field(..., ge=1)
    language: str = Field(default="vi", max_length=8)


class PracticeItemOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    kind: Literal["MCQ", "FLASHCARD"]
    sortOrder: int
    prompt: str
    sourceLabel: str
    options: list[dict] | None = None
    correctKey: str | None = None
    answer: str | None = None
    explanation: str | None = None


class PracticeSetOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    courseId: str
    courseCode: str
    slideKey: str
    weekNumber: int
    status: str
    language: str
    reviewedBy: str | None = None
    reviewedAt: str | None = None
    itemCount: int
    items: list[PracticeItemOut] = Field(default_factory=list)


class PracticeItemUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prompt: str | None = None
    options: list[dict] | None = None
    correctKey: str | None = None
    answer: str | None = None
    explanation: str | None = None
    sourceLabel: str | None = None


class PracticeReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decision: Literal["PUBLISHED", "REJECTED"]
