import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, Course, Document, DocumentChunk
from src.repositories.chunk_repository import ChunkRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Course(id="SSA101", code="SSA101", name="SSA101", description=""))
    session.flush()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.mark.parametrize(
    ("filename", "content", "message"),
    [
        ("week.pdf", b"content", "Only .md and .txt"),
        ("week.md", b"", "empty"),
        ("week.txt", b"\xff", "UTF-8"),
        ("week.md", b"x" * (2 * 1024 * 1024 + 1), "2MB"),
    ],
    ids=["extension", "empty", "utf8", "size"],
)
def test_validation_rejects_unsupported_content(filename, content, message):
    from src.services.rag.admin_document_ingest_service import validate_admin_document

    with pytest.raises(ValueError, match=message):
        validate_admin_document(filename, content)


def test_admin_document_lifecycle_only_exposes_published_curriculum_chunks(db_session, tmp_path):
    from src.services.rag.admin_document_ingest_service import AdminDocumentIngestService

    service = AdminDocumentIngestService(db_session, uploads_root=tmp_path)
    created = service.ingest_new(
        course_code="SSA101",
        filename="week1.md",
        content=b"# Week 1\n\nContent",
        actor_user_id="admin_demo",
    )

    chunks = ChunkRepository(db_session).list_chunks_for_course(subject_code="SSA101")
    assert created["chunk_count"] == 2
    assert chunks == []
    document = db_session.get(Document, created["id"])
    assert document.metadata_info["source"] == "admin_curriculum"
    document.publication_status = "PUBLISHED"
    db_session.flush()
    chunks = ChunkRepository(db_session).list_chunks_for_course(subject_code="SSA101")
    assert len(chunks) == 2
    assert all(chunk.doc_title == "week1" for chunk in chunks)

    replaced = service.replace(
        document_id=created["id"],
        filename="week2.txt",
        content=b"Replacement only",
        actor_user_id="admin_demo",
    )
    assert replaced["id"] != created["id"]
    assert replaced["version"] == "2"
    assert replaced["chunk_count"] == 1
    assert db_session.get(Document, created["id"]).publication_status == "PUBLISHED"
    assert db_session.get(Document, replaced["id"]).previous_version_id == created["id"]
    assert db_session.query(DocumentChunk).filter_by(document_id=created["id"]).count() == 2
    assert db_session.query(DocumentChunk).filter_by(document_id=replaced["id"]).count() == 1
    # The published predecessor remains the learner-visible version while its
    # replacement stays a draft awaiting validation and publication.
    assert [chunk.doc_title for chunk in ChunkRepository(db_session).list_chunks_for_course(subject_code="SSA101")] == ["week1", "week1"]

    service.delete(document_id=replaced["id"], actor_user_id="admin_demo")
    assert db_session.get(Document, replaced["id"]) is None
    assert db_session.get(Document, created["id"]) is not None


def test_admin_document_rejects_truncating_documents(db_session, tmp_path):
    from src.services.rag.admin_document_ingest_service import AdminDocumentIngestService

    content = b"\n\n".join(f"Paragraph {index}".encode() for index in range(81))
    service = AdminDocumentIngestService(db_session, uploads_root=tmp_path)

    with pytest.raises(ValueError, match="80 paragraphs"):
        service.ingest_new(
            course_code="SSA101",
            filename="too-long.md",
            content=content,
            actor_user_id="admin_demo",
        )

    assert db_session.query(Document).count() == 0
    assert db_session.query(DocumentChunk).count() == 0
    assert list(tmp_path.iterdir()) == []


def test_admin_document_delete_keeps_file_until_transaction_commits(db_session, tmp_path):
    from src.services.rag.admin_document_ingest_service import AdminDocumentIngestService

    service = AdminDocumentIngestService(db_session, uploads_root=tmp_path)
    created = service.ingest_new(
        course_code="SSA101",
        filename="keep-on-rollback.md",
        content=b"Content",
        actor_user_id="admin_demo",
    )
    db_session.commit()
    document = db_session.get(Document, created["id"])
    file_path = service._absolute_path(document.file_path)

    cleanup_path = service.delete(document_id=created["id"], actor_user_id="admin_demo")
    assert cleanup_path == file_path
    assert file_path.exists()
    db_session.rollback()
    assert db_session.get(Document, created["id"]) is not None
    assert file_path.exists()


def test_admin_cannot_replace_or_delete_student_upload(db_session, tmp_path):
    from src.services.rag.admin_document_ingest_service import AdminDocumentIngestService

    document = Document(
        id="student-doc",
        course_id="SSA101",
        title="Private",
        file_path="private.txt",
        doc_type="NOTES",
        version="1.0",
        metadata_info={"source": "student_upload"},
    )
    db_session.add(document)
    db_session.flush()
    service = AdminDocumentIngestService(db_session, uploads_root=tmp_path)

    with pytest.raises(PermissionError):
        service.replace(document_id=document.id, filename="x.txt", content=b"x", actor_user_id="admin")
    with pytest.raises(PermissionError):
        service.delete(document_id=document.id, actor_user_id="admin")
