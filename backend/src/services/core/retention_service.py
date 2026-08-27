"""Periodic (not just lazy-on-request) cleanup for Cursus Chat's
time-bounded tables. `cursus_chat.py::_cleanup()` still runs on every
request as a cheap first line of defense, but a student who never chats
again would otherwise leave rows behind forever until someone else's
request happens to sweep them — this runs on a schedule regardless of
traffic (see `src.main`'s APScheduler wiring)."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.db import models

# Confirmed/expired action proposals and old briefing impressions carry no
# ongoing purpose once stale, but keeping them briefly (rather than deleting
# immediately on expiry) leaves a short audit trail for support/debugging.
_ACTION_PROPOSAL_RETENTION = timedelta(days=30)
_BRIEFING_IMPRESSION_RETENTION = timedelta(days=90)


def run_retention(db: Session) -> dict[str, int]:
    now = datetime.utcnow()
    result = {
        "conversations_deleted": 0,
        "action_proposals_expired": 0,
        "action_proposals_deleted": 0,
        "briefing_impressions_deleted": 0,
    }

    result["conversations_deleted"] = (
        db.query(models.ChatConversation)
        .filter(models.ChatConversation.expires_at <= now)
        .delete(synchronize_session=False)
    )

    result["action_proposals_expired"] = (
        db.query(models.ChatActionProposal)
        .filter(models.ChatActionProposal.status == "PENDING", models.ChatActionProposal.expires_at <= now)
        .update({"status": "EXPIRED"}, synchronize_session=False)
    )

    result["action_proposals_deleted"] = (
        db.query(models.ChatActionProposal)
        .filter(
            models.ChatActionProposal.status.in_(["CONFIRMED", "CANCELLED", "EXPIRED"]),
            models.ChatActionProposal.expires_at <= now - _ACTION_PROPOSAL_RETENTION,
        )
        .delete(synchronize_session=False)
    )

    result["briefing_impressions_deleted"] = (
        db.query(models.ChatBriefingImpression)
        .filter(models.ChatBriefingImpression.shown_at <= now - _BRIEFING_IMPRESSION_RETENTION)
        .delete(synchronize_session=False)
    )

    db.commit()
    return result
