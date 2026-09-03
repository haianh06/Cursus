"""Landing-page chat bubble (no auth) -- src/api/public.py::landing_chat.
This widget is a fixed FAQ lookup (no LLM call ever), so these exercise the
lookup table directly, not any AI mock.
"""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_landing_chat_faq_lists_items(client):
    resp = await client.get("/api/v1/public/landing-chat/faq")
    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert items
    assert all(item["id"] and item["question"] for item in items)


@pytest.mark.asyncio
async def test_landing_chat_returns_preset_answer_for_known_question(client):
    faq = await client.get("/api/v1/public/landing-chat/faq")
    question_id = faq.json()["items"][0]["id"]

    resp = await client.post("/api/v1/public/landing-chat", json={"question_id": question_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["answer"]


@pytest.mark.asyncio
async def test_landing_chat_returns_english_answer_when_lang_en(client):
    faq = await client.get("/api/v1/public/landing-chat/faq?lang=en")
    question_id = faq.json()["items"][0]["id"]

    resp = await client.post("/api/v1/public/landing-chat", json={"question_id": question_id, "lang": "en"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["answer"]


@pytest.mark.asyncio
async def test_landing_chat_rejects_unknown_question_id(client):
    resp = await client.post("/api/v1/public/landing-chat", json={"question_id": "not-a-real-id"})
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_landing_chat_rejects_empty_question_id(client):
    resp = await client.post("/api/v1/public/landing-chat", json={"question_id": "   "})
    assert resp.status_code in (400, 422), resp.text


@pytest.mark.asyncio
async def test_landing_chat_rate_limited_after_max_per_hour(client):
    from src.api.public import LANDING_CHAT_LIMIT_PER_HOUR
    from src.services.core import rate_limiter

    faq = await client.get("/api/v1/public/landing-chat/faq")
    question_id = faq.json()["items"][0]["id"]

    # Test client has no real per-request IP variation (no proxy-header
    # middleware configured), so every call in this suite shares one
    # in-memory bucket -- reset it here so this test's count starts clean
    # regardless of what earlier tests in this file already sent.
    rate_limiter._memory.clear()

    for _ in range(LANDING_CHAT_LIMIT_PER_HOUR):
        resp = await client.post("/api/v1/public/landing-chat", json={"question_id": question_id})
        assert resp.status_code == 200, resp.text

    over_limit_resp = await client.post("/api/v1/public/landing-chat", json={"question_id": question_id})
    assert over_limit_resp.status_code == 429
