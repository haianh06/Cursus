"""Build MCQ + flashcard practice items from course content.

Adapted from develop's `src/services/practice_generator.py`, but grounded
against THIS branch's DB-backed `ChunkRepository`/`RetrievalService`
(`src/services/retrieval_service.py`) instead of develop's static-file
`src.services.rag` module — that module has no course/org concept and isn't
wired to the tenant-scoped chunk store this branch actually uses.

Follows the shared `ai_service_client.generate_structured()` convention
(LLM call delegated to ai-service), a broad try/except around the call,
and a deterministic fallback (never a hard failure) when no real key is
configured or the call/parse fails.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.repositories.chunk_repository import ChunkRecord, ChunkRepository
from src.services.academic.academic_calendar import clamp_study_week, slide_key_for_week, slot_number
from src.services.core.ai_service_client import generate_structured
from src.services.core.llm import has_configured_llm
from src.services.rag.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

MCQ_COUNT = 10
FLASHCARD_COUNT = 10
OPTION_KEYS = ("A", "B", "C", "D")

SYSTEM_PROMPT = """Ban soan bo on tap tu tai lieu mon hoc da cho.

QUY TAC:
1. Chi dung thong tin trong tai lieu. Khong bia, khong lay cau hoi thi.
2. Dung 10 cau MCQ (4 lua chon A-D, dung 1 dap an) va dung 10 flashcard.
3. Moi muc phai co source_label sao chep NGUYEN VAN tu nhan nguon da cung cap.
4. MCQ kiem tra khai niem/dinh nghia trong tai lieu, khong phai meo danh do.
5. Flashcard: mat truoc la thuat ngu ngan, mat sau la dinh nghia 1-2 cau.
6. Chi tra JSON, khong markdown.
"""


class _McqSpec(BaseModel):
    prompt: str
    options: dict[str, str] = Field(default_factory=dict)
    correct_key: str = "A"
    explanation: str = ""
    source_label: str = ""


class _FlashcardSpec(BaseModel):
    front: str
    back: str
    source_label: str = ""


class _PracticePackPayload(BaseModel):
    mcq: list[_McqSpec] = Field(default_factory=list)
    flashcards: list[_FlashcardSpec] = Field(default_factory=list)


def generate_pack(
    *,
    db: Session,
    subject_code: str,
    week_number: int,
    student_id: str | None = None,
    language: str = "vi",
) -> tuple[list[dict[str, Any]], str]:
    """Return (item specs, resolved slide_key)."""
    week = clamp_study_week(week_number)
    chunks, slide_key = _chunks_for_week(
        db, subject_code=subject_code, week_number=week, student_id=student_id
    )
    if not chunks:
        raise ValueError("No course material available to generate practice from")

    if has_configured_llm():
        try:
            return _from_llm(chunks, language), slide_key
        except Exception as exc:  # noqa: BLE001 — provider/network must not block the flow
            logger.warning("practice_llm_failed subject=%s error=%s", subject_code, exc)

    return _fallback_pack(chunks, language), slide_key


def _chunks_for_week(
    db: Session,
    *,
    subject_code: str,
    week_number: int,
    student_id: str | None,
) -> tuple[list[ChunkRecord], str]:
    repo = ChunkRepository(db)
    all_chunks = repo.list_chunks_for_course(subject_code=subject_code, student_id=student_id)
    if not all_chunks:
        return [], slide_key_for_week(week_number)

    grouped: dict[int, list[ChunkRecord]] = {}
    unlabeled: list[ChunkRecord] = []
    for chunk in all_chunks:
        number = slot_number(chunk.source_label or "") or slot_number(chunk.section or "")
        if number is None:
            unlabeled.append(chunk)
            continue
        grouped.setdefault(number, []).append(chunk)

    if week_number in grouped:
        return grouped[week_number][:12], slide_key_for_week(week_number)
    if grouped:
        nearest = min(grouped, key=lambda slot: (abs(slot - week_number), slot))
        return grouped[nearest][:12], slide_key_for_week(nearest)

    # No week-labeled material at all — fall back to lexical/embedding
    # retrieval for a generic "this week's lecture" query, then to whatever
    # course chunks exist so a request never comes back empty.
    retrieval = RetrievalService(repo)
    hits = retrieval.retrieve(
        subject_code=subject_code,
        question=f"Tuan {week_number} bai giang noi dung chinh",
        student_id=student_id,
    )
    if hits:
        return [item.chunk for item in hits][:12], slide_key_for_week(week_number)
    return unlabeled[:12], slide_key_for_week(week_number)


def _from_llm(chunks: list[ChunkRecord], language: str) -> list[dict[str, Any]]:
    excerpts = "\n\n".join(f"[Nguon: {chunk.source_label}]\n{chunk.text}" for chunk in chunks[:12])
    lang_line = "Viet tieng Viet." if language.lower().startswith("vi") else "Write in English."
    payload = generate_structured(
        schema_model=_PracticePackPayload,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=f"{lang_line}\n\nTAI LIEU:\n{excerpts}",
        intent="practice",
    )

    allowed = {chunk.source_label for chunk in chunks if chunk.source_label}
    default_label = chunks[0].source_label or ""

    items: list[dict[str, Any]] = []
    for index, raw in enumerate(payload.mcq[:MCQ_COUNT], start=1):
        items.append(_normalize_mcq(raw, index, allowed, default_label))
    for index, raw in enumerate(payload.flashcards[:FLASHCARD_COUNT], start=1):
        items.append(_normalize_card(raw, index, allowed, default_label))

    if len([item for item in items if item["kind"] == "MCQ"]) < MCQ_COUNT:
        raise ValueError("LLM returned too few MCQ items")
    if len([item for item in items if item["kind"] == "FLASHCARD"]) < FLASHCARD_COUNT:
        raise ValueError("LLM returned too few flashcards")
    return items


def _normalize_mcq(
    raw: _McqSpec, index: int, allowed: set[str], default_label: str
) -> dict[str, Any]:
    options = [
        {"key": key, "text": str(raw.options.get(key) or "").strip() or f"Lua chon {key}"}
        for key in OPTION_KEYS
    ]
    correct = (raw.correct_key or "A").strip().upper()[:1]
    if correct not in OPTION_KEYS:
        correct = "A"
    label = (raw.source_label or "").strip()
    if allowed and label not in allowed:
        label = default_label
    answer = next((item["text"] for item in options if item["key"] == correct), "")
    return {
        "kind": "MCQ",
        "sort_order": index,
        "prompt": raw.prompt.strip() or f"Cau hoi {index}",
        "options": options,
        "correct_key": correct,
        "answer": answer,
        "explanation": (raw.explanation or "").strip(),
        "source_label": label,
    }


def _normalize_card(
    raw: _FlashcardSpec, index: int, allowed: set[str], default_label: str
) -> dict[str, Any]:
    label = (raw.source_label or "").strip()
    if allowed and label not in allowed:
        label = default_label
    return {
        "kind": "FLASHCARD",
        "sort_order": index,
        "prompt": raw.front.strip() or f"Thuat ngu {index}",
        "options": None,
        "correct_key": None,
        "answer": raw.back.strip(),
        "explanation": "",
        "source_label": label,
    }


def _fallback_pack(chunks: list[ChunkRecord], language: str) -> list[dict[str, Any]]:
    vi = language.lower().startswith("vi")
    items: list[dict[str, Any]] = []
    pool = chunks
    for index in range(MCQ_COUNT):
        chunk = pool[index % len(pool)]
        other = pool[(index + 1) % len(pool)]
        topic = chunk.section or chunk.doc_title or "bai giang"
        excerpt = _clip(chunk.text or topic, 90)
        distractors = [
            _clip(other.text or other.section or "Noi dung buoi khac", 80),
            "Phat bieu nay trai voi tai lieu mon hoc." if vi else "This contradicts the course material.",
            "Khong duoc neu trong tai lieu nay." if vi else "Not stated in this material.",
        ]
        prompt = (
            f"Theo tai lieu mon hoc, noi dung nao dung ve {topic}?"
            if vi
            else f"According to the course material, which statement about {topic} is correct?"
        )
        options = [
            {"key": "A", "text": excerpt},
            {"key": "B", "text": distractors[0]},
            {"key": "C", "text": distractors[1]},
            {"key": "D", "text": distractors[2]},
        ]
        items.append(
            {
                "kind": "MCQ",
                "sort_order": index + 1,
                "prompt": prompt,
                "options": options,
                "correct_key": "A",
                "answer": excerpt,
                "explanation": excerpt,
                "source_label": chunk.source_label or "",
            }
        )
    for index in range(FLASHCARD_COUNT):
        chunk = pool[index % len(pool)]
        front = chunk.section or f"{chunk.course_code} #{index + 1}"
        items.append(
            {
                "kind": "FLASHCARD",
                "sort_order": index + 1,
                "prompt": str(front)[:80],
                "options": None,
                "correct_key": None,
                "answer": _clip(chunk.text or str(front), 220),
                "explanation": "",
                "source_label": chunk.source_label or "",
            }
        )
    return items


def _clip(text: str, limit: int) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "..."
