"""Wellbeing/crisis-safety check for Cursus Chat — deliberately separate from
`guardrail_service.py` (academic-integrity guardrail): different concern
(student safety, not cheating prevention), different consequence (never a
"cannot help" dead end — always a supportive answer + real hotline numbers),
and must run BEFORE the academic guardrail so a message that happens to also
look like a "graded_deliverable" ask (e.g. "em không muốn làm bài nữa, muốn
biến mất") is never misrouted into the wrong response.

Rule-based (not LLM-based) on purpose: a crisis message must never depend on
an LLM call succeeding, and a false negative here is far worse than a false
positive — err toward triggering. Not admin-toggleable like guardrail rules;
this is not a policy an org should be able to relax.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# VI (with and without diacritics, since students often type accent-free)
# and EN patterns for self-harm/suicide ideation. Intentionally broad rather
# than clever — a false positive just shows a supportive message with an
# "I'm actually fine" escape hatch is unnecessary since the answer never
# blocks the student from continuing to chat about anything else.
_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\b(tự tử|tu tu|tự sát|tu sat)\b",
        r"\b(muốn chết|muon chet|không muốn sống|khong muon song)\b",
        r"\bmuốn biến mất\b|\bmuon bien mat\b",
        r"\btự làm hại|tu lam hai|tự hại bản thân|tu hai ban than\b",
        r"\bkhông ai (cần|quan tâm)\b.{0,20}\b(tôi|em|mình)\b",
        r"\bsuicide|self[\s-]?harm|kill myself|end my life|want to die\b",
        r"\bi (can'?t|cannot) (go on|do this anymore)\b",
    )
)

_HOTLINES_VI = (
    "Đường dây nóng Tư vấn Tâm lý Học đường 1800-599-920 (miễn phí, 24/7)",
    "Ngày Mai (hỗ trợ khủng hoảng tâm lý): 096 306 1414",
)

_ANSWER_VI = (
    "Mình nghe thấy bạn đang rất khó khăn, và điều đó quan trọng hơn bất kỳ "
    "câu hỏi bài học nào lúc này. Mình không phải chuyên gia và không thể "
    "thay thế người có thể thực sự giúp bạn — nhưng bạn không cần phải tự "
    "vượt qua một mình.\n\n"
    "Nếu bạn đang nghĩ đến việc làm hại bản thân, hãy liên hệ ngay:\n"
    + "\n".join(f"- {line}" for line in _HOTLINES_VI)
    + "\n\nNếu tiện, hãy nói chuyện với một người bạn tin tưởng hoặc phòng "
    "Công tác Sinh viên của trường ngay hôm nay. Mình vẫn ở đây nếu bạn muốn "
    "quay lại nói tiếp, về chuyện này hay bất cứ điều gì khác."
)


@dataclass(frozen=True)
class CrisisDecision:
    triggered: bool
    answer: str | None = None


def evaluate(message: str) -> CrisisDecision:
    text = (message or "").strip()
    if not text:
        return CrisisDecision(triggered=False)
    if any(pattern.search(text) for pattern in _PATTERNS):
        return CrisisDecision(triggered=True, answer=_ANSWER_VI)
    return CrisisDecision(triggered=False)
