from __future__ import annotations

from pydantic import BaseModel, Field


class StructuredGenerateRequest(BaseModel):
    """system_prompt/user_prompt arrive already fully built by the caller
    (backend already has the DB/retrieval context by the time it calls
    here) — this service only owns the LLM round-trip and JSON-schema
    enforcement, not prompt construction."""

    system_prompt: str = Field(min_length=1)
    user_prompt: str = Field(min_length=1)
    json_schema: dict = Field(description="JSON schema the response must satisfy (e.g. Pydantic's model_json_schema()).")
    schema_name: str = Field(default="payload", min_length=1)
    intent: str = Field(default="structured_task")


class StructuredGenerateResponse(BaseModel):
    data: dict
