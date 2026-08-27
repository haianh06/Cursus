"""Admin/CTSV-only queue for Cursus Chat crisis-safety triggers. Deliberately
separate from `src/api/instructor.py`'s guardrail review queue — see
`models.CrisisEscalation`'s docstring for why."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.audit_repository import AuditRepository
from src.security.authorization import require_roles
from src.services.core.audit_service import AuditService

router = APIRouter(
    prefix="/admin/crisis-escalations",
    tags=["admin-crisis-escalations"],
    dependencies=[Depends(require_roles(models.UserRole.ADMIN))],
)


class ResolveRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000)


def _serialize(row: models.CrisisEscalation) -> dict:
    return {
        "id": row.id,
        "studentId": row.student_id,
        "conversationId": row.conversation_id,
        "messageExcerpt": row.message_excerpt,
        "status": row.status,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "acknowledgedBy": row.acknowledged_by,
        "acknowledgedAt": row.acknowledged_at.isoformat() if row.acknowledged_at else None,
        "resolutionNote": row.resolution_note,
    }


@router.get("")
def list_crisis_escalations(
    status_filter: str | None = None,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    query = db.query(models.CrisisEscalation)
    if status_filter:
        query = query.filter_by(status=status_filter.upper())
    rows = query.order_by(models.CrisisEscalation.created_at.desc()).limit(200).all()
    students = {
        row.id: row.full_name
        for row in db.query(models.User).filter(models.User.id.in_([r.student_id for r in rows])).all()
    }
    items = []
    for row in rows:
        item = _serialize(row)
        item["studentName"] = students.get(row.student_id, "Unknown")
        items.append(item)
    return {"items": items}


@router.post("/{escalation_id}/acknowledge")
async def acknowledge_crisis_escalation(
    escalation_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    row = db.query(models.CrisisEscalation).filter_by(id=escalation_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Crisis escalation not found")
    if row.status == "OPEN":
        row.acknowledged_by = current_user.id
        row.acknowledged_at = datetime.utcnow()
        row.status = "ACKNOWLEDGED"
        db.commit()
        await AuditService(AuditRepository(db)).log_event(
            event_type="CRISIS_ESCALATION_ACKNOWLEDGED", decision="ALLOW",
            actor_user_id=current_user.id, resource_type="CRISIS_ESCALATION", resource_id=row.id,
        )
    return _serialize(row)


@router.post("/{escalation_id}/resolve")
async def resolve_crisis_escalation(
    escalation_id: str,
    payload: ResolveRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    row = db.query(models.CrisisEscalation).filter_by(id=escalation_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Crisis escalation not found")
    row.status = "RESOLVED"
    row.resolution_note = payload.note
    if row.acknowledged_by is None:
        row.acknowledged_by = current_user.id
        row.acknowledged_at = datetime.utcnow()
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="CRISIS_ESCALATION_RESOLVED", decision="ALLOW",
        actor_user_id=current_user.id, resource_type="CRISIS_ESCALATION", resource_id=row.id,
    )
    return _serialize(row)
