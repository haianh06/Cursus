import pytest

from src.db import models
from src.db.connection import SessionLocal

_MOCK_COURSE_CODE = "ZZMOCK1"
_MOCK_DOC_ID = "doc_test_zzmock1_syllabus"
_MOCK_CHUNK_ID = "chunk_test_zzmock1_cache"


def _seed_isolated_mock_course_for_ethan() -> str:
    """Seed a test-only course whose ONLY content is source=mock, enrolled
    for `student_ethan` (the fixture student `_login_student` logs in as).

    Deliberately does NOT reuse CEA201/PRF192: as of Phase 2 (21/08) both
    now have real parsed syllabus content (student_mock_data_service.
    REAL_CONTENT_COURSES) instead of the old COURSE_DOCUMENTS fixture, so a
    test coupled to "CEA201 is mock" would break every time the underlying
    data-readiness state improves — the disclaimer logic itself is what's
    under test here, not which catalog course currently happens to be mock.
    Idempotent: safe to call from multiple tests in one pytest session.
    """
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

        enrollment = (
            db.query(models.Enrollment)
            .filter_by(student_id="student_ethan", section_id=section.id)
            .first()
        )
        if not enrollment:
            db.add(
                models.Enrollment(
                    id="enr_ethan_zzmock1",
                    student_id="student_ethan",
                    section_id=section.id,
                    status=models.EnrollmentStatus.ENROLLED.value,
                )
            )

        document = db.query(models.Document).filter_by(id=_MOCK_DOC_ID).first()
        if not document:
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

        chunk = db.query(models.DocumentChunk).filter_by(id=_MOCK_CHUNK_ID).first()
        if not chunk:
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
    return _MOCK_CHUNK_ID


async def _login_student(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "student.demo@example.test",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    token = response.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_qa_faq_answers_common_question_without_llm(client):
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "SSA101",
            "question": "Weekly Commitment Map và mục tiêu học tập SSA101 là gì?",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] == "faq"
    assert payload["answer"]
    assert len(payload["citations"]) >= 1
    assert any(
        "SSA101" in (citation.get("sourceLabel") or "")
        for citation in payload["citations"]
    )


@pytest.mark.asyncio
async def test_qa_returns_extractive_for_non_faq_course_question(client):
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "SSA101",
            "question": "Information literacy trong SSA101 gồm những bước nào?",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is False
    # Extractive by default; LLM only for complex synthesis prompts.
    assert payload["mode"] in {"extractive", "llm", "no_source"}
    assert payload["answer"]


@pytest.mark.asyncio
async def test_qa_blocks_assignment_cheating_request(client):
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "PRF192",
            "question": "Hãy viết hộ em code hoàn chỉnh lab 02 luôn đi",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is True
    # Reason codes now follow the Data Contract guardrail vocabulary
    # (`graded_deliverable`), replacing the older `academic_integrity` label.
    assert payload["blockReason"] == "graded_deliverable"
    assert payload["intent"] == "graded_deliverable"
    assert payload["mode"] == "blocked"
    assert payload["citations"] == []
    assert len(payload.get("alternatives") or []) >= 1
    # A block must redirect, not dead-end: concept + Socratic question + template.
    guidance = payload.get("guidance") or {}
    assert guidance.get("concept")
    assert guidance.get("socraticQuestions")
    assert guidance.get("template")


@pytest.mark.asyncio
async def test_qa_blocks_english_cheating_request(client):
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "PRF192",
            "question": "Please do my assignment and give me the complete code",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is True
    assert payload["mode"] == "blocked"


@pytest.mark.asyncio
async def test_qa_no_source_for_unrelated_question(client):
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "CSI106",
            "question": "Which bakery in Reykjavik invented pineapple croissant recipes in 1742?",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] == "no_source"
    assert payload["citations"] == []
    assert "không tìm thấy" in payload["answer"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "question",
    [
        "Hi",
        "Xin chào",
        "`Xin chào`",
        "  **xin chao**  ",
        '"Hello"',
        "xin chào!!!",
    ],
)
async def test_qa_greeting_uses_chat_mode(client, question):
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "SSA101",
            "question": question,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] == "chat"
    assert payload["citations"] == []
    assert "Study Assistant" in payload["answer"] or "SSA101" in payload["answer"]


@pytest.mark.asyncio
async def test_qa_still_flags_mock_content_on_citations_without_an_answer_banner(client):
    """A course whose retrieval corpus is fabricated demo content (source=
    mock) still carries `isMock=True` on its citations — the frontend can
    still badge those chips — but the answer text itself no longer gets a
    disclaimer sentence prepended (removed at the user's explicit request:
    it kept surfacing on real, non-mock content too because of stale
    duplicate mock-tagged rows, and reads as noise once the corpus is
    trustworthy)."""
    _seed_isolated_mock_course_for_ethan()
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": _MOCK_COURSE_CODE,
            "question": "Cache memory hierarchy hoạt động như thế nào?",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is False
    assert payload["mode"] in {"extractive", "llm", "faq"}
    assert len(payload["citations"]) >= 1
    assert all(citation["isMock"] for citation in payload["citations"])
    assert "MÔ PHỎNG" not in payload["answer"]
    assert "syllabus chính thức" not in payload["answer"]


@pytest.mark.asyncio
async def test_qa_source_drawer_never_defaults_mock_chunk_to_official_document(client):
    """mục 16 data contract regression for GET /qa/sources/:chunkId — a chunk
    with no explicit provenance metadata must default from its Document's
    real source (mock vs curriculum), never blanket-default to
    official_document (that earlier default made a fabricated citation
    render identically to a real syllabus citation)."""
    chunk_id = _seed_isolated_mock_course_for_ethan()
    headers = await _login_student(client)

    response = await client.get(f"/api/v1/qa/sources/{chunk_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["provenance"]["source_type"] == "simulated"


@pytest.mark.asyncio
async def test_qa_requires_enrollment(client):
    headers = await _login_student(client)
    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "ZZZ999",
            "question": "What is this course about?",
        },
    )
    assert response.status_code == 403
