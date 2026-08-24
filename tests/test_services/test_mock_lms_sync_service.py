"""Unit tests for MockLmsSyncService -- fixture-based, no real HTTP call to a
running Mock LMS (a fake client stands in)."""
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import (
    Assignment,
    AssessmentType,
    Base,
    Course,
    CourseSection,
    Document,
    DocumentChunk,
    User,
    UserRole,
)
from src.repositories.chunk_repository import ChunkRepository
from src.services.core import source_precedence
from src.services.core.mock_lms_sync_service import MockLmsSyncService, MockLmsSyncValidationError


class FakeMockLmsClient:
    """Stands in for a real MockLmsClient -- fixture data only, no HTTP."""

    def __init__(self, courses: list[dict], assignments_by_code: dict[str, list[dict]]):
        self._courses = courses
        self._assignments_by_code = assignments_by_code

    def list_courses(self) -> list[dict]:
        return self._courses

    def list_assignments(self, course_code: str) -> list[dict]:
        return self._assignments_by_code.get(course_code, [])


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _seed_course_with_assignment(db, *, code: str, title: str, due_date: datetime) -> None:
    instructor = User(
        id=f"inst_{code}", email=f"{code}@test.local", password_hash="x",
        full_name="Test Instructor", role=UserRole.INSTRUCTOR.value,
    )
    db.add(instructor)
    course = Course(id=f"course_{code.lower()}", code=code, name=f"{code} name", description="")
    db.add(course)
    db.flush()
    section = CourseSection(
        id=f"sec_{code.lower()}", course_id=course.id, instructor_id=instructor.id,
        term="Fall2026", section_code="SE0001",
    )
    db.add(section)
    db.flush()
    db.add(
        Assignment(
            id=f"asn_{code.lower()}_1", section_id=section.id, title=title,
            description="", due_date=due_date, max_points=100,
            assessment_type=AssessmentType.ASSIGNMENT.value,
        )
    )
    db.commit()


def test_preview_detects_a_conflicting_due_date_and_mock_lms_wins(db):
    _seed_course_with_assignment(
        db, code="PRF192", title="Assignment 1", due_date=datetime(2026, 9, 21)
    )
    client = FakeMockLmsClient(
        courses=[{"id": "c1", "course_code": "PRF192", "name": "PRF192 name", "semester": "1", "credit": 3}],
        assignments_by_code={
            "PRF192": [
                {
                    "id": "mock_asn_1", "name": "Assignment 1", "description": "",
                    "due_at": "2026-09-30T00:00:00", "points_possible": 15,
                    "updated_at": "2026-08-21T00:00:00",
                }
            ]
        },
    )

    result = MockLmsSyncService(db, client=client).preview()

    assert result["totalEvaluated"] == 1
    assert result["changedCount"] == 1
    change = result["changes"][0]
    assert change["courseCode"] == "PRF192"
    assert change["before"] == "2026-09-21T00:00:00"
    assert change["after"] == "2026-09-30T00:00:00"
    assert change["winningTier"] == source_precedence.MOCK_LMS
    assert change["winningTierLabel"] == source_precedence.label_for(source_precedence.MOCK_LMS)


def test_preview_reports_no_change_when_dates_already_match(db):
    _seed_course_with_assignment(
        db, code="PRF192", title="Assignment 1", due_date=datetime(2026, 9, 30)
    )
    client = FakeMockLmsClient(
        courses=[{"id": "c1", "course_code": "PRF192", "name": "PRF192 name", "semester": "1", "credit": 3}],
        assignments_by_code={
            "PRF192": [
                {
                    "id": "mock_asn_1", "name": "Assignment 1", "description": "",
                    "due_at": "2026-09-30T00:00:00", "points_possible": 15,
                    "updated_at": "2026-08-21T00:00:00",
                }
            ]
        },
    )

    result = MockLmsSyncService(db, client=client).preview()

    assert result["totalEvaluated"] == 1
    assert result["changedCount"] == 0
    assert result["changes"] == []


def test_preview_treats_a_course_cursus_has_never_seen_as_a_new_value_from_mock_lms(db):
    """No Course row at all yet -- everything Mock LMS reports is "new", not a
    conflict with an existing value, but still resolves to the MOCK_LMS tier."""
    client = FakeMockLmsClient(
        courses=[{"id": "c1", "course_code": "CEA201", "name": "CEA201 name", "semester": "1", "credit": 3}],
        assignments_by_code={
            "CEA201": [
                {
                    "id": "mock_asn_1", "name": "Assignment 1", "description": "",
                    "due_at": "2026-09-30T00:00:00", "points_possible": 15,
                    "updated_at": "2026-08-21T00:00:00",
                }
            ]
        },
    )

    result = MockLmsSyncService(db, client=client).preview()

    assert result["changedCount"] == 1
    change = result["changes"][0]
    assert change["before"] is None
    assert change["winningTier"] == source_precedence.MOCK_LMS


def _client_for(code: str, name: str, assignment_id: str, assignment_name: str, due_at: str) -> FakeMockLmsClient:
    return FakeMockLmsClient(
        courses=[{"id": "c1", "course_code": code, "name": name, "semester": "1", "credit": 3}],
        assignments_by_code={
            code: [
                {
                    "id": assignment_id, "name": assignment_name, "description": "",
                    "due_at": due_at, "points_possible": 15, "updated_at": "2026-08-21T00:00:00",
                }
            ]
        },
    )


def test_publish_requires_a_reason(db):
    client = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-09-30T00:00:00")
    with pytest.raises(MockLmsSyncValidationError):
        MockLmsSyncService(db, client=client).publish(reason="  ", actor_user_id=None)


def test_publish_creates_a_version_and_a_citable_fact_chunk_for_a_brand_new_course(db):
    """CEA201 has no Course row in Cursus yet -- publish() must create one, then
    make the fact retrievable/citable, not just record a diff nobody can query."""
    client = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-09-30T00:00:00")
    service = MockLmsSyncService(db, client=client)

    version = service.publish(reason="Initial sync", actor_user_id="admin_1")
    db.commit()

    assert version.sync_version == 1
    assert version.reason == "Initial sync"
    assert version.rolled_back_from is None
    assert len(version.payload) == 1
    assert version.payload[0]["after"] == "2026-09-30T00:00:00"

    course = db.query(Course).filter_by(code="CEA201").first()
    assert course is not None

    chunks = ChunkRepository(db).list_chunks_for_course(subject_code="CEA201")
    assert len(chunks) == 1
    assert chunks[0].content_source == "mock_lms"
    assert "Assignment 1" in chunks[0].text
    assert "30/09/2026" in chunks[0].text


def test_publish_updates_a_matching_live_assignment_due_date(db):
    """When a live Assignment DOES exist with the same title (the rare case),
    publish() updates it in place rather than only recording a diff."""
    _seed_course_with_assignment(
        db, code="PRF192", title="Assignment 1", due_date=datetime(2026, 9, 21)
    )
    client = _client_for("PRF192", "PRF192 name", "a1", "Assignment 1", "2026-09-30T00:00:00")

    MockLmsSyncService(db, client=client).publish(reason="Deadline moved", actor_user_id="admin_1")
    db.commit()

    live = db.query(Assignment).filter_by(id="asn_prf192_1").first()
    assert live.due_date == datetime(2026, 9, 30)


def test_rollback_restores_the_before_value_and_records_a_new_version(db):
    client = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-09-30T00:00:00")
    service = MockLmsSyncService(db, client=client)
    v1 = service.publish(reason="Initial sync", actor_user_id="admin_1")
    db.commit()

    # Simulate a second, different sync (e.g. the deadline moved again).
    client2 = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-10-15T00:00:00")
    service2 = MockLmsSyncService(db, client=client2)
    v2 = service2.publish(reason="Deadline moved again", actor_user_id="admin_1")
    db.commit()
    assert v2.sync_version == 2

    v3 = service.rollback(target_version=v1.sync_version, reason="Undo the move", actor_user_id="admin_1")
    db.commit()

    assert v3.sync_version == 3
    assert v3.rolled_back_from == v1.sync_version
    chunks = ChunkRepository(db).list_chunks_for_course(subject_code="CEA201")
    assert "Assignment 1" in chunks[0].text


def test_rollback_requires_a_reason_and_rejects_unknown_version(db):
    client = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-09-30T00:00:00")
    service = MockLmsSyncService(db, client=client)
    service.publish(reason="Initial sync", actor_user_id="admin_1")
    db.commit()

    with pytest.raises(MockLmsSyncValidationError):
        service.rollback(target_version=1, reason="", actor_user_id=None)
    with pytest.raises(LookupError):
        service.rollback(target_version=999, reason="ok", actor_user_id=None)


def test_publish_twice_with_unchanged_mock_lms_data_is_idempotent(db):
    """Regression test for a real bug caught during Checkpoint 4 UI testing:
    publish() used to re-report all 144 assignments as "changed" on every run
    forever, even immediately after a successful publish, because preview()
    only ever compared against the (almost always absent) live `Assignment`
    row -- never against the fact chunk publish() itself had just written. A
    second, unmodified sync must report zero changes."""
    client = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-09-30T00:00:00")
    service = MockLmsSyncService(db, client=client)

    v1 = service.publish(reason="Initial sync", actor_user_id="admin_1")
    db.commit()
    assert len(v1.payload) == 1

    second_preview = service.preview()
    assert second_preview["changedCount"] == 0, (
        "publish() must be idempotent -- rerunning with unchanged Mock LMS "
        "data should detect nothing to change"
    )

    v2 = service.publish(reason="No-op resync", actor_user_id="admin_1")
    db.commit()
    assert len(v2.payload) == 0


def test_a_real_deadline_change_is_still_detected_after_a_prior_publish(db):
    """The idempotency fix above must not make the service blind to genuine
    subsequent changes (e.g. an admin editing the deadline in the Mock LMS
    UI, then re-syncing)."""
    client_v1 = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-09-30T00:00:00")
    MockLmsSyncService(db, client=client_v1).publish(reason="Initial sync", actor_user_id="admin_1")
    db.commit()

    client_v2 = _client_for("CEA201", "CEA201 name", "a1", "Assignment 1", "2026-10-15T00:00:00")
    service_v2 = MockLmsSyncService(db, client=client_v2)
    preview2 = service_v2.preview()
    assert preview2["changedCount"] == 1
    assert preview2["changes"][0]["before"] == "2026-09-30T00:00:00"
    assert preview2["changes"][0]["after"] == "2026-10-15T00:00:00"
