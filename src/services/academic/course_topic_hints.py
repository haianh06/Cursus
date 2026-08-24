"""Suggest a better course when retrieval is empty but the topic looks foreign.

Ported from origin/develop verbatim — the 4-course catalog it references
(SSA101/PRF192/CEA201/CSI106) matches this branch's own Gate2 seed data
(`src/services/student_mock_data_service.py`), so no adaptation was needed.

Data-driven token → course map. Extensible without special-casing user sentences.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.services.rag.query_normalization import fold_accents


@dataclass(frozen=True)
class TopicCourseHint:
    topic_label: str
    suggested_codes: tuple[str, ...]


# Folded topic tokens / phrases → home course(s). Broad classes, not fixed Q&A.
_TOPIC_COURSES: tuple[tuple[tuple[str, ...], str, tuple[str, ...]], ...] = (
    (("cpu", "alu", "datapath", "pipeline", "cache", "bus", "interrupt"), "CPU / kiến trúc máy", ("CEA201",)),
    (("von neumann", "boolean", "tcp", "udp", "complexity", "pseudocode"), "CS intro", ("CSI106",)),
    (("scanf", "printf", "pointer", "do-while", "vong lap", "struct"), "lập trình C", ("PRF192",)),
    (
        ("commitment map", "academic integrity", "note taking", "smart goal"),
        "kỹ năng học thuật",
        ("SSA101",),
    ),
)


def hint_for_empty_retrieval(*, subject_code: str, question: str) -> str | None:
    """Return a redirect hint, or None to keep the generic no-source message."""
    code = (subject_code or "").strip().upper()
    folded = fold_accents(question or "").lower()
    folded = re.sub(r"\s+", " ", folded).strip()
    if not folded or not code:
        return None

    for tokens, label, homes in _TOPIC_COURSES:
        if not any(token in folded for token in tokens):
            continue
        if code in homes:
            return None
        homes_txt = " / ".join(homes)
        return (
            f"Không tìm thấy thông tin liên quan trong tài liệu môn {code}. "
            f"Chủ đề “{label}” thường thuộc {homes_txt} — thử chọn đúng môn đó rồi hỏi lại nhé."
        )
    return None
