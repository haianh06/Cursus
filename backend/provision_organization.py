# provision_organization.py
#
# Creates an organization's Job #0: the org row itself plus its first Admin
# user — the only account-creation path that isn't gated by an invite,
# because it's what *issues* the very first invite. Real institutions get
# exactly this once, run by ops/the Cursus team, never by an end user.
#
# For a sandbox-kind org, also seeds the 2 other demo role accounts
# (Instructor, Student) with fixed, well-known emails — these are the 3
# accounts POST /auth/demo-session logs a visitor into. Password is a real
# random Argon2-hashed secret nobody needs to know, because the frontend
# never authenticates the demo accounts with a password (see /demo/select-role).
#
# Usage:
#   python provision_organization.py <slug> "<name>" <production|sandbox> \
#       --admin-email admin@school.edu --admin-name "Jane Admin"
#
# Idempotent: re-running with the same slug/emails updates nothing and
# reports what already exists, never duplicates or overwrites.
import argparse
import secrets
import sys
import os
import uuid
from datetime import UTC, datetime

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.db.connection import SessionLocal
from src.db.models import Organization, OrganizationMembership, User, UserRole
from src.security.passwords import hash_password


def _now():
    return datetime.now(UTC).replace(tzinfo=None)


def _ensure_org(db, slug: str, name: str, kind: str) -> Organization:
    org = db.query(Organization).filter_by(slug=slug).first()
    if org:
        print(f"[provision] Organization '{slug}' already exists.")
        return org
    org = Organization(
        id=f"org_{uuid.uuid4().hex}",
        name=name,
        slug=slug,
        kind=kind,
        created_at=_now(),
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    print(f"[provision] Created organization '{slug}' ({kind}).")
    return org


def _ensure_user(db, org: Organization, email: str, full_name: str, role: str) -> User:
    user = db.query(User).filter_by(email=email).first()
    if user:
        print(f"[provision] User {email} already exists, skipping.")
        return user
    user = User(
        id=f"user_{uuid.uuid4().hex}",
        email=email,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        full_name=full_name,
        role=role,
        organization_id=org.id,
        is_email_verified=True,
        is_active=True,
        created_at=_now(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(
        OrganizationMembership(
            id=f"orgmem_{uuid.uuid4().hex}",
            user_id=user.id,
            organization_id=org.id,
            role=role,
            created_at=_now(),
        )
    )
    db.commit()
    print(f"[provision] Created {role} {email} in '{org.slug}'.")
    return user


DEMO_ROLE_ACCOUNTS = [
    ("demo.student@cursusdemo.local", "Demo Student", UserRole.STUDENT.value),
    ("demo.instructor@cursusdemo.local", "Demo Instructor", UserRole.INSTRUCTOR.value),
    ("demo.admin@cursusdemo.local", "Demo Admin", UserRole.ADMIN.value),
]


def main():
    parser = argparse.ArgumentParser(description="Provision a new Cursus organization")
    parser.add_argument("slug")
    parser.add_argument("name")
    parser.add_argument("kind", choices=["production", "sandbox"])
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-name", required=True)
    args = parser.parse_args()

    db = SessionLocal()
    try:
        org = _ensure_org(db, args.slug, args.name, args.kind)
        _ensure_user(db, org, args.admin_email, args.admin_name, UserRole.ADMIN.value)

        if args.kind == "sandbox":
            for email, full_name, role in DEMO_ROLE_ACCOUNTS:
                _ensure_user(db, org, email, full_name, role)
    finally:
        db.close()

    print("[provision] Done.")


if __name__ == "__main__":
    main()
