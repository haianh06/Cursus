"""Generate SYNTHETIC assignment/deadline data for every seeded course.

Confirmed by direct inspection of 4 different parsed syllabus files (PRF192, CEA201,
MAS291, SWE202c -- see plan discussion) that the real syllabus chunks contain NO
structured assignment list, due dates, or per-component grading weights -- only
qualitative policy text ("submit on time", "attend >=80% of sessions"). There is nothing
to extract, so this script invents a plausible-but-fake assignment schedule instead of
trying to parse one out of text that doesn't contain it.

This is simulated data in the same sense as the rest of the project's `simulated`
provenance tier (mục 16 data contract in PROJECT_CONTEXT.md) -- good enough to
demonstrate the sync/draft/approve flow, not a claim about FPT's real assignment
calendar for these courses.
"""
from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import Base, ENGINE, SessionLocal  # noqa: E402
from app.models import PlatformAssignment, PlatformCourse  # noqa: E402

TERM_START = datetime(2026, 8, 24)  # arbitrary Monday, illustrative only

# (name, week offset, points) -- 4 checkpoints per course, points sum to 100.
TEMPLATE = [
    ("Assignment 1", 4, 15),
    ("Assignment 2", 8, 15),
    ("Progress Test", 10, 20),
    ("Final Project", 14, 50),
]


def main() -> None:
    Base.metadata.create_all(bind=ENGINE)
    db = SessionLocal()
    try:
        courses = db.query(PlatformCourse).order_by(PlatformCourse.code).all()
        created = 0
        for course in courses:
            for name, week_offset, points in TEMPLATE:
                assignment_id = f"{course.id}_{name.lower().replace(' ', '_')}"
                assignment = db.get(PlatformAssignment, assignment_id)
                due_at = TERM_START + timedelta(weeks=week_offset)
                if assignment is None:
                    assignment = PlatformAssignment(
                        id=assignment_id,
                        course_id=course.id,
                        name=name,
                        description=f"Synthetic checkpoint for {course.code} (Mock LMS demo data).",
                        due_at=due_at,
                        points_possible=points,
                        updated_at=datetime.utcnow(),
                    )
                    db.add(assignment)
                    created += 1
                else:
                    # Idempotent re-run: keep any manually-edited due_at (via the web UI)
                    # untouched, only backfill if somehow missing.
                    if assignment.due_at is None:
                        assignment.due_at = due_at
        db.commit()
        print(f"Seeded assignments for {len(courses)} courses ({created} rows created).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
