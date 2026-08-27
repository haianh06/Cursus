"""Unit tests for create_self_reported_help_alert (PROJECT_CONTEXT.md §13.3).

Wired into POST /student/reflections when a confirmed reflection includes
the "request_help" adjustment — see src/api/student.py::save_reflection.
"""

from __future__ import annotations

import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.services.risk_signal_service import create_self_reported_help_alert
from tests.support.semester_practice_fixtures import (
    enroll_student,
    ensure_course,
    ensure_org,
    ensure_user,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _setup_student_with_section(*, prefix: str) -> tuple[str, str]:
    org_id = ensure_org(f"risksig-org-{prefix}", f"Risk Signal Org {prefix}")
    student_id = ensure_user(
        email=f"risksig.student.{prefix}.{uuid.uuid4().hex}@example.test",
        org_id=org_id,
        role=models.UserRole.STUDENT,
    )
    instructor_id = ensure_user(
        email=f"risksig.instr.{prefix}.{uuid.uuid4().hex}@example.test",
        org_id=org_id,
        role=models.UserRole.INSTRUCTOR,
    )
    course_id = ensure_course(code=f"RSK{prefix.upper()}", org_id=org_id, name="Risk Signal Course")
    section_id = enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)
    return student_id, section_id


def test_creates_one_open_high_signal_per_section(db):
    student_id, section_id = _setup_student_with_section(prefix="a")
    rows = create_self_reported_help_alert(db, student_id, 1, "Cần hỗ trợ gấp")
    assert len(rows) == 1
    assert rows[0].section_id == section_id
    assert rows[0].risk_type == "SELF_REPORTED_HELP_REQUEST"
    assert rows[0].risk_level == "HIGH"
    assert rows[0].resolved_at is None
    assert rows[0].evidence["weekNumber"] == 1
    assert rows[0].evidence["note"] == "Cần hỗ trợ gấp"


def test_second_call_updates_the_existing_open_signal_instead_of_duplicating(db):
    """Saving the reflection again this week (or a later week) while the
    first alert is still open must refresh it, not pile up duplicates in
    the instructor's HITL queue."""
    student_id, section_id = _setup_student_with_section(prefix="b")
    create_self_reported_help_alert(db, student_id, 1, "tuần 1")
    rows = create_self_reported_help_alert(db, student_id, 2, "tuần 2")
    assert len(rows) == 1

    open_signals = (
        db.query(models.RiskSignal)
        .filter_by(
            student_id=student_id,
            section_id=section_id,
            risk_type="SELF_REPORTED_HELP_REQUEST",
        )
        .all()
    )
    assert len(open_signals) == 1
    assert open_signals[0].evidence["weekNumber"] == 2
    assert open_signals[0].evidence["note"] == "tuần 2"


def test_creates_a_signal_for_every_enrolled_section(db):
    student_id, section_a = _setup_student_with_section(prefix="c1")
    org_id = ensure_org("risksig-org-c2", "Risk Signal Org C2")
    instructor_id = ensure_user(
        email=f"risksig.instr.c2.{uuid.uuid4().hex}@example.test",
        org_id=org_id,
        role=models.UserRole.INSTRUCTOR,
    )
    course_id = ensure_course(code="RSKC2", org_id=org_id, name="Risk Signal Course C2")
    section_b = enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)

    rows = create_self_reported_help_alert(db, student_id, 1, None)
    section_ids = {row.section_id for row in rows}
    assert section_ids == {section_a, section_b}
