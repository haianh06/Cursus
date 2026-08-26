"""Unified Cursus chat API — one continuous conversation per student,
replacing the old stateless `/api/v1/qa` (single-shot) and per-course
`/student/companion/threads*` (multi-thread) surfaces. See
`src/services/ai/chat_orchestrator_service.py` for the orchestration."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.schemas.student_chat import ChatMessageOut, ChatStateOut, SendChatMessageRequest
from src.security.authorization import require_roles
from src.services.ai.chat_orchestrator_service import ChatOrchestratorService

router = APIRouter(
    prefix="/student/chat",
    tags=["chat"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


def get_service(db: Session = Depends(get_db)) -> ChatOrchestratorService:
    return ChatOrchestratorService(db)


@router.get("", response_model=ChatStateOut)
def get_chat(
    current_user: models.User = Depends(get_current_user_from_token),
    service: ChatOrchestratorService = Depends(get_service),
) -> ChatStateOut:
    return ChatStateOut(**service.get_state(student_id=current_user.id))


@router.delete("", status_code=204)
def clear_chat(
    current_user: models.User = Depends(get_current_user_from_token),
    service: ChatOrchestratorService = Depends(get_service),
) -> None:
    service.clear(student_id=current_user.id)


@router.post("/messages", response_model=ChatMessageOut, status_code=201)
def send_chat_message(
    payload: SendChatMessageRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: ChatOrchestratorService = Depends(get_service),
) -> ChatMessageOut:
    try:
        result = service.send_message(
            student_id=current_user.id,
            subject_code=payload.subjectCode,
            message=payload.message,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return ChatMessageOut(**result)
