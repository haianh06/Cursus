"""Periodic (not just lazy-on-request) cleanup for Cursus Chat's
time-bounded tables. `cursus_chat.py::_cleanup()` still runs on every
request as a cheap first line of defense, but a student who never chats
again would otherwise leave rows behind forever until someone else's
request happens to sweep them — this runs on a schedule regardless of
traffic (see `src.main`'s APScheduler wiring).

Retention windows are read from Settings (env-configurable,
`CHAT_ACTION_PROPOSAL_RETENTION_DAYS`/`CHAT_BRIEFING_IMPRESSION_RETENTION_DAYS`)
rather than hardcoded — the 30/90-day defaults are an engineering judgment
call, not a data-retention policy decision an org has actually signed off
on; a real deployment should set these explicitly once that review happens.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from src.config import get_settings
from src.db import models


def run_retention(db: Session) -> dict[str, int]:
    settings = get_settings()
    action_proposal_retention = timedelta(days=settings.chat_action_proposal_retention_days)
    briefing_impression_retention = timedelta(days=settings.chat_briefing_impression_retention_days)
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
            models.ChatActionProposal.expires_at <= now - action_proposal_retention,
        )
        .delete(synchronize_session=False)
    )

    result["briefing_impressions_deleted"] = (
        db.query(models.ChatBriefingImpression)
        .filter(models.ChatBriefingImpression.shown_at <= now - briefing_impression_retention)
        .delete(synchronize_session=False)
    )

    db.commit()
    return result
