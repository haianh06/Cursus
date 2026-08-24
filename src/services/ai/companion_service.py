"""Per-course companion chat: threaded Q&A that reuses the Study Assistant's
guardrail + retrieval + answer pipeline instead of reimplementing it, PLUS
emotional-support routing (`chat_router_service.py`) and a crisis-safety
reply (`empathic_reply_service.py`) — ported after discovering that develop's
`qa_service.py` (not its `companion_service.py`, which is actually just the
empathic-reply generator under a name that collides with this file's class)
is the real unified orchestrator: crisis check -> guardrail -> route
(companion / study / mixed) -> answer. That ordering is replicated in
`send_message()` below. Guardrails are never skipped for the study path.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from src.repositories.chunk_repository import ChunkRepository
from src.repositories.conversation_repository import MAX_THREADS_PER_COURSE, ConversationRepository
from src.services.ai.chat_router_service import ChatRouterService
from src.services.ai.empathic_reply_service import EmpathicReplyService
from src.services.ai.qa_answer_service import QaAnswerService
from src.services.core.guardrail_service import INTENT_HINT, INTENT_OUT_OF_SCOPE, GuardrailService
from src.services.mock.student_mock_data_service import StudentMockDataService
from src.services.rag import web_search_service
from src.services.rag.query_normalization import normalize_query
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

SENDER_USER = "USER"
SENDER_ASSISTANT = "ASSISTANT"
_HISTORY_LIMIT = 12


class CompanionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._conversations = ConversationRepository(db)
        self._chunks = ChunkRepository(db)
        self._guardrail = GuardrailService(db)
        self._router = ChatRouterService()
        self._empathic = EmpathicReplyService()
        self._retrieval = RetrievalService(self._chunks)
        self._answer = QaAnswerService()

    # ── Threads ──────────────────────────────────────────────────────────
    def list_threads(self, *, student_id: str, subject_code: str) -> list[dict[str, Any]]:
        code = subject_code.strip().upper()
        self._require_course_access(student_id, code)
        return [self._serialize_thread(row) for row in self._conversations.list_for_student_course(
            student_id=student_id, subject_code=code
        )]

    def create_thread(self, *, student_id: str, subject_code: str, title: str = "") -> dict[str, Any]:
        code = subject_code.strip().upper()
        self._require_course_access(student_id, code)
        if self._conversations.count_for_course(student_id=student_id, subject_code=code) >= MAX_THREADS_PER_COURSE:
            self._conversations.delete_oldest_for_course(student_id=student_id, subject_code=code)
        row = self._conversations.create(student_id=student_id, subject_code=code, title=title or f"Chat {code}")
        self._db.commit()
        return self._serialize_thread(row)

    def get_thread(self, *, student_id: str, conversation_id: str) -> dict[str, Any]:
        row = self._conversations.get_owned(conversation_id=conversation_id, student_id=student_id)
        if row is None:
            raise LookupError("Conversation not found")
        messages = self._conversations.list_messages(conversation_id=row.id)
        return {**self._serialize_thread(row), "messages": [self._serialize_message(m) for m in messages]}

    def delete_thread(self, *, student_id: str, conversation_id: str) -> None:
        if not self._conversations.delete_owned(conversation_id=conversation_id, student_id=student_id):
            raise LookupError("Conversation not found")
        self._db.commit()

    # ── Messaging ────────────────────────────────────────────────────────
    def send_message(self, *, student_id: str, conversation_id: str, message: str) -> dict[str, Any]:
        conversation = self._conversations.get_owned(conversation_id=conversation_id, student_id=student_id)
        if conversation is None:
            raise LookupError("Conversation not found")
        code = conversation.subject_code or ""
        self._require_course_access(student_id, code)

        history_rows = self._conversations.list_messages(conversation_id=conversation.id, limit=_HISTORY_LIMIT)
        history = [
            {"role": "assistant" if row.sender == SENDER_ASSISTANT else "user", "content": row.content}
            for row in history_rows
        ]

        self._conversations.add_message(conversation_id=conversation.id, sender=SENDER_USER, content=message)

        normalized = normalize_query(message)
        query = normalized.cleaned or message

        if self._router.is_crisis(query):
            answer, mode = self._empathic.reply(
                question=query, subject_code=code, history=history, crisis=True
            )
            assistant_message = self._conversations.add_message(
                conversation_id=conversation.id,
                sender=SENDER_ASSISTANT,
                content=answer,
                metadata={"mode": mode, "intent": "companion_crisis"},
            )
            self._conversations.touch(conversation)
            self._db.commit()
            return self._serialize_message(assistant_message)

        decision = self._guardrail.evaluate(query)

        if decision.blocked:
            answer = decision.answer or "Minh khong lam bai ho duoc."
            mode = "blocked"
        elif decision.intent == INTENT_OUT_OF_SCOPE:
            answer = decision.answer or ""
            mode = "out_of_scope"
        elif decision.intent == INTENT_HINT:
            steps = decision.guidance.get("steps") or []
            answer = f"{decision.guidance.get('concept', '')}\n\n{chr(10).join(steps)}".strip()
            mode = "guidance"
        else:
            route = self._router.route(query)
            if route.route == "companion":
                answer, mode = self._empathic.reply(question=query, subject_code=code, history=history)
            else:
                retrieved = self._retrieval.retrieve(subject_code=code, question=query, student_id=student_id)
                answer, _citations, mode = self._answer.answer(
                    question=query, subject_code=code, retrieved=retrieved
                )
                if mode == "no_source":
                    answer = self._web_fallback(question=query, subject_code=code, base_answer=answer)
                    mode = "web_search" if web_search_service.has_web_search() else mode
                if route.route == "mixed":
                    empathy, _ = self._empathic.reply(question=query, subject_code=code, history=history)
                    answer = f"{answer}\n\n---\n{empathy}"

        assistant_message = self._conversations.add_message(
            conversation_id=conversation.id,
            sender=SENDER_ASSISTANT,
            content=answer,
            metadata={"mode": mode, "intent": decision.intent},
        )
        self._conversations.touch(conversation)
        self._db.commit()
        return self._serialize_message(assistant_message)

    def _web_fallback(self, *, question: str, subject_code: str, base_answer: str) -> str:
        if not web_search_service.has_web_search():
            return base_answer
        results = web_search_service.search(query=question, subject_code=subject_code)
        if not results:
            return base_answer
        lines = [
            "Khong tim thay trong tai lieu mon hoc, nhung mot vai nguon web co the lien quan:",
            "",
        ]
        for item in results[:3]:
            lines.append(f"- {item.title}: {item.snippet} ({item.url})")
        return "\n".join(lines)

    def _require_course_access(self, student_id: str, subject_code: str) -> None:
        StudentMockDataService(self._db).ensure_if_missing(student_id)
        if not self._chunks.student_enrolled_in_course(student_id=student_id, subject_code=subject_code):
            raise PermissionError(f"Student is not enrolled in {subject_code}")

    @staticmethod
    def _serialize_thread(row) -> dict[str, Any]:
        return {
            "id": row.id,
            "subjectCode": row.subject_code,
            "title": row.title,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        }

    @staticmethod
    def _serialize_message(row) -> dict[str, Any]:
        return {
            "id": row.id,
            "conversationId": row.conversation_id,
            "sender": row.sender,
            "content": row.content,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "metadata": row.metadata_info or {},
        }
