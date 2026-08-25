import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.db.connection import SessionLocal
from src.db.models import (
    AdminCourseOverride,
    Course,
    CourseIngestJob,
    Document,
    DocumentChunk,
    Organization,
    User,
    UserRole,
)
from src.repositories.admin_course_repository import AdminCourseRepository
from src.security.passwords import hash_password

COURSE_CODE = "CRUD901"


def _clean_admin_course() -> None:
    db = SessionLocal()
    try:
        document_ids = [item.id for item in db.query(Document).filter_by(course_id=COURSE_CODE).all()]
        if document_ids:
            db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(document_ids)).delete(synchronize_session=False)
        db.query(CourseIngestJob).filter_by(course_code=COURSE_CODE).delete()
        db.query(Document).filter_by(course_id=COURSE_CODE).delete()
        db.query(AdminCourseOverride).filter_by(subject_code=COURSE_CODE).delete()
        db.query(Course).filter_by(code=COURSE_CODE).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_admin_course():
    _clean_admin_course()
    yield
    _clean_admin_course()


def _ensure_admin() -> None:
    """Same shared `id="admin_demo"` fixture as test_admin.py/
    test_admin_guardrail.py -- gets an organization_id here too so
    whichever of the 3 creates the row first, GET /audit/events (org-scoped
    since mục 9 ý2) still works for it."""
    db = SessionLocal()
    try:
        if db.query(User).filter_by(id="admin_demo").first() is None:
            org_id = f"org_admin_test_{uuid.uuid4().hex[:8]}"
            db.add(Organization(
                id=org_id, name="Admin Test Org", slug=org_id, kind="production",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ))
            db.add(User(
                id="admin_demo",
                email="admin.demo@example.test",
                password_hash=hash_password("AdminPassword123"),
                full_name="Admin Demo",
                role=UserRole.ADMIN.value,
                organization_id=org_id,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            ))
            db.commit()
    finally:
        db.close()


async def _headers(client, email, password):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def admin_headers(client):
    _ensure_admin()
    return await _headers(client, "admin.demo@example.test", "AdminPassword123")


@pytest.mark.asyncio
async def test_admin_course_hide_and_restore_lifecycle(client):
    headers = await admin_headers(client)
    created = await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "CRUD Course", "semester": "9"},
        headers=headers,
    )
    duplicate = await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "Duplicate", "semester": "9"},
        headers=headers,
    )
    hidden = await client.delete(f"/api/v1/admin/courses/{COURSE_CODE}", headers=headers)
    restored = await client.post(f"/api/v1/admin/courses/{COURSE_CODE}/restore", headers=headers)

    assert created.status_code == 201
    assert any(item["subject_code"] == COURSE_CODE for item in created.json()["data"]["courses"])
    assert duplicate.status_code == 409
    assert hidden.status_code == 200
    assert all(item["subject_code"] != COURSE_CODE for item in hidden.json()["data"]["courses"])
    assert restored.status_code == 200
    assert any(item["subject_code"] == COURSE_CODE for item in restored.json()["data"]["courses"])


@pytest.mark.asyncio
async def test_admin_document_upload_replace_list_and_delete(client):
    headers = await admin_headers(client)
    await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "CRUD Course", "semester": "9"},
        headers=headers,
    )
    invalid = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents",
        files={"file": ("week.pdf", b"pdf", "application/pdf")},
        headers=headers,
    )
    uploaded = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents",
        files={"file": ("week.md", b"# Week\n\nContent", "text/markdown")},
        headers=headers,
    )
    listed = await client.get(f"/api/v1/admin/courses/{COURSE_CODE}/documents", headers=headers)

    assert invalid.status_code == 400
    assert uploaded.status_code == 202
    assert uploaded.json()["data"]["status"] == "processing"
    documents = listed.json()["data"]["documents"]
    assert len(documents) == 1
    assert documents[0]["chunk_count"] == 2
    document_id = documents[0]["id"]

    replaced = await client.put(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}",
        files={"file": ("replacement.txt", b"Replacement", "text/plain")},
        headers=headers,
    )
    after_replace = await client.get(f"/api/v1/admin/courses/{COURSE_CODE}/documents", headers=headers)
    assert replaced.status_code == 202
    assert after_replace.json()["data"]["documents"][0]["chunk_count"] == 1

    deleted = await client.delete(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}", headers=headers
    )
    after_delete = await client.get(f"/api/v1/admin/courses/{COURSE_CODE}/documents", headers=headers)
    assert deleted.status_code == 202
    assert after_delete.json()["data"]["documents"] == []
    db = SessionLocal()
    try:
        delete_job = (
            db.query(CourseIngestJob)
            .filter_by(course_code=COURSE_CODE, operation="delete")
            .order_by(CourseIngestJob.created_at.desc())
            .first()
        )
        assert delete_job.status == "ingested"
        assert delete_job.document_id is None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_courses_read_persists_stale_job_failure(client):
    headers = await admin_headers(client)
    await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "CRUD Course", "semester": "9"},
        headers=headers,
    )
    setup = SessionLocal()
    try:
        job = AdminCourseRepository(setup, catalog_codes=set()).start_job(
            COURSE_CODE, operation="upload"
        )
        job.created_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
        job_id = job.id
        setup.commit()
    finally:
        setup.close()

    response = await client.get("/api/v1/admin/courses", headers=headers)

    assert response.status_code == 200
    row = next(
        item for item in response.json()["data"]["courses"]
        if item["subject_code"] == COURSE_CODE
    )
    assert row["ingest_status"] == "failed"
    verify = SessionLocal()
    try:
        persisted = verify.get(CourseIngestJob, job_id)
        assert persisted.status == "failed"
        assert persisted.error == "Ingest job timed out"
        assert persisted.completed_at is not None
    finally:
        verify.close()


@pytest.mark.asyncio
async def test_document_publish_requires_passing_validation_first(client):
    headers = await admin_headers(client)
    await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "CRUD Course", "semester": "9"},
        headers=headers,
    )
    await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents",
        files={"file": ("week.md", b"# Week\n\nContent", "text/markdown")},
        headers=headers,
    )
    document_id = (await client.get(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents", headers=headers
    )).json()["data"]["documents"][0]["id"]

    # Freshly ingested, never validated -- publish must be refused.
    unvalidated_publish = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}/publish",
        json={"change_reason": "premature publish attempt"},
        headers=headers,
    )
    assert unvalidated_publish.status_code == 400

    validated = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}/validate",
        headers=headers,
    )
    assert validated.status_code == 200, validated.text
    checks = validated.json()["data"]["checks"]
    assert validated.json()["data"]["valid"] is True
    assert checks == {
        "official_scope": True,
        "admin_source": True,
        "checksum_matches_file": True,
        "readable_file": True,
        "has_chunks": True,
        "course_provenance": True,
    }

    published = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}/publish",
        json={"change_reason": "now it passed validation"},
        headers=headers,
    )
    assert published.status_code == 200, published.text

    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        assert document.publication_status == "PUBLISHED"
        assert document.checksum is not None
        assert document.validated_at is not None
    finally:
        db.close()

    archived = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}/archive",
        json={"change_reason": "superseded"},
        headers=headers,
    )
    assert archived.status_code == 200, archived.text


@pytest.mark.asyncio
async def test_document_replace_forces_revalidation(client):
    headers = await admin_headers(client)
    await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "CRUD Course", "semester": "9"},
        headers=headers,
    )
    await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents",
        files={"file": ("week.md", b"# Week\n\nContent", "text/markdown")},
        headers=headers,
    )
    document_id = (await client.get(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents", headers=headers
    )).json()["data"]["documents"][0]["id"]

    await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}/validate",
        headers=headers,
    )
    db = SessionLocal()
    try:
        assert db.get(Document, document_id).validated_at is not None
    finally:
        db.close()

    await client.put(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}",
        files={"file": ("replacement.md", b"# Replaced\n\nNew content", "text/markdown")},
        headers=headers,
    )

    db = SessionLocal()
    try:
        document = db.get(Document, document_id)
        assert document.validated_at is None, "replacing content must force re-validation"
        assert document.checksum is not None
    finally:
        db.close()

    publish_before_revalidate = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents/{document_id}/publish",
        json={"change_reason": "should still be blocked"},
        headers=headers,
    )
    assert publish_before_revalidate.status_code == 400


@pytest.mark.asyncio
async def test_upload_accepts_doc_type_and_enables_quiz_generation(client):
    """doc_type used to be hardcoded to SYLLABUS on every upload -- nothing
    in the whole codebase could ever produce a LECTURE-tagged document, so
    AI quiz generation (which filters strictly on doc_type == "LECTURE")
    was structurally unreachable, in every environment, always. Covers the
    fix end-to-end: upload with doc_type=LECTURE -> generate_with_ai."""
    headers = await admin_headers(client)
    await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "CRUD Course", "semester": "9"},
        headers=headers,
    )
    uploaded = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents",
        files={"file": ("week1.md", b"# Week 1\n\nPhotosynthesis converts light energy into chemical energy.", "text/markdown")},
        data={"doc_type": "LECTURE"},
        headers=headers,
    )
    assert uploaded.status_code == 202, uploaded.text

    db = SessionLocal()
    try:
        document = db.query(Document).filter_by(course_id=COURSE_CODE).first()
        assert document is not None
        assert document.doc_type == "LECTURE"
    finally:
        db.close()

    documents = await client.get(f"/api/v1/admin/courses/{COURSE_CODE}/documents", headers=headers)
    assert documents.json()["data"]["documents"][0]["doc_type"] == "LECTURE"


@pytest.mark.asyncio
async def test_upload_rejects_unknown_doc_type(client):
    headers = await admin_headers(client)
    await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "CRUD Course", "semester": "9"},
        headers=headers,
    )

    response = await client.post(
        f"/api/v1/admin/courses/{COURSE_CODE}/documents",
        files={"file": ("week.md", b"# Week\n\nContent", "text/markdown")},
        data={"doc_type": "NOT_A_REAL_TYPE"},
        headers=headers,
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_student_cannot_manage_admin_courses_or_documents(client):
    headers = await _headers(client, "student.demo@example.test", "password123")

    response = await client.post(
        "/api/v1/admin/courses",
        json={"subject_code": COURSE_CODE, "subject_name": "No", "semester": "9"},
        headers=headers,
    )
    assert response.status_code == 403


def test_background_runner_opens_and_closes_its_own_session(monkeypatch):
    from src.repositories.admin_course_repository import AdminCourseRepository
    from src.services.core import admin_ingest_runner

    setup = SessionLocal()
    try:
        job = AdminCourseRepository(setup, catalog_codes=set()).start_job(
            "BOUND901", operation="upload"
        )
        job_id = job.id
        setup.commit()
    finally:
        setup.close()

    class TrackingSession:
        def __init__(self, wrapped):
            self.wrapped = wrapped
            self.closed = False

        def __getattr__(self, name):
            return getattr(self.wrapped, name)

        def close(self):
            self.closed = True
            self.wrapped.close()

    class FakeIngestService:
        def __init__(self, db):
            self.db = db

        def ingest_new(self, **payload):
            return {"id": None, "chunk_count": 0}

    opened = TrackingSession(SessionLocal())
    monkeypatch.setattr(admin_ingest_runner, "SessionLocal", lambda: opened)
    monkeypatch.setattr(admin_ingest_runner, "AdminDocumentIngestService", FakeIngestService)

    admin_ingest_runner.run_admin_ingest_job(
        job_id=job_id,
        operation="upload",
        payload={
            "course_code": "BOUND901",
            "filename": "week.md",
            "content": b"content",
            "actor_user_id": None,
        },
    )

    assert opened.closed is True
    verify = SessionLocal()
    try:
        assert verify.get(CourseIngestJob, job_id).status == "ingested"
        verify.delete(verify.get(CourseIngestJob, job_id))
        verify.commit()
    finally:
        verify.close()
