"""Shared two-organization test fixtures for the Semester / Academic-term /
Practice-set / Companion-chat subsystems.

Mirrors the pattern in `tests/test_security/test_tenant_isolation.py`
(direct `SessionLocal()` inserts + `hash_password`) so org-isolation tests
for these new subsystems follow the same convention as the existing
tenancy tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from src.db.connection import SessionLocal
from src.db.models import (
    Course,
    CourseSection,
    Enrollment,
    EnrollmentStatus,
    Organization,
    User,
    UserRole,
)
from src.security.passwords import hash_password

PASSWORD = "TestPassword123"


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def ensure_org(slug: str, name: str) -> str:
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=slug).first()
        if org:
            return org.id
        org = Organization(id=f"org_{uuid.uuid4().hex}", name=name, slug=slug, kind="production", created_at=_now())
        db.add(org)
        db.commit()
        return org.id
    finally:
        db.close()


def ensure_user(*, email: str, org_id: str, role: UserRole, password: str = PASSWORD) -> str:
    db = SessionLocal()
    try:
        existing = db.query(User).filter_by(email=email).first()
        if existing:
            return existing.id
        user = User(
            id=f"user_{uuid.uuid4().hex}",
            email=email,
            password_hash=hash_password(password),
            full_name=email.split("@")[0],
            role=role.value,
            organization_id=org_id,
            is_email_verified=True,
            is_active=True,
            created_at=_now(),
        )
        db.add(user)
        db.commit()
        return user.id
    finally:
        db.close()


def ensure_course(*, code: str, org_id: str, name: str | None = None) -> str:
    db = SessionLocal()
    try:
        existing = db.query(Course).filter_by(code=code).first()
        if existing:
            return existing.id
        course = Course(
            id=code,
            code=code,
            name=name or code,
            description=f"Test course {code}",
            organization_id=org_id,
        )
        db.add(course)
        db.commit()
        return course.id
    finally:
        db.close()


def enroll_student(*, student_id: str, course_id: str, instructor_id: str, section_id: str | None = None) -> str:
    db = SessionLocal()
    try:
        section_id = section_id or f"sec_{uuid.uuid4().hex[:10]}"
        section = db.query(CourseSection).filter_by(id=section_id).first()
        if section is None:
            section = CourseSection(
                id=section_id,
                course_id=course_id,
                instructor_id=instructor_id,
                term="Test2026",
                section_code=f"SEC-{section_id[-6:]}",
            )
            db.add(section)
            db.flush()
        existing = (
            db.query(Enrollment).filter_by(student_id=student_id, section_id=section.id).first()
        )
        if existing is None:
            db.add(
                Enrollment(
                    id=f"enr_{uuid.uuid4().hex[:10]}",
                    student_id=student_id,
                    section_id=section.id,
                    status=EnrollmentStatus.ENROLLED.value,
                    enrolled_at=_now(),
                )
            )
        db.commit()
        return section.id
    finally:
        db.close()


async def login(client, email: str, password: str = PASSWORD) -> str:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    # `_extract_access_token` (src/api/auth.py) prefers the access-token
    # cookie over the Authorization header. httpx's AsyncClient keeps a
    # cookie jar across calls on the same `client` fixture, so a second
    # login (a different actor) would silently hijack every later Bearer
    # -token call in the test. Clear it so each returned token is the one
    # actually used.
    client.cookies.clear()
    return response.json()["token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
