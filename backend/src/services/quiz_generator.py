"""Generate quiz questions from a course's lecture chunks (LLM optional).

Mirrors the retired practice_generator.py's LLM-optional pattern: with no
real Google API key configured (the case in this dev/test environment —
GOOGLE_API_KEY defaults to the placeholder "test-key"), questions are built
deterministically straight from the lecture text so the feature still works
end-to-end for a demo.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from pydantic import BaseModel

from src.services.core.ai_service_client import generate_structured
from src.services.core.llm import has_configured_llm

logger = logging.getLogger(__name__)

MIN_COUNT = 1
MAX_COUNT = 20
CHUNK_WINDOW = 16

SYSTEM_PROMPT = """Bạn soạn câu hỏi trắc nghiệm ôn tập từ tài liệu bài giảng được cung cấp.

QUY TẮC:
1. Chỉ dùng thông tin trong tài liệu được cung cấp. Không bịa đặt, không lấy câu hỏi thi PE/FE.
2. Sinh đúng {count} câu hỏi, mỗi câu là MULTIPLE_CHOICE (4 lựa chọn, đúng 1 đáp án) hoặc
   TRUE_FALSE (đúng/sai về một phát biểu liên quan tới tài liệu).
3. Câu hỏi kiểm tra khái niệm/định nghĩa trong tài liệu, không phải mẹo đánh đố.
4. Câu hỏi và đáp án phải viết bằng tiếng Việt có dấu, không chèn ký hiệu markdown (#, *, -).
5. Chỉ trả về JSON, không markdown, không giải thích thêm.

SCHEMA:
{{"questions": [
  {{"question_text": "...", "question_type": "MULTIPLE_CHOICE", "options": ["...", "...", "...", "..."], "correct_answer": "..."}},
  {{"question_text": "...", "question_type": "TRUE_FALSE", "correct_answer": "true"}}
]}}"""


def generate_questions(
    chunks: list[tuple[Any, Any]],
    count: int,
) -> list[dict[str, Any]]:
    """chunks: list of (DocumentChunk, Document) tuples for one course."""
    count = max(MIN_COUNT, min(count, MAX_COUNT))
    if not chunks:
        raise ValueError("No lecture material found for this course")

    if has_configured_llm():
        try:
            return _from_llm(chunks, count)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.warning("quiz_generate_llm_invalid error=%s", exc)
        except Exception as exc:  # noqa: BLE001 — provider/network must not block demo
            logger.error("quiz_generate_llm_failed error=%s", exc)

    return _fallback_questions(chunks, count)


class _QuizPayload(BaseModel):
    questions: list[dict[str, Any]] = []


def _from_llm(chunks: list[tuple[Any, Any]], count: int) -> list[dict[str, Any]]:
    excerpts = "\n\n".join(
        f"[Nguồn: {doc.title}]\n{chunk.text}" for chunk, doc in chunks[:CHUNK_WINDOW]
    )
    result = generate_structured(
        schema_model=_QuizPayload,
        system_prompt=SYSTEM_PROMPT.format(count=count),
        user_prompt=f"TÀI LIỆU BÀI GIẢNG:\n{excerpts}",
        intent="quiz_generation",
    )
    questions = _normalize_payload(result.model_dump(), count)
    if len(questions) < 1:
        raise ValueError("LLM returned no usable questions")
    return questions


def _normalize_payload(payload: dict[str, Any], count: int) -> list[dict[str, Any]]:
    raw_questions = payload.get("questions")
    if not isinstance(raw_questions, list):
        raise ValueError("LLM payload missing questions list")
    out: list[dict[str, Any]] = []
    for raw in raw_questions[:count]:
        if not isinstance(raw, dict):
            continue
        question_type = str(raw.get("question_type") or "").strip().upper()
        question_text = re.sub(r"\s+", " ", _strip_markdown(str(raw.get("question_text") or ""))).strip()
        if not question_text:
            continue
        if question_type == "TRUE_FALSE":
            normalized = str(raw.get("correct_answer") or "").strip().lower()
            if normalized not in ("true", "false"):
                continue
            out.append(
                {
                    "question_text": question_text,
                    "question_type": "TRUE_FALSE",
                    "options": ["True", "False"],
                    "correct_answer": "True" if normalized == "true" else "False",
                    "points": 1,
                }
            )
        elif question_type == "MULTIPLE_CHOICE":
            options = [
                re.sub(r"\s+", " ", _strip_markdown(str(opt))).strip()
                for opt in (raw.get("options") or [])
                if str(opt).strip()
            ]
            correct = re.sub(r"\s+", " ", _strip_markdown(str(raw.get("correct_answer") or ""))).strip()
            if len(options) < 2 or correct not in options:
                continue
            out.append(
                {
                    "question_text": question_text,
                    "question_type": "MULTIPLE_CHOICE",
                    "options": options,
                    "correct_answer": correct,
                    "points": 1,
                }
            )
    return out


GENERIC_DISTRACTORS = [
    "Phát biểu này trái với tài liệu bài giảng.",
    "Không được đề cập trong tài liệu này.",
    "Chỉ đúng một phần, không phải toàn bộ nội dung được hỏi.",
    "Đây là thông tin từ một bài giảng khác, không liên quan câu hỏi này.",
]


def _fallback_questions(chunks: list[tuple[Any, Any]], count: int) -> list[dict[str, Any]]:
    """No real LLM key: build multiple-choice questions straight from the
    lecture text (same shape the retired practice_generator used for MCQ).

    A course with very few chunks can make the "next" chunk wrap around to
    the SAME chunk as the correct answer, which used to silently produce two
    identical-looking options — always guarantee 4 distinct option strings.
    """
    pool = chunks
    out: list[dict[str, Any]] = []
    for index in range(count):
        chunk, doc = pool[index % len(pool)]
        other_chunk, other_doc = pool[(index + 1) % len(pool)]
        topic = doc.title or "bài giảng"
        correct_excerpt = _clip(chunk.text, 90)

        options = [correct_excerpt]
        distractor = _clip(other_chunk.text or other_doc.title, 80)
        if distractor and distractor not in options:
            options.append(distractor)
        for generic in GENERIC_DISTRACTORS:
            if len(options) >= 4:
                break
            if generic not in options:
                options.append(generic)

        out.append(
            {
                "question_text": f"Theo tài liệu bài giảng '{topic}', nội dung nào sau đây đúng?",
                "question_type": "MULTIPLE_CHOICE",
                "options": options,
                "correct_answer": correct_excerpt,
                "points": 1,
            }
        )
    return out


def _strip_markdown(text: str) -> str:
    """Lecture chunks are stored as raw markdown — headings/bullets/emphasis
    markers leak straight into a question's options if not stripped first."""
    text = re.sub(r"(?m)^#{1,6}\s*", "", text or "")
    text = re.sub(r"(?m)^\s*[-*+]\s+", "", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"[`*_#]", "", text)
    return text


def _clip(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", _strip_markdown(text)).strip()
    if len(cleaned) <= limit:
        return cleaned or "Nội dung bài giảng"
    return cleaned[: limit - 1].rstrip() + "…"


