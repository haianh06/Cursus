# src/api/self_study.py
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles
from src.services.academic.self_study_service import (
    SelfStudyConflictError,
    SelfStudyService,
    SelfStudyWindowError,
)

router = APIRouter(
    prefix="/student/self-study",
    tags=["student-self-study"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


class StartSelfStudyRequest(BaseModel):
    block_id: str = Field(alias="blockId")


def _http_for(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc) or "Not found")
    if isinstance(exc, SelfStudyWindowError):
        # Deliberately 400, not 403 -- a 403 on any authenticated endpoint
        # trips the frontend's global auto-logout handler.
        return HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, SelfStudyConflictError):
        return HTTPException(status_code=409, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail="Internal error")


@router.get("/upcoming")
def get_upcoming(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return SelfStudyService(db).upcoming(student_id=current_user.id)


@router.get("/weekly-stats")
def get_weekly_stats(
    week_start: date | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return SelfStudyService(db).weekly_stats(student_id=current_user.id, week_start=week_start)


@router.get("/sessions/active")
def get_active_session(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return SelfStudyService(db).active(student_id=current_user.id)


@router.post("/sessions")
def start_session(
    payload: StartSelfStudyRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        return SelfStudyService(db).start(student_id=current_user.id, block_id=payload.block_id)
    except (LookupError, ValueError) as exc:
        db.rollback()
        raise _http_for(exc) from exc


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        return SelfStudyService(db).get_session(student_id=current_user.id, session_id=session_id)
    except LookupError as exc:
        raise _http_for(exc) from exc


@router.post("/sessions/{session_id}/abandon")
def abandon_session(
    session_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        return SelfStudyService(db).abandon(student_id=current_user.id, session_id=session_id)
    except LookupError as exc:
        raise _http_for(exc) from exc
