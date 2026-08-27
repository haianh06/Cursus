"""Structured-generation entry point used across the codebase.

Replaces the old `get_llm().with_structured_output(Model).invoke(messages)`
LangChain/Gemini call: callers still build the system/user prompt strings
and still own DB reads, retrieval, and retry heuristics — only the LLM
round-trip itself happens here, in `src.services.core.ai_engine` (OpenAI).
That used to be a separate HTTP hop to a standalone ai-service; ai-service
was folded into this same process so a single Render deploy only needs one
service, and this call is now in-process. Kept as a thin wrapper (not a
straight call to ai_engine from each of the ~8 call sites) so none of them
had to change: same name, same signature, same sync call shape.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from src.config import get_settings
from src.services.core.ai_engine.structured import generate_structured_sync
from src.services.core.llm_budget_service import check_and_increment_sync

ModelT = TypeVar("ModelT", bound=BaseModel)


class LlmBudgetExceededError(RuntimeError):
    """Raised instead of calling ai_engine once the daily request budget
    (Settings.llm_daily_request_limit) is used up. Every existing caller
    already wraps this call in a broad try/except + deterministic fallback
    (the same shape used when no LLM key was configured at all), so this
    degrades the same way rather than needing new handling per call site."""


def generate_structured(
    *,
    schema_model: type[ModelT],
    system_prompt: str,
    user_prompt: str,
    intent: str,
    schema_name: str | None = None,
    timeout: float = 60.0,
) -> ModelT:
    """Raises on any failure (LLM call, schema mismatch, daily budget
    exceeded) — callers already wrap this in their own try/except +
    `has_configured_llm()`-style fallback, exactly as they did around the
    old direct `get_llm()` call. `timeout` is accepted for interface
    compatibility with the old HTTP client's signature; the OpenAI SDK
    manages its own request timeout internally."""
    del timeout
    if not check_and_increment_sync():
        raise LlmBudgetExceededError("Daily ai-service request budget exceeded")
    data = generate_structured_sync(
        settings=get_settings(),
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        json_schema=schema_model.model_json_schema(),
        schema_name=schema_name or schema_model.__name__,
        intent=intent,
    )
    return schema_model.model_validate(data)
