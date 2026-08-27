"""Thin HTTP client to ai-service's structured-generation endpoint.

Replaces the old `get_llm().with_structured_output(Model).invoke(messages)`
LangChain/Gemini call: backend still builds the system/user prompt strings
and still owns DB reads, retrieval, and retry heuristics — only the LLM
round-trip itself now happens in ai-service (OpenAI), reached the same way
`cursus_chat.py` already reaches it for the interactive-chat stream.
"""

from __future__ import annotations

from typing import TypeVar

import httpx
from pydantic import BaseModel

from src.config import get_settings
from src.services.core.llm_budget_service import check_and_increment_sync

ModelT = TypeVar("ModelT", bound=BaseModel)


class LlmBudgetExceededError(RuntimeError):
    """Raised instead of calling ai-service once the daily request budget
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
    """Raises on any failure (network, non-2xx, schema mismatch, daily
    budget exceeded) — callers already wrap this in their own try/except +
    `has_configured_llm()`-style fallback, exactly as they did around the
    old direct `get_llm()` call."""
    if not check_and_increment_sync():
        raise LlmBudgetExceededError("Daily ai-service request budget exceeded")
    settings = get_settings()
    response = httpx.post(
        f"{settings.ai_service_url.rstrip('/')}/v1/structured/generate",
        headers={"x-ai-service-key": settings.ai_service_internal_key or ""},
        json={
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "json_schema": schema_model.model_json_schema(),
            "schema_name": schema_name or schema_model.__name__,
            "intent": intent,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()["data"]
    return schema_model.model_validate(data)
