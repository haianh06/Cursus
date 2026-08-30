"""Cursus Chat's two-tier answer cache (chat_cache_service.py).

Runs against the in-process memory fallback -- tests set `settings.redis_url
= None` explicitly rather than relying on the ambient test env, since the
module caches a module-level `_redis` client/`_redis_disabled` flag across
calls within a process.
"""

from __future__ import annotations

import pytest

from src.config import get_settings
from src.services.core import chat_cache_service


@pytest.fixture(autouse=True)
def _no_redis_and_clean_memory():
    settings = get_settings()
    original_url = settings.redis_url
    settings.redis_url = None
    chat_cache_service._memory.clear()
    yield
    settings.redis_url = original_url
    chat_cache_service._memory.clear()


@pytest.mark.parametrize(
    "question",
    ["Hi", "hi", "hi!", "  Hi  ", "Hii", "Hello", "Hey", "Chào", "chào bạn", "Xin chào", "Cảm ơn", "cam on ban", "ok", "Oke."],
)
def test_canned_answer_matches_common_greetings(question):
    assert chat_cache_service.canned_answer(question) is not None


@pytest.mark.parametrize(
    "question",
    ["Điều kiện qua môn SSA101 là gì?", "How do I submit my assignment?", "", "   ", "Higher order functions là gì?"],
)
def test_canned_answer_does_not_match_real_questions(question):
    # "Higher order functions" starts with "Hi" as a substring but must not
    # fold down to the bare "hi" key (exact-match only, not prefix/substring).
    assert chat_cache_service.canned_answer(question) is None


@pytest.mark.asyncio
async def test_semantic_cache_miss_when_empty():
    result = await chat_cache_service.find_similar(["CSI106"], [1.0, 0.0, 0.0])
    assert result is None


@pytest.mark.asyncio
async def test_semantic_cache_hit_after_store():
    course_codes = ["CSI106", "CEA201"]
    vector = [1.0, 0.0, 0.0]
    citations = [{"id": "c1", "title": "Syllabus"}]

    await chat_cache_service.store(course_codes, "Điều kiện qua môn là gì?", vector, "Bạn cần điểm trung bình >= 5.", citations)

    # A near-identical vector (same direction, tiny perturbation) should
    # still hit -- cosine similarity is what matters, not exact equality.
    near_identical = [0.999, 0.001, 0.0]
    hit = await chat_cache_service.find_similar(course_codes, near_identical)

    assert hit is not None
    assert hit.answer == "Bạn cần điểm trung bình >= 5."
    assert hit.citations == citations
    assert hit.similarity > 0.9


@pytest.mark.asyncio
async def test_semantic_cache_respects_similarity_threshold():
    course_codes = ["CSI106"]
    await chat_cache_service.store(course_codes, "Điều kiện qua môn là gì?", [1.0, 0.0, 0.0], "answer", [])

    # Orthogonal vector -- an unrelated question must not match.
    miss = await chat_cache_service.find_similar(course_codes, [0.0, 1.0, 0.0])
    assert miss is None


@pytest.mark.asyncio
async def test_semantic_cache_is_scoped_per_exact_course_set():
    """A cached answer must never surface for a student enrolled in a
    DIFFERENT set of courses -- its citations could reference a course that
    student never enrolled in."""
    vector = [1.0, 0.0, 0.0]
    await chat_cache_service.store(["CSI106", "CEA201"], "q", vector, "answer for CSI106+CEA201", [])

    same_set_reordered = await chat_cache_service.find_similar(["CEA201", "CSI106"], vector)
    assert same_set_reordered is not None

    different_set = await chat_cache_service.find_similar(["CSI106"], vector)
    assert different_set is None

    unrelated_set = await chat_cache_service.find_similar(["PRO192", "PRF192"], vector)
    assert unrelated_set is None


@pytest.mark.asyncio
async def test_semantic_cache_noop_without_query_vector_or_course_codes():
    assert await chat_cache_service.find_similar([], [1.0, 0.0]) is None
    assert await chat_cache_service.find_similar(["CSI106"], None) is None
    # store() must not raise and must not create an entry either.
    await chat_cache_service.store([], "q", [1.0, 0.0], "answer", [])
    await chat_cache_service.store(["CSI106"], "q", None, "answer", [])
    assert await chat_cache_service.find_similar(["CSI106"], [1.0, 0.0]) is None


@pytest.mark.asyncio
async def test_semantic_cache_disabled_via_settings():
    settings = get_settings()
    settings.chat_cache_enabled = False
    try:
        await chat_cache_service.store(["CSI106"], "q", [1.0, 0.0], "answer", [])
        assert await chat_cache_service.find_similar(["CSI106"], [1.0, 0.0]) is None
    finally:
        settings.chat_cache_enabled = True


@pytest.mark.asyncio
async def test_semantic_cache_evicts_oldest_beyond_max_entries():
    settings = get_settings()
    original_max = settings.chat_cache_max_entries_per_key
    settings.chat_cache_max_entries_per_key = 2
    try:
        await chat_cache_service.store(["CSI106"], "q1", [1.0, 0.0, 0.0], "answer1", [])
        await chat_cache_service.store(["CSI106"], "q2", [0.0, 1.0, 0.0], "answer2", [])
        await chat_cache_service.store(["CSI106"], "q3", [0.0, 0.0, 1.0], "answer3", [])

        # The oldest entry (q1's vector) should have been evicted.
        evicted = await chat_cache_service.find_similar(["CSI106"], [1.0, 0.0, 0.0])
        assert evicted is None

        still_present = await chat_cache_service.find_similar(["CSI106"], [0.0, 0.0, 1.0])
        assert still_present is not None
        assert still_present.answer == "answer3"
    finally:
        settings.chat_cache_max_entries_per_key = original_max
