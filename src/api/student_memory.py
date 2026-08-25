# src/api/student_memory.py
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles
from src.services.ai.student_memory_service import StudentMemoryService

router = APIRouter(
    prefix="/student/memory",
    tags=["student-memory"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


class SetConsentRequest(BaseModel):
    granted: bool


@router.get("/consent")
def get_consent(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return {"granted": StudentMemoryService(db).has_consent(current_user.id)}


@router.put("/consent")
def put_consent(
    payload: SetConsentRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    granted = StudentMemoryService(db).set_consent(current_user.id, payload.granted)
    return {"granted": granted}


@router.get("")
def list_entries(
    subjectCode: str | None = Query(default=None, min_length=2, max_length=32),  # noqa: N803
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    service = StudentMemoryService(db)
    return {
        "granted": service.has_consent(current_user.id),
        "entries": service.list_entries(current_user.id, subjectCode),
    }


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    if not StudentMemoryService(db).delete_entry(current_user.id, entry_id):
        raise HTTPException(status_code=404, detail="Memory entry not found")
    return {"ok": True, "id": entry_id}


@router.delete("")
def forget_all(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    deleted = StudentMemoryService(db).forget_all(current_user.id)
    return {"ok": True, "deleted": deleted}
