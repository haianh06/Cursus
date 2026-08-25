"""Pydantic schema for the LLM-drafted reflection summary (preview only).

Used exclusively by `ReflectionEngine.build_summary_llm`, which backs
`POST /student/reflections/preview-summary` — the student always sees and can
edit this text before anything is persisted (Blueprint §3.1). `save_reflection`
never calls the LLM path; its fallback stays the deterministic
`ReflectionEngine.build_summary` so a saved reflection can never depend on an
LLM call succeeding.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class LlmReflectionSummaryPayload(BaseModel):
    summary: str = Field(..., min_length=1, max_length=1200)


class LlmReflectionSuggestionPayload(BaseModel):
    """Next-week study suggestion drafted from this week's stats + the
    student's 5 self-feedback answers + free-text note (see
    `src/services/ai/reflection_suggestion.py`). Bounded so a bad/creative
    LLM output can never blow up a plan's schedule: the multiplier only ever
    nudges task durations within +/-30%, never rewrites task identity."""

    summary: str = Field(..., min_length=1, max_length=600)
    estimated_minutes_multiplier: float = Field(default=1.0, ge=0.7, le=1.3)
