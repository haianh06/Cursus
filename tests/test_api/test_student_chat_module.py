"""Unified student chat API (`/api/v1/student/chat*`) — successor to the old
split test_qa_module.py (`POST /api/v1/qa`, stateless) + test_companion_api.py
(`/student/companion/threads*`, per-course threads) after the chatbot
rebuild: one continuous conversation per student, always persisted, plus a
new regression this rebuild introduces — a blocked answer now writes a real
`GuardrailEvent` row (previously only seed/test fixtures ever did)."""

from __future__ import annotations

import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from tests.support.semester_practice_fixtures import (
    auth_headers,
    enroll_student,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)

_MOCK_COURSE_CODE = "ZZMOCK1"
_MOCK_DOC_ID = "doc_test_zzmock1_syllabus"
_MOCK_CHUNK_ID = "chunk_test_zzmock1_cache"


def _code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


def _seed_chunk(course_id: str, course_code: str) -> None:
    db = SessionLocal()
    try:
        doc = models.Document(
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
            models.DocumentChunk(
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
    instructor_email = f"chat.instr.{prefix.lower()}.{uuid.uuid4().hex}@example.test"
    student_email = f"chat.stu.{prefix.lower()}.{uuid.uuid4().hex}@example.test"
    instructor_id = ensure_user(email=instructor_email, org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_id = ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    code = _code(prefix)
    course_id = ensure_course(code=code, org_id=org_id)
    enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)
    _seed_chunk(course_id, code)
    return {"course_code": code, "student_id": student_id, "student_email": student_email}


async def _login_student(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "student.demo@example.test", "password": "password123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _seed_isolated_mock_course_for_ethan() -> None:
    """Same fixture course as the old test_qa_module.py — isolated,
    fabricated-only content, never confused with a real catalog subject."""
    db = SessionLocal()
    try:
        course = db.query(models.Course).filter_by(code=_MOCK_COURSE_CODE).first()
        if not course:
            course = models.Course(
                id="course_test_zzmock1",
                code=_MOCK_COURSE_CODE,
                name="Test-Only Mock Course",
                description="Isolated fixture course — never a real catalog subject.",
            )
            db.add(course)
            db.flush()

        section = db.query(models.CourseSection).filter_by(id="sec_zzmock1_demo").first()
        if not section:
            section = models.CourseSection(
                id="sec_zzmock1_demo",
                course_id=course.id,
                instructor_id="inst_demo",
                term="Fall2026",
                section_code="SE1899",
            )
            db.add(section)
            db.flush()

        if not db.query(models.Enrollment).filter_by(student_id="student_ethan", section_id=section.id).first():
            db.add(
                models.Enrollment(
                    id="enr_ethan_zzmock1",
                    student_id="student_ethan",
                    section_id=section.id,
                    status=models.EnrollmentStatus.ENROLLED.value,
                )
            )

        if not db.query(models.Document).filter_by(id=_MOCK_DOC_ID).first():
            db.add(
                models.Document(
                    id=_MOCK_DOC_ID,
                    course_id=course.id,
                    title="ZZMOCK1 Fabricated Lecture — Cache Memory",
                    file_path="mock_data/documents/ZZMOCK1/lecture_cache.md",
                    doc_type=models.DocType.LECTURE.value,
                    version="1.0",
                    metadata_info={"source": "mock", "course_code": _MOCK_COURSE_CODE},
                )
            )
            db.flush()

        if not db.query(models.DocumentChunk).filter_by(id=_MOCK_CHUNK_ID).first():
            db.add(
                models.DocumentChunk(
                    id=_MOCK_CHUNK_ID,
                    document_id=_MOCK_DOC_ID,
                    chunk_index=0,
                    text=(
                        "Cache memory hierarchy: Registers -> L1/L2 cache -> "
                        "Main memory -> Secondary storage. Direct-mapped: "
                        "each memory block maps to exactly one cache line."
                    ),
                    token_count=25,
                    metadata_info={
                        "section": "Cache Memory",
                        "source_label": "ZZMOCK1 Fabricated Lecture — Cache Memory",
                    },
                )
            )
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_send_message_persists_and_is_readable_via_get(client):
    ctx = await _setup(client, org_slug="chat-org-a", prefix="CHA")
    token = await login(client, ctx["student_email"])

    msg_resp = await client.post(
        "/api/v1/student/chat/messages",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"], "message": f"Noi dung chinh cua {ctx['course_code']} la gi?"},
    )
    assert msg_resp.status_code == 201, msg_resp.text
    assert msg_resp.json()["sender"] == "ASSISTANT"
    assert msg_resp.json()["content"]

    state_resp = await client.get("/api/v1/student/chat", headers=auth_headers(token))
    assert state_resp.status_code == 200
    messages = state_resp.json()["messages"]
    assert len(messages) == 2
    assert messages[0]["sender"] == "USER"
    assert messages[1]["sender"] == "ASSISTANT"


@pytest.mark.asyncio
async def test_second_message_lands_in_the_same_continuous_thread(client):
    """No more per-course thread partitioning -- a 2nd message on a
    different course still appends to the SAME conversation."""
    ctx_a = await _setup(client, org_slug="chat-org-f1", prefix="CHF1")
    token = await login(client, ctx_a["student_email"])

    first = await client.post(
        "/api/v1/student/chat/messages",
        headers=auth_headers(token),
        json={"subjectCode": ctx_a["course_code"], "message": "Xin chào"},
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/student/chat/messages",
        headers=auth_headers(token),
        json={"message": "Cảm ơn bạn"},
    )
    assert second.status_code == 201

    state_resp = await client.get("/api/v1/student/chat", headers=auth_headers(token))
    assert len(state_resp.json()["messages"]) == 4


@pytest.mark.asyncio
async def test_clear_chat_deletes_all_messages(client):
    ctx = await _setup(client, org_slug="chat-org-g", prefix="CHG")
    token = await login(client, ctx["student_email"])
    await client.post(
        "/api/v1/student/chat/messages",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"], "message": "Xin chào"},
    )
    clear_resp = await client.delete("/api/v1/student/chat", headers=auth_headers(token))
    assert clear_resp.status_code == 204

    state_resp = await client.get("/api/v1/student/chat", headers=auth_headers(token))
    assert state_resp.json()["messages"] == []


@pytest.mark.asyncio
async def test_graded_deliverable_request_is_blocked_and_writes_guardrail_event(client):
    """Regression for this rebuild's new behavior: a blocked answer must now
    write a real `GuardrailEvent` row (classification=BLOCKED, review_status=
    PENDING) keyed to the student's own Message -- previously only
    seed/test fixtures ever created these, so the instructor guardrail
    review queue never received live traffic."""
    ctx = await _setup(client, org_slug="chat-org-b", prefix="CHB")
    token = await login(client, ctx["student_email"])

    msg_resp = await client.post(
        "/api/v1/student/chat/messages",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"], "message": "Hãy viết hộ em code hoàn chỉnh lab 02 luôn đi"},
    )
    assert msg_resp.status_code == 201
    body = msg_resp.json()
    assert body["mode"] == "blocked"
    assert body["blocked"] is True
    assert body["blockReason"] == "graded_deliverable"
    assert body["intent"] == "graded_deliverable"
    guidance = body.get("guidance") or {}
    assert guidance.get("concept")
    assert guidance.get("socraticQuestions")
    assert guidance.get("template")

    db = SessionLocal()
    try:
        user_message = (
            db.query(models.Message)
            .filter_by(content="Hãy viết hộ em code hoàn chỉnh lab 02 luôn đi", sender="USER")
            .order_by(models.Message.created_at.desc())
            .first()
        )
        assert user_message is not None
        event = db.query(models.GuardrailEvent).filter_by(message_id=user_message.id).first()
        assert event is not None
        assert event.classification == "BLOCKED"
        assert event.review_status == "PENDING"
        assert event.block_reason == "graded_deliverable"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_crisis_message_gets_safety_reply_not_study_pipeline(client):
    ctx = await _setup(client, org_slug="chat-org-d", prefix="CHD")
    token = await login(client, ctx["student_email"])

    msg_resp = await client.post(
        "/api/v1/student/chat/messages",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"], "message": "em muon tu tu qua, khong chiu noi nua"},
    )
    assert msg_resp.status_code == 201
    body = msg_resp.json()
    assert body["mode"] == "companion_crisis"
    assert body["content"]


@pytest.mark.asyncio
async def test_emotional_message_routes_to_companion_not_no_source(client):
    ctx = await _setup(client, org_slug="chat-org-e", prefix="CHE")
    token = await login(client, ctx["student_email"])

    msg_resp = await client.post(
        "/api/v1/student/chat/messages",
        headers=auth_headers(token),
        json={"subjectCode": ctx["course_code"], "message": "em met qua, ap luc hoc hanh lam em chan nan"},
    )
    assert msg_resp.status_code == 201
    assert msg_resp.json()["mode"].startswith("companion")


@pytest.mark.asyncio
async def test_greeting_uses_chat_mode(client):
    headers = await _login_student(client)
    response = await client.post(
        "/api/v1/student/chat/messages",
        headers=headers,
        json={"subjectCode": "SSA101", "message": "Xin chào"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] == "chat"
    assert payload["citations"] == []


@pytest.mark.asyncio
async def test_unrelated_question_with_no_subject_never_errors(client):
    """No subjectCode, no academic retrieval, no help-bank match -- the
    student's own live state is still always assembled (cheap, always
    available), so under the no-LLM/LLM-failed fallback it becomes the
    last-resort answer rather than a bare "no source" -- when an LLM IS
    available it would instead see this is off-topic and set
    insufficient_context itself. Either way this must never error."""
    headers = await _login_student(client)
    response = await client.post(
        "/api/v1/student/chat/messages",
        headers=headers,
        json={"message": "Which bakery in Reykjavik invented pineapple croissant recipes in 1742?"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] in {"no_source", "extractive", "llm"}
    if payload["mode"] == "no_source":
        assert payload["citations"] == []


@pytest.mark.asyncio
async def test_still_flags_mock_content_on_citations_without_an_answer_banner(client):
    """A course whose retrieval corpus is fabricated demo content (source=
    mock) still carries isMock=True on its citations, but the answer text
    itself no longer gets a disclaimer sentence prepended (removed at the
    user's explicit request)."""
    _seed_isolated_mock_course_for_ethan()
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/student/chat/messages",
        headers=headers,
        json={"subjectCode": _MOCK_COURSE_CODE, "message": "Cache memory hierarchy hoạt động như thế nào?"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] in {"extractive", "llm"}
    assert len(payload["citations"]) >= 1
    assert any(c["isMock"] for c in payload["citations"])
    assert "MÔ PHỎNG" not in payload["content"]
    assert "syllabus chính thức" not in payload["content"]


@pytest.mark.asyncio
async def test_requires_enrollment_for_a_given_subject_code(client):
    headers = await _login_student(client)
    response = await client.post(
        "/api/v1/student/chat/messages",
        headers=headers,
        json={"subjectCode": "ZZZ999", "message": "What is this course about?"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_help_bank_question_answers_how_to_use_a_feature(client):
    """New capability from the rebuild: a question about the APP ITSELF
    (not course content) should be answerable via the app_help_bank
    grounding, even with no subjectCode."""
    headers = await _login_student(client)
    response = await client.post(
        "/api/v1/student/chat/messages",
        headers=headers,
        json={"message": "Làm sao để đặt lịch tự học Pomodoro trong app?"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] in {"extractive", "llm"}
    assert any(c["kind"] == "help" for c in payload["citations"])


@pytest.mark.asyncio
async def test_state_question_answers_from_the_students_own_live_data(client):
    """New capability: a question about the student's own current plan/week
    should be answerable purely from StudentContextService, with no
    subjectCode and no course retrieval involved."""
    headers = await _login_student(client)
    response = await client.post(
        "/api/v1/student/chat/messages",
        headers=headers,
        json={"message": "Tuần học hiện tại của em là tuần mấy?"},
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] in {"extractive", "llm"}
