"""Test-only helper for obtaining a usable, plaintext invite token.

Registration is invite-only (see `AuthService.register`): the role and
organization for a newly-registered user always come from a previously
issued `OrgInvite` row, never from the register request body. The plaintext
invite token is only ever available at creation time (it's hashed before
storage, and no API response ever echoes it back — it only goes out over
email), so the simplest reliable way for a test to obtain one is to insert
the `OrgInvite` row directly, mirroring the direct-DB-insert style already
used by `_deactivate_user` in `tests/test_api/test_auth_module.py` and
`tests/test_api/test_password_reset_module.py`.
"""

import uuid
from datetime import UTC, datetime, timedelta

from src.db.connection import SessionLocal
from src.db.models import Organization, OrgInvite, User
from src.security.passwords import hash_password
from src.security.tokens import hash_opaque_token


def create_test_invite(
    email: str,
    role: str = "STUDENT",
    *,
    full_name: str = "Test User",
    org_slug: str = "test-org",
) -> str:
    """Insert an `Organization` (if needed) and a valid `OrgInvite` for
    `email` directly via the DB, and return the plaintext invite token that
    can be passed as `invite_token` to `POST /auth/register`.
    """
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=org_slug).first()
        if not org:
            org = Organization(
                id=f"org_{uuid.uuid4().hex}",
                name="Test Org",
                slug=org_slug,
                kind="production",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(org)
            db.commit()

        token = f"test-invite-token-{uuid.uuid4().hex}"
        db.add(
            OrgInvite(
                id=f"invite_{uuid.uuid4().hex}",
                organization_id=org.id,
                email=email.strip().lower(),
                full_name=full_name,
                role=role,
                invited_by_user_id=None,
                token_hash=hash_opaque_token(token),
                expires_at=datetime.now(UTC).replace(tzinfo=None) + timedelta(days=1),
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
        return token
    finally:
        db.close()


def create_direct_user(
    email: str,
    password: str,
    *,
    full_name: str = "Test User",
    role: str = "STUDENT",
    is_email_verified: bool = False,
    is_active: bool = True,
) -> User:
    """Insert a `User` row directly, bypassing the invite/register flow.

    `AuthService.register` now unconditionally marks invited users as
    email-verified (the invite, sent to a known address, *is* the
    verification), so it can no longer produce an unverified user — which
    a handful of tests need in order to exercise the independent
    `/auth/email/*` verification-token endpoints. Those endpoints don't
    care how the user came to exist, so a direct insert is the simplest,
    most decoupled way to get one.
    """
    db = SessionLocal()
    try:
        user = User(
            id=f"user_{uuid.uuid4().hex}",
            email=email.strip().lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            organization_id=None,
            is_email_verified=is_email_verified,
            is_active=is_active,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()
