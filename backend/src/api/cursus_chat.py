"""Student-scoped Cursus Chat gateway. AI generation remains in ai-service."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.api.plans import _EVENT_FOR_STATUS, apply_task_status_update
from src.config import Settings, get_settings
from src.db import models
from src.db.connection import get_db
from src.repositories.audit_repository import AuditRepository
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.ownership_repository import OwnershipRepository
from src.security.authorization import require_roles
from src.services.academic.academic_calendar import current_week_for_student
from src.services.ai.plan_builder import resolve_current_plan, serialize_plan
from src.services.core.ai_service_client import generate_structured
from src.services.core.audit_service import AuditService
from src.services.core.crisis_safety_service import evaluate as evaluate_crisis
from src.services.core.email_provider import build_email_service
from src.services.core.guardrail_service import GuardrailService
from src.services.core.llm import has_configured_llm
from src.services.core.llm_budget_service import check_and_increment_async
from src.services.core.notification_service import NotificationService
from src.services.core.rate_limiter import allow as rate_limit_allow
from src.services.rag.document_content_validator import scan_for_suspicious_patterns
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/student/cursus", tags=["cursus-chat"], dependencies=[Depends(require_roles(models.UserRole.STUDENT))])
_TTL = timedelta(days=7)
_BRIEFING_KEY = "daily_greeting"
_BRIEFING_DEFAULT_CAP = timedelta(days=1)
_BRIEFING_MESSAGE = (
    "Chào bạn! Mình là Cursus — hỏi mình về nội dung môn học, kế hoạch tuần, "
    "hoặc cách dùng app đều được."
)
_RATE_LIMIT_WINDOW_SECONDS = 60


def _single_event_stream(*, conversation_id: str, text: str) -> StreamingResponse:
    async def _gen():
        yield f"event: meta\ndata: {json.dumps({'conversationId': conversation_id})}\n\n"
        yield f"event: delta\ndata: {json.dumps({'text': text})}\n\n"
        yield "event: done\ndata: {}\n\n"
    return StreamingResponse(_gen(), media_type="text/event-stream")


def _error_stream(*, code: str, message: str | None = None) -> StreamingResponse:
    async def _gen():
        payload = {"code": code}
        if message:
            payload["message"] = message
        yield f"event: error\ndata: {json.dumps(payload)}\n\n"
    return StreamingResponse(_gen(), media_type="text/event-stream")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    conversation_id: str | None = None

class ActionProposalRequest(BaseModel):
    action_type: str = Field(pattern="^(open_reflection|update_task_status)$")
    payload: dict = Field(default_factory=dict)

class BriefingDismissRequest(BaseModel):
    briefing_key: str = _BRIEFING_KEY
    snooze_days: int = Field(default=1, ge=0, le=30)


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

    sources: list[dict[str, str]] = []
    for hit in hits:
        # LLM08 defense-in-depth (see document_content_validator.py's own
        # docstring): that scan already runs at ingest/upload time and flags
        # (never blocks) a document for admin review, but a flagged document
        # can still be sitting in the index -- this is the second, retrieval
        # -time gate that actually keeps a matched chunk's text out of what
        # gets sent to ai-service, rather than only warning a human later.
        flags = scan_for_suspicious_patterns(hit.chunk.text)
        if flags:
            logger.warning(
                "cursus_chat_suspicious_chunk_excluded chunk_id=%s patterns=%s",
                hit.chunk.chunk_id, [f["pattern"] for f in flags],
            )
            continue
        sources.append(
            {
                "id": hit.chunk.chunk_id,
                "title": hit.chunk.doc_title,
                "section": hit.chunk.section or "",
                "text": hit.chunk.text[:4000],
                "isMock": bool(getattr(hit.chunk, "content_source", None) == "mock"),
            }
        )
        if len(sources) >= 5:
            break
    return sources


def _intent(question: str, sources: list[dict[str, str]]) -> str:
    lowered = question.lower()
    if any(word in lowered for word in ("kế hoạch", "plan", "tạo task", "sửa task")):
        return "plan_action"
    if any(word in lowered for word in ("reflection", "phản tư")):
        return "reflection_navigation"
    if any(word in lowered for word in ("tính năng", "chức năng", "cách dùng")):
        return "product_help"
    return "course_fact" if len(sources) <= 2 else "course_complex"


async def _audit_chat_decision(db: Session, *, event_type: str, decision: str, student_id: str, conversation_id: str, extra: dict) -> None:
    try:
        await AuditService(AuditRepository(db)).log_event(
            event_type=event_type,
            decision=decision,
            actor_user_id=student_id,
            resource_type="CHAT",
            resource_id=conversation_id,
            metadata=extra,
        )
    except Exception:
        logger.exception("cursus_chat_audit_failed event_type=%s", event_type)


async def _escalate_crisis(db: Session, *, student: models.User, conversation_id: str, message: str, settings: Settings) -> None:
    """Persist a CrisisEscalation row (Admin/CTSV-only queue) and send an
    immediate email best-effort. Must never raise into the caller — a
    failure here (e.g. no SMTP configured) must not affect the supportive
    in-chat answer the student already received."""
    try:
        escalation = models.CrisisEscalation(
            id=str(uuid4()), student_id=student.id, conversation_id=conversation_id,
            message_excerpt=message[:2000], status="OPEN", created_at=datetime.utcnow(),
        )
        db.add(escalation)
        db.commit()
    except Exception:
        logger.exception("crisis_escalation_persist_failed student_id=%s", student.id)
        db.rollback()
        return

    to_email = settings.crisis_escalation_email or settings.ops_alert_email
    if not to_email:
        logger.warning("crisis_escalation_no_email_configured student_id=%s escalation_id=%s", student.id, escalation.id)
        return
    try:
        notification_service = NotificationService(settings, build_email_service(settings))
        await notification_service.send_ops_alert(
            to_email,
            subject="[Cursus] Cảnh báo an toàn sinh viên — cần xử lý ngay",
            body_text=(
                f"Sinh viên: {student.full_name} ({student.email})\n"
                f"Thời điểm: {escalation.created_at.isoformat()}\n"
                f"Trích đoạn tin nhắn: {escalation.message_excerpt}\n\n"
                "Vui lòng liên hệ sinh viên hoặc phối hợp phòng Công tác Sinh viên "
                "sớm nhất có thể. Xem chi tiết trong Admin Console > Crisis Escalations."
            ),
        )
    except Exception:
        logger.exception("crisis_escalation_email_failed student_id=%s escalation_id=%s", student.id, escalation.id)


class _TaskActionExtraction(BaseModel):
    task_id: str | None = None
    status: str | None = None


def _propose_action(db: Session, *, student_id: str, intent: str, message: str) -> tuple[str, dict] | None:
    """Best-effort: never raises, returns None when no confident proposal
    can be made. `update_task_status` is only ever proposed for a task id
    that genuinely exists in the student's own current-week open tasks and
    a status the app actually supports — the LLM extraction is a suggestion,
    membership in that real set is what's trusted."""
    try:
        if intent == "reflection_navigation":
            week = current_week_for_student(db, student_id)
            return "open_reflection", {"weekNumber": week}

        if intent == "plan_action":
            if not has_configured_llm():
                return None
            week = current_week_for_student(db, student_id)
            plan = resolve_current_plan(db, student_id=student_id, week_number=week)
            if plan is None:
                return None
            tasks = serialize_plan(db, plan)["tasks"]
            open_tasks = [t for t in tasks if t["status"] != "COMPLETED"]
            if not open_tasks:
                return None
            listing = "\n".join(f'- id={t["id"]} title="{t["title"]}" status={t["status"]}' for t in open_tasks)
            extraction = generate_structured(
                schema_model=_TaskActionExtraction,
                system_prompt=(
                    "Bạn xác định sinh viên đang muốn đổi trạng thái của TASK nào trong "
                    "danh sách dưới, và trạng thái mới là gì (một trong TODO, IN_PROGRESS, "
                    "COMPLETED, SKIPPED — không chọn DEFERRED vì việc đó cần lý do riêng). "
                    "Nếu không rõ ràng sinh viên đang nói về task nào, trả về task_id=null."
                ),
                user_prompt=f"Danh sách task đang mở:\n{listing}\n\nTin nhắn của sinh viên: {message}",
                intent="plan_action",
            )
            valid_ids = {t["id"] for t in open_tasks}
            valid_statuses = set(_EVENT_FOR_STATUS) - {"DEFERRED"}
            if extraction.task_id in valid_ids and extraction.status in valid_statuses:
                return "update_task_status", {"taskId": extraction.task_id, "status": extraction.status}
            return None
    except Exception:
        logger.exception("cursus_chat_action_proposal_failed intent=%s", intent)
    return None


@router.post("/stream")
async def stream_chat(payload: ChatRequest, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> StreamingResponse:
    _cleanup(db)
    conversation = _conversation(db, current_user.id, payload.conversation_id)
    db.add(models.ChatMessage(id=str(uuid4()), conversation_id=conversation.id, role="user", content=payload.message, metadata_info={}))
    db.commit()

    crisis = evaluate_crisis(payload.message)
    if crisis.triggered:
        await _audit_chat_decision(db, event_type="CRISIS_SAFETY_TRIGGERED", decision="ALLOW", student_id=current_user.id, conversation_id=conversation.id, extra={})

        async def crisis_response():
            yield f"event: meta\ndata: {json.dumps({'conversationId': conversation.id})}\n\n"
            yield f"event: delta\ndata: {json.dumps({'text': crisis.answer})}\n\n"
            yield "event: done\ndata: {}\n\n"
        return StreamingResponse(crisis_response(), media_type="text/event-stream")

    decision = GuardrailService(db).evaluate(payload.message)
    if decision.blocked:
        await _audit_chat_decision(
            db, event_type="GUARDRAIL_DECISION", decision="BLOCK", student_id=current_user.id,
            conversation_id=conversation.id, extra={"reason": decision.reason, "intent": decision.intent},
        )

        async def blocked():
            yield f"event: meta\ndata: {json.dumps({'conversationId': conversation.id})}\n\n"
            yield f"event: delta\ndata: {json.dumps({'text': decision.answer})}\n\n"
            yield "event: done\ndata: {}\n\n"
        return StreamingResponse(blocked(), media_type="text/event-stream")
    if decision.reason == "out_of_scope":
        await _audit_chat_decision(
            db, event_type="GUARDRAIL_DECISION", decision="ALLOW", student_id=current_user.id,
            conversation_id=conversation.id, extra={"reason": decision.reason, "intent": decision.intent},
        )

    sources = _context(db, current_user.id, payload.message)
    intent = _intent(payload.message, sources)

    async def relay():
        answer = ""
        yield f"event: meta\ndata: {json.dumps({'conversationId': conversation.id, 'intent': intent})}\n\n"
        try:
            # ai-service sends "event: X" and "data: Y" as separate lines;
            # httpx.aiter_lines() yields them one at a time, so the event
            # name for the *next* data line must be tracked across
            # iterations -- forwarding a bare "data: ..." line with no
            # preceding "event: ..." (the previous version of this loop)
            # left every relayed delta un-typed and silently dropped by any
            # SSE consumer that dispatches on event name.
            current_event = "message"
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", f"{settings.ai_service_url.rstrip('/')}/v1/generate/stream", headers={"x-ai-service-key": settings.ai_service_internal_key or ""}, json={"message": payload.message, "intent": intent, "context": sources}) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("event:"):
                            current_event = line.split(":", 1)[1].strip()
                            continue
                        if not line.startswith("data:"):
                            continue
                        data_raw = line.split(":", 1)[1].strip()
                        if current_event == "delta":
                            data = json.loads(data_raw)
                            answer += data.get("text", "")
                            yield f"event: delta\ndata: {data_raw}\n\n"
                        elif current_event == "error":
                            yield f"event: error\ndata: {data_raw}\n\n"
                        # ai-service's own "done" is not forwarded -- this
                        # relay emits its own "done" below, after citations
                        # and any action proposal have also been sent.
            if sources:
                yield f"event: citation\ndata: {json.dumps({'items': [{'id': item['id'], 'chunkId': item['id'], 'title': item['title'], 'document': item['title'], 'section': item['section'], 'isMock': item['isMock']} for item in sources]})}\n\n"
            db.add(models.ChatMessage(id=str(uuid4()), conversation_id=conversation.id, role="assistant", content=answer, metadata_info={"citations": sources, "intent": intent}))
            conversation.updated_at = datetime.utcnow(); conversation.expires_at = datetime.utcnow() + _TTL; db.commit()

            if intent in ("plan_action", "reflection_navigation"):
                proposed = _propose_action(db, student_id=current_user.id, intent=intent, message=payload.message)
                if proposed is not None:
                    action_type, action_payload = proposed
                    proposal = models.ChatActionProposal(
                        id=str(uuid4()), student_id=current_user.id, action_type=action_type,
                        payload=action_payload, status="PENDING", expires_at=datetime.utcnow() + timedelta(minutes=15),
                    )
                    db.add(proposal)
                    db.commit()
                    yield f"event: action_proposal\ndata: {json.dumps({'id': proposal.id, 'actionType': action_type, 'payload': action_payload})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except Exception:
            db.rollback()
            yield "event: error\ndata: {\"code\":\"AI_UNAVAILABLE\"}\n\n"
    return StreamingResponse(relay(), media_type="text/event-stream")


@router.get("/briefing")
def get_briefing(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    """Frequency-capped app-open greeting. `shown_at` on the latest row is
    reused as a "suppressed until" timestamp (see `/briefing/dismiss`) rather
    than adding a migration for a separate column."""
    last = (
        db.query(models.ChatBriefingImpression)
        .filter_by(student_id=current_user.id, briefing_key=_BRIEFING_KEY)
        .order_by(models.ChatBriefingImpression.shown_at.desc())
        .first()
    )
    if last is not None and last.shown_at > datetime.utcnow():
        return {"show": False}
    return {"show": True, "briefingKey": _BRIEFING_KEY, "message": _BRIEFING_MESSAGE}


@router.post("/briefing/dismiss")
def dismiss_briefing(payload: BriefingDismissRequest, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    suppressed_until = datetime.utcnow() + (timedelta(days=payload.snooze_days) if payload.snooze_days > 0 else _BRIEFING_DEFAULT_CAP)
    db.add(models.ChatBriefingImpression(id=str(uuid4()), student_id=current_user.id, briefing_key=payload.briefing_key, shown_at=suppressed_until))
    db.commit()
    return {"ok": True, "suppressedUntil": suppressed_until.isoformat()}


@router.get("/conversations")
def conversations(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    _cleanup(db); db.commit()
    rows = db.query(models.ChatConversation).filter_by(student_id=current_user.id).order_by(models.ChatConversation.updated_at.desc()).all()
    return {"items": [{"id": row.id, "updatedAt": row.updated_at.isoformat()} for row in rows]}


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(conversation_id: str, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    conversation = db.query(models.ChatConversation).filter_by(id=conversation_id, student_id=current_user.id).first()
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    rows = db.query(models.ChatMessage).filter_by(conversation_id=conversation_id).order_by(models.ChatMessage.created_at).all()
    return {
        "id": conversation.id,
        "messages": [
            {"role": row.role, "content": row.content, "createdAt": row.created_at.isoformat(), "citations": row.metadata_info.get("citations", [])}
            for row in rows
        ],
    }


@router.get("/export")
def export_history(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    rows = db.query(models.ChatMessage).join(models.ChatConversation).filter(models.ChatConversation.student_id == current_user.id).order_by(models.ChatMessage.created_at).all()
    return {"exportedAt": datetime.utcnow().isoformat(), "messages": [{"role": row.role, "content": row.content, "createdAt": row.created_at.isoformat(), "citations": row.metadata_info.get("citations", [])} for row in rows]}


@router.delete("/history")
def delete_history(current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    deleted = db.query(models.ChatConversation).filter_by(student_id=current_user.id).delete(synchronize_session=False); db.commit()
    return {"deleted": deleted}

@router.post("/actions")
def propose_action(payload: ActionProposalRequest, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    proposal = models.ChatActionProposal(id=str(uuid4()), student_id=current_user.id, action_type=payload.action_type, payload=payload.payload, status="PENDING", expires_at=datetime.utcnow() + timedelta(minutes=15))
    db.add(proposal); db.commit(); return {"id": proposal.id, "actionType": proposal.action_type, "payload": proposal.payload, "status": proposal.status}

@router.post("/actions/{proposal_id}/confirm")
def confirm_action(proposal_id: str, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    proposal = db.query(models.ChatActionProposal).filter_by(id=proposal_id, student_id=current_user.id).first()
    if proposal is None or proposal.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=404, detail="Action proposal not found")
    if proposal.status != "PENDING":
        return {"status": proposal.status}

    if proposal.action_type == "update_task_status":
        task_id = proposal.payload.get("taskId")
        status = proposal.payload.get("status")
        if not task_id or not status:
            raise HTTPException(status_code=400, detail="Action proposal missing taskId/status")
        if not OwnershipRepository(db).student_owns_study_task(current_user.id, task_id):
            raise HTTPException(status_code=404, detail="Study task not found")
        result = apply_task_status_update(db, task_id=task_id, current_user=current_user, status=status)
        proposal.status = "CONFIRMED"
        db.commit()
        return {"status": proposal.status, "actionType": proposal.action_type, "result": result}

    if proposal.action_type == "open_reflection":
        week_number = proposal.payload.get("weekNumber")
        proposal.status = "CONFIRMED"
        db.commit()
        navigate_to = "/student/reflection" + (f"?week={week_number}" if week_number else "")
        return {"status": proposal.status, "actionType": proposal.action_type, "navigateTo": navigate_to}

    proposal.status = "CONFIRMED"; db.commit()
    return {"status": proposal.status, "actionType": proposal.action_type, "payload": proposal.payload}


@router.post("/actions/{proposal_id}/cancel")
def cancel_action(proposal_id: str, current_user: models.User = Depends(get_current_user_from_token), db: Session = Depends(get_db)):
    proposal = db.query(models.ChatActionProposal).filter_by(id=proposal_id, student_id=current_user.id).first()
    if proposal is None:
        raise HTTPException(status_code=404, detail="Action proposal not found")
    if proposal.status == "PENDING":
        proposal.status = "CANCELLED"
        db.commit()
    return {"status": proposal.status}
