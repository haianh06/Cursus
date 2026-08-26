"""Record and read Gemini quota-exhaustion (429 RESOURCE_EXHAUSTED) events.

No API exists to check remaining quota ahead of a call, so this is purely
reactive: `record_quota_event` is called right where a real call gets
rejected (`chat_answer_service.py`, `empathic_reply_service.py`), using its
own short-lived DB session so those call sites don't need a `db` parameter
threaded through them. `get_status` is the read side for the admin panel and
is safe to call with the request's own session.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_HOURS = 24


def record_quota_event(*, model: str, source: str) -> None:
    from src.db import models
    from src.db.connection import SessionLocal

    db = SessionLocal()
    try:
        db.add(
            models.LLMQuotaEvent(
                id=f"quota_{uuid.uuid4().hex[:16]}",
                occurred_at=datetime.utcnow(),
                model=model,
                source=source,
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001
        logger.exception("llm_quota_event_record_failed")
    finally:
        db.close()


def get_status(db, *, window_hours: int = DEFAULT_WINDOW_HOURS) -> dict:
    from src.db import models

    since = datetime.utcnow() - timedelta(hours=window_hours)
    events = (
        db.query(models.LLMQuotaEvent)
        .filter(models.LLMQuotaEvent.occurred_at >= since)
        .order_by(models.LLMQuotaEvent.occurred_at.desc())
        .all()
    )
    last = events[0] if events else None
    return {
        "windowHours": window_hours,
        "countInWindow": len(events),
        "lastExhaustedAt": last.occurred_at.isoformat() if last else None,
        "lastModel": last.model if last else None,
        "lastSource": last.source if last else None,
    }
