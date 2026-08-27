"""Tests for course practice sets: student request -> instructor review ->
student sees published sets. Grounded via THIS branch's ChunkRepository, org
-scoped via course_id."""

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


def _seed_chunks(course_id: str, course_code: str) -> None:
    db = SessionLocal()
    try:
        doc = Document(
            id=f"doc_{course_id}",
            course_id=course_id,
            title=f"{course_code} Lecture",
            file_path="mock.md",
            doc_type="LECTURE",
            version="1.0",
            metadata_info={"source": "test"},
        )
        db.add(doc)
        db.flush()
        for i in range(3):
            db.add(
                DocumentChunk(
                    id=f"chunk_{course_id}_{i}",
                    document_id=doc.id,
                    chunk_index=i,
                    text=f"Noi dung bai giang {course_code} phan {i}: khai niem quan trong so {i}.",
                    token_count=20,
                    metadata_info={"course_code": course_code, "doc_type": "LECTURE", "source_label": f"{course_code} slide {i}"},
                )
            )
        db.commit()
    finally:
        db.close()


async def _setup_course_with_student(client, *, org_slug: str, prefix: str):
    org_id = ensure_org(org_slug, org_slug)
    instructor_email = f"prac.instr.{prefix.lower()}.{uuid.uuid4().hex}@example.test"
    student_email = f"prac.stu.{prefix.lower()}.{uuid.uuid4().hex}@example.test"
    instructor_id = ensure_user(email=instructor_email, org_id=org_id, role=UserRole.INSTRUCTOR)
    student_id = ensure_user(email=student_email, org_id=org_id, role=UserRole.STUDENT)
    code = _code(prefix)
    course_id = ensure_course(code=code, org_id=org_id)
    enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)
    _seed_chunks(course_id, code)
    return {
        "org_id": org_id,
        "course_id": course_id,
        "course_code": code,
        "instructor_email": instructor_email,
        "student_email": student_email,
    }


@pytest.mark.asyncio
async def test_student_request_then_instructor_review_flow(client):
    ctx = await _setup_course_with_student(client, org_slug="prac-org-a", prefix="PRA")

    student_token = await login(client, ctx["student_email"])
    request_resp = await client.post(
        "/api/v1/student/practice/request",
        headers=auth_headers(student_token),
        json={"courseCode": ctx["course_code"], "weekNumber": 1, "language": "vi"},
    )
    assert request_resp.status_code == 202, request_resp.text
    body = request_resp.json()
    assert body["status"] == "PENDING_REVIEW"
    assert body["itemCount"] == 20
    set_id = body["id"]

    # Student cannot see the pending set's content yet -- a normal "nothing
    # published yet" empty state (200 + null), not a 404 error.
    pending_get = await client.get(
        "/api/v1/student/practice",
        headers=auth_headers(student_token),
        params={"course_code": ctx["course_code"], "week_number": 1},
    )
    assert pending_get.status_code == 200
    assert pending_get.json() is None

    instructor_token = await login(client, ctx["instructor_email"])
    list_resp = await client.get("/api/v1/instructor/practice", headers=auth_headers(instructor_token))
    assert list_resp.status_code == 200
    assert any(item["id"] == set_id for item in list_resp.json())

    review_resp = await client.post(
        f"/api/v1/instructor/practice/{set_id}/review",
        headers=auth_headers(instructor_token),
        json={"decision": "PUBLISHED"},
    )
    assert review_resp.status_code == 200, review_resp.text
    assert review_resp.json()["status"] == "PUBLISHED"

    published_get = await client.get(
        "/api/v1/student/practice",
        headers=auth_headers(student_token),
        params={"course_code": ctx["course_code"], "week_number": 1},
    )
    assert published_get.status_code == 200, published_get.text
    assert published_get.json()["status"] == "PUBLISHED"
    assert len(published_get.json()["items"]) == 20


@pytest.mark.asyncio
async def test_instructor_from_other_org_cannot_review(client):
    ctx = await _setup_course_with_student(client, org_slug="prac-org-b", prefix="PRB")
    other_org_id = ensure_org("prac-org-c", "Prac Org C")
    other_instructor_email = f"prac.instr.other.{uuid.uuid4().hex}@example.test"
    ensure_user(email=other_instructor_email, org_id=other_org_id, role=UserRole.INSTRUCTOR)

    student_token = await login(client, ctx["student_email"])
    request_resp = await client.post(
        "/api/v1/student/practice/request",
        headers=auth_headers(student_token),
        json={"courseCode": ctx["course_code"], "weekNumber": 2, "language": "vi"},
    )
    set_id = request_resp.json()["id"]

    other_token = await login(client, other_instructor_email)
    list_resp = await client.get("/api/v1/instructor/practice", headers=auth_headers(other_token))
    assert list_resp.status_code == 200
    assert all(item["id"] != set_id for item in list_resp.json())

    review_resp = await client.post(
        f"/api/v1/instructor/practice/{set_id}/review",
        headers=auth_headers(other_token),
        json={"decision": "PUBLISHED"},
    )
    assert review_resp.status_code == 403


@pytest.mark.asyncio
async def test_student_not_enrolled_cannot_request_practice(client):
    ctx = await _setup_course_with_student(client, org_slug="prac-org-d", prefix="PRD")
    outsider_email = f"prac.outsider.{uuid.uuid4().hex}@example.test"
    ensure_user(email=outsider_email, org_id=ctx["org_id"], role=UserRole.STUDENT)

    outsider_token = await login(client, outsider_email)
    resp = await client.post(
        "/api/v1/student/practice/request",
        headers=auth_headers(outsider_token),
        json={"courseCode": ctx["course_code"], "weekNumber": 1, "language": "vi"},
    )
    assert resp.status_code == 403
