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
