"""Wellbeing/crisis-safety check for Cursus Chat — deliberately separate from
`guardrail_service.py` (academic-integrity guardrail): different concern
(student safety, not cheating prevention), different consequence (never a
"cannot help" dead end — always a supportive answer + real hotline numbers,
AND an immediate escalation to Admin/CTSV, see `cursus_chat.py::stream_chat`
and `src/api/admin_crisis_escalations.py`), and must run BEFORE the academic
guardrail so a message that happens to also look like a "graded_deliverable"
ask (e.g. "em không muốn làm bài nữa, muốn biến mất") is never misrouted
into the wrong response.

Rule-based (not LLM-based) on purpose: a crisis message must never depend on
an LLM call succeeding, and a false negative here is far worse than a false
positive — err toward triggering. Not admin-toggleable like guardrail rules;
this is not a policy an org should be able to relax.

IMPORTANT — scope of what this module actually is: a rule-based keyword/
phrase matcher written by an engineer, not a clinically validated
screening instrument. It is ONE layer of defense (paired with human
escalation so a person, not just this code, makes the real judgment call)
and should not be treated as sufficient on its own without review by
people qualified in student mental-health response and by the
institution's legal/compliance function — see `docs/` production-readiness
notes. Treat a "no match" here as "this specific pattern list didn't fire
today", not as "this message was clinically screened for risk and cleared".
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from src.services.rag.query_normalization import fold_accents

# Written once in (mostly) accented Vietnamese, compiled twice: once as-is
# and once with `fold_accents()` applied to the pattern source (regex
# metacharacters like \b/(/)/| have no diacritics, so folding them is a
# no-op) -- `evaluate()` then matches the folded set against the folded
# message, so a single source pattern catches both "tự tử" and the
# accent-stripped "tu tu" a student types without hand-duplicating every
# spelling. (`đ` does not decompose under Unicode NFD, so fold_accents
# leaves it as-is -- a known, pre-existing limitation shared with every
# other fold_accents() consumer in this codebase, e.g. guardrail_rules.py.)
# Organized by theme for maintainability — add new phrasing here as real
# (redacted) examples surface, don't rely on this list being exhaustive.
_VI_PATTERN_SOURCES: tuple[str, ...] = (
    # Direct suicide/self-harm intent or method
    r"\btự tử\b", r"\btự sát\b", r"\btự vẫn\b",
    r"\btự làm hại( bản thân)?\b", r"\btự hại( bản thân)?\b",
    r"\bcắt (tay|cổ tay)\b", r"\brạch tay\b",
    r"\buống thuốc (quá liều|cho chết)\b", r"\bnhảy lầu\b", r"\btreo cổ\b",
    # Hopelessness / wish to die or disappear
    r"\bmuốn chết\b", r"\bkhông muốn sống\b", r"\bchán sống\b",
    r"\bmuốn biến mất( mãi mãi)?\b", r"\bmuốn kết thúc (tất cả|cuộc đời|mọi thứ)\b",
    r"\bmuốn giải thoát\b", r"\bkhông còn (lý do|ý nghĩa) (gì )?để sống\b",
    r"\bsống (không|chẳng) có ý nghĩa( gì)?\b", r"\bthà chết còn hơn\b",
    # Burden / worthlessness framing common in real crisis language
    r"\bkhông ai (cần|quan tâm|yêu thương)\b.{0,20}\b(tôi|em|mình)\b",
    r"\b(tôi|em|mình) là (gánh nặng|vô dụng|thừa thãi)\b",
    r"\bmọi người sẽ (tốt hơn|nhẹ nhõm hơn) nếu (không có|thiếu) (tôi|em|mình)\b",
    # Explicit plan/goodbye language
    r"\bđây là lời (tạm biệt|chào tạm biệt) cuối cùng\b",
    r"\bkhông cần (lo|quan tâm) cho (tôi|em|mình) nữa\b",
)
_VI_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE) for pattern in _VI_PATTERN_SOURCES
)
_VI_PATTERNS_FOLDED: tuple[re.Pattern[str], ...] = tuple(
    re.compile(fold_accents(pattern), re.IGNORECASE) for pattern in _VI_PATTERN_SOURCES
)

_EN_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bsuicid(e|al)\b", r"\bkill(ing)? myself\b", r"\bend(ing)? my( own)? life\b",
        r"\bself[\s-]?harm(ing)?\b", r"\bhurt(ing)? myself\b", r"\bcut(ting)? myself\b",
        r"\bwant(ed)? to die\b", r"\bbetter off dead\b", r"\bno reason to live\b",
        r"\bcan'?t (go on|take it anymore|do this anymore)\b",
        r"\bi'?m (a )?burden\b", r"\bnobody (would )?(care|notice) if i (was|were) gone\b",
        r"\bthis is (my )?goodbye\b",
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
    "vượt qua một mình. Mình cũng đã báo cho phòng Công tác Sinh viên của "
    "trường để có người liên hệ hỗ trợ bạn sớm nhất.\n\n"
    "Nếu bạn đang nghĩ đến việc làm hại bản thân, hãy liên hệ ngay:\n"
    + "\n".join(f"- {line}" for line in _HOTLINES_VI)
    + "\n\nNếu tiện, hãy nói chuyện với một người bạn tin tưởng ngay hôm nay. "
    "Mình vẫn ở đây nếu bạn muốn quay lại nói tiếp, về chuyện này hay bất cứ "
    "điều gì khác."
)


@dataclass(frozen=True)
class CrisisDecision:
    triggered: bool
    answer: str | None = None


def evaluate(message: str) -> CrisisDecision:
    text = (message or "").strip()
    if not text:
        return CrisisDecision(triggered=False)
    folded = fold_accents(text)
    if any(pattern.search(text) for pattern in _VI_PATTERNS):
        return CrisisDecision(triggered=True, answer=_ANSWER_VI)
    if any(pattern.search(folded) for pattern in _VI_PATTERNS):
        return CrisisDecision(triggered=True, answer=_ANSWER_VI)
    if any(pattern.search(text) for pattern in _EN_PATTERNS):
        return CrisisDecision(triggered=True, answer=_ANSWER_VI)
    return CrisisDecision(triggered=False)
