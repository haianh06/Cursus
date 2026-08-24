"""`AuditRepository.add(commit=True)` must never let a write failure crash
the primary flow it accompanies -- found 22/08 when a live-DB schema gap
(`audit_logs.organization_id` not yet applied via
scripts/sql/add_audit_log_org_scoping_22aug.sql) was silently taking down
EVERY login, since `log_event()` runs as a trailing, committing side effect
of `POST /auth/login`."""
from __future__ import annotations

from sqlalchemy.exc import SQLAlchemyError

from src.db.connection import SessionLocal
from src.db.models import AuditLog
from src.repositories.audit_repository import AuditRepository


def _make_audit_log(event_type: str = "LOGIN_SUCCESS") -> AuditLog:
    import uuid
    from datetime import UTC, datetime

    return AuditLog(
        id=f"audit_{uuid.uuid4().hex}",
        actor_user_id=None,
        event_type=event_type,
        decision="ALLOW",
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )


def test_add_with_commit_true_succeeds_normally():
    db = SessionLocal()
    try:
        repo = AuditRepository(db)
        result = repo.add(_make_audit_log())
        assert result is not None
        assert result.id.startswith("audit_")
    finally:
        db.query(AuditLog).filter_by(id=result.id).delete()
        db.commit()
        db.close()


def test_add_with_commit_true_swallows_a_db_error_instead_of_raising(monkeypatch):
    db = SessionLocal()
    try:
        repo = AuditRepository(db)

        def _boom():
            raise SQLAlchemyError("simulated: column organization_id does not exist")

        monkeypatch.setattr(db, "commit", _boom)
        rolled_back = {"called": False}
        monkeypatch.setattr(db, "rollback", lambda: rolled_back.__setitem__("called", True))

        result = repo.add(_make_audit_log())

        assert result is None
        assert rolled_back["called"] is True
    finally:
        db.close()


def test_add_with_commit_false_still_raises_on_flush_failure(monkeypatch):
    # Batched (commit=False) callers own the transaction alongside other
    # pending writes -- swallowing here would silently discard THOSE too,
    # so this path is intentionally left to raise, unlike commit=True.
    db = SessionLocal()
    try:
        repo = AuditRepository(db)

        def _boom():
            raise SQLAlchemyError("simulated flush failure")

        monkeypatch.setattr(db, "flush", _boom)

        try:
            repo.add(_make_audit_log(), commit=False)
            raised = False
        except SQLAlchemyError:
            raised = True
        assert raised
    finally:
        db.rollback()
        db.close()
