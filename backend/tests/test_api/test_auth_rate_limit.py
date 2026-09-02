import uuid

import pytest

import src.api.auth as auth_module


class _ProdSettings:
    """Minimal stand-in so `_enforce_rate_limit`'s app_env check treats the
    request as production -- the real per-account rate limits are skipped
    under APP_ENV=test (see tests/conftest.py) so the rest of the suite can
    log into the same seeded demo accounts repeatedly without tripping them.
    """

    app_env = "production"


@pytest.fixture
def enforce_rate_limits(monkeypatch):
    monkeypatch.setattr(auth_module, "get_settings", lambda: _ProdSettings())


@pytest.mark.asyncio
async def test_login_email_rate_limit_returns_429(client, enforce_rate_limits):
    email = f"bruteforce.{uuid.uuid4().hex}@example.test"
    limit, _window = auth_module.LOGIN_EMAIL_LIMIT

    for _ in range(limit):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_forgot_password_email_rate_limit_returns_429(client, enforce_rate_limits):
    email = f"resetflood.{uuid.uuid4().hex}@example.test"
    limit, _window = auth_module.PASSWORD_RESET_EMAIL_LIMIT

    for _ in range(limit):
        response = await client.post(
            "/api/v1/auth/password/forgot",
            json={"email": email},
        )
        assert response.status_code == 200

    response = await client.post(
        "/api/v1/auth/password/forgot",
        json={"email": email},
    )
    assert response.status_code == 429
    assert "Retry-After" in response.headers
