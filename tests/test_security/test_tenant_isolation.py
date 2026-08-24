"""Cross-tenant isolation tests for the B2B2C org model.

Scope note: this pass adds `organization_id` to the identity/catalog root
tables (users, organizations, org_invites, courses, programs,
curriculum_versions) and enforces org scoping on the endpoints that
actually read/write those tables today (invite creation/listing/revoke,
registration). Existing student/instructor data endpoints
(courses/enrollments/plans/etc.) are NOT yet org-filtered — that's tracked
as a fast-follow in docs/planning/v2/11-Cursus-ERD-Multitenancy.md, not
silently assumed done here.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from src.db.connection import SessionLocal, engine
from src.db.models import Organization, OrgInvite, User, UserRole
from src.repositories.org_invite_repository import OrgInviteRepository
from src.security.passwords import hash_password
from src.security.tokens import hash_opaque_token


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _ensure_org(slug: str, name: str) -> str:
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=slug).first()
        if org:
            return org.id
        org = Organization(
            id=f"org_{uuid.uuid4().hex}", name=name, slug=slug, kind="production", created_at=_now()
        )
        db.add(org)
        db.commit()
        return org.id
    finally:
        db.close()


def _ensure_admin(email: str, org_id: str, password: str = "AdminPassword123") -> None:
    db = SessionLocal()
    try:
        if db.query(User).filter_by(email=email).first():
            return
        db.add(
            User(
                id=f"user_{uuid.uuid4().hex}",
                email=email,
                password_hash=hash_password(password),
                full_name="Org Admin",
                role=UserRole.ADMIN.value,
                organization_id=org_id,
                is_email_verified=True,
                is_active=True,
                created_at=_now(),
            )
        )
        db.commit()
    finally:
        db.close()


def _insert_invite(*, organization_id: str, email: str, role: str = "STUDENT") -> OrgInvite:
    db = SessionLocal()
    try:
        invite = OrgInvite(
            id=f"invite_{uuid.uuid4().hex}",
            organization_id=organization_id,
            email=email,
            full_name="Invitee",
            role=role,
            invited_by_user_id=None,
            token_hash=hash_opaque_token(f"tok-{uuid.uuid4().hex}"),
            expires_at=_now() + timedelta(days=1),
            created_at=_now(),
        )
        db.add(invite)
        db.commit()
        db.refresh(invite)
        return invite
    finally:
        db.close()


async def _login(client, email: str, password: str = "AdminPassword123") -> str:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]


@pytest.mark.asyncio
async def test_admin_cannot_list_another_orgs_invites(client):
    org_a = _ensure_org("test-org-a", "Org A")
    org_b = _ensure_org("test-org-b", "Org B")
    _ensure_admin("admin.orga@example.test", org_a)
    _ensure_admin("admin.orgb@example.test", org_b)
    _insert_invite(organization_id=org_a, email="student.orga@example.test")
    _insert_invite(organization_id=org_b, email="student.orgb@example.test")

    token_a = await _login(client, "admin.orga@example.test")
    response = await client.get(
        "/api/v1/admin/invites", headers={"Authorization": f"Bearer {token_a}"}
    )
    assert response.status_code == 200
    emails = {invite["email"] for invite in response.json()}
    assert "student.orga@example.test" in emails
    assert "student.orgb@example.test" not in emails


@pytest.mark.asyncio
async def test_admin_cannot_revoke_another_orgs_invite(client):
    org_a = _ensure_org("test-org-a", "Org A")
    org_b = _ensure_org("test-org-b", "Org B")
    _ensure_admin("admin.orga@example.test", org_a)
    _ensure_admin("admin.orgb@example.test", org_b)
    foreign_invite = _insert_invite(organization_id=org_b, email="foreign.student@example.test")

    token_a = await _login(client, "admin.orga@example.test")
    response = await client.delete(
        f"/api/v1/admin/invites/{foreign_invite.id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_register_assigns_organization_from_invite_not_client(client):
    org_a = _ensure_org("test-org-a", "Org A")
    email = f"newmember.{uuid.uuid4().hex}@example.test"
    fixed_token = f"fixed-token-{uuid.uuid4().hex}"

    db = SessionLocal()
    try:
        db.add(
            OrgInvite(
                id=f"invite_{uuid.uuid4().hex}",
                organization_id=org_a,
                email=email,
                full_name="Invitee",
                role="INSTRUCTOR",
                invited_by_user_id=None,
                token_hash=hash_opaque_token(fixed_token),
                expires_at=_now() + timedelta(days=1),
                created_at=_now(),
            )
        )
        db.commit()
    finally:
        db.close()

    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPassword123",
            "full_name": "New Instructor",
            "invite_token": fixed_token,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "INSTRUCTOR"
    assert body["user"]["organization_id"] == org_a

    db = SessionLocal()
    try:
        user = db.query(User).filter_by(email=email).first()
        assert user.organization_id == org_a
    finally:
        db.close()


def test_org_invite_repository_scopes_by_organization():
    """Repository-level unit test: list_for_org must never cross the
    organization boundary, independent of any API-layer check."""
    org_a = _ensure_org("test-org-a", "Org A")
    org_b = _ensure_org("test-org-b", "Org B")
    _insert_invite(organization_id=org_a, email=f"a.{uuid.uuid4().hex}@example.test")
    _insert_invite(organization_id=org_b, email=f"b.{uuid.uuid4().hex}@example.test")

    db = SessionLocal()
    try:
        repo = OrgInviteRepository(db)
        org_a_invites = repo.list_for_org(org_a)
        assert all(invite.organization_id == org_a for invite in org_a_invites)
    finally:
        db.close()


def test_db_connection_role_bypasses_rls_diagnostic():
    """Documents a real finding rather than hiding it: the app's Postgres
    connection role has BYPASSRLS, so the RLS policies created by
    migrations/versions/20260812_organizations_and_tenancy.py are inert for
    this connection today — application-layer organization_id filtering
    (exercised by the tests above) is the actual enforcement boundary.
    This test is Postgres-only (SQLite, used by the rest of the suite, has
    no such concept) and is skipped there rather than faked."""
    if engine.dialect.name != "postgresql":
        pytest.skip("BYPASSRLS is a Postgres-only concept; test suite runs on SQLite")

    with engine.connect() as conn:
        bypass = conn.execute(
            text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user")
        ).scalar()

    if bypass:
        pytest.xfail(
            "Known gap: DB role has BYPASSRLS, RLS policies are inert. "
            "See docs/planning/v2/11-Cursus-ERD-Multitenancy.md for the "
            "recommended least-privilege role remediation."
        )
    # If this ever starts failing (i.e. no longer xfails), it means the
    # connection role was fixed — update this test to assert real RLS
    # enforcement (e.g. SET LOCAL app.current_org_id + cross-org SELECT
    # returns zero rows) instead of just checking the role attribute.
