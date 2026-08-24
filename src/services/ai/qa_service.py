"""Orchestrate Study Assistant Q&A: guardrail → chat → FAQ → retrieve → answer."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from src.repositories.chunk_repository import ChunkRepository
from src.schemas.qa import QaResponse
from src.services.ai.conversation_intent_service import ConversationIntentService
from src.services.ai.faq_service import FaqService
from src.services.ai.qa_answer_service import QaAnswerService
from src.services.core.guardrail_service import (
    INTENT_HINT,
    INTENT_KNOWLEDGE,
    INTENT_OUT_OF_SCOPE,
    GuardrailService,
)
from src.services.mock.student_mock_data_service import StudentMockDataService
from src.services.rag.query_normalization import normalize_query
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

# Suggested follow-ups so a grounded answer ends with a next step rather than
# a full stop (Blueprint §3.1: "answer → citation → đoạn trích → câu hỏi tiếp theo").
_DEFAULT_FOLLOW_UPS = (
    "Điều kiện qua môn SSA101 là gì?",
    "Dự án SSA101 gồm bao nhiêu phần?",
    "Em nên bắt đầu phân tích stakeholder từ đâu?",
)

# Engine labels. `deterministic` covers every non-LLM path; the UI must show
# this honestly instead of implying a live model produced the text.
ENGINE_LLM = "llm"
ENGINE_DETERMINISTIC = "deterministic"


class QaService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._chunks = ChunkRepository(db)
        self._guardrail = GuardrailService(db)
        self._chat = ConversationIntentService()
        self._faq = FaqService()
        self._retrieval = RetrievalService(self._chunks)
        self._answer = QaAnswerService()

    def ask(
        self,
        *,
        student_id: str,
        subject_code: str,
        question: str,
    ) -> QaResponse:
        code = subject_code.strip().upper()
        StudentMockDataService(self._db).ensure_if_missing(student_id)

        if not self._chunks.student_enrolled_in_course(
            student_id=student_id,
            subject_code=code,
        ):
            raise PermissionError(f"Student is not enrolled in {code}")

        normalized = normalize_query(question)
        # Use cleaned text for guardrail/chat/retrieval so backticks/typos don't break matching.
        query = normalized.cleaned or question

        decision = self._guardrail.evaluate(query)

        if decision.blocked:
            logger.info(
                "qa_blocked student=%s subject=%s intent=%s reason=%s",
                student_id,
                code,
                decision.intent,
                decision.reason,
            )
            return QaResponse(
                blocked=True,
                answer=decision.answer
                or "Mình không làm bài hộ được. Hãy hỏi về khái niệm hoặc tài liệu môn.",
                blockReason=decision.reason,
                citations=[],
                mode="blocked",
                alternatives=list(decision.alternatives),
                intent=decision.intent,
                guidance=decision.guidance,
                followUpQuestions=list(_DEFAULT_FOLLOW_UPS),
                engine=ENGINE_DETERMINISTIC,
            )

        if decision.intent == INTENT_OUT_OF_SCOPE:
            # Refuse to guess rather than hallucinate a plausible number.
            logger.info("qa_out_of_scope student=%s subject=%s", student_id, code)
            return QaResponse(
                blocked=False,
                answer=decision.answer or "",
                blockReason="out_of_scope",
                citations=[],
                mode="out_of_scope",
                alternatives=[],
                intent=decision.intent,
                guidance={},
                followUpQuestions=list(_DEFAULT_FOLLOW_UPS),
                engine=ENGINE_DETERMINISTIC,
            )

        if decision.intent == INTENT_HINT:
            # Allowed — answered as step-by-step guidance, still grounded when
            # the retriever finds something relevant.
            retrieved = self._retrieval.retrieve(
                subject_code=code, question=query, student_id=student_id
            )
            _, citations, _ = self._answer.answer(
                question=query, subject_code=code, retrieved=retrieved
            )
            steps = decision.guidance.get("steps") or []
            body = "\n".join(steps) if steps else ""
            answer = (
                f"{decision.guidance.get('concept', '')}\n\n{body}".strip()
                or "Mình gợi ý bạn chia nhỏ việc này thành các bước rồi làm lần lượt."
            )
            logger.info("qa_hint student=%s subject=%s", student_id, code)
            return QaResponse(
                blocked=False,
                answer=answer,
                blockReason=None,
                citations=self._with_excerpts(citations),
                mode="guidance",
                alternatives=[],
                intent=decision.intent,
                guidance=decision.guidance,
                followUpQuestions=list(
                    decision.guidance.get("socraticQuestions") or _DEFAULT_FOLLOW_UPS
                ),
                engine=ENGINE_DETERMINISTIC,
            )

        chat = self._chat.resolve(query, subject_code=code)
        if chat.is_chat and chat.answer:
            logger.info(
                "qa_chat student=%s subject=%s original=%r cleaned=%r",
                student_id,
                code,
                normalized.original,
                query,
            )
            return QaResponse(
                blocked=False,
                answer=chat.answer,
                blockReason=None,
                citations=[],
                mode="chat",
                alternatives=[],
                intent=INTENT_KNOWLEDGE,
                followUpQuestions=list(_DEFAULT_FOLLOW_UPS),
                engine=ENGINE_DETERMINISTIC,
            )

        faq = self._faq.match(subject_code=code, question=query)
        if faq is not None:
            answer, citations, mode = self._faq.to_response_parts(faq)
            logger.info(
                "qa_faq student=%s subject=%s id=%s",
                student_id,
                code,
                faq.entry.id,
            )
            return QaResponse(
                blocked=False,
                answer=answer,
                blockReason=None,
                citations=self._with_excerpts(citations),
                mode=mode,  # type: ignore[arg-type]
                alternatives=[],
                intent=INTENT_KNOWLEDGE,
                followUpQuestions=list(_DEFAULT_FOLLOW_UPS),
                engine=ENGINE_DETERMINISTIC,
            )

        retrieved = self._retrieval.retrieve(
            subject_code=code,
            question=query,
            student_id=student_id,
        )
        answer, citations, mode = self._answer.answer(
            question=query,
            subject_code=code,
            retrieved=retrieved,
        )
        logger.info(
            "qa_answered student=%s subject=%s mode=%s citations=%s",
            student_id,
            code,
            mode,
            len(citations),
        )
        return QaResponse(
            blocked=False,
            answer=answer,
            blockReason=None,
            citations=self._with_excerpts(citations),
            mode=mode,  # type: ignore[arg-type]
            alternatives=[],
            intent=INTENT_KNOWLEDGE,
            followUpQuestions=list(_DEFAULT_FOLLOW_UPS),
            engine=ENGINE_LLM if mode == "llm" else ENGINE_DETERMINISTIC,
        )

    def _with_excerpts(self, citations: list) -> list:
        """Attach document title + excerpt so a citation chip can open the
        source drawer without a second round-trip."""
        from src.db import models

        for citation in citations:
            if citation.excerpt and citation.document:
                continue
            chunk = (
                self._db.query(models.DocumentChunk)
                .filter_by(id=citation.chunkId)
                .first()
            )
            if chunk is None:
                citation.document = citation.docTitle or citation.sourceLabel
                continue
            document = (
                self._db.query(models.Document)
                .filter_by(id=chunk.document_id)
                .first()
            )
            citation.document = document.title if document else citation.sourceLabel
            citation.excerpt = _excerpt(chunk.text)
            meta = chunk.metadata_info or {}
            citation.section = citation.section or meta.get("section")
        return citations


def _excerpt(text: str, *, limit: int = 480) -> str:
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rsplit(" ", 1)[0] + "…"
