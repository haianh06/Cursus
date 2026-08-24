import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.connection import SessionLocal
from src.db.models import Base, Course, DocType, Document, DocumentChunk, Organization, User, UserRole
from src.repositories.admin_course_repository import AdminCourseRepository
from src.schemas.admin_schemas import AdminKpiData
from src.security.passwords import hash_password
from src.services.mock import demo_data
from src.services.mock.demo_data import load_class_snapshot, load_curriculum

try:
    from src.services.core.admin_read_service import AdminDataUnavailable, AdminReadService
except ModuleNotFoundError as exc:
    if exc.name != "src.services.admin_read_service":
        raise
    AdminDataUnavailable = RuntimeError
    AdminReadService = None

try:
    from src.api.admin import get_admin_read_service
except ModuleNotFoundError as exc:
    if exc.name != "src.api.admin":
        raise
    get_admin_read_service = None


@pytest.fixture
def admin_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _new_admin_service(db):
    assert AdminReadService is not None, "AdminReadService is not implemented"
    return AdminReadService(db)


def test_admin_read_service_counts_only_curriculum_chunks(admin_db):
    admin_db.add(Course(id="OTP101", code="OTP101", name="Orientation", description=""))
    admin_db.add_all(
        [
            Document(
                id="doc_admin_curriculum",
                course_id="OTP101",
                title="OTP101 syllabus",
                file_path="data/otp101.md",
                doc_type=DocType.SYLLABUS.value,
                version="1.0",
                metadata_info={"source": "curriculum"},
            ),
            Document(
                id="doc_admin_personal",
                course_id="OTP101",
                title="Student notes",
                file_path="data/notes.md",
                doc_type=DocType.NOTES.value,
                version="1.0",
                metadata_info={"source": "student_upload", "uploaded_by": "student_demo"},
            ),
        ]
    )
    admin_db.flush()
    admin_db.add_all(
        [
            DocumentChunk(
                id="chunk_admin_curriculum",
                document_id="doc_admin_curriculum",
                chunk_index=0,
                text="Approved",
                token_count=1,
                metadata_info={},
            ),
            DocumentChunk(
                id="chunk_admin_personal",
                document_id="doc_admin_personal",
                chunk_index=0,
                text="Private",
                token_count=1,
                metadata_info={},
            ),
        ]
    )
    admin_db.commit()

    data = _new_admin_service(admin_db).list_courses()

    otp101 = next(item for item in data["courses"] if item["subject_code"] == "OTP101")
    assert data["subject_count"] == 48
    assert len(data["courses"]) == 48
    assert otp101["chunk_count"] == 1
    assert otp101["ingest_status"] == "ingested"
    pen = next(item for item in data["courses"] if item["subject_code"] == "PEN")
    assert pen["chunk_count"] == 0
    assert pen["ingest_status"] == "not_ingested"
    assert [course["subject_code"] for course in data["courses"][:4]] == [
        "OTP101",
        "PEN",
        "PHE_COM*1",
        "TMI_ELE",
    ]


def test_admin_read_service_flags_mock_only_content_separately_from_real(admin_db):
    """mục 16 data contract regression test: a course whose only Document is
    student_mock_data_service's fabricated COURSE_DOCUMENTS (source=mock)
    must NOT show as "ingested" (that badge is reserved for
    official_document-provenance content) and must not silently merge its
    chunk count into the real chunk_count."""
    admin_db.add(Course(id="TMI_ELE", code="TMI_ELE", name="Elective", description=""))
    admin_db.add(
        Document(
            id="doc_mock_tmi",
            course_id="TMI_ELE",
            title="TMI_ELE fabricated syllabus",
            file_path="mock_data/documents/TMI_ELE/syllabus.md",
            doc_type=DocType.SYLLABUS.value,
            version="1.0",
            metadata_info={"source": "mock", "course_code": "TMI_ELE"},
        )
    )
    admin_db.flush()
    admin_db.add_all(
        [
            DocumentChunk(
                id=f"chunk_mock_tmi_{i}",
                document_id="doc_mock_tmi",
                chunk_index=i,
                text=f"Fabricated paragraph {i}",
                token_count=1,
                metadata_info={},
            )
            for i in range(3)
        ]
    )
    admin_db.commit()

    data = _new_admin_service(admin_db).list_courses()

    tmi = next(item for item in data["courses"] if item["subject_code"] == "TMI_ELE")
    assert tmi["ingest_status"] == "mock_only"
    assert tmi["chunk_count"] == 0
    assert tmi["mock_chunk_count"] == 3


def test_admin_read_service_real_content_wins_ingested_status_over_mock(admin_db):
    """If a course somehow has both (e.g. mock fixture ran before the real
    syllabus was parsed), the real-content badge must win — a course is
    never allowed to look less-ingested than it actually is, but mock
    content alone must never look more-ingested than it actually is."""
    admin_db.add(Course(id="OTP101", code="OTP101", name="Orientation", description=""))
    admin_db.add_all(
        [
            Document(
                id="doc_real_otp",
                course_id="OTP101",
                title="Real syllabus",
                file_path="data/otp101.md",
                doc_type=DocType.SYLLABUS.value,
                version="1.0",
                metadata_info={"source": "curriculum"},
            ),
            Document(
                id="doc_mock_otp",
                course_id="OTP101",
                title="Fabricated syllabus",
                file_path="mock_data/documents/OTP101/syllabus.md",
                doc_type=DocType.SYLLABUS.value,
                version="1.0",
                metadata_info={"source": "mock"},
            ),
        ]
    )
    admin_db.flush()
    admin_db.add_all(
        [
            DocumentChunk(id="chunk_real_otp", document_id="doc_real_otp", chunk_index=0, text="Real", token_count=1, metadata_info={}),
            DocumentChunk(id="chunk_mock_otp", document_id="doc_mock_otp", chunk_index=0, text="Fake", token_count=1, metadata_info={}),
        ]
    )
    admin_db.commit()

    data = _new_admin_service(admin_db).list_courses()

    otp = next(item for item in data["courses"] if item["subject_code"] == "OTP101")
    assert otp["ingest_status"] == "ingested"
    assert otp["chunk_count"] == 1
    assert otp["mock_chunk_count"] == 1


def test_admin_read_service_sorts_numeric_semesters_then_subject_code(admin_db):
    catalog = {
        "subject_count": 3,
        "subjects": [
            {"Subject Code": "SEM10", "Subject Name": "Semester ten", "Semester": "10"},
            {"Subject Code": "SEM2B", "Subject Name": "Semester two B", "Semester": "2"},
            {"Subject Code": "SEM2A", "Subject Name": "Semester two A", "Semester": "2"},
        ],
    }
    data = AdminReadService(admin_db, curriculum_loader=lambda: catalog).list_courses()

    assert [(course["semester"], course["subject_code"]) for course in data["courses"]] == [
        ("2", "SEM2A"),
        ("2", "SEM2B"),
        ("10", "SEM10"),
    ]


def test_admin_read_service_merges_added_and_hidden_course_overlays(admin_db):
    catalog = {
        "subject_count": 2,
        "subjects": [
            {"Subject Code": "SSA101", "Subject Name": "SSA", "Semester": "1"},
            {"Subject Code": "PRF192", "Subject Name": "PRF", "Semester": "2"},
        ],
    }
    repo = AdminCourseRepository(admin_db, catalog_codes={"SSA101", "PRF192"})
    repo.hide_course("PRF192", "admin_demo")
    repo.add_course("NEW101", "New course", "9", "admin_demo")

    data = AdminReadService(admin_db, curriculum_loader=lambda: catalog).list_courses()

    assert data["subject_count"] == 2
    assert [course["subject_code"] for course in data["courses"]] == ["SSA101", "NEW101"]
    assert next(course for course in data["courses"] if course["subject_code"] == "NEW101")["is_added"] is True


def test_failed_and_processing_jobs_override_chunk_derived_status(admin_db):
    catalog = {
        "subject_count": 1,
        "subjects": [{"Subject Code": "SSA101", "Subject Name": "SSA", "Semester": "1"}],
    }
    repo = AdminCourseRepository(admin_db, catalog_codes={"SSA101"})
    failed = repo.start_job("SSA101", operation="upload")
    repo.finish_job(failed.id, status="failed", error="File must be UTF-8 text")

    row = AdminReadService(admin_db, curriculum_loader=lambda: catalog).list_courses()["courses"][0]
    assert row["ingest_status"] == "failed"
    assert row["ingest_error"] == "File must be UTF-8 text"

    repo.start_job("SSA101", operation="upload")
    row = AdminReadService(admin_db, curriculum_loader=lambda: catalog).list_courses()["courses"][0]
    assert row["ingest_status"] == "processing"
    assert row["ingest_error"] is None


def test_admin_read_service_returns_approved_simulated_kpi(admin_db):
    data = _new_admin_service(admin_db).get_kpi()

    assert data["with_cursus_overall"] == 0.78
    assert data["baseline_overall"] == 0.45
    assert "mô phỏng" in data["method_note"].lower()
    assert "độc lập" in data["method_note"].lower()


@pytest.mark.parametrize(
    "comparison",
    [
        {"with_cursus_overall": "0.78", "baseline_overall": 0.45, "note": "Valid note"},
        {"with_cursus_overall": 1.01, "baseline_overall": 0.45, "note": "Valid note"},
        {"with_cursus_overall": 0.78, "baseline_overall": 0.45, "note": "   "},
    ],
)
def test_admin_read_service_rejects_malformed_kpi_payloads(admin_db, comparison):
    service = AdminReadService(
        admin_db,
        snapshot_loader=lambda: {"kpi_comparison": comparison},
    )

    with pytest.raises(AdminDataUnavailable):
        service.get_kpi()


def test_admin_read_service_rejects_missing_sources(admin_db):
    assert AdminReadService is not None, "AdminReadService is not implemented"
    service = AdminReadService(
        admin_db,
        curriculum_loader=lambda: {},
        snapshot_loader=lambda: {},
    )

    with pytest.raises(AdminDataUnavailable):
        service.list_courses()
    with pytest.raises(AdminDataUnavailable):
        service.get_kpi()


def test_demo_data_loaders_do_not_depend_on_current_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_curriculum()["subject_count"] == 48
    assert load_class_snapshot()["kpi_comparison"]["with_cursus_overall"] == 0.78


@pytest.mark.parametrize("broken_source", [None, "{not valid json", "[]"])
def test_admin_courses_retry_recovers_after_curriculum_source_is_repaired(
    admin_db, tmp_path, monkeypatch, broken_source
):
    valid_source = (demo_data.DATA_DIR / demo_data.CURRICULUM_FILE).read_text(encoding="utf-8")
    source_path = tmp_path / demo_data.CURRICULUM_FILE
    monkeypatch.setattr(demo_data, "DATA_DIR", tmp_path)

    if broken_source is not None:
        source_path.write_text(broken_source, encoding="utf-8")

    service = AdminReadService(admin_db)
    with pytest.raises(AdminDataUnavailable):
        service.list_courses()

    source_path.write_text(valid_source, encoding="utf-8")

    assert service.list_courses()["subject_count"] == 48


def test_admin_kpi_schema_strips_method_note_and_rejects_whitespace_only_values():
    data = AdminKpiData(
        with_cursus_overall=0.78,
        baseline_overall=0.45,
        method_note="  Simulated scenarios are independent.  ",
    )

    assert data.method_note == "Simulated scenarios are independent."

    with pytest.raises(ValidationError):
        AdminKpiData(
            with_cursus_overall=0.78,
            baseline_overall=0.45,
            method_note=" \t\n ",
        )


def _ensure_admin_user() -> None:
    """`id="admin_demo"` is shared, idempotently-created fixture state across
    several test files (test_admin_guardrail.py, test_admin_course_crud.py,
    this one) -- whichever runs first "wins" for the whole pytest session,
    so all 3 give it the same treatment: an organization_id, needed since
    GET /audit/events became org-scoped (mục 9 ý2)."""
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email="admin.demo@example.test").first()
        if existing:
            return

        org_id = f"org_admin_test_{uuid.uuid4().hex[:8]}"
        db.add(
            Organization(
                id=org_id, name="Admin Test Org", slug=org_id, kind="production",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.add(
            User(
                id="admin_demo",
                email="admin.demo@example.test",
                password_hash=hash_password("AdminPassword123"),
                full_name="Admin Demo",
                role=UserRole.ADMIN.value,
                organization_id=org_id,
                is_email_verified=True,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()


async def _login(client, email: str, password: str = "password123") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


async def _admin_headers(client) -> dict[str, str]:
    _ensure_admin_user()
    return await _login(client, "admin.demo@example.test", "AdminPassword123")


async def _role_headers(client, email: str) -> dict[str, str]:
    return await _login(client, email)


@pytest.mark.asyncio
async def test_admin_courses_endpoint_uses_success_envelope(client):
    headers = await _admin_headers(client)
    response = await client.get("/api/v1/admin/courses", headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["subject_count"] == 48
    assert len(payload["data"]["courses"]) == 48


@pytest.mark.asyncio
async def test_admin_kpi_endpoint_returns_seed_values_and_method_note(client):
    headers = await _admin_headers(client)
    response = await client.get("/api/v1/admin/kpi", headers=headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["with_cursus_overall"] == 0.78
    assert data["baseline_overall"] == 0.45
    assert "mô phỏng" in data["method_note"].lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/v1/admin/courses", "/api/v1/admin/kpi"])
async def test_admin_endpoints_require_authentication(client, path):
    response = await client.get(path)

    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("email", ["student.demo@example.test", "instructor.demo@example.test"])
async def test_non_admin_roles_cannot_read_admin_endpoints(client, email):
    headers = await _role_headers(client, email)
    for path in ("/api/v1/admin/courses", "/api/v1/admin/kpi"):
        response = await client.get(path, headers=headers)
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_courses_returns_controlled_error_when_data_is_unavailable(client):
    assert get_admin_read_service is not None, "Admin admin router is not implemented"
    from src.main import app

    headers = await _admin_headers(client)
    db = SessionLocal()
    service = AdminReadService(db, curriculum_loader=lambda: {})
    app.dependency_overrides[get_admin_read_service] = lambda: service
    try:
        response = await client.get("/api/v1/admin/courses", headers=headers)
        assert response.status_code == 503
        assert response.json()["detail"] == "Admin data is temporarily unavailable"
    finally:
        app.dependency_overrides.pop(get_admin_read_service, None)
        db.close()


@pytest.mark.asyncio
async def test_admin_kpi_returns_controlled_error_when_data_is_unavailable(client):
    assert get_admin_read_service is not None, "Admin admin router is not implemented"
    from src.main import app

    headers = await _admin_headers(client)
    db = SessionLocal()
    service = AdminReadService(db, snapshot_loader=lambda: {})
    app.dependency_overrides[get_admin_read_service] = lambda: service
    try:
        response = await client.get("/api/v1/admin/kpi", headers=headers)
        assert response.status_code == 503
        assert response.json()["detail"] == "Admin data is temporarily unavailable"
    finally:
        app.dependency_overrides.pop(get_admin_read_service, None)
        db.close()
