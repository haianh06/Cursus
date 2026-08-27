"""P0#6 minimal viable version (mục 6.3/6.4 Cài đặt): self-service hard
delete of a student's own reflections. Must be scoped to the caller only --
another student's data must survive."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.db.connection import SessionLocal
from src.db.models import UserRole, WeeklyReflection
from tests.support.semester_practice_fixtures import auth_headers, ensure_org, ensure_user, login


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _seed_reflection(student_id: str, week_number: int) -> str:
    db = SessionLocal()
    try:
        row = WeeklyReflection(
            id=f"refl_{uuid.uuid4().hex[:10]}",
            student_id=student_id,
            week_number=week_number,
            content="Tuần này em học được...",
            generated_at=_now(),
            metrics={},
        )
        db.add(row)
        db.commit()
        return row.id
    finally:
        db.close()


def _count(model, **filters) -> int:
    db = SessionLocal()
    try:
        return db.query(model).filter_by(**filters).count()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_delete_my_personal_data_removes_only_the_caller_reflections(client):
    org = ensure_org("privacy-org-a", "Privacy Org A")
    target_email = f"privacy.target.{uuid.uuid4().hex}@example.test"
    other_email = f"privacy.other.{uuid.uuid4().hex}@example.test"
    target_id = ensure_user(email=target_email, org_id=org, role=UserRole.STUDENT)
    other_id = ensure_user(email=other_email, org_id=org, role=UserRole.STUDENT)

    _seed_reflection(target_id, week_number=1)
    _seed_reflection(target_id, week_number=2)

    # Another student's data must never be touched by this call.
    _seed_reflection(other_id, week_number=1)

    token = await login(client, target_email)
    resp = await client.post(
        "/api/v1/student/personal-data/delete", headers=auth_headers(token)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {"reflectionsDeleted": 2}

    assert _count(WeeklyReflection, student_id=target_id) == 0

    # The other student's rows survived untouched.
    assert _count(WeeklyReflection, student_id=other_id) == 1

    # Idempotent: nothing left for the target student, second call is a no-op.
    resp_again = await client.post(
        "/api/v1/student/personal-data/delete", headers=auth_headers(token)
    )
    assert resp_again.status_code == 200
    assert resp_again.json() == {"reflectionsDeleted": 0}
