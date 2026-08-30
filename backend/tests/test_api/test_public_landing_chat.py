"""Landing-page chat bubble (no auth) -- src/api/public.py::landing_chat.
conftest.py forces has_configured_llm() False for the whole suite, so these
exercise the deterministic fallback path, not a real LLM call.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_landing_chat_returns_fallback_answer_without_llm_configured(client):
    resp = await client.post("/api/v1/public/landing-chat", json={"question": "Cursus la gi?"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"]
    assert body["generated_by_llm"] is False


@pytest.mark.asyncio
async def test_landing_chat_rejects_empty_question(client):
    resp = await client.post("/api/v1/public/landing-chat", json={"question": "   "})
    assert resp.status_code in (400, 422), resp.text


@pytest.mark.asyncio
async def test_landing_chat_rejects_question_over_max_length(client):
    resp = await client.post("/api/v1/public/landing-chat", json={"question": "a" * 501})
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_landing_chat_rate_limited_after_max_per_hour(client):
    from src.api.public import LANDING_CHAT_LIMIT_PER_HOUR
    from src.services.core import rate_limiter

    # Test client has no real per-request IP variation (no proxy-header
    # middleware configured), so every call in this suite shares one
    # in-memory bucket -- reset it here so this test's count starts clean
    # regardless of what earlier tests in this file already sent.
    rate_limiter._memory.clear()

    for i in range(LANDING_CHAT_LIMIT_PER_HOUR):
        resp = await client.post(
            "/api/v1/public/landing-chat",
            json={"question": f"Cau hoi so {i}?"},
        )
        assert resp.status_code == 200, resp.text

    over_limit_resp = await client.post(
        "/api/v1/public/landing-chat",
        json={"question": "Mot cau hoi nua"},
    )
    assert over_limit_resp.status_code == 429
