import pytest

from src.db import models
from src.db.connection import SessionLocal


def _seed_document(*, doc_id: str, course_id: str, title: str, source: str, uploaded_by: str | None = None) -> None:
    db = SessionLocal()
    try:
        if db.query(models.Document).filter_by(id=doc_id).first() is not None:
            return
        metadata: dict = {"source": source}
        if uploaded_by:
            metadata["uploaded_by"] = uploaded_by
        db.add(
            models.Document(
                id=doc_id,
                course_id=course_id,
                title=title,
                doc_type="LECTURE",
                file_path=f"mock://{doc_id}.md",
                version="v1",
                metadata_info=metadata,
            )
        )
        db.flush()
        for index, text in enumerate(["Phần mở đầu.", "Phần nội dung chính."]):
            db.add(
                models.DocumentChunk(
                    id=f"{doc_id}_chunk_{index}",
                    document_id=doc_id,
                    chunk_index=index,
                    text=text,
                    token_count=len(text.split()),
                    metadata_info={"source_label": title},
                )
            )
        db.commit()
    finally:
        db.close()


async def _student_headers(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "student.demo@example.test", "password": "password123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.mark.asyncio
async def test_enrolled_student_can_read_document_content(client):
    _seed_document(
        doc_id="doc_ssa101_lecture01",
        course_id="SSA101",
        title="SSA101 - Buổi 1",
        source="curriculum",
    )
    response = await client.get(
        "/api/v1/student/courses/SSA101/documents/doc_ssa101_lecture01",
        headers=await _student_headers(client),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == "doc_ssa101_lecture01"
    assert payload["title"] == "SSA101 - Buổi 1"
    assert payload["content"] == "Phần mở đầu.\n\nPhần nội dung chính."


@pytest.mark.asyncio
async def test_another_students_private_upload_is_hidden(client):
    _seed_document(
        doc_id="doc_ssa101_private_note",
        course_id="SSA101",
        title="Ghi chú riêng của sinh viên khác",
        source="student_upload",
        uploaded_by="__someone_else__",
    )
    response = await client.get(
        "/api/v1/student/courses/SSA101/documents/doc_ssa101_private_note",
        headers=await _student_headers(client),
    )
    assert response.status_code == 404
