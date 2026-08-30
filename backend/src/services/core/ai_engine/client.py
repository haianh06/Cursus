"""OpenAI-compatible client + shared error classification for ai_engine.

Moved from the standalone ai-service (app/main.py) when that service was
folded into backend as an in-process module (single Render service instead
of two, so there's only one instance that can cold-start). Two client
builders exist because callers split the same way they did in ai-service:
`stream_chat_generate` (cursus_chat.py's `/stream` route, already async) uses
the async client; `generate_structured_sync` is called from plain sync
functions across the codebase (plan_builder, quiz_generator, etc. — none of
them `await` it) and uses the sync client so it keeps blocking the same way
the old httpx.post() call already did, without having to convert every
caller's call chain to async.
"""
from __future__ import annotations

import openai
from openai import AsyncOpenAI, OpenAI

from src.config import Settings
from src.services.core.ai_engine.routing import ModelRoute

# Địa chỉ mặc định của OpenAI, khai tường minh chứ không để SDK tự suy.
#
# Vì sao không truyền `base_url=None` cho SDK tự lo: `config.py` gọi
# `load_dotenv()`, nên MỌI dòng trong `.env` được xuất ra `os.environ` — kể cả
# `OPENAI_BASE_URL=` bỏ trống, thành biến môi trường có tồn tại với giá trị là
# chuỗi rỗng. Nhận `base_url=None`, SDK quay ra đọc `os.environ` đúng biến đó,
# thấy `""` và dùng luôn làm địa chỉ. Kết quả: mọi request bắn vào URL rỗng và
# trả `APIConnectionError: Connection error` — trông y hệt mất mạng, trong khi
# khoá, model và đường truyền đều bình thường.
#
# Đây đúng là cấu hình mà `.env.example` hướng dẫn cho người dùng OpenAI thật
# ("để trống nếu dùng thẳng OpenAI"), nên nếu không chốt cứng ở đây thì đường
# đi mặc định của tài liệu là đường hỏng.
_DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"


def _base_url(settings: Settings) -> str:
    return (settings.openai_base_url or "").strip() or _DEFAULT_OPENAI_BASE_URL


def openai_client(settings: Settings) -> OpenAI:
    return OpenAI(
        api_key=settings.openai_api_key or "",
        base_url=_base_url(settings),
        timeout=settings.llm_request_timeout_seconds,
    )


def async_openai_client(settings: Settings) -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key or "",
        base_url=_base_url(settings),
        timeout=settings.llm_request_timeout_seconds,
    )


def model_for_route(route: ModelRoute, settings: Settings) -> str:
    return getattr(settings, route.model_env.lower())


def error_code_for(exc: Exception) -> str:
    """Distinguishes the handful of failure modes backend/frontend actually
    show a different message for (see cursus_chat.py's SSE relay and
    CursusChat.jsx) from a generic "AI is down" -- rather than collapsing
    every OpenAI failure into one AI_UNAVAILABLE code."""
    if isinstance(exc, openai.RateLimitError):
        # openai's APIError.__init__ already extracts `.code` from the
        # response body for us (`insufficient_quota` vs the generic
        # `rate_limit_exceeded`) -- no need to re-parse `exc.body` here.
        if getattr(exc, "code", None) == "insufficient_quota":
            return "QUOTA_EXHAUSTED"
        return "RATE_LIMITED"
    if isinstance(exc, openai.AuthenticationError | openai.PermissionDeniedError):
        # A bad/missing OPENAI_API_KEY -- distinct from a real OpenAI outage
        # so ops alerting (and manual QA) can tell "we misconfigured the
        # secret" apart from "the provider is down".
        return "AI_MISCONFIGURED"
    if isinstance(exc, openai.APIConnectionError | openai.APITimeoutError):
        return "AI_UNAVAILABLE"
    return "AI_UNAVAILABLE"
