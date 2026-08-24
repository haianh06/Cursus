"""Tests for the Student Memory feature (consent + entry management only —
see src/services/ai/student_memory_service.py module docstring for why this
deliberately does NOT wire into the live QA/companion answer pipeline)."""

from __future__ import annotations

import uuid

import pytest

from src.db.connection import SessionLocal
from src.db.models import UserRole
from src.services.ai.student_memory_service import StudentMemoryService
from tests.support.semester_practice_fixtures import auth_headers, ensure_org, ensure_user, login


@pytest.mark.asyncio
async def test_consent_defaults_to_false_and_can_be_toggled(client):
    org = ensure_org("mem-org-a", "Memory Org A")
    email = f"mem.student.a.{uuid.uuid4().hex}@example.test"
    ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    initial = await client.get("/api/v1/student/memory/consent", headers=auth_headers(token))
    assert initial.status_code == 200
    assert initial.json() == {"granted": False}

    granted = await client.put(
        "/api/v1/student/memory/consent", headers=auth_headers(token), json={"granted": True}
    )
    assert granted.status_code == 200
    assert granted.json() == {"granted": True}

    confirm = await client.get("/api/v1/student/memory/consent", headers=auth_headers(token))
    assert confirm.json() == {"granted": True}


@pytest.mark.asyncio
async def test_withdrawing_consent_hard_deletes_entries(client):
    org = ensure_org("mem-org-b", "Memory Org B")
    email = f"mem.student.b.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    await client.put("/api/v1/student/memory/consent", headers=auth_headers(token), json={"granted": True})

    db = SessionLocal()
    try:
        service = StudentMemoryService(db)
        service.record_updates(
            student_id=student_id,
            subject_code="SSA101",
            conversation_id=None,
            updates=[{"kind": "weak_topic", "content": "Struggles with recursion"}],
        )
    finally:
        db.close()

    listed = await client.get("/api/v1/student/memory", headers=auth_headers(token))
    assert len(listed.json()["entries"]) == 1

    await client.put("/api/v1/student/memory/consent", headers=auth_headers(token), json={"granted": False})

    after_withdraw = await client.get("/api/v1/student/memory", headers=auth_headers(token))
    assert after_withdraw.json()["entries"] == []


@pytest.mark.asyncio
async def test_record_updates_is_a_noop_without_consent(client):
    org = ensure_org("mem-org-c", "Memory Org C")
    email = f"mem.student.c.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=email, org_id=org, role=UserRole.STUDENT)

    db = SessionLocal()
    try:
        service = StudentMemoryService(db)
        applied = service.record_updates(
            student_id=student_id,
            subject_code="SSA101",
            conversation_id=None,
            updates=[{"kind": "preference", "content": "Prefers short answers"}],
        )
        assert applied == []
        assert service.list_entries(student_id) == []
    finally:
        db.close()


@pytest.mark.asyncio
async def test_repeated_similar_fact_reinforces_instead_of_duplicating(client):
    org = ensure_org("mem-org-d", "Memory Org D")
    email = f"mem.student.d.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=email, org_id=org, role=UserRole.STUDENT)

    db = SessionLocal()
    try:
        service = StudentMemoryService(db)
        service.set_consent(student_id, True)
        service.record_updates(
            student_id=student_id, subject_code=None, conversation_id=None,
            updates=[{"kind": "preference", "content": "Prefers short answers"}],
        )
        service.record_updates(
            student_id=student_id, subject_code=None, conversation_id=None,
            updates=[{"kind": "preference", "content": "  prefers   SHORT answers  "}],
        )
        entries = service.list_entries(student_id)
        assert len(entries) == 1
        assert entries[0]["reinforceCount"] == 2
    finally:
        db.close()


@pytest.mark.asyncio
async def test_delete_one_entry(client):
    org = ensure_org("mem-org-e", "Memory Org E")
    email = f"mem.student.e.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=email, org_id=org, role=UserRole.STUDENT)
    token = await login(client, email)

    db = SessionLocal()
    try:
        service = StudentMemoryService(db)
        service.set_consent(student_id, True)
        [entry] = service.record_updates(
            student_id=student_id, subject_code="SSA101", conversation_id=None,
            updates=[{"kind": "weak_topic", "content": "Struggles with recursion"}],
        )
    finally:
        db.close()

    response = await client.delete(f"/api/v1/student/memory/{entry['id']}", headers=auth_headers(token))
    assert response.status_code == 200, response.text

    listed = await client.get("/api/v1/student/memory", headers=auth_headers(token))
    assert listed.json()["entries"] == []


@pytest.mark.asyncio
async def test_student_cannot_delete_another_students_entry(client):
    org = ensure_org("mem-org-f", "Memory Org F")
    owner_email = f"mem.student.f.owner.{uuid.uuid4().hex}@example.test"
    other_email = f"mem.student.f.other.{uuid.uuid4().hex}@example.test"
    owner_id = ensure_user(email=owner_email, org_id=org, role=UserRole.STUDENT)
    ensure_user(email=other_email, org_id=org, role=UserRole.STUDENT)

    db = SessionLocal()
    try:
        service = StudentMemoryService(db)
        service.set_consent(owner_id, True)
        [entry] = service.record_updates(
            student_id=owner_id, subject_code=None, conversation_id=None,
            updates=[{"kind": "preference", "content": "Prefers short answers"}],
        )
    finally:
        db.close()

    other_token = await login(client, other_email)
    response = await client.delete(
        f"/api/v1/student/memory/{entry['id']}", headers=auth_headers(other_token)
    )
    assert response.status_code == 404
