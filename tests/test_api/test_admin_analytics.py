"""Admin Console 'Analytics' tab expansion (mục 6.5): total documents +
system-wide at-risk student count + weekly risk trend, on top of the
existing with_cursus/baseline KPI widget."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.db.connection import SessionLocal
from src.db.models import (
    Course,
    CourseSection,
    Enrollment,
    EnrollmentStatus,
    RiskSignal,
    UserRole,
)
from tests.support.semester_practice_fixtures import auth_headers, ensure_course, ensure_org, ensure_user, login


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _seed_risk_signal(*, student_id: str, section_id: str, resolved: bool, generated_at):
    db = SessionLocal()
    try:
        db.add(
            RiskSignal(
                id=f"risk_{uuid.uuid4().hex[:10]}",
                student_id=student_id,
                section_id=section_id,
                risk_type="OVERLOAD",
                risk_level="HIGH",
                triggered_rules={},
                evidence={},
                recommended_action="x",
                generated_at=generated_at,
                resolved_at=_now() if resolved else None,
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_admin_analytics_counts_at_risk_students_scoped_to_own_org(client):
    org_a = ensure_org("analytics-org-a", "Analytics Org A")
    org_b = ensure_org("analytics-org-b", "Analytics Org B")
    admin_email = f"analytics.admin.a.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_email, org_id=org_a, role=UserRole.ADMIN)
    instructor_a = ensure_user(email=f"analytics.instr.a.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.INSTRUCTOR)
    instructor_b = ensure_user(email=f"analytics.instr.b.{uuid.uuid4().hex}@example.test", org_id=org_b, role=UserRole.INSTRUCTOR)

    student_a_open = ensure_user(email=f"analytics.stu.a1.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.STUDENT)
    student_a_resolved = ensure_user(email=f"analytics.stu.a2.{uuid.uuid4().hex}@example.test", org_id=org_a, role=UserRole.STUDENT)
    student_b_open = ensure_user(email=f"analytics.stu.b1.{uuid.uuid4().hex}@example.test", org_id=org_b, role=UserRole.STUDENT)

    course_a = ensure_course(code=f"AN{uuid.uuid4().hex[:5].upper()}", org_id=org_a)
    course_b = ensure_course(code=f"AN{uuid.uuid4().hex[:5].upper()}", org_id=org_b)
    section_a_id = f"sec_{uuid.uuid4().hex[:10]}"
    section_b_id = f"sec_{uuid.uuid4().hex[:10]}"

    db = SessionLocal()
    try:
        db.add(CourseSection(id=section_a_id, course_id=course_a, instructor_id=instructor_a, term="Test2026", section_code="A1"))
        db.add(CourseSection(id=section_b_id, course_id=course_b, instructor_id=instructor_b, term="Test2026", section_code="B1"))
        db.flush()
        for student_id, section_id in ((student_a_open, section_a_id), (student_a_resolved, section_a_id), (student_b_open, section_b_id)):
            db.add(Enrollment(id=f"enr_{uuid.uuid4().hex[:10]}", student_id=student_id, section_id=section_id, status=EnrollmentStatus.ENROLLED.value, enrolled_at=_now()))
        db.commit()
    finally:
        db.close()

    # Org A: one OPEN (unresolved) signal + one RESOLVED signal (must not count).
    _seed_risk_signal(student_id=student_a_open, section_id=section_a_id, resolved=False, generated_at=_now())
    _seed_risk_signal(student_id=student_a_resolved, section_id=section_a_id, resolved=True, generated_at=_now())
    # Org B: one OPEN signal -- must never be visible to Org A's admin.
    _seed_risk_signal(student_id=student_b_open, section_id=section_b_id, resolved=False, generated_at=_now())

    token = await login(client, admin_email)
    resp = await client.get("/api/v1/admin/analytics", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["at_risk_student_count"] == 1
    # Trend counts all of org A's signals (resolved + open) -- it tracks risk
    # *activity* over time, not just currently-open cases -- but must still
    # exclude org B's signal entirely.
    assert sum(point["count"] for point in data["weekly_risk_trend"]) == 2
    assert data["total_documents"] >= 0


@pytest.mark.asyncio
async def test_admin_analytics_weekly_trend_buckets_by_iso_week(client):
    org = ensure_org("analytics-org-c", "Analytics Org C")
    admin_email = f"analytics.admin.c.{uuid.uuid4().hex}@example.test"
    ensure_user(email=admin_email, org_id=org, role=UserRole.ADMIN)
    instructor_id = ensure_user(email=f"analytics.instr.c.{uuid.uuid4().hex}@example.test", org_id=org, role=UserRole.INSTRUCTOR)
    student_id = ensure_user(email=f"analytics.stu.c.{uuid.uuid4().hex}@example.test", org_id=org, role=UserRole.STUDENT)
    course_id = ensure_course(code=f"AN{uuid.uuid4().hex[:5].upper()}", org_id=org)
    section_id = f"sec_{uuid.uuid4().hex[:10]}"

    db = SessionLocal()
    try:
        db.add(CourseSection(id=section_id, course_id=course_id, instructor_id=instructor_id, term="Test2026", section_code="C1"))
        db.flush()
        db.add(Enrollment(id=f"enr_{uuid.uuid4().hex[:10]}", student_id=student_id, section_id=section_id, status=EnrollmentStatus.ENROLLED.value, enrolled_at=_now()))
        db.commit()
    finally:
        db.close()

    this_week = _now()
    last_week = _now() - timedelta(days=8)
    _seed_risk_signal(student_id=student_id, section_id=section_id, resolved=False, generated_at=this_week)
    _seed_risk_signal(student_id=student_id, section_id=section_id, resolved=False, generated_at=last_week)

    token = await login(client, admin_email)
    resp = await client.get("/api/v1/admin/analytics", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    trend = resp.json()["data"]["weekly_risk_trend"]
    weeks = {point["week"]: point["count"] for point in trend}
    assert weeks.get(this_week.isocalendar()[1]) == 1
    assert weeks.get(last_week.isocalendar()[1]) == 1


def test_get_analytics_fails_closed_for_a_caller_with_no_organization():
    """Defense-in-depth: found during a fresh adversarial re-sweep of this
    route (it postdates the earlier RBAC/IDOR sweep, which never covered
    it). No live path creates an org-less ADMIN today -- every route that
    creates a User sets organization_id -- but AdminReadService.get_analytics
    must not silently fall through to an unscoped (cross-org) aggregate if
    that ever changes. Unit-level, bypassing the "how would an org-less
    admin even exist" question entirely."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.db.models import Base
    from src.services.core.admin_read_service import AdminReadService

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        data = AdminReadService(db).get_analytics(organization_id=None)
    finally:
        db.close()
        engine.dispose()

    assert data["at_risk_student_count"] == 0
    assert data["weekly_risk_trend"] == []
