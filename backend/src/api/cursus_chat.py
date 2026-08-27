"""Student-scoped Cursus Chat gateway. AI generation remains in ai-service."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.config import Settings, get_settings
from src.db import models
from src.db.connection import get_db
from src.repositories.chunk_repository import ChunkRepository
from src.security.authorization import require_roles
from src.services.core.guardrail_service import GuardrailService
from src.services.rag.retrieval_service import RetrievalService

router = APIRouter(prefix="/student/cursus", tags=["cursus-chat"], dependencies=[Depends(require_roles(models.UserRole.STUDENT))])
_TTL = timedelta(days=7)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    conversation_id: str | None = None


def _cleanup(db: Session) -> None:
    db.query(models.ChatConversation).filter(models.ChatConversation.expires_at <= datetime.utcnow()).delete(synchronize_session=False)


def _conversation(db: Session, student_id: str, conversation_id: str | None) -> models.ChatConversation:
    now = datetime.utcnow()
    if conversation_id:
        row = db.query(models.ChatConversation).filter_by(id=conversation_id, student_id=student_id).first()
        if row is None or row.expires_at <= now:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return row
    row = models.ChatConversation(id=str(uuid4()), student_id=student_id, created_at=now, updated_at=now, expires_at=now + _TTL)
    db.add(row)
    return row


def _context(db: Session, student_id: str, question: str) -> list[dict[str, str]]:
    codes = [r[0] for r in db.query(models.Course.code).join(models.CourseSection).join(models.Enrollment).filter(models.Enrollment.student_id == student_id, models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value).all()]
    repo = ChunkRepository(db)
    hits = []
    for code in codes:
        hits.extend(RetrievalService(repo, top_k=3).retrieve(subject_code=code, question=question, student_id=student_id))
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return [{"id": hit.chunk.chunk_id, "title": hit.chunk.doc_title, "section": hit.chunk.section or "", "text": hit.chunk.text[:4000]} for hit in hits[:5]]


def _intent(question: str, sources: list[dict[str, str]]) -> str:
    lowered = question.lower()
    if any(word in lowered for word in ("kế hoạch", "plan", "tạo task", "sửa task")):
        return "plan_action"
    if any(word in lowered for word in ("reflection", "phản tư")):
        return "reflection_navigation"
    if any(word in lowered for word in ("tính năng", "chức năng", "cách dùng")):
        return "product_help"
    return "course_fact" if len(sources) <= 2 else "course_complex"


@router.post("/stream")
async def stream_chat(payload: ChatRequest, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> StreamingResponse:
    _cleanup(db)
    decision = GuardrailService(db).evaluate(payload.message)
    conversation = _conversation(db, current_user.id, payload.conversation_id)
    db.add(models.ChatMessage(id=str(uuid4()), conversation_id=conversation.id, role="user", content=payload.message, metadata_info={}))
    db.commit()
    if decision.blocked:
        async def blocked():
            yield f"event: meta\ndata: {json.dumps({'conversationId': conversation.id})}\n\n"
            yield f"event: delta\ndata: {json.dumps({'text': decision.answer})}\n\n"
            yield "event: done\ndata: {}\n\n"
        return StreamingResponse(blocked(), media_type="text/event-stream")
    sources = _context(db, current_user.id, payload.message)
    intent = _intent(payload.message, sources)

    async def relay():
        answer = ""
        yield f"event: meta\ndata: {json.dumps({'conversationId': conversation.id, 'intent': intent})}\n\n"
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", f"{settings.ai_service_url.rstrip('/')}/v1/generate/stream", headers={"x-ai-service-key": settings.ai_service_internal_key or ""}, json={"message": payload.message, "intent": intent, "context": sources}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = json.loads(line[6:])
                        if "text" in data:
                            answer += data["text"]
                        yield line + "\n\n"
            if sources:
                yield f"event: citation\ndata: {json.dumps({'items': [{k: item[k] for k in ('id','title','section')} for item in sources]})}\n\n"
            db.add(models.ChatMessage(id=str(uuid4()), conversation_id=conversation.id, role="assistant", content=answer, metadata_info={"citations": sources, "intent": intent}))
            conversation.updated_at = datetime.utcnow(); conversation.expires_at = datetime.utcnow() + _TTL; db.commit()
        except Exception:
            db.rollback()
            yield "event: error\ndata: {\"code\":\"AI_UNAVAILABLE\"}\n\n"
    return StreamingResponse(relay(), media_type="text/event-stream")


@router.get("/conversations")
def conversations(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    _cleanup(db); db.commit()
    rows = db.query(models.ChatConversation).filter_by(student_id=current_user.id).order_by(models.ChatConversation.updated_at.desc()).all()
    return {"items": [{"id": row.id, "updatedAt": row.updated_at.isoformat()} for row in rows]}


@router.get("/export")
def export_history(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    rows = db.query(models.ChatMessage).join(models.ChatConversation).filter(models.ChatConversation.student_id == current_user.id).order_by(models.ChatMessage.created_at).all()
    return {"exportedAt": datetime.utcnow().isoformat(), "messages": [{"role": row.role, "content": row.content, "createdAt": row.created_at.isoformat(), "citations": row.metadata_info.get("citations", [])} for row in rows]}


@router.delete("/history")
def delete_history(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    deleted = db.query(models.ChatConversation).filter_by(student_id=current_user.id).delete(synchronize_session=False); db.commit()
    return {"deleted": deleted}
