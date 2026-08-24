"""Detect greetings / meta chat that should not go through course RAG."""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.services.rag.query_normalization import normalize_query


@dataclass(frozen=True)
class ConversationIntent:
    is_chat: bool
    answer: str | None = None


# Patterns run against accent-folded, formatting-stripped text.
_GREETING_RE = re.compile(
    r"^("
    r"hi+|hello+|hey+|yo+|sup|"
    r"chao(\s+ban)?|xin\s*chao|alo|e|"
    r"good\s+(morning|afternoon|evening)|"
    r"howdy"
    r")[\s!.,?~]*$",
    re.IGNORECASE,
)

_THANKS_RE = re.compile(
    r"^("
    r"thanks?|thank\s+you|ty|"
    r"cam\s*on|thanks\s+a\s+lot"
    r")[\s!.,?~]*$",
    re.IGNORECASE,
)

_HELP_RE = re.compile(
    r"^("
    r"help|help\s+me|"
    r"ban\s+lam\s+duoc\s+gi|may\s+lam\s+duoc\s+gi|"
    r"ban\s+giup\s+duoc\s+gi|what\s+can\s+you\s+do|"
    r"how\s+do\s+you\s+work|ban\s+la\s+ai"
    r")[\s!.,?~]*$",
    re.IGNORECASE,
)


class ConversationIntentService:
    def resolve(self, question: str, *, subject_code: str) -> ConversationIntent:
        normalized = normalize_query(question)
        text = normalized.folded
        if not text:
            return ConversationIntent(is_chat=False)

        if _GREETING_RE.match(text):
            return ConversationIntent(
                is_chat=True,
                answer=(
                    f"Chào bạn! Mình là Study Assistant cho môn {subject_code}. "
                    "Bạn có thể hỏi về syllabus, bài giảng, FAQ, hoặc nhờ tóm tắt "
                    "học liệu / ghi chú đã upload. Ví dụ: “Tóm tắt syllabus” hoặc "
                    "“Weekly Commitment Map là gì?”."
                ),
            )

        if _THANKS_RE.match(text):
            return ConversationIntent(
                is_chat=True,
                answer=(
                    "Không có gì! Nếu cần, cứ hỏi tiếp về nội dung môn "
                    f"{subject_code} nhé."
                ),
            )

        if _HELP_RE.match(text):
            return ConversationIntent(
                is_chat=True,
                answer=(
                    f"Với môn {subject_code}, mình có thể:\n"
                    "1. Trả lời FAQ cơ bản ngay (không gọi LLM — tiết kiệm quota)\n"
                    "2. Trích học liệu / ghi chú đã upload kèm citation\n"
                    "3. Tóm tắt syllabus hoặc lecture notes\n"
                    "4. Gọi Gemini chỉ khi câu hỏi cần so sánh / phân tích sâu\n"
                    "5. Gợi ý hướng học — nhưng không làm hộ bài tập\n\n"
                    "Thử chip FAQ trên màn hình, hoặc hỏi ví dụ: "
                    "“Lab 02 yêu cầu gì?” / “Tóm tắt syllabus”."
                ),
            )

        return ConversationIntent(is_chat=False)
