import uuid
from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import AuditLog, GuardrailPolicyVersion, GuardrailRule, Organization, User, UserRole
from src.repositories.audit_repository import AuditRepository
from src.repositories.guardrail_rule_repository import GuardrailRuleRepository
from src.security.passwords import hash_password


@pytest.fixture(autouse=True)
def reset_guardrail_state():
    db = SessionLocal()
    try:
        db.query(AuditLog).filter_by(event_type="guardrail_rule_updated").delete()
        db.query(GuardrailPolicyVersion).delete()
        db.query(GuardrailRule).delete()
        repository = GuardrailRuleRepository(db)
        repository.ensure_seeded()
        db.commit()
    finally:
        db.close()


def _ensure_admin_user() -> None:
    """A dedicated, org-having admin -- not the shared admin.demo@example.test
    fixture, which has no organization_id (mục 9 ý2: GET /audit/events is
    org-scoped now and 404s for an org-less admin instead of silently
    showing every organization's log). Same pattern already established in
    tests/test_api/test_admin_settings.py's _ensure_org_and_admin()."""
    db = SessionLocal()
    try:
        if db.query(User).filter_by(id="admin_demo").first() is None:
            org_id = f"org_guardrail_test_{uuid.uuid4().hex[:8]}"
            db.add(
                Organization(
                    id=org_id, name="Guardrail Test Org", slug=org_id, kind="production",
                    created_at=datetime.now(UTC).replace(tzinfo=None),
                )
            )
            db.add(
                User(
                    id="admin_demo",
                    email="admin.demo@example.test",
                    password_hash=hash_password("AdminPassword123"),
                    full_name="Admin Demo",
                    role=UserRole.ADMIN.value,
                    organization_id=org_id,
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
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _admin_headers(client) -> dict[str, str]:
    _ensure_admin_user()
    return await _login(client, "admin.demo@example.test", "AdminPassword123")


async def _student_headers(client) -> dict[str, str]:
    return await _login(client, "student.demo@example.test", "password123")


@pytest.mark.asyncio
async def test_admin_lists_five_rules_enabled_by_default(client):
    """Blueprint §4.2 has 6 guardrail matrix rows; 3 are affirmatively-answered
    intents (ask_knowledge/ask_hint/feedback-on-own-work, nothing to block),
    leaving 5 blocking rule groups: graded_deliverable (HOMEWORK_VI/FULL_CODE/
    HOMEWORK_EN) plus prompt_injection and out_of_scope."""
    response = await client.get("/api/v1/admin/guardrail-rules", headers=await _admin_headers(client))

    assert response.status_code == 200
    data = response.json()["data"]
    assert [rule["code"] for rule in data["rules"]] == [
        "HOMEWORK_VI",
        "FULL_CODE",
        "HOMEWORK_EN",
        "PROMPT_INJECTION",
        "OUT_OF_SCOPE",
    ]
    # HOMEWORK_EN grew from 6 to 9 patterns 15/08/2026 after a live guardrail
    # audit found English "do it for me" phrasing that didn't say "for me"
    # right next to the verb (e.g. "...so I can submit it") slipping through —
    # see docs/PROJECT_CONTEXT.md mục 14.2.
    assert [rule["pattern_count"] for rule in data["rules"]] == [12, 5, 9, 11, 10]
    assert data["any_disabled"] is False


@pytest.mark.asyncio
async def test_student_cannot_read_or_mutate_rules(client):
    headers = await _student_headers(client)

    assert (await client.get("/api/v1/admin/guardrail-rules", headers=headers)).status_code == 403
    assert (
        await client.patch(
            "/api/v1/admin/guardrail-rules/FULL_CODE",
            json={"enabled": False},
            headers=headers,
        )
    ).status_code == 403


@pytest.mark.asyncio
async def test_admin_toggle_and_restore_are_audited(client):
    headers = await _admin_headers(client)
    toggled = await client.patch(
        "/api/v1/admin/guardrail-rules/FULL_CODE",
        json={"enabled": False},
        headers=headers,
    )
    restored = await client.post(
        "/api/v1/admin/guardrail-rules/restore-defaults",
        json={},
        headers=headers,
    )

    assert toggled.status_code == 200
    assert toggled.json()["data"]["rule"]["enabled"] is False
    assert toggled.json()["data"]["any_disabled"] is True
    assert restored.status_code == 200
    assert restored.json()["data"]["any_disabled"] is False
    events = await client.get(
        "/api/v1/audit/events?event_type=guardrail_rule_updated",
        headers=headers,
    )
    metadata = [event["metadata"] for event in events.json()]
    assert any(item.get("enabled") is False for item in metadata)
    assert any(item.get("restore_defaults") is True for item in metadata)


@pytest.mark.asyncio
async def test_unknown_rule_returns_not_found(client):
    response = await client.patch(
        "/api/v1/admin/guardrail-rules/NOT_A_RULE",
        json={"enabled": False},
        headers=await _admin_headers(client),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_core_locked_rule_cannot_be_disabled(client):
    headers = await _admin_headers(client)

    response = await client.patch(
        "/api/v1/admin/guardrail-rules/PROMPT_INJECTION",
        json={"enabled": False},
        headers=headers,
    )
    assert response.status_code == 409

    db = SessionLocal()
    try:
        rule = db.query(GuardrailRule).filter_by(code="PROMPT_INJECTION").one()
        assert rule.core_locked is True
        assert rule.enabled is True
    finally:
        db.close()


@pytest.mark.asyncio
async def test_core_locked_rule_can_still_be_re_enabled(client):
    # core_locked only blocks turning a rule OFF; re-confirming it as
    # enabled=True must not be treated as a violation.
    headers = await _admin_headers(client)

    response = await client.patch(
        "/api/v1/admin/guardrail-rules/PROMPT_INJECTION",
        json={"enabled": True},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["rule"]["enabled"] is True


@pytest.mark.asyncio
async def test_rule_change_publishes_a_policy_version_visible_in_history(client):
    headers = await _admin_headers(client)

    toggled = await client.patch(
        "/api/v1/admin/guardrail-rules/FULL_CODE",
        json={"enabled": False, "reason": "temporary rollout pause"},
        headers=headers,
    )
    assert toggled.status_code == 200
    version_after_toggle = toggled.json()["data"]["rule"]["current_version"]
    assert version_after_toggle is not None

    history = await client.get("/api/v1/admin/guardrail-rules/history", headers=headers)
    assert history.status_code == 200
    versions = history.json()["data"]["versions"]
    assert len(versions) == 1
    assert versions[0]["version"] == version_after_toggle
    assert versions[0]["is_active"] is True
    assert versions[0]["rules_snapshot"]["FULL_CODE"] is False
    assert versions[0]["change_reason"] == "temporary rollout pause"

    restored = await client.post(
        "/api/v1/admin/guardrail-rules/restore-defaults",
        json={},
        headers=headers,
    )
    assert restored.status_code == 200

    history_after_restore = await client.get(
        "/api/v1/admin/guardrail-rules/history", headers=headers
    )
    versions_after_restore = history_after_restore.json()["data"]["versions"]
    assert len(versions_after_restore) == 2
    # Newest first; the first version created is no longer active and now
    # records the version that superseded it.
    assert versions_after_restore[0]["is_active"] is True
    assert versions_after_restore[1]["is_active"] is False
    assert versions_after_restore[1]["version"] == version_after_toggle
    assert versions_after_restore[0]["source_version"] == version_after_toggle


@pytest.mark.asyncio
async def test_failed_audit_rolls_back_rule_change(client, monkeypatch):
    headers = await _admin_headers(client)

    def fail_audit(*args, **kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(AuditRepository, "add", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        await client.patch(
            "/api/v1/admin/guardrail-rules/FULL_CODE",
            json={"enabled": False},
            headers=headers,
        )

    db = SessionLocal()
    try:
        assert db.query(GuardrailRule).filter_by(code="FULL_CODE").one().enabled is True
    finally:
        db.close()
