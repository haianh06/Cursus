import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.config import Settings
from src.main import app as main_app
from src.security.exception_handlers import register_exception_handlers
from src.security.middleware import (
    CsrfProtectionMiddleware,
    RateLimitMiddleware,
    RequestContextMiddleware,
    SecurityHeadersMiddleware,
)

TEST_SECRET = "unit-test-secret-key-at-least-32-characters-long"


@pytest.mark.asyncio
async def test_security_headers_and_request_ids_on_real_app():
    transport = ASGITransport(app=main_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health", headers={"X-Request-ID": "req-test-1"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-test-1"
    assert response.headers["X-Correlation-ID"] == "req-test-1"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_env", ["development", "production"])
async def test_csrf_protection_blocks_cookie_authenticated_unsafe_request(app_env):
    app = FastAPI()
    settings = Settings(
        jwt_secret_key=TEST_SECRET,
        app_env=app_env,
        csrf_protection_enabled=True,
    )
    app.add_middleware(CsrfProtectionMiddleware, settings=settings)

    @app.post("/unsafe")
    async def unsafe():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        blocked = await client.post(
            "/unsafe",
            headers={"Cookie": f"{settings.access_token_cookie_name}=access-cookie"},
        )
        allowed = await client.post(
            "/unsafe",
            headers={
                "Cookie": (
                    f"{settings.access_token_cookie_name}=access-cookie; "
                    f"{settings.csrf_cookie_name}=csrf-value"
                ),
                settings.csrf_header_name: "csrf-value",
            },
        )
        bearer_allowed = await client.post(
            "/unsafe",
            headers={
                "Cookie": f"{settings.access_token_cookie_name}=access-cookie",
                "Authorization": "Bearer token",
            },
        )

    assert blocked.status_code == 403
    assert allowed.status_code == 200
    assert bearer_allowed.status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/demo-session", "/api/v1/auth/google-login"],
)
async def test_csrf_exempts_session_bootstrap_endpoints_even_with_a_stale_cookie(path):
    """A browser with a stale/invalid access or refresh cookie (from a
    previous, now-dead session) and no CSRF header must still be able to
    reach these bootstrap endpoints — otherwise there is no way to ever
    obtain a fresh CSRF token again (it can only come from one of these
    endpoints' own response body), permanently locking that browser out
    behind "CSRF validation failed" until it clears cookies by hand. Found
    via a live user report reproducing exactly this: a stale refresh_token
    cookie present, no CSRF header yet, POST /auth/refresh -> 403, cascading
    into demo-session also being unreachable.
    """
    app = FastAPI()
    settings = Settings(
        jwt_secret_key=TEST_SECRET,
        app_env="production",
        csrf_protection_enabled=True,
    )
    app.add_middleware(CsrfProtectionMiddleware, settings=settings)

    @app.post(path)
    async def bootstrap_endpoint():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        response = await client.post(
            path,
            headers={"Cookie": f"{settings.refresh_token_cookie_name}=stale-dead-token"},
        )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_rate_limiter_returns_429_after_limit():
    app = FastAPI()
    settings = Settings(
        jwt_secret_key=TEST_SECRET,
        redis_url=None,
        rate_limit_requests=2,
        rate_limit_window_seconds=60,
    )
    app.add_middleware(RateLimitMiddleware, settings=settings)

    @app.get("/limited")
    async def limited():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        assert (await client.get("/limited")).status_code == 200
        assert (await client.get("/limited")).status_code == 200
        limited_response = await client.get("/limited")

    assert limited_response.status_code == 429
    assert limited_response.headers["Retry-After"]


@pytest.mark.asyncio
async def test_global_exception_handler_returns_request_id():
    settings = Settings(jwt_secret_key=TEST_SECRET, cors_origins="https://cursus-mu.vercel.app")
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app, settings)

    @app.get("/boom")
    async def boom():
        raise RuntimeError("boom")

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/boom",
            headers={"X-Request-ID": "req-boom", "Origin": "https://cursus-mu.vercel.app"},
        )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Internal server error",
        "request_id": "req-boom",
    }
    # A cross-origin 500 with no Access-Control-Allow-Origin is a hard
    # network failure to the browser (fetch() rejects with no status/body
    # ever visible to JS), not a readable error -- see _apply_cors()'s
    # docstring. Found via a live user report where a real backend 500
    # showed up in the UI only as "could not connect to server".
    assert response.headers["access-control-allow-origin"] == "https://cursus-mu.vercel.app"
    assert response.headers["access-control-allow-credentials"] == "true"


@pytest.mark.asyncio
async def test_security_headers_middleware_sets_https_hsts():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/headers")
    async def headers():
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        response = await client.get("/headers")

    assert response.status_code == 200
    assert response.headers["Strict-Transport-Security"] == (
        "max-age=31536000; includeSubDomains"
    )
