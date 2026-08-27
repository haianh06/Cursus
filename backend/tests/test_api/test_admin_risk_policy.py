from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import User, UserRole
from src.security.passwords import hash_password
from src.services.ai.risk_engine import DEFAULT_SEVERITY_BANDS, DEFAULT_SIGNAL_THRESHOLDS, DEFAULT_SIGNAL_WEIGHTS

VALID_BANDS = [list(band) for band in DEFAULT_SEVERITY_BANDS]


def _ensure_admin_user() -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email="riskpolicy.admin@example.test").first():
            return
        db.add(
            User(
                id="riskpolicy_admin",
                email="riskpolicy.admin@example.test",
                password_hash=hash_password("AdminPassword123"),
                full_name="Risk Policy Admin",
                role=UserRole.ADMIN.value,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()


async def _login(client, email: str, password: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _admin_headers(client) -> dict[str, str]:
    _ensure_admin_user()
    return await _login(client, "riskpolicy.admin@example.test", "AdminPassword123")


@pytest.mark.asyncio
async def test_get_active_policy_returns_defaults_when_none_published_yet(client):
    headers = await _admin_headers(client)
    response = await client.get("/api/v1/admin/risk-policy", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["policyVersion"] is None
    assert body["signalWeights"] == DEFAULT_SIGNAL_WEIGHTS


@pytest.mark.asyncio
async def test_publish_requires_authentication(client):
    response = await client.post(
        "/api/v1/admin/risk-policy",
        json={
            "signalWeights": DEFAULT_SIGNAL_WEIGHTS,
            "signalThresholds": DEFAULT_SIGNAL_THRESHOLDS,
            "severityBands": VALID_BANDS,
            "reason": "no auth",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_non_admin_cannot_publish_policy(client):
    headers = await _login(client, "student.demo@example.test", "password123")
    response = await client.post(
        "/api/v1/admin/risk-policy",
        headers=headers,
        json={
            "signalWeights": DEFAULT_SIGNAL_WEIGHTS,
            "signalThresholds": DEFAULT_SIGNAL_THRESHOLDS,
            "severityBands": VALID_BANDS,
            "reason": "student trying to publish",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_publish_without_reason_is_rejected(client):
    headers = await _admin_headers(client)
    response = await client.post(
        "/api/v1/admin/risk-policy",
        headers=headers,
        json={
            "signalWeights": DEFAULT_SIGNAL_WEIGHTS,
            "signalThresholds": DEFAULT_SIGNAL_THRESHOLDS,
            "severityBands": VALID_BANDS,
            "reason": "",
        },
    )
    assert response.status_code == 422  # Pydantic min_length=1 on `reason`


@pytest.mark.asyncio
async def test_publish_rejects_out_of_bounds_weight(client):
    headers = await _admin_headers(client)
    bad_weights = dict(DEFAULT_SIGNAL_WEIGHTS, OVERDUE_TASKS_2_PLUS=-1)
    response = await client.post(
        "/api/v1/admin/risk-policy",
        headers=headers,
        json={
            "signalWeights": bad_weights,
            "signalThresholds": DEFAULT_SIGNAL_THRESHOLDS,
            "severityBands": VALID_BANDS,
            "reason": "trying a negative weight",
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_publish_then_history_then_rollback_round_trip(client):
    headers = await _admin_headers(client)

    publish_resp = await client.post(
        "/api/v1/admin/risk-policy",
        headers=headers,
        json={
            "signalWeights": DEFAULT_SIGNAL_WEIGHTS,
            "signalThresholds": DEFAULT_SIGNAL_THRESHOLDS,
            "severityBands": VALID_BANDS,
            "reason": "e2e test publish",
        },
    )
    assert publish_resp.status_code == 200
    v1 = publish_resp.json()["policyVersion"]

    tightened = dict(DEFAULT_SIGNAL_THRESHOLDS, COMPLETION_BELOW_40=0.5)
    publish2_resp = await client.post(
        "/api/v1/admin/risk-policy",
        headers=headers,
        json={
            "signalWeights": DEFAULT_SIGNAL_WEIGHTS,
            "signalThresholds": tightened,
            "severityBands": VALID_BANDS,
            "reason": "e2e test tighten threshold",
        },
    )
    assert publish2_resp.status_code == 200
    v2 = publish2_resp.json()["policyVersion"]
    assert v2 == v1 + 1

    history_resp = await client.get("/api/v1/admin/risk-policy/history", headers=headers)
    assert history_resp.status_code == 200
    versions = [row["policyVersion"] for row in history_resp.json()]
    assert v1 in versions and v2 in versions

    rollback_resp = await client.post(
        f"/api/v1/admin/risk-policy/{v1}/rollback",
        headers=headers,
        json={"reason": "e2e test rollback"},
    )
    assert rollback_resp.status_code == 200
    rolled = rollback_resp.json()
    assert rolled["policyVersion"] == v2 + 1
    assert rolled["rolledBackFrom"] == v1
    assert rolled["signalThresholds"] == DEFAULT_SIGNAL_THRESHOLDS  # back to v1's values


@pytest.mark.asyncio
async def test_rollback_to_unknown_version_is_404(client):
    headers = await _admin_headers(client)
    response = await client.post(
        "/api/v1/admin/risk-policy/999999/rollback",
        headers=headers,
        json={"reason": "does not exist"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_preview_does_not_create_a_new_version(client):
    headers = await _admin_headers(client)
    before = await client.get("/api/v1/admin/risk-policy/history", headers=headers)
    before_count = len(before.json())

    response = await client.post(
        "/api/v1/admin/risk-policy/preview",
        headers=headers,
        json={
            "signalWeights": DEFAULT_SIGNAL_WEIGHTS,
            "signalThresholds": DEFAULT_SIGNAL_THRESHOLDS,
            "severityBands": VALID_BANDS,
        },
    )
    assert response.status_code == 200
    assert "changedCount" in response.json()

    after = await client.get("/api/v1/admin/risk-policy/history", headers=headers)
    assert len(after.json()) == before_count
