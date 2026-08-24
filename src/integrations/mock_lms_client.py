"""OAuth client_credentials client for the Mock LMS REST API (mục 6.6).

Deliberately talks to Mock LMS only over HTTP with its own bearer token -- no
shared DB, no shared auth. Token is cached in-process and refetched a little
before it actually expires; a 401 on a data call also triggers exactly one
refetch-and-retry, in case the token was revoked/rotated out from under us.
"""
from __future__ import annotations

import time

import httpx

from src.config import get_settings


class MockLmsClientError(RuntimeError):
    """Raised for any Mock LMS integration failure (auth, network, bad response)."""


class MockLmsClient:
    def __init__(self, *, base_url: str | None = None, client_id: str | None = None,
                 client_secret: str | None = None, timeout: float = 10.0) -> None:
        settings = get_settings()
        self._base_url = (base_url or settings.mock_lms_base_url).rstrip("/")
        self._client_id = client_id or settings.mock_lms_client_id
        self._client_secret = client_secret or settings.mock_lms_client_secret
        self._timeout = timeout
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def _ensure_credentials(self) -> None:
        if not self._client_id or not self._client_secret:
            raise MockLmsClientError(
                "MOCK_LMS_CLIENT_ID/MOCK_LMS_CLIENT_SECRET not configured -- "
                "run mock-lms/scripts/create_oauth_client.py and set them."
            )

    def _fetch_token(self) -> str:
        self._ensure_credentials()
        try:
            resp = httpx.post(
                f"{self._base_url}/oauth/token",
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise MockLmsClientError(f"Mock LMS unreachable at {self._base_url}: {exc}") from exc
        if resp.status_code != 200:
            raise MockLmsClientError(f"Mock LMS OAuth token request failed: {resp.status_code} {resp.text}")
        payload = resp.json()
        self._token = payload["access_token"]
        # Refresh a bit early so an in-flight request never races an expiring token.
        self._token_expires_at = time.monotonic() + payload["expires_in"] - 30
        return self._token

    def _get_token(self) -> str:
        if self._token is None or time.monotonic() >= self._token_expires_at:
            return self._fetch_token()
        return self._token

    def _get(self, path: str, *, retried: bool = False) -> httpx.Response:
        token = self._get_token()
        try:
            resp = httpx.get(
                f"{self._base_url}{path}",
                headers={"Authorization": f"Bearer {token}"},
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise MockLmsClientError(f"Mock LMS unreachable at {self._base_url}: {exc}") from exc
        if resp.status_code == 401 and not retried:
            self._token = None  # force a fresh token, then retry exactly once
            return self._get(path, retried=True)
        if resp.status_code != 200:
            raise MockLmsClientError(f"Mock LMS request to {path} failed: {resp.status_code} {resp.text}")
        return resp

    def list_courses(self) -> list[dict]:
        return self._get("/api/v1/courses").json()

    def list_assignments(self, course_code: str) -> list[dict]:
        return self._get(f"/api/v1/courses/{course_code}/assignments").json()
