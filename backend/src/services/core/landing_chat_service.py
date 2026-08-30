"""Public landing-page chat widget — a pre-login product demo for anonymous
visitors, same pattern as Intercom/Drift's marketing-site chat bubble.
Reachable with zero auth, so this is deliberately scoped away from any
student data or course retrieval: it only ever answers "what is Cursus"
style questions, grounded in a fixed system prompt, never a live DB read.
"""
from __future__ import annotations

from pydantic import BaseModel

from src.services.core.ai_service_client import generate_structured
from src.services.core.llm import has_configured_llm

MAX_QUESTION_LENGTH = 500

SYSTEM_PROMPT = """Bạn là trợ lý giới thiệu sản phẩm Cursus cho khách truy cập landing page, CHƯA đăng nhập.

Cursus là gì: nền tảng AI đồng hành học tập theo chu trình Plan-Do-Reflect -- biến syllabus thành kế hoạch tuần, trả lời câu hỏi luôn kèm trích dẫn nguồn tài liệu, KHÔNG làm hộ bài (guardrail chặn hoặc chuyển hướng gợi mở kiểu Socratic), giảng viên giám sát tiến độ và can thiệp khi cần.

QUY TẮC BẮT BUỘC:
1. CHỈ trả lời câu hỏi về sản phẩm Cursus (tính năng, cách hoạt động, đối tượng dùng, an toàn học thuật, giá/demo). Câu hỏi ngoài phạm vi này (bài tập, kiến thức môn học cụ thể, chuyện riêng tư, hỏi thay đăng nhập...) -- trả lời ngắn gọn, hướng người dùng bấm "Trải nghiệm Cursus" để dùng thử, không cố trả lời thay.
2. KHÔNG có quyền truy cập dữ liệu học tập của bất kỳ ai -- không bịa thông tin khoá học/điểm số/deadline cụ thể của người dùng thật.
3. Trả lời ngắn gọn (2-4 câu). Tiếng Việt có dấu, trừ khi người dùng hỏi bằng tiếng Anh thì trả lời tiếng Anh.
4. Chỉ trả về đúng JSON theo schema, không thêm giải thích/markdown ngoài JSON.

SCHEMA: {"answer": "..."}"""

FALLBACK_ANSWER = (
    "Cursus là trợ lý AI đồng hành học tập theo chu trình Plan-Do-Reflect: biến "
    "syllabus thành kế hoạch tuần, trả lời có trích dẫn nguồn, không làm hộ bài, "
    "giảng viên giám sát tiến độ. Bấm \"Trải nghiệm Cursus\" để dùng thử ngay."
)


class _LandingChatReply(BaseModel):
    answer: str = ""


def answer(question: str) -> dict:
    question = (question or "").strip()
    if not question:
        raise ValueError("question is required")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"question too long (max {MAX_QUESTION_LENGTH} characters)")

    if not has_configured_llm():
        return {"answer": FALLBACK_ANSWER, "generatedByLlm": False}

    try:
        payload = generate_structured(
            schema_model=_LandingChatReply,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=question,
            intent="landing_chat",
        )
        text = payload.answer.strip()
        return {"answer": text or FALLBACK_ANSWER, "generatedByLlm": bool(text)}
    except Exception:  # noqa: BLE001 -- provider/budget/network must not block the widget
        return {"answer": FALLBACK_ANSWER, "generatedByLlm": False}
