import hmac
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.config import Settings
from src.security.request_context import correlation_id_var, request_id_var

logger = logging.getLogger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Session-bootstrap endpoints: a client can legitimately call these with a
# stale/expired auth cookie still present but no CSRF token yet (that token
# can only ever be *obtained* from one of these same endpoints' response
# body — see auth.py's `csrf_token` field). Requiring a CSRF header here is
# a deadlock, not a defense: forging a cross-site call to one of these only
# gets an attacker a session *they already control* (login CSRF), not access
# to the victim's data, since the response is never visible to the attacker
# page. Real CSRF protection still applies to every other authenticated,
# state-changing endpoint once a session exists.
CSRF_EXEMPT_PATHS = {
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/auth/demo-session",
    "/api/v1/auth/google-login",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        correlation_id = request.headers.get("x-correlation-id") or request_id
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        token_request = request_id_var.set(request_id)
        token_correlation = correlation_id_var.set(correlation_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request_completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "elapsed_ms": elapsed_ms,
                },
            )
            request_id_var.reset(token_request)
            correlation_id_var.reset(token_correlation)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Cache-Control", "no-store")
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )
        return response


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if self._should_enforce(request) and not self._is_valid_csrf(request):
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "detail": "CSRF validation failed",
                    "request_id": getattr(request.state, "request_id", None),
                },
            )
        return await call_next(request)

    def _should_enforce(self, request: Request) -> bool:
        # Enforce whenever the flag is on — including shared staging with
        # APP_ENV=development. Bearer clients (Vite demo) are exempt; cookie
        # session clients must send the double-submit CSRF header.
        if not self._settings.csrf_protection_enabled:
            return False
        if request.method in SAFE_METHODS:
            return False
        if request.headers.get("authorization", "").startswith("Bearer "):
            return False
        if request.url.path in CSRF_EXEMPT_PATHS:
            return False
        return any(
            cookie_name in request.cookies
            for cookie_name in (
                self._settings.access_token_cookie_name,
                self._settings.refresh_token_cookie_name,
                self._settings.mfa_trusted_device_cookie_name,
            )
        )

    def _is_valid_csrf(self, request: Request) -> bool:
        cookie_token = request.cookies.get(self._settings.csrf_cookie_name)
        header_token = request.headers.get(self._settings.csrf_header_name)
        if not cookie_token or not header_token:
            return False
        return hmac.compare_digest(cookie_token, header_token)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings
        self._memory: dict[str, tuple[int, int]] = {}
        self._redis = None
        self._redis_disabled = False

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if not self._settings.rate_limit_enabled or request.url.path == "/health":
            return await call_next(request)

        allowed, retry_after = await self._allow_request(request)
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests",
                    "request_id": getattr(request.state, "request_id", None),
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)

    async def _allow_request(self, request: Request) -> tuple[bool, int]:
        key = self._rate_limit_key(request)
        if self._settings.redis_url and not self._redis_disabled:
            try:
                return await self._allow_request_redis(key)
            except Exception:
                self._redis_disabled = True
                logger.warning("Redis rate limiter unavailable; using memory fallback")
        return self._allow_request_memory(key)

    async def _allow_request_redis(self, key: str) -> tuple[bool, int]:
        if self._redis is None:
            from redis.asyncio import Redis

            self._redis = Redis.from_url(self._settings.redis_url, decode_responses=True)
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self._settings.rate_limit_window_seconds)
        ttl = await self._redis.ttl(key)
        retry_after = max(int(ttl), 1)
        return count <= self._settings.rate_limit_requests, retry_after

    def _allow_request_memory(self, key: str) -> tuple[bool, int]:
        now = int(time.time())
        window = now // self._settings.rate_limit_window_seconds
        count_window, count = self._memory.get(key, (window, 0))
        if count_window != window:
            count_window, count = window, 0
        count += 1
        self._memory[key] = (count_window, count)
        retry_after = self._settings.rate_limit_window_seconds - (
            now % self._settings.rate_limit_window_seconds
        )
        return count <= self._settings.rate_limit_requests, retry_after

    def _rate_limit_key(self, request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        client_ip = (
            forwarded_for.split(",", 1)[0].strip()
            if forwarded_for
            else request.client.host if request.client else "unknown"
        )
        return f"rate-limit:{client_ip}:{request.method}:{request.url.path}"
