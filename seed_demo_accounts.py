# seed_demo_accounts.py
#
# Minimal, idempotent seeder for the 3 reviewer/demo accounts (student,
# instructor, admin). Unlike seed.py --reset, this never truncates or
# touches any other table — it only upserts 3 rows in `users` by primary
# key, safe to run against a shared database that already has real data.
#
# Usage: python seed_demo_accounts.py
import sys
import os
import uuid
from datetime import UTC, datetime, timedelta

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.db.connection import SessionLocal
from src.db.models import Organization, OrganizationMembership, User, UserRole
from src.security.passwords import hash_password

DEMO_PASSWORD_HASH = hash_password("password123")
FPT_ORG_SLUG = "fpt-university"

DEMO_ACCOUNTS = [
    dict(id="student_ethan", email="student.demo@example.test",
         full_name="Ethan Nguyen", role=UserRole.STUDENT.value),
    dict(id="inst_demo", email="instructor.demo@example.test",
         full_name="Dr. Hoang Minh Nguyen", role=UserRole.INSTRUCTOR.value),
    dict(id="admin_demo", email="admin.demo@example.test",
         full_name="Le Thi Admin", role=UserRole.ADMIN.value),
]


def main():
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=FPT_ORG_SLUG).first()
        if not org:
            print(
                f"[seed-demo] No '{FPT_ORG_SLUG}' organization found — run the "
                "20260812_organizations_and_tenancy migration first "
                "(alembic upgrade head)."
            )
            sys.exit(1)

        now = datetime.now(UTC).replace(tzinfo=None)
        for acc in DEMO_ACCOUNTS:
            existing = db.query(User).filter_by(email=acc["email"]).first()
            if existing:
                print(f"[seed-demo] {acc['email']} already exists, skipping.")
                continue
            db.add(User(
                id=acc["id"],
                email=acc["email"],
                password_hash=DEMO_PASSWORD_HASH,
                full_name=acc["full_name"],
                role=acc["role"],
                organization_id=org.id,
                is_email_verified=True,
                created_at=datetime.utcnow() - timedelta(days=365),
            ))
            # No relationship() links User <-> OrganizationMembership, so the
            # ORM has no instance-level dependency info and won't reliably
            # order the INSERTs by FK on its own — flush the user row first.
            db.flush()
            db.add(OrganizationMembership(
                id=f"orgmem_{uuid.uuid4().hex}",
                user_id=acc["id"],
                organization_id=org.id,
                role=acc["role"],
                created_at=now,
            ))
            print(f"[seed-demo] Created {acc['role']}: {acc['email']} (org={org.slug})")
        db.commit()
        print("[seed-demo] Done.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
