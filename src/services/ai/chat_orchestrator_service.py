"""The single entry point for the rebuilt Cursus chat — replaces the old
`QaService` (stateless `/api/v1/qa`) and `CompanionService` (stateful,
per-course threads) with one always-persisted, single-continuous-thread
orchestrator. See docs at C:\\Users\\anhng\\.claude\\plans\\piped-sprouting-waffle.md
for the full rebuild plan/rationale.

Turn order: crisis check (hard safety gate, before anything else, no LLM
needed) -> guardrail (now writes a real `GuardrailEvent` row on block, so the
instructor review queue finally receives real traffic instead of only seed
data) -> greeting/thanks -> ask_hint -> companion/study/mixed routing
(`ChatRouterService`, unchanged) -> for study/mixed: ONE `ChatAnswerService`
call spanning academic retrieval + the student's own live state + app-usage
help, LLM decides which of those actually answer the question.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.conversation_repository import ConversationRepository
from src.schemas.student_chat import ChatCitation
from src.services.ai.app_help_service import AppHelpService
from src.services.ai.chat_answer_service import ChatAnswerService
from src.services.ai.chat_router_service import ChatRouterService
from src.services.ai.conversation_intent_service import ConversationIntentService
from src.services.ai.empathic_reply_service import EmpathicReplyService
from src.services.ai.faq_service import FaqService
from src.services.ai.student_context_service import StudentContextService
from src.services.ai.student_memory_service import StudentMemoryService
from src.services.core.guardrail_service import (
    INTENT_HINT,
    INTENT_OUT_OF_SCOPE,
    GuardrailDecision,
    GuardrailService,
)
from src.services.mock.student_mock_data_service import StudentMockDataService
from src.services.rag.query_normalization import normalize_query
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

SENDER_USER = "USER"
SENDER_ASSISTANT = "ASSISTANT"
_HISTORY_LIMIT = 12


class ChatOrchestratorService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._conversations = ConversationRepository(db)
        self._chunks = ChunkRepository(db)
        self._guardrail = GuardrailService(db)
        self._chat_intent = ConversationIntentService()
        self._router = ChatRouterService()
        self._empathic = EmpathicReplyService()
        self._retrieval = RetrievalService(self._chunks)
        self._answer = ChatAnswerService()
        self._faq = FaqService()
        self._help = AppHelpService()
        self._student_context = StudentContextService(db)
        self._memory = StudentMemoryService(db)

    # ── read the conversation ────────────────────────────────────────────
    def get_state(self, *, student_id: str) -> dict[str, Any]:
        conversation = self._conversations.get_or_create_single(student_id=student_id)
        self._db.commit()
        messages = self._conversations.list_messages(conversation_id=conversation.id)
        return {
            "conversationId": conversation.id,
            "messages": [self._serialize_message(m) for m in messages],
        }

    def clear(self, *, student_id: str) -> None:
        conversation = self._conversations.get_or_create_single(student_id=student_id)
        self._conversations.clear_messages(conversation=conversation)
        self._db.commit()

    # ── send a message ───────────────────────────────────────────────────
    def send_message(self, *, student_id: str, subject_code: str | None, message: str) -> dict[str, Any]:
        code = (subject_code or "").strip().upper() or None
        if code:
            self._require_enrollment(student_id, code)

        StudentMockDataService(self._db).ensure_if_missing(student_id)
        conversation = self._conversations.get_or_create_single(student_id=student_id)
        if code:
            conversation.subject_code = code

        history = self._history(conversation)

        normalized = normalize_query(message)
        query = normalized.cleaned or message

        user_message = self._conversations.add_message(
            conversation_id=conversation.id,
            sender=SENDER_USER,
            content=message,
            metadata={"subjectCode": code} if code else {},
        )

        if self._router.is_crisis(query):
            answer, mode, degraded_reason = self._empathic.reply(
                question=query, subject_code=code or "", history=history, crisis=True
            )
            return self._finish(conversation, answer, mode=mode, subject_code=code, degraded_reason=degraded_reason)

        decision = self._guardrail.evaluate(query)

        if decision.blocked:
            self._record_guardrail_event(user_message, decision)
            return self._finish(
                conversation,
                decision.answer or "Mình không làm bài hộ được. Hãy hỏi về khái niệm hoặc tài liệu môn.",
                mode="blocked",
                subject_code=code,
                blocked=True,
                block_reason=decision.reason,
                guidance=decision.guidance,
                intent=decision.intent,
                alternatives=list(decision.alternatives),
            )

        if decision.intent == INTENT_OUT_OF_SCOPE:
            return self._finish(
                conversation, decision.answer or "", mode="out_of_scope", subject_code=code,
                block_reason="out_of_scope", intent=decision.intent,
            )

        chat = self._chat_intent.resolve(query, subject_code=code or "")
        if chat.is_chat and chat.answer:
            return self._finish(conversation, chat.answer, mode="chat", subject_code=code)

        if decision.intent == INTENT_HINT:
            steps = decision.guidance.get("steps") or []
            body = "\n".join(steps)
            answer = (
                f"{decision.guidance.get('concept', '')}\n\n{body}".strip()
                or "Mình gợi ý bạn chia nhỏ việc này thành các bước rồi làm lần lượt."
            )
            return self._finish(
                conversation, answer, mode="guidance", subject_code=code, guidance=decision.guidance,
                intent=decision.intent,
            )

        route = self._router.route(query)
        if route.route == "companion":
            answer, mode, degraded_reason = self._empathic.reply(question=query, subject_code=code or "", history=history)
            return self._finish(conversation, answer, mode=mode, subject_code=code, degraded_reason=degraded_reason)

        academic_chunks = self._retrieval.retrieve(
            subject_code=code, question=query, student_id=student_id
        ) if code else []
        faq_match = self._faq.match(subject_code=code, question=query) if code else None
        help_matches = self._help.match(query)
        student_context = self._student_context.build(student_id)
        # Đọc trí nhớ đa phiên đã có consent (chỉ nối phần đọc trong đợt này
        # — record_updates/ghi tự động sau mỗi lượt để fast-follow sau).
        memory_block = self._memory.build_context_block(student_id, code)
        if memory_block:
            student_context["text"] = f"{student_context['text']}\n\n{memory_block}"

        answer, citations, mode, degraded_reason = self._answer.answer(
            question=query,
            subject_code=code,
            academic_chunks=academic_chunks,
            student_context=student_context,
            help_matches=help_matches,
            faq_matches=[faq_match] if faq_match else [],
        )

        if route.route == "mixed":
            empathy, _empathy_mode, empathy_degraded = self._empathic.reply(
                question=query, subject_code=code or "", history=history
            )
            answer = f"{answer}\n\n---\n{empathy}"
            degraded_reason = degraded_reason or empathy_degraded

        engine = "llm" if mode == "llm" else "deterministic"
        return self._finish(
            conversation, answer, mode=mode, subject_code=code, citations=citations, engine=engine,
            degraded_reason=degraded_reason,
        )

    # ── helpers ──────────────────────────────────────────────────────────
    def _require_enrollment(self, student_id: str, subject_code: str) -> None:
        if not self._chunks.student_enrolled_in_course(student_id=student_id, subject_code=subject_code):
            raise PermissionError(f"Student is not enrolled in {subject_code}")

    def _history(self, conversation: models.Conversation) -> list[dict[str, str]]:
        rows = self._conversations.list_messages(conversation_id=conversation.id, limit=_HISTORY_LIMIT)
        return [
            {"role": "assistant" if row.sender == SENDER_ASSISTANT else "user", "content": row.content}
            for row in rows
        ]

    def _record_guardrail_event(self, user_message: models.Message, decision: GuardrailDecision) -> None:
        """First real writer of `GuardrailEvent` — previously only seed
        scripts/tests created these rows, so the instructor guardrail review
        queue never received live traffic. Field contract matches exactly
        what `src/api/instructor.py`'s `_visible_guardrail_events`/
        `_serialize_guardrail_review`/`POST /guardrail-reviews/{id}` read."""
        self._db.add(
            models.GuardrailEvent(
                id=f"grail_{uuid.uuid4().hex[:16]}",
                message_id=user_message.id,
                classification="BLOCKED",
                safety_evaluation={
                    "reason": decision.reason,
                    "rule_code": decision.rule_code,
                    "response": decision.answer,
                },
                review_status="PENDING",
                block_reason=decision.reason,
                blocked_answer=decision.answer,
                reviewed_by=None,
                reviewed_at=None,
                created_at=datetime.utcnow(),
                reviewer_note=None,
            )
        )

    def _finish(
        self,
        conversation: models.Conversation,
        answer: str,
        *,
        mode: str,
        subject_code: str | None,
        citations: list[ChatCitation] | None = None,
        blocked: bool = False,
        block_reason: str | None = None,
        guidance: dict | None = None,
        engine: str = "deterministic",
        intent: str = "ask_knowledge",
        alternatives: list[str] | None = None,
        degraded_reason: str | None = None,
    ) -> dict[str, Any]:
        citations = citations or []
        assistant_message = self._conversations.add_message(
            conversation_id=conversation.id,
            sender=SENDER_ASSISTANT,
            content=answer,
            metadata={
                "mode": mode,
                "subjectCode": subject_code,
                "citations": [c.model_dump(mode="json") for c in citations],
                "blocked": blocked,
                "blockReason": block_reason,
                "guidance": guidance or {},
                "engine": engine,
                "intent": intent,
                "alternatives": alternatives or [],
                "degradedReason": degraded_reason,
            },
        )
        self._conversations.touch(conversation)
        self._db.commit()
        return self._serialize_message(assistant_message)

    @staticmethod
    def _serialize_message(row: models.Message) -> dict[str, Any]:
        meta = row.metadata_info or {}
        return {
            "id": row.id,
            "sender": row.sender,
            "content": row.content,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "mode": meta.get("mode", "extractive" if row.sender == SENDER_ASSISTANT else "chat"),
            "citations": meta.get("citations", []),
            "blocked": bool(meta.get("blocked", False)),
            "blockReason": meta.get("blockReason"),
            "guidance": meta.get("guidance", {}),
            "engine": meta.get("engine", "deterministic"),
            "subjectCode": meta.get("subjectCode"),
            "intent": meta.get("intent", "ask_knowledge"),
            "alternatives": meta.get("alternatives", []),
            "degradedReason": meta.get("degradedReason"),
        }
