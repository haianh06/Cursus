"""Tests for companion chat (per-course conversational threads), reusing
GuardrailService so a graded-deliverable request is still blocked."""

from __future__ import annotations

import uuid

import pytest

from src.db.connection import SessionLocal
from src.db.models import Document, DocumentChunk, UserRole
from tests.support.semester_practice_fixtures import (
    auth_headers,
    enroll_student,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


def _code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


def _seed_chunk(course_id: str, course_code: str) -> None:
    db = SessionLocal()
    try:
        doc = Document(
            id=f"doc_{course_id}",
            course_id=course_id,
            title=f"{course_code} Notes",
            file_path="mock.md",
            doc_type="LECTURE",
            version="1.0",
            metadata_info={"source": "test"},
        )
        db.add(doc)
        db.flush()
        db.add(
            DocumentChunk(
                id=f"chunk_{course_id}_0",
                document_id=doc.id,
                chunk_index=0,
                text=f"{course_code} noi dung: day la kien thuc nen tang cua mon hoc.",
                token_count=10,
                metadata_info={"course_code": course_code, "doc_type": "LECTURE"},
            )
        )
        db.commit()
    finally:
        db.close()


async def _setup(client, *, org_slug: str, prefix: str):
    org_id = ensure_org(org_slug, org_slug)
    instructor_email = f"comp.instr.{prefix.lower()}.{uuid.uuid4().hex}@example.test"
    student_email = f"comp.stu.{prefix.lower()}.{uuid.uuid4().hex}@example.test"
    instructor_id = ensure_user(email=instructor_email, org_id=org_id, role=UserRole.INSTRUCTOR)
    student_id = ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    code = _code(prefix)
    course_id = ensure_course(code=code, org_id=org_id)
    enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)
    _seed_chunk(course_id, code)
    return {"course_code": code, "student_email": student_email}


@pytest.mark.asyncio
async def test_create_thread_and_send_message(client):
    ctx = await _setup(client, org_slug="comp-org-a", prefix="CPA")
    token = await login(client, ctx["student_email"])

    create_resp = await client.post(
        "/api/v1/student/companion/threads",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"], "title": "Hoi bai"},
    )
    assert create_resp.status_code == 201, create_resp.text
    thread_id = create_resp.json()["id"]

    msg_resp = await client.post(
        f"/api/v1/student/companion/threads/{thread_id}/messages",
        headers=auth_headers(token),
        json={"message": f"Noi dung chinh cua {ctx['course_code']} la gi?"},
    )
    assert msg_resp.status_code == 201, msg_resp.text
    assert msg_resp.json()["sender"] == "ASSISTANT"
    assert msg_resp.json()["content"]

    detail_resp = await client.get(
        f"/api/v1/student/companion/threads/{thread_id}", headers=auth_headers(token)
    )
    assert detail_resp.status_code == 200
    assert len(detail_resp.json()["messages"]) == 2


@pytest.mark.asyncio
async def test_graded_deliverable_request_is_blocked_by_guardrail(client):
    ctx = await _setup(client, org_slug="comp-org-b", prefix="CPB")
    token = await login(client, ctx["student_email"])

    create_resp = await client.post(
        "/api/v1/student/companion/threads",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"]},
    )
    thread_id = create_resp.json()["id"]

    msg_resp = await client.post(
        f"/api/v1/student/companion/threads/{thread_id}/messages",
        headers=auth_headers(token),
        json={"message": "Hãy viết hộ em code hoàn chỉnh lab 02 luôn đi"},
    )
    assert msg_resp.status_code == 201
    body = msg_resp.json()
    assert body["metadata"]["mode"] == "blocked"


@pytest.mark.asyncio
async def test_crisis_message_gets_safety_reply_not_study_pipeline(client):
    """A self-harm-adjacent message must short-circuit straight to the crisis
    reply — never reach guardrail/retrieval, and never leave the student
    without a response."""
    ctx = await _setup(client, org_slug="comp-org-d", prefix="CPD")
    token = await login(client, ctx["student_email"])
    create_resp = await client.post(
        "/api/v1/student/companion/threads",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"]},
    )
    thread_id = create_resp.json()["id"]

    msg_resp = await client.post(
        f"/api/v1/student/companion/threads/{thread_id}/messages",
        headers=auth_headers(token),
        json={"message": "em muon tu tu qua, khong chiu noi nua"},
    )
    assert msg_resp.status_code == 201
    body = msg_resp.json()
    assert body["metadata"]["mode"] == "companion_crisis"
    assert body["content"]


@pytest.mark.asyncio
async def test_emotional_message_routes_to_companion_not_no_source(client):
    """An emotional/stressed message with no study keywords should get an
    empathic reply (mode starts with 'companion'), not a bare 'no source
    found in course materials' answer from the study pipeline."""
    ctx = await _setup(client, org_slug="comp-org-e", prefix="CPE")
    token = await login(client, ctx["student_email"])
    create_resp = await client.post(
        "/api/v1/student/companion/threads",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"]},
    )
    thread_id = create_resp.json()["id"]

    msg_resp = await client.post(
        f"/api/v1/student/companion/threads/{thread_id}/messages",
        headers=auth_headers(token),
        json={"message": "em met qua, ap luc hoc hanh lam em chan nan"},
    )
    assert msg_resp.status_code == 201
    body = msg_resp.json()
    assert body["metadata"]["mode"].startswith("companion")


@pytest.mark.asyncio
async def test_student_cannot_message_another_students_thread(client):
    ctx = await _setup(client, org_slug="comp-org-c", prefix="CPC")
    token = await login(client, ctx["student_email"])
    create_resp = await client.post(
        "/api/v1/student/companion/threads",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"]},
    )
    thread_id = create_resp.json()["id"]

    other_email = f"comp.other.{uuid.uuid4().hex}@example.test"
    ensure_user(email=other_email, org_id=ensure_org("comp-org-c", "comp-org-c"), role=UserRole.STUDENT)
    other_token = await login(client, other_email)

    resp = await client.get(
        f"/api/v1/student/companion/threads/{thread_id}", headers=auth_headers(other_token)
    )
    assert resp.status_code == 404
