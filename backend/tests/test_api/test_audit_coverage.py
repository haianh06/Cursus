import pytest
from datetime import UTC, datetime

from src.db import models
from src.db.connection import SessionLocal


async def _login(client, email: str, password: str = "password123") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _latest_event(event_type: str):
    db = SessionLocal()
    try:
        return (
            db.query(models.AuditLog)
            .filter(models.AuditLog.event_type == event_type)
            .order_by(models.AuditLog.created_at.desc())
            .first()
        )
    finally:
        db.close()


@pytest.mark.asyncio
async def test_self_service_data_delete_is_audited(client):
    headers = await _login(client, "student.demo@example.test")

    response = await client.post("/api/v1/student/personal-data/delete", headers=headers)
    assert response.status_code == 200

    event = _latest_event("SELF_SERVICE_DATA_DELETE")
    assert event is not None
    assert event.decision == "ALLOW"
    assert event.resource_type == "STUDENT_PERSONAL_DATA"
    # Số lượng đã xoá phải nằm trong metadata — một dòng log "đã xoá" mà
    # không nói xoá bao nhiêu thì không dùng được khi đối chiếu khiếu nại.
    assert "reflectionsDeleted" in (event.metadata_info or {})


@pytest.mark.asyncio
async def test_guardrail_review_decided_is_audited(client):
    # First, we need to create a guardrail event that is BLOCKED so we can review it
    from tests.test_api.test_admin import _ensure_admin_user

    _ensure_admin_user()

    # Create a BLOCKED guardrail event via admin API (or create it directly in DB)
    db = SessionLocal()
    try:
        # Get the student
        student = db.query(models.User).filter_by(
            email="student.demo@example.test"
        ).first()

        # Create a guardrail event
        event = models.GuardrailEvent(
            id="test_event_123",
            student_id=student.id,
            classification="BLOCKED",
            safety_evaluation={"question": "Test question"},
            created_at=datetime.now(UTC).replace(tzinfo=None)
        )
        db.add(event)
        db.commit()
        event_id = event.id
    finally:
        db.close()

    # Now login as instructor and decide the guardrail review
    headers = await _login(client, "instructor.demo@example.test")

    response = await client.post(
        f"/api/v1/instructor/guardrail-reviews/{event_id}",
        headers=headers,
        json={"decision": "UNBLOCK", "note": "Appeal approved"}
    )
    assert response.status_code == 200

    event = _latest_event("GUARDRAIL_REVIEW_DECIDED")
    assert event is not None
    assert event.decision == "ALLOW"
    assert event.resource_type == "GUARDRAIL_EVENT"
    assert event.resource_id == event_id
    assert "decision" in (event.metadata_info or {})


@pytest.mark.asyncio
async def test_submit_intervention_is_audited(client):
    # First, we need to get a risk_id or create one
    from tests.test_api.test_admin import _ensure_admin_user

    _ensure_admin_user()

    # Create a risk signal
    db = SessionLocal()
    try:
        # Get the student
        student = db.query(models.User).filter_by(
            email="student.demo@example.test"
        ).first()

        # Create a risk signal with all required fields
        risk = models.RiskSignal(
            id="test_risk_123",
            student_id=student.id,
            section_id="sec_ssa101_demo",
            assignment_id=None,
            risk_type="LOW_COMPLETION",
            risk_level="MEDIUM",
            triggered_rules={"rule": "test"},
            evidence={"note": "test"},
            recommended_action="Reach out",
            generated_at=datetime.now(UTC).replace(tzinfo=None),
            resolved_at=None,
        )
        db.add(risk)
        db.commit()
        risk_id = risk.id
    finally:
        db.close()

    # Now login as instructor and submit intervention
    headers = await _login(client, "instructor.demo@example.test")

    response = await client.post(
        f"/api/v1/instructor/risks/{risk_id}/intervention",
        headers=headers,
        json={"decision": "APPROVE", "note": "Approved"}
    )
    assert response.status_code == 200

    event = _latest_event("SUBMIT_INTERVENTION")
    assert event is not None
    assert event.decision == "ALLOW"
    assert event.resource_type == "RISK_SIGNAL"
    assert event.resource_id == risk_id
    assert "decision" in (event.metadata_info or {})
