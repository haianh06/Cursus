from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.domains.structured.schemas import StructuredGenerateRequest


async def generate_structured(client: AsyncOpenAI, *, model: str, request: StructuredGenerateRequest) -> dict:
    """One structured chat-completion round-trip. `strict=False` mirrors the
    permissiveness LangChain's `with_structured_output` had in backend
    (optional fields, no `additionalProperties` ban) rather than OpenAI's
    stricter native structured-output mode, so schemas built from
    Pydantic's default `model_json_schema()` don't need reshaping."""
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": request.schema_name,
                "schema": request.json_schema,
                "strict": False,
            },
        },
    )
    content = response.choices[0].message.content
    return json.loads(content)
