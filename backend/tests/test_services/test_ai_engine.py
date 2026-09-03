"""Coverage for src.services.core.ai_engine — ported from the formerly
standalone ai-service's own test suite (backend/ai-service/tests) when that
service was folded in-process. The old suite also asserted on the internal
-key HTTP auth boundary (`x-ai-service-key`) and a standalone `/health`
route; both are gone by design now that there's no separate network hop to
authenticate or probe, so those cases aren't ported. OpenAI itself is always
mocked here — these tests never call out."""

from __future__ import annotations

import json

import openai
import pytest

from src.config import Settings
from src.services.core.ai_engine import chat_stream, client as ai_client, structured
from src.services.core.ai_engine.routing import select_model


def _settings(**overrides) -> Settings:
    return Settings(openai_api_key="test-key", **overrides)


# ---- routing ----

def test_complex_intents_route_to_strong_model():
    for intent in ("course_complex", "plan_action", "reflection", "practice"):
        route = select_model(intent=intent, source_count=0, message="ngắn")
        assert route.model_env == "OPENAI_STRONG_MODEL"


def test_many_sources_route_to_strong_model():
    route = select_model(intent="course_fact", source_count=3, message="ngắn")
    assert route.model_env == "OPENAI_STRONG_MODEL"


def test_long_message_routes_to_strong_model():
    route = select_model(intent="course_fact", source_count=0, message="a" * 701)
    assert route.model_env == "OPENAI_STRONG_MODEL"


def test_simple_short_request_routes_to_light_model():
    route = select_model(intent="course_fact", source_count=1, message="ngắn")
    assert route.model_env == "OPENAI_LIGHT_MODEL"


# ---- error classification ----

def _fake_rate_limit_error(code: str | None) -> openai.RateLimitError:
    import httpx

    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=429, request=request)
    body = {"code": code} if code else None
    return openai.RateLimitError("rate limited", response=response, body=body)


def test_error_code_for_classifies_insufficient_quota_as_quota_exhausted():
    exc = _fake_rate_limit_error("insufficient_quota")
    assert ai_client.error_code_for(exc) == "QUOTA_EXHAUSTED"


def test_error_code_for_classifies_plain_rate_limit_as_rate_limited():
    exc = _fake_rate_limit_error("rate_limit_exceeded")
    assert ai_client.error_code_for(exc) == "RATE_LIMITED"


def test_error_code_for_classifies_unknown_exception_as_ai_unavailable():
    assert ai_client.error_code_for(RuntimeError("boom")) == "AI_UNAVAILABLE"


# ---- fakes for the OpenAI SDK shape used by structured/chat_stream ----

class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeChoice:
    def __init__(self, content: str):
        self.message = _FakeMessage(content)


class _FakeChatCompletion:
    def __init__(self, content: str):
        self.choices = [_FakeChoice(content)]


class _FakeStreamDelta:
    def __init__(self, content: str | None):
        self.content = content


class _FakeStreamChoice:
    def __init__(self, content: str | None):
        self.delta = _FakeStreamDelta(content)


class _FakeStreamChunk:
    def __init__(self, content: str | None):
        self.choices = [_FakeStreamChoice(content)]


class _FakeChatStream:
    def __init__(self, deltas: list[str]):
        self._deltas = deltas

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for chunk in self._deltas:
            yield _FakeStreamChunk(chunk)


class _FakeSyncChatCompletions:
    def __init__(self, content: str):
        self._content = content

    def create(self, **kwargs):
        return _FakeChatCompletion(self._content)


class _FakeAsyncChatCompletions:
    def __init__(self, stream_deltas: list[str] | None = None, error: Exception | None = None):
        self._stream_deltas = stream_deltas or []
        self._error = error

    async def create(self, **kwargs):
        if self._error:
            raise self._error
        return _FakeChatStream(self._stream_deltas)


class _FakeSyncOpenAIClient:
    def __init__(self, content: str):
        self.chat = type("Chat", (), {"completions": _FakeSyncChatCompletions(content)})()


class _FakeAsyncOpenAIClient:
    def __init__(self, stream_deltas: list[str] | None = None, error: Exception | None = None):
        self.chat = type("Chat", (), {"completions": _FakeAsyncChatCompletions(stream_deltas, error)})()


# ---- structured.generate_structured_sync ----

def test_generate_structured_sync_returns_parsed_json(monkeypatch):
    payload = {"tasks": [{"title": "Đọc syllabus"}]}
    monkeypatch.setattr(structured, "openai_client", lambda settings: _FakeSyncOpenAIClient(json.dumps(payload)))

    data = structured.generate_structured_sync(
        settings=_settings(),
        system_prompt="Bạn là trợ lý lập kế hoạch.",
        user_prompt="Tuần này em cần làm gì?",
        json_schema={"type": "object", "properties": {"tasks": {"type": "array"}}},
        schema_name="LlmPlanPayload",
        intent="plan_action",
    )
    assert data == payload


def test_generate_structured_sync_wraps_failure_with_error_code(monkeypatch):
    class _BoomClient:
        @property
        def chat(self):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(structured, "openai_client", lambda settings: _BoomClient())

    with pytest.raises(structured.AiEngineError) as exc_info:
        structured.generate_structured_sync(
            settings=_settings(), system_prompt="s", user_prompt="u",
            json_schema={}, schema_name="x", intent="plan_action",
        )
    assert exc_info.value.code == "AI_UNAVAILABLE"


# ---- chat_stream.generate_chat_stream ----

async def test_generate_chat_stream_emits_delta_and_done(monkeypatch):
    monkeypatch.setattr(chat_stream, "async_openai_client", lambda settings: _FakeAsyncOpenAIClient(stream_deltas=["Xin ", "chào"]))

    events = [event async for event in chat_stream.generate_chat_stream(
        settings=_settings(), message="Xin chào Cursus", intent="course_fact", context=[],
    )]
    assert {"type": "delta", "text": "Xin "} in events
    assert {"type": "delta", "text": "chào"} in events
    assert events[-1] == {"type": "done"}


async def test_generate_chat_stream_strips_cjk_characters_from_deltas(monkeypatch):
    # Language-drift regression: a light model occasionally code-switches
    # mid-sentence into Chinese/Japanese/Korean despite the system prompt --
    # the belt-and-suspenders filter must strip those characters rather than
    # let them reach the student.
    monkeypatch.setattr(
        chat_stream, "async_openai_client",
        lambda settings: _FakeAsyncOpenAIClient(stream_deltas=["tự", "安抚", " mình", "です", " nhé"]),
    )

    events = [event async for event in chat_stream.generate_chat_stream(
        settings=_settings(), message="an ủi bản thân thế nào", intent="course_fact", context=[],
    )]
    deltas = "".join(event["text"] for event in events if event["type"] == "delta")
    assert deltas == "tự mình nhé"


async def test_generate_chat_stream_emits_error_event_on_provider_failure(monkeypatch):
    monkeypatch.setattr(chat_stream, "async_openai_client", lambda settings: _FakeAsyncOpenAIClient(error=RuntimeError("provider unavailable")))

    events = [event async for event in chat_stream.generate_chat_stream(
        settings=_settings(), message="hi", intent="course_fact", context=[],
    )]
    assert events == [{"type": "error", "code": "AI_UNAVAILABLE"}]
