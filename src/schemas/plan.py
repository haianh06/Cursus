"""Pydantic schemas for LLM-generated weekly-plan tasks (non-demo assignments only).

The Gate2 demo assignment (`gate2_demo.PART1_ASSIGNMENT_ID`) never uses this —
it keeps its hand-authored, fully deterministic task template so the rehearsed
demo path can never be destabilized by an LLM response. This schema backs the
fallback generator in `plan_builder.py` for any *other* assignment, replacing
the previous 5-task generic hardcoded template with a real, syllabus-grounded
LLM decomposition (falls back to that same generic template on any LLM error
or when no API key is configured).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LlmPlanTaskPayload(BaseModel):
    key: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=200)
    estimated_minutes: int = Field(..., ge=10, le=300)
    weekday: int = Field(..., ge=0, le=6, description="0=Monday .. 6=Sunday")
    priority: str = Field(default="MEDIUM")
    deliverable: str | None = None
    suggestion_reason: str = Field(..., min_length=1, max_length=300)
    source_chunk_ids: list[str] = Field(default_factory=list)


class LlmPlanPayload(BaseModel):
    tasks: list[LlmPlanTaskPayload] = Field(default_factory=list)
    insufficient_context: bool = False
