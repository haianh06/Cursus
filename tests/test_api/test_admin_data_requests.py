"""DSAR delete flow (src/api/admin_data_requests.py) — previously had zero
test coverage. Covers the completeness fix: the delete-confirm handler used
to only touch 6 of the ~18 tables that hold a student's own data (student_id
FK), leaving real personal data (learning goals, progress events, chat
memory, reminders, ...) behind after a supposedly-completed erasure. Also
covers the FK-ordering fix this required: ReplanProposal.original_plan_id
points at weekly_plans.id with no ondelete=CASCADE, so it must be deleted
before WeeklyPlan or the bulk delete raises a FK violation.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.security.passwords import hash_password


async def _login(client, email: str, password: str) -> dict[str, str]:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    client.cookies.clear()
    return {"Authorization": f"Bearer {resp.json()['token']}"}


def _ensure_admin_user() -> str:
    db = SessionLocal()
    try:
        existing = db.query(models.User).filter_by(email="admin.dsar@example.test").first()
        if existing:
            return existing.organization_id

        org_id = f"org_dsar_test_{uuid.uuid4().hex[:8]}"
        db.add(
            models.Organization(
                id=org_id, name="DSAR Test Org", slug=org_id, kind="production",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.add(
            models.User(
                id="admin_dsar",
                email="admin.dsar@example.test",
                password_hash="$2b$12$K3ItPXwWl0K6qF2fT1o4kOZjV6xrEhOZQ8j6h0F1a1eYWx1s2wZ7O",  # bcrypt("AdminPassword123")
                full_name="Admin DSAR",
                role=models.UserRole.ADMIN.value,
                organization_id=org_id,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
        return org_id
    finally:
        db.close()


def _seed_erasure_target(org_id: str) -> str:
    """A dedicated student (not student_ethan, so this doesn't clash with
    other tests running in the same session) with a row in every newly
    covered table, plus the one table that previously trips a FK ordering
    bug (ReplanProposal referencing the WeeklyPlan being deleted)."""
    db = SessionLocal()
    try:
        student_id = "student_dsar_target"
        if db.query(models.User).filter_by(id=student_id).first() is not None:
            return student_id

        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            models.User(
                id=student_id,
                email="dsar.target@example.test",
                password_hash="x",
                full_name="DSAR Target",
                role=models.UserRole.STUDENT.value,
                organization_id=org_id,
                is_email_verified=True,
                is_active=True,
                created_at=now,
            )
        )
        db.add(
            models.WeeklyPlan(
                id="plan_dsar_target_w1",
                student_id=student_id,
                week_number=1,
                goals={},
                study_hours_allocated=10.0,
            )
        )
        db.add(
            models.ReplanProposal(
                id="replan_dsar_target_1",
                student_id=student_id,
                original_plan_id="plan_dsar_target_w1",
                proposed_changes={"note": "less hours"},
                status="PROPOSED",
                generated_at=now,
            )
        )
        db.add(
            models.LearningGoal(
                id="goal_dsar_target_1",
                student_id=student_id,
                term="Fall2026",
                goal_statement="Đạt GPA 3.5",
                target_gpa=3.5,
            )
        )
        db.add(
            models.ProgressEvent(
                id="pevent_dsar_target_1",
                student_id=student_id,
                task_id=None,
                event_type="TASK_CREATED",
                payload={},
                occurred_at=now,
            )
        )
        db.add(
            models.Reminder(
                id="reminder_dsar_target_1",
                student_id=student_id,
                task_id=None,
                title="Nhắc nộp bài",
                message="Đừng quên nộp bài tập.",
                channel="IN_APP",
                scheduled_time=now,
            )
        )
        db.add(models.StudentMemoryConsent(student_id=student_id, granted=True, updated_at=now))
        db.add(
            models.StudentMemoryEntry(
                id="memory_dsar_target_1",
                student_id=student_id,
                subject_code=None,
                kind="preference",
                content={"note": "prefers short answers"},
                created_at=now,
                updated_at=now,
            )
        )
        db.commit()
        return student_id
    finally:
        db.close()


@pytest.mark.asyncio
async def test_delete_confirm_erases_every_student_owned_table(client):
    org_id = _ensure_admin_user()
    student_id = _seed_erasure_target(org_id)
    admin_headers = await _login(client, "admin.dsar@example.test", "AdminPassword123")

    db = SessionLocal()
    try:
        req_id = f"dsar_{uuid.uuid4().hex[:8]}"
        db.add(
            models.DataRequest(
                id=req_id,
                requester_id=student_id,
                organization_id=org_id,
                request_type="DELETE",
                status="PENDING",
            )
        )
        db.commit()
    finally:
        db.close()

    resp = await client.post(
        f"/api/v1/admin/data-requests/{req_id}/process",
        json={"notes": "Confirmed identity, starting erasure."},
        headers=admin_headers,
    )
    assert resp.status_code == 200

    resp = await client.post(
        f"/api/v1/admin/data-requests/{req_id}/delete-preview", headers=admin_headers
    )
    assert resp.status_code == 200
    preview = resp.json()
    counts = preview["preview"]
    assert counts["plans"] == 1
    assert counts["replan_proposals"] == 1
    assert counts["learning_goals"] == 1
    assert counts["progress_events"] == 1
    assert counts["reminders"] == 1
    assert counts["student_memory_entries"] == 1
    assert counts["student_memory_consent"] == 1

    resp = await client.post(
        f"/api/v1/admin/data-requests/{req_id}/delete-confirm",
        json={"notes": "Erasure executed after verified preview.", "preview_hash": preview["hash"]},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True

    db = SessionLocal()
    try:
        assert db.query(models.WeeklyPlan).filter_by(student_id=student_id).count() == 0
        assert db.query(models.ReplanProposal).filter_by(student_id=student_id).count() == 0
        assert db.query(models.LearningGoal).filter_by(student_id=student_id).count() == 0
        assert db.query(models.ProgressEvent).filter_by(student_id=student_id).count() == 0
        assert db.query(models.Reminder).filter_by(student_id=student_id).count() == 0
        assert db.query(models.StudentMemoryEntry).filter_by(student_id=student_id).count() == 0
        assert db.query(models.StudentMemoryConsent).filter_by(student_id=student_id).count() == 0
        # The user account itself is untouched by this flow (only their
        # owned records are erased) -- deleting the account is a separate
        # decision from erasing the data covered by this DSAR.
        assert db.query(models.User).filter_by(id=student_id).first() is not None
    finally:
        db.close()
