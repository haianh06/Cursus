"""Companion chat API: per-course conversational Q&A (separate thread surface
from the single-shot Study Assistant Q&A in `src/api/qa.py`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.schemas.companion import (
    CreateThreadRequest,
    MessageOut,
    SendMessageRequest,
    ThreadDetailOut,
    ThreadOut,
)
from src.security.authorization import require_roles
from src.services.ai.companion_service import CompanionService

router = APIRouter(
    prefix="/student/companion",
    tags=["companion-chat"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


def get_service(db: Session = Depends(get_db)) -> CompanionService:
    return CompanionService(db)


@router.get("/threads", response_model=list[ThreadOut])
def list_threads(
    subject_code: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: CompanionService = Depends(get_service),
) -> list[ThreadOut]:
    try:
        rows = service.list_threads(student_id=current_user.id, subject_code=subject_code)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return [ThreadOut(**row) for row in rows]


@router.post("/threads", response_model=ThreadOut, status_code=201)
def create_thread(
    payload: CreateThreadRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: CompanionService = Depends(get_service),
) -> ThreadOut:
    try:
        row = service.create_thread(
            student_id=current_user.id, subject_code=payload.subjectCode, title=payload.title
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ThreadOut(**row)


@router.get("/threads/{conversation_id}", response_model=ThreadDetailOut)
def get_thread(
    conversation_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: CompanionService = Depends(get_service),
) -> ThreadDetailOut:
    try:
        row = service.get_thread(student_id=current_user.id, conversation_id=conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ThreadDetailOut(**row)


@router.delete("/threads/{conversation_id}", status_code=204)
def delete_thread(
    conversation_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: CompanionService = Depends(get_service),
) -> None:
    try:
        service.delete_thread(student_id=current_user.id, conversation_id=conversation_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/threads/{conversation_id}/messages", response_model=MessageOut, status_code=201)
def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: CompanionService = Depends(get_service),
) -> MessageOut:
    try:
        row = service.send_message(
            student_id=current_user.id, conversation_id=conversation_id, message=payload.message
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return MessageOut(**row)
