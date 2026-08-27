import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.db.models import AuditLog, User

logger = logging.getLogger(__name__)


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def add(self, audit_log: AuditLog, *, commit: bool = True) -> AuditLog | None:
        self._db.add(audit_log)
        if commit:
            # `commit=True` callers (login, guardrail decisions, etc.) treat
            # this as a trailing, already-independent side effect -- by the
            # time this runs, whatever it's auditing (session creation, a
            # guardrail block) has already happened and, where relevant,
            # already been committed in its own earlier transaction. So a
            # rollback here only discards this one audit-log insert, never
            # unrelated pending work -- safe to swallow a write failure
            # rather than let a security-relevant primary flow 500 because
            # its *audit trail* couldn't be written (e.g. the live Supabase
            # dev DB not yet having `organization_id` applied via
            # scripts/sql/add_audit_log_org_scoping_22aug.sql -- this was
            # silently taking down EVERY login until caught 22/08).
            # `commit=False` callers batch this into a caller-owned
            # transaction alongside other pending writes; rolling back here
            # would discard that unrelated work too, so those still raise
            # unchanged -- narrower blast radius (one admin mutation fails
            # loudly) than login being unusable app-wide.
            try:
                self._db.commit()
                self._db.refresh(audit_log)
            except SQLAlchemyError:
                self._db.rollback()
                logger.exception(
                    "audit_log_write_failed event_type=%s -- continuing without an audit trail "
                    "for this event rather than blocking the primary flow it accompanies",
                    audit_log.event_type,
                )
                return None
        else:
            self._db.flush()
        return audit_log

    def get_org_for_user(self, user_id: str | None) -> str | None:
        """Best-effort lookup used to stamp a new AuditLog row with the
        actor's *current* organization at write time (mục 9 ý2). Returns
        None for a missing/anonymous actor -- log_event() still writes the
        row, just without an organization_id, exactly like every other
        field on this table that can be None."""
        if not user_id:
            return None
        user = self._db.query(User).filter_by(id=user_id).first()
        return user.organization_id if user else None

    def list_events(
        self,
        *,
        event_type: str | None = None,
        actor_user_id: str | None = None,
        organization_id: str | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        query = self._db.query(AuditLog)
        if event_type:
            query = query.filter_by(event_type=event_type)
        if actor_user_id:
            query = query.filter_by(actor_user_id=actor_user_id)
        if organization_id:
            # Exact match only -- a NULL organization_id row (pre-backfill
            # history, or a system event with no actor) is excluded for
            # every viewer rather than shown to everyone. See the model's
            # own comment for why that's the safe default here.
            query = query.filter(AuditLog.organization_id == organization_id)
        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()
