"""ai-service endpoint coverage: internal-key auth, streaming chat relay,
and the structured-generation endpoint backend uses for Plan/Reflection/
Practice. OpenAI itself is always mocked — these tests never call out."""

from __future__ import annotations

import json

import app.main as main_module
from tests.conftest import INTERNAL_KEY


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeChatCompletion:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeChatCompletions:
    def __init__(self, content: str):
        self._content = content

    async def create(self, **kwargs):
        return _FakeChatCompletion(self._content)


class _FakeChat:
    def __init__(self, content: str):
        self.completions = _FakeChatCompletions(content)


class _FakeStreamEvent:
    def __init__(self, event_type: str, delta: str = ""):
        self.type = event_type
        self.delta = delta


class _FakeResponseStream:
    def __init__(self, deltas: list[str]):
        self._deltas = deltas

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._deltas:
            yield _FakeStreamEvent("response.output_text.delta", chunk)
        yield _FakeStreamEvent("response.completed")


class _FakeResponses:
    def __init__(self, deltas: list[str]):
        self._deltas = deltas

    async def create(self, **kwargs):
        return _FakeResponseStream(self._deltas)


class _FakeOpenAIClient:
    def __init__(self, chat_content: str = "{}", stream_deltas: list[str] | None = None, **kwargs):
        self.chat = _FakeChat(chat_content)
        self.responses = _FakeResponses(stream_deltas or [])


async def test_health_does_not_require_auth(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready"}


async def test_structured_generate_rejects_missing_key(client):
    resp = await client.post(
        "/v1/structured/generate",
        json={"system_prompt": "s", "user_prompt": "u", "json_schema": {}, "schema_name": "x", "intent": "plan_action"},
    )
    assert resp.status_code == 401


async def test_structured_generate_rejects_wrong_key(client):
    resp = await client.post(
        "/v1/structured/generate",
        headers={"x-ai-service-key": "wrong"},
        json={"system_prompt": "s", "user_prompt": "u", "json_schema": {}, "schema_name": "x", "intent": "plan_action"},
    )
    assert resp.status_code == 401


async def test_structured_generate_returns_parsed_json(client, monkeypatch):
    payload = {"tasks": [{"title": "Đọc syllabus"}]}
    monkeypatch.setattr(main_module, "AsyncOpenAI", lambda **kwargs: _FakeOpenAIClient(chat_content=json.dumps(payload)))

    resp = await client.post(
        "/v1/structured/generate",
        headers={"x-ai-service-key": INTERNAL_KEY},
        json={
            "system_prompt": "Bạn là trợ lý lập kế hoạch.",
            "user_prompt": "Tuần này em cần làm gì?",
            "json_schema": {"type": "object", "properties": {"tasks": {"type": "array"}}},
            "schema_name": "LlmPlanPayload",
            "intent": "plan_action",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"data": payload}


async def test_generate_stream_rejects_missing_key(client):
    resp = await client.post("/v1/generate/stream", json={"message": "hi", "intent": "course_fact"})
    assert resp.status_code == 401


async def test_generate_stream_emits_delta_and_done(client, monkeypatch):
    monkeypatch.setattr(main_module, "AsyncOpenAI", lambda **kwargs: _FakeOpenAIClient(stream_deltas=["Xin ", "chào"]))

    async with client.stream(
        "POST", "/v1/generate/stream",
        headers={"x-ai-service-key": INTERNAL_KEY},
        json={"message": "Xin chào Cursus", "intent": "course_fact", "context": []},
    ) as resp:
        assert resp.status_code == 200
        body = b""
        async for chunk in resp.aiter_bytes():
            body += chunk

    text = body.decode("utf-8")
    assert 'event: delta\ndata: {"text": "Xin "}' in text
    assert 'event: delta\ndata: {"text": "ch\\u00e0o"}' in text
    assert "event: done" in text


async def test_generate_stream_emits_error_event_on_provider_failure(client, monkeypatch):
    class _BoomClient:
        def __init__(self, **kwargs):
            pass

        @property
        def responses(self):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(main_module, "AsyncOpenAI", lambda **kwargs: _BoomClient())

    async with client.stream(
        "POST", "/v1/generate/stream",
        headers={"x-ai-service-key": INTERNAL_KEY},
        json={"message": "hi", "intent": "course_fact", "context": []},
    ) as resp:
        body = b""
        async for chunk in resp.aiter_bytes():
            body += chunk

    assert "event: error" in body.decode("utf-8")


def _fake_rate_limit_error(code: str | None) -> openai.RateLimitError:
    import httpx2

    request = httpx2.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx2.Response(status_code=429, request=request)
    body = {"error": {"code": code}} if code else None
    return openai.RateLimitError("rate limited", response=response, body=body)


def test_error_code_for_classifies_insufficient_quota_as_quota_exhausted():
    exc = _fake_rate_limit_error("insufficient_quota")
    assert main_module._error_code_for(exc) == "QUOTA_EXHAUSTED"


def test_error_code_for_classifies_plain_rate_limit_as_rate_limited():
    exc = _fake_rate_limit_error("rate_limit_exceeded")
    assert main_module._error_code_for(exc) == "RATE_LIMITED"


def test_error_code_for_classifies_unknown_exception_as_ai_unavailable():
    assert main_module._error_code_for(RuntimeError("boom")) == "AI_UNAVAILABLE"
