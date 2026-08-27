"""Generic sliding-window-ish rate limiter (fixed window, Redis-backed with
an in-process memory fallback) — same algorithm as
`src.security.middleware.RateLimitMiddleware`, extracted so call sites other
than that generic per-route/per-IP middleware (e.g. a per-student cap on
Cursus Chat, independent of the general API rate limit) can reuse it with
their own key/limit/window.
"""

from __future__ import annotations

import logging
import time

from src.config import get_settings

logger = logging.getLogger(__name__)

_memory: dict[str, tuple[int, int]] = {}
_redis = None
_redis_disabled = False


async def allow(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds)."""
    global _redis, _redis_disabled
    settings = get_settings()
    if settings.redis_url and not _redis_disabled:
        try:
            if _redis is None:
                from redis.asyncio import Redis

                _redis = Redis.from_url(settings.redis_url, decode_responses=True)
            count = await _redis.incr(key)
            if count == 1:
                await _redis.expire(key, window_seconds)
            ttl = await _redis.ttl(key)
            return count <= limit, max(int(ttl), 1)
        except Exception:
            _redis_disabled = True
            logger.warning("rate_limiter_redis_unavailable_using_memory_fallback")
    return _allow_memory(key, limit=limit, window_seconds=window_seconds)


def _allow_memory(key: str, *, limit: int, window_seconds: int) -> tuple[bool, int]:
    now = int(time.time())
    window = now // window_seconds
    count_window, count = _memory.get(key, (window, 0))
    if count_window != window:
        count_window, count = window, 0
    count += 1
    _memory[key] = (count_window, count)
    retry_after = window_seconds - (now % window_seconds)
    return count <= limit, retry_after
