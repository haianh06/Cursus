"""Two-tier answer cache for Cursus Chat, so a repeat/near-duplicate question
skips retrieval and the LLM call entirely.

- **Canned answers** (``canned_answer``): exact-match, after light
  normalization, against a small fixed set of context-free small talk
  (greetings, thanks, "who are you"). Zero cost -- no embedding call, no
  Redis round trip, no DB query. This alone covers the reported "even 'Hi'
  takes 15-20s" case, since a plain greeting used to still run full RAG
  retrieval (one Gemini embedding call per enrolled course) before ever
  reaching the LLM.

- **Semantic FAQ cache** (``find_similar`` / ``store``): Redis-backed (with
  an in-process memory fallback, same pattern as ``rate_limiter.py``),
  looked up by cosine similarity against the question's embedding -- which
  the caller (cursus_chat.py's ``_context()``) already computes once for
  retrieval, so a cache hit/miss check costs no extra network call either
  way. Scoped per the **exact set** of the asking student's enrolled course
  codes (never per-individual-course, never global) so a cached answer's
  citations can never reference a course the asking student isn't enrolled
  in -- two students who share the identical course load (the common case
  for a fixed-schedule cohort) transparently share cache entries; a student
  enrolled in a different combination never sees another cohort's answer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass

from src.config import get_settings
from src.services.rag.embedding_service import cosine_similarity
from src.services.rag.query_normalization import fold_accents

logger = logging.getLogger(__name__)

_memory: dict[str, list[dict]] = {}
_redis = None
_redis_disabled = False


# ── Tier 1: canned answers ────────────────────────────────────────────────
# Keys are accent-stripped, lowercased, trailing punctuation removed --
# matches however `_candidates()`-style folding is done elsewhere in this
# codebase (guardrail_service.py, query_normalization.py) so "Chào!",
# "chao", and "CHÀO" all hit the same entry.
_CANNED_ANSWERS: dict[str, str] = {
    "hi": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "hii": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "hello": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "hey": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "chao": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "chao ban": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "xin chao": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "chao cursus": "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, hoặc cách dùng app đều được.",
    "cam on": "Không có gì đâu, còn cần mình giúp gì nữa không?",
    "cam on ban": "Không có gì đâu, còn cần mình giúp gì nữa không?",
    "cam on nhe": "Không có gì đâu, còn cần mình giúp gì nữa không?",
    "thanks": "You're welcome! Anything else I can help with?",
    "thank you": "You're welcome! Anything else I can help with?",
    "ok": "Ok bạn nhé, cứ hỏi mình bất cứ lúc nào.",
    "oke": "Ok bạn nhé, cứ hỏi mình bất cứ lúc nào.",
    "ban la ai": "Mình là Cursus — trợ lý học tập giúp bạn hiểu tài liệu môn học, lập kế hoạch tuần và tự đánh giá.",
    "ban la gi": "Mình là Cursus — trợ lý học tập giúp bạn hiểu tài liệu môn học, lập kế hoạch tuần và tự đánh giá.",
    "ban giup duoc gi": (
        "Mình giúp được: giải thích nội dung môn học theo tài liệu đã học, "
        "gợi ý cách bắt đầu bài tập (không làm hộ), và điều hướng tới kế "
        "hoạch tuần hoặc phần tự đánh giá."
    ),
    "who are you": (
        "I'm Cursus — your study assistant for explaining course material, "
        "getting unstuck on assignments (with hints, not answers), and "
        "your weekly plan or reflection."
    ),
}

_TRAILING_PUNCT_RE = re.compile(r"[!.?,~\s]+$")


def canned_answer(question: str) -> str | None:
    key = fold_accents((question or "").strip().lower())
    key = _TRAILING_PUNCT_RE.sub("", key).strip()
    return _CANNED_ANSWERS.get(key)


# ── Tier 2: semantic FAQ cache ────────────────────────────────────────────
@dataclass(frozen=True)
class CachedAnswer:
    answer: str
    citations: list[dict]
    similarity: float
    suggestions: list[str]


def _cache_key(course_codes: list[str]) -> str:
    canonical = ",".join(sorted(code.strip().upper() for code in course_codes if code))
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()[:16]
    return f"chat_semantic_cache:{digest}"


async def _get_redis():
    global _redis, _redis_disabled
    settings = get_settings()
    if not settings.redis_url or _redis_disabled:
        return None
    try:
        if _redis is None:
            from redis.asyncio import Redis

            _redis = Redis.from_url(settings.redis_url, decode_responses=True)
        return _redis
    except Exception:
        _redis_disabled = True
        logger.warning("chat_cache_redis_unavailable_using_memory_fallback")
        return None


async def _read_entries(key: str) -> list[dict]:
    global _redis_disabled
    redis = await _get_redis()
    if redis is not None:
        try:
            raw = await redis.lrange(key, 0, -1)
            return [json.loads(item) for item in raw]
        except Exception:
            # A reachability failure here (not just a bad key) means every
            # future call this process makes would otherwise pay the same
            # connect-timeout cost -- disable Redis for the rest of the
            # process's lifetime, same as _get_redis()'s own construction
            # failure branch, so this stays a cache-speed-up, never a
            # latency regression when Redis is briefly unavailable.
            _redis_disabled = True
            logger.warning("chat_cache_redis_read_failed_falling_back_to_memory")
    return list(_memory.get(key, []))


async def _append_entry(key: str, entry: dict, *, max_entries: int, ttl_seconds: int) -> None:
    global _redis_disabled
    redis = await _get_redis()
    if redis is not None:
        try:
            await redis.rpush(key, json.dumps(entry))
            await redis.ltrim(key, -max_entries, -1)
            await redis.expire(key, ttl_seconds)
            return
        except Exception:
            _redis_disabled = True
            logger.warning("chat_cache_redis_write_failed_falling_back_to_memory")
    bucket = _memory.setdefault(key, [])
    bucket.append(entry)
    del bucket[: -max_entries or len(bucket)]


async def find_similar(
    course_codes: list[str], query_vector: list[float] | None
) -> CachedAnswer | None:
    settings = get_settings()
    if not settings.chat_cache_enabled or not query_vector or not course_codes:
        return None
    entries = await _read_entries(_cache_key(course_codes))
    best_entry: dict | None = None
    best_similarity = 0.0
    for entry in entries:
        vector = entry.get("embedding")
        if not vector:
            continue
        similarity = cosine_similarity(query_vector, vector)
        if similarity > best_similarity:
            best_similarity, best_entry = similarity, entry
    if best_entry is not None and best_similarity >= settings.chat_cache_similarity_threshold:
        return CachedAnswer(
            answer=best_entry["answer"],
            citations=best_entry.get("citations") or [],
            similarity=best_similarity,
            suggestions=best_entry.get("suggestions") or [],
        )
    return None


async def store(
    course_codes: list[str],
    question: str,
    query_vector: list[float] | None,
    answer: str,
    citations: list[dict],
    suggestions: list[str] | None = None,
) -> None:
    settings = get_settings()
    if not settings.chat_cache_enabled or not query_vector or not course_codes or not answer:
        return
    entry = {
        "question": (question or "")[:500],
        "embedding": query_vector,
        "answer": answer,
        "citations": citations,
        "suggestions": suggestions or [],
        "cached_at": time.time(),
    }
    try:
        await _append_entry(
            _cache_key(course_codes),
            entry,
            max_entries=settings.chat_cache_max_entries_per_key,
            ttl_seconds=settings.chat_cache_ttl_seconds,
        )
    except Exception:
        # Caching is a pure optimization -- never fail the actual chat
        # response because writing to the cache afterward broke.
        logger.exception("chat_cache_store_failed")
