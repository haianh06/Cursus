"""Non-streaming structured-JSON generation (Plan/Reflection/Practice/Quiz).
Moved from the standalone ai-service (app/domains/structured/service.py +
the /v1/structured/generate route in app/main.py) — callers already build
system_prompt/user_prompt from their own DB/retrieval context; this only
owns the LLM round-trip + schema-shaped JSON back.

`strict=False` mirrors the permissiveness LangChain's `with_structured_output`
had (optional fields, no `additionalProperties` ban) rather than OpenAI's
stricter native structured-output mode, so schemas built from Pydantic's
default `model_json_schema()` don't need reshaping.
"""
from __future__ import annotations

import json

from src.config import Settings
from src.services.core.ai_engine.client import error_code_for, model_for_route, openai_client
from src.services.core.ai_engine.routing import select_model


class AiEngineError(RuntimeError):
    """Wraps any OpenAI-call failure with the same error-code classification
    ai-service used to return over HTTP (see client.error_code_for)."""

    def __init__(self, code: str, original: Exception):
        super().__init__(code)
        self.code = code
        self.original = original


def generate_structured_sync(
    *,
    settings: Settings,
    system_prompt: str,
    user_prompt: str,
    json_schema: dict,
    schema_name: str,
    intent: str,
) -> dict:
    route = select_model(intent=intent, source_count=0, message=user_prompt)
    model = model_for_route(route, settings)
    client = openai_client(settings)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "schema": json_schema, "strict": False},
            },
        )
    except Exception as exc:
        raise AiEngineError(error_code_for(exc), exc) from exc
    return json.loads(response.choices[0].message.content)
