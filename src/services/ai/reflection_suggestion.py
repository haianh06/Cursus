"""Next-week study suggestion drafted from a reflection's stats + answers.

Standalone module (no dependency on `reflection_engine.py` or `plan_builder.py`,
to avoid a circular import — both of those import this one) so `plan_builder`
and `weekly_plan_engine` can each apply the suggestion to their own task list
representation when building next week's draft from a confirmed reflection.

Best-effort like `ReflectionEngine.build_summary_llm`: returns `None` (never
raises) when no LLM is configured or the call fails, so "Tạo kế hoạch tuần
sau" never depends on an LLM call succeeding — it just skips the nudge.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.schemas.reflection import LlmReflectionSuggestionPayload
from src.services.core.llm import get_llm, has_configured_llm

logger = logging.getLogger(__name__)

REFLECTION_SUGGESTION_VERSION = "reflection_suggestion_v1"
PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "reflection_suggestion_v1.md"


def build_next_week_suggestion(
    *, facts: dict, answers: list[dict]
) -> tuple[LlmReflectionSuggestionPayload | None, dict]:
    """Returns (suggestion, trace). `suggestion` is None when no LLM is
    configured or the call fails/returns nothing usable — callers should
    treat that as "no adjustment, no insight text" and carry on unchanged."""
    trace = {"llm_attempted": False, "llm_success": False}
    if not has_configured_llm():
        return None, trace

    trace["llm_attempted"] = True
    try:
        system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
        user_prompt = f"Facts: {facts}\nStudent answers: {answers}\n"
        llm = get_llm().with_structured_output(LlmReflectionSuggestionPayload)
        payload = llm.invoke(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        if not isinstance(payload, LlmReflectionSuggestionPayload):
            payload = LlmReflectionSuggestionPayload.model_validate(payload)
        if not payload.summary.strip():
            return None, trace
        trace["llm_success"] = True
        return payload, trace
    except Exception:
        logger.exception("llm_reflection_suggestion_failed")
        return None, trace
