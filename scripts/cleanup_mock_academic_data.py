"""Remove mock academic data that StudentMockDataService injected into
existing accounts (Weekly Planner production-readiness audit, item #1
cleanup — see docs shared with the product owner 2026-08-18).

This is a DATA cleanup, not a schema migration. Kept as a standalone,
idempotent script rather than an Alembic revision because it needs
dry-run preview, a per-row JSON backup, and safe re-run semantics that
don't fit Alembic's linear "applied once" model.

Scope is pattern-based, not hardcoded to any specific student — it
targets exactly the ID scheme StudentMockDataService uses when it
provisions mock academic data (see student_mock_data_service.py):

  - CourseSection.id LIKE 'section_mock_%'
    Deleting these cascades (DB-level ON DELETE CASCADE, see models.py)
    to every Enrollment / Assignment / CalendarEvent row that references
    them — there is no need to delete those tables separately.
  - RiskSignal rows whose `evidence` JSON is exactly the literal seed
    marker {"note": "demo risk for instructor.demo"} — a hardcoded
    demo-seed row (not created by StudentMockDataService, but confirmed
    via manual inspection to be fake, self-labeled as a demo artifact,
    not derived from real risk-policy logic).

Deliberately NEVER touched:
  - `courses` rows — SSA101/PRF192/CEA201/CSI106 are real curriculum
    catalog entries, also referenced by real SemesterSetup enrollments.
  - `documents` / `document_chunks` rows — syllabus/RAG content that may
    be the only material backing real chat history for a course, even
    though it was originally authored by the mock service.
  - Any CourseSection NOT matching the 'section_mock_' prefix (e.g. the
    docker startup demo seed's sec_ssa101_demo / sec_oth999_other — a
    separate, intentionally-gated demo dataset, out of scope here).

Usage:
    python scripts/cleanup_mock_academic_data.py --mode preview
    python scripts/cleanup_mock_academic_data.py --mode apply

--mode preview: writes a backup of everything that WOULD be deleted, then
runs the real DELETE statements inside a transaction and ROLLS BACK —
so the printed counts reflect exactly what Postgres's own cascade would
remove, without changing anything.

--mode apply: writes a fresh backup, then runs the same DELETE statements
and COMMITS. Safe to run more than once — a second run finds nothing
left matching the patterns above and deletes 0 rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select

from src.config import get_settings
from src.db import models
from src.db.connection import SessionLocal

MOCK_SECTION_PREFIX = "section_mock_"
DEMO_RISK_EVIDENCE_MARKER = {"note": "demo risk for instructor.demo"}


def _row_to_dict(row) -> dict:
    out = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, datetime):
            value = value.isoformat()
        out[column.name] = value
    return out


def find_mock_section_ids(db) -> list[str]:
    return list(
        db.scalars(
            select(models.CourseSection.id).where(
                models.CourseSection.id.like(f"{MOCK_SECTION_PREFIX}%")
            )
        )
    )


def find_demo_risk_signal_ids(db) -> list[str]:
    # `evidence` is a plain JSON column (not JSONB) — Postgres's plain
    # `json` type has no `=` operator, and matching on a specific JSON
    # path is unnecessarily DB-specific for what's a small maintenance
    # scan. Compare client-side instead so this works identically on
    # SQLite (tests) and Postgres (real deployments).
    rows = db.execute(select(models.RiskSignal.id, models.RiskSignal.evidence)).all()
    return [row.id for row in rows if row.evidence == DEMO_RISK_EVIDENCE_MARKER]


def collect_backup_payload(db, *, section_ids: list[str], risk_ids: list[str]) -> dict:
    """Fetch (not delete) every row that would be removed, for the JSON
    backup. Children of the mock sections are looked up explicitly here
    (rather than relied on ORM cascade loading) so the backup is complete
    even though the actual deletion later relies on DB-level cascade."""
    sections = db.scalars(
        select(models.CourseSection).where(models.CourseSection.id.in_(section_ids))
    ).all() if section_ids else []
    enrollments = db.scalars(
        select(models.Enrollment).where(models.Enrollment.section_id.in_(section_ids))
    ).all() if section_ids else []
    assignments = db.scalars(
        select(models.Assignment).where(models.Assignment.section_id.in_(section_ids))
    ).all() if section_ids else []
    calendar_events = db.scalars(
        select(models.CalendarEvent).where(models.CalendarEvent.section_id.in_(section_ids))
    ).all() if section_ids else []
    risk_signals = db.scalars(
        select(models.RiskSignal).where(models.RiskSignal.id.in_(risk_ids))
    ).all() if risk_ids else []

    return {
        "course_sections": [_row_to_dict(r) for r in sections],
        "enrollments": [_row_to_dict(r) for r in enrollments],
        "assignments": [_row_to_dict(r) for r in assignments],
        "calendar_events": [_row_to_dict(r) for r in calendar_events],
        "risk_signals": [_row_to_dict(r) for r in risk_signals],
    }


def write_backup(payload: dict, backup_dir: Path, *, label: str) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = backup_dir / f"mock_academic_data_backup_{label}_{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def delete_targets(db, *, section_ids: list[str], risk_ids: list[str]) -> None:
    """Issue the actual DELETE statements. Enrollment/Assignment/
    CalendarEvent rows are removed by the database's own ON DELETE
    CASCADE when their CourseSection is deleted — we only issue DELETE
    against CourseSection and RiskSignal directly. The child row counts
    reported to the caller come from `collect_backup_payload`, fetched
    just before this runs, not from this function."""
    if section_ids:
        db.execute(delete(models.CourseSection).where(models.CourseSection.id.in_(section_ids)))
    if risk_ids:
        db.execute(delete(models.RiskSignal).where(models.RiskSignal.id.in_(risk_ids)))


def run(*, mode: str, backup_dir: Path, db=None) -> dict:
    owns_session = db is None
    db = db or SessionLocal()
    try:
        section_ids = find_mock_section_ids(db)
        risk_ids = find_demo_risk_signal_ids(db)
        payload = collect_backup_payload(db, section_ids=section_ids, risk_ids=risk_ids)

        summary = {
            "mode": mode,
            "course_sections_matched": len(section_ids),
            "enrollments_to_cascade": len(payload["enrollments"]),
            "assignments_to_cascade": len(payload["assignments"]),
            "calendar_events_to_cascade": len(payload["calendar_events"]),
            "risk_signals_matched": len(risk_ids),
            "section_ids": section_ids,
            "risk_signal_ids": risk_ids,
        }

        if not section_ids and not risk_ids:
            summary["backup_path"] = None
            summary["note"] = "Nothing matched the mock-data patterns — already clean."
            return summary

        backup_path = write_backup(payload, backup_dir, label=mode)
        summary["backup_path"] = str(backup_path)

        if mode == "preview":
            delete_targets(db, section_ids=section_ids, risk_ids=risk_ids)
            db.rollback()
        elif mode == "apply":
            delete_targets(db, section_ids=section_ids, risk_ids=risk_ids)
            db.commit()
        else:
            raise ValueError(f"unknown mode: {mode}")

        return summary
    finally:
        if owns_session:
            db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--mode", choices=["preview", "apply"], required=True)
    parser.add_argument(
        "--backup-dir",
        default=str(ROOT / "data" / "mock_cleanup_backups"),
        help="Directory to write the JSON backup into",
    )
    args = parser.parse_args()

    get_settings.cache_clear()
    summary = run(mode=args.mode, backup_dir=Path(args.backup_dir))

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary.get("note"):
        return 0
    if args.mode == "preview":
        print("\nPREVIEW ONLY — transaction rolled back, nothing was actually deleted.")
    else:
        print("\nAPPLIED — changes committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
