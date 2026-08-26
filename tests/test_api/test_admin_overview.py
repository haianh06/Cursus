import pytest

from tests.test_api.test_admin import _ensure_admin_user


@pytest.mark.asyncio
async def test_admin_overview_requires_admin_role(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.demo@example.test", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/overview", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_overview_returns_school_pulse_and_work_queue(client):
    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/overview", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["system_status"] in {"HEALTHY", "DEGRADED"}
    assert "active_students" in data["school_pulse"]
    assert "active_instructors" in data["school_pulse"]
    assert "unresolved_risk" in data["school_pulse"]
    assert "invitation_activation" in data["school_pulse"]
    assert isinstance(data["work_queue"]["items"], list)
    assert isinstance(data["recent_critical_changes"], list)


@pytest.mark.asyncio
async def test_admin_work_queue_endpoint(client):
    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/work-queue", headers=headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["items"], list)


@pytest.mark.asyncio
async def test_llm_quota_status_requires_admin_role(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.demo@example.test", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/llm-quota-status", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_llm_quota_status_reflects_recorded_events(client):
    """Gemini gives no way to query remaining quota ahead of a call, so this
    endpoint is purely reactive -- confirms a real recorded 429 shows up."""
    from src.services.core.llm_quota_service import record_quota_event

    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/llm-quota-status", headers=headers)
    assert resp.status_code == 200, resp.text
    before = resp.json()["countInWindow"]

    record_quota_event(model="gemini-3.6-flash", source="test_admin_overview")

    resp = await client.get("/api/v1/admin/llm-quota-status", headers=headers)
    data = resp.json()
    assert data["countInWindow"] == before + 1
    assert data["lastModel"] == "gemini-3.6-flash"
    assert data["lastSource"] == "test_admin_overview"
    assert data["lastExhaustedAt"] is not None


@pytest.mark.asyncio
async def test_admin_overview_never_shows_fabricated_zero_percent_with_no_denominator(client):
    """A rate metric with a zero denominator must report `value: null`, not
    a misleading `0.0` -- see admin_overview_service._metric()."""
    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/overview", headers=headers)
    activation = resp.json()["school_pulse"]["invitation_activation"]
    if activation["denominator"] == 0:
        assert activation["value"] is None
