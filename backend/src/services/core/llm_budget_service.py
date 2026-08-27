"""Soft daily circuit-breaker on ai-service calls (chat + Plan/Reflection/
Practice/Quiz generation) — NOT a real OpenAI billing cap (this code has no
API access to OpenAI's own usage/billing endpoints, that requires a
separate admin-level key outside this codebase's scope). This only counts
how many times *this app* has asked ai-service to generate something today
and refuses further calls past a configured threshold
(`Settings.llm_daily_request_limit`), so a bug or abuse loop cannot run
unnoticed all day. An ops alert (email + log) fires once when the threshold
is first crossed for the day.

Both a sync and an async variant are provided: `ai_service_client.py`'s
`generate_structured()` is called from synchronous FastAPI route handlers
(Plan/Reflection/Practice), while `cursus_chat.py`'s streaming endpoint is
already async. Same day-keyed counter semantics either way.
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from src.config import get_settings

logger = logging.getLogger(__name__)

_memory: dict[str, int] = {}
_alerted_dates: set[str] = set()
_redis_sync = None
_redis_sync_disabled = False
_redis_async = None
_redis_async_disabled = False


def _today_key() -> str:
    return f"llm-daily-budget:{datetime.now(UTC).date().isoformat()}"


def _over_budget_memory(key: str, limit: int) -> tuple[bool, int]:
    count = _memory.get(key, 0) + 1
    _memory[key] = count
    return count <= limit, count


def check_and_increment_sync() -> bool:
    """Returns True if this call is within today's budget (and increments
    the counter either way, matching the rate-limiter's own semantics)."""
    global _redis_sync, _redis_sync_disabled
    settings = get_settings()
    key = _today_key()
    limit = settings.llm_daily_request_limit
    count: int | None = None
    if settings.redis_url and not _redis_sync_disabled:
        try:
            if _redis_sync is None:
                from redis import Redis

                _redis_sync = Redis.from_url(settings.redis_url, decode_responses=True)
            count = _redis_sync.incr(key)
            if count == 1:
                _redis_sync.expire(key, 86400)
        except Exception:
            _redis_sync_disabled = True
            logger.warning("llm_budget_redis_unavailable_using_memory_fallback")
    if count is None:
        _, count = _over_budget_memory(key, limit)
    allowed = count <= limit
    if not allowed:
        _maybe_alert(count, limit)
    return allowed


async def check_and_increment_async() -> bool:
    global _redis_async, _redis_async_disabled
    settings = get_settings()
    key = _today_key()
    limit = settings.llm_daily_request_limit
    count: int | None = None
    if settings.redis_url and not _redis_async_disabled:
        try:
            if _redis_async is None:
                from redis.asyncio import Redis

                _redis_async = Redis.from_url(settings.redis_url, decode_responses=True)
            count = await _redis_async.incr(key)
            if count == 1:
                await _redis_async.expire(key, 86400)
        except Exception:
            _redis_async_disabled = True
            logger.warning("llm_budget_redis_unavailable_using_memory_fallback")
    if count is None:
        _, count = _over_budget_memory(key, limit)
    allowed = count <= limit
    if not allowed:
        _maybe_alert(count, limit)
    return allowed


def _maybe_alert(count: int, limit: int) -> None:
    """Fire the ops alert once per day, not once per rejected request."""
    date_str = datetime.now(UTC).date().isoformat()
    if date_str in _alerted_dates:
        return
    _alerted_dates.add(date_str)
    logger.error("llm_daily_budget_exceeded count=%s limit=%s date=%s", count, limit, date_str)
    try:
        _send_ops_alert_best_effort(count=count, limit=limit, date_str=date_str)
    except Exception:
        logger.exception("llm_daily_budget_alert_email_failed")


def _send_ops_alert_best_effort(*, count: int, limit: int, date_str: str) -> None:
    """Fire-and-forget email — this module is called from both sync and
    async call sites, so it schedules the send rather than awaiting it."""
    import asyncio

    from src.config import get_settings
    from src.services.core.email_provider import build_email_service
    from src.services.core.notification_service import NotificationService

    settings = get_settings()
    to_email = settings.ops_alert_email or settings.crisis_escalation_email
    if not to_email:
        logger.warning("llm_daily_budget_exceeded_no_ops_alert_email_configured")
        return

    notification_service = NotificationService(settings, build_email_service(settings))

    async def _send() -> None:
        await notification_service.send_ops_alert(
            to_email,
            subject=f"[Cursus] Vượt ngưỡng gọi AI trong ngày ({date_str})",
            body_text=(
                f"Số lần gọi ai-service hôm nay ({count}) đã vượt ngưỡng cấu hình "
                f"({limit}). Chat và các tính năng dùng AI (Plan/Reflection/Practice/"
                f"Quiz) đang bị tạm chặn cho đến hết ngày hoặc khi ngưỡng được tăng "
                f"qua biến môi trường LLM_DAILY_REQUEST_LIMIT."
            ),
        )

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_send())
    except RuntimeError:
        asyncio.run(_send())
