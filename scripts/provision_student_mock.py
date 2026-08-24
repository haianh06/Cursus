"""Backfill mock academic data for one or more Student accounts.

Examples:
  python scripts/provision_student_mock.py --email anhnguyenhaii2309@gmail.com
  python scripts/provision_student_mock.py --all-missing
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import get_settings
from src.db.connection import SessionLocal
from src.db.models import Enrollment, User, UserRole
from src.services.student_mock_data_service import StudentMockDataService


def main() -> int:
    parser = argparse.ArgumentParser(description="Provision mock student planner data")
    parser.add_argument("--email", help="Student email to provision")
    parser.add_argument(
        "--all-missing",
        action="store_true",
        help="Provision every STUDENT account that has zero enrollments",
    )
    args = parser.parse_args()

    get_settings.cache_clear()
    db = SessionLocal()
    service = StudentMockDataService(db)
    try:
        if args.email:
            user = db.query(User).filter_by(email=args.email.lower().strip()).first()
            if not user:
                print(f"User not found: {args.email}")
                return 1
            result = service.ensure_for_student(user.id)
            print(result)
            return 0

        if args.all_missing:
            students = db.query(User).filter_by(role=UserRole.STUDENT.value).all()
            count = 0
            for student in students:
                has_enrollment = (
                    db.query(Enrollment.id)
                    .filter_by(student_id=student.id)
                    .first()
                    is not None
                )
                if has_enrollment:
                    continue
                service.ensure_for_student(student.id)
                count += 1
                print(f"provisioned {student.email}")
            print(f"done: {count} students")
            return 0

        parser.error("Provide --email or --all-missing")
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
