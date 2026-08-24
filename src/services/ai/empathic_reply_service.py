"""Empathic (non-therapy) companion replies for the Companion chat surface.

Adapted from origin/develop's `companion_service.py` — renamed to avoid
colliding with this branch's `CompanionService` (thread/message orchestrator
in `src/services/companion_service.py`, which already existed under that
name before this file was added). Uses this branch's `get_llm()`/
`has_configured_llm()` pattern (`src/services/llm.py`) rather than develop's
`invoke_with_model_fallback` helper, to avoid introducing new LLM-call
machinery beyond what `qa_answer_service.py` already established.
"""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import BaseModel

from src.services.core.llm import get_llm, has_configured_llm
from src.services.core.provider_errors import classify_provider_error

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "companion_v1.md"

CRISIS_REPLY = (
    "Mình nghe bạn đang rất nặng lòng — cảm ơn bạn đã chia sẻ. "
    "Mình chỉ là trợ lý học tập, không thể thay nhà tham vấn chuyên nghiệp. "
    "Nếu bạn đang nghĩ đến việc tự làm hại bản thân, hãy liên hệ ngay "
    "trung tâm hỗ trợ sinh viên / tư vấn tâm lý của trường hoặc người lớn tin cậy, "
    "hoặc dịch vụ khẩn cấp địa phương. Bạn không phải chịu một mình.\n\n"
    "Nếu muốn, mình có thể ngồi lại với bạn về áp lực học tập hoặc chia nhỏ việc cần làm tuần này."
)

_TEMPLATE_REPLY = (
    "Cảm ơn bạn đã chia sẻ. Nghe có vẻ tuần này khá áp lực — mình ở đây nếu bạn "
    "muốn kể thêm, hoặc mình có thể giúp chia nhỏ việc cần làm cho môn học này "
    "thành các bước nhỏ hơn, dễ thở hơn."
)


class EmpathicReplyPayload(BaseModel):
    answer: str
    needs_professional_help: bool = False


class EmpathicReplyService:
    def reply(
        self,
        *,
        question: str,
        subject_code: str,
        history: list[dict[str, str]] | None = None,
        crisis: bool = False,
    ) -> tuple[str, str]:
        """Return (answer, mode). mode is companion | companion_crisis."""
        if crisis:
            return CRISIS_REPLY, "companion_crisis"

        if not has_configured_llm():
            return _TEMPLATE_REPLY, "companion"

        try:
            system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
            messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
            for turn in history or []:
                role = "assistant" if turn.get("role") == "assistant" else "user"
                content = (turn.get("content") or "").strip()
                if content:
                    messages.append({"role": role, "content": content})
            messages.append(
                {
                    "role": "user",
                    "content": f"Môn đang mở: {subject_code}\nTin nhắn sinh viên: {question}",
                }
            )
            llm = get_llm().with_structured_output(EmpathicReplyPayload)
            payload = llm.invoke(messages)
            if not isinstance(payload, EmpathicReplyPayload):
                payload = EmpathicReplyPayload.model_validate(payload)
            answer = payload.answer.strip()
            if payload.needs_professional_help:
                return f"{answer}\n\n---\n{CRISIS_REPLY}", "companion_crisis"
            return answer or _TEMPLATE_REPLY, "companion"
        except Exception as exc:
            failure = classify_provider_error(exc)
            logger.warning("empathic_reply_failed code=%s: %s", failure.code, failure.message)
            return _TEMPLATE_REPLY, "companion"
