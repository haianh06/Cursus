"""Route student messages to companion / study / mixed intents.

Ported from origin/develop verbatim — pure regex classifier, no schema/DB
dependency, so no tenancy adaptation was needed. Wired into
`companion_service.py`'s `send_message()` ahead of the guardrail/retrieval
pipeline so an emotionally-distressed message gets an empathic reply (or the
crisis safety response) instead of being run through academic Q&A.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from src.services.rag.query_normalization import fold_accents

ChatRoute = Literal["companion", "study", "mixed"]


@dataclass(frozen=True)
class RouteDecision:
    route: ChatRoute
    companion_score: float
    study_score: float


_COMPANION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(buon|met|moi|met\s*moi|stress|ap\s*luc|lo\s*lang|lo\s*au|so\s*hai)\b",
        r"\b(chan\s*nan|that\s*vong|tuyet\s*vong|co\s*don|co\s*doc)\b",
        r"\b(khong\s*muon\s*hoc|bo\s*cuoc|chap\s*het|kiet\s*suc)\b",
        r"\b(tam\s*su|chia\s*se|nghe\s*minh|dong\s*vien)\b",
        r"\b(anxious|depressed|lonely|overwhelmed|burnout|sad|tired)\b",
        r"\b(i\s+feel|feeling|stressed|hopeless|give\s+up)\b",
        r"\b(khoc|mat\s*ngu|mat\s*an|hoang\s*loan)\b",
    )
)

_STUDY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(syllabus|lab|assignment|deadline|bai\s*tap|bai\s*giang)\b",
        r"\b(khai\s*niem|dinh\s*nghia|giai\s*thich|tom\s*tat|vi\s*du)\b",
        r"\b(chapter|chuong|tuan\s*\d+|week\s*\d+|grading|diem)\b",
        r"\b(algorithm|protocol|cache|cpu|network|database|sql|oop)\b",
        r"\b(lam\s*sao|nhu\s*the\s*nao|la\s*gi|what\s+is|how\s+to|explain)\b",
        # Compare / contrast — any topic, not phrase-specific.
        r"\b(so\s*sanh|khac\s*nhau|compare|phan\s*tich|difference|versus|vs)\b",
        # Programming / CS surface forms students type without "?" or "giải thích".
        r"\b(for|while|do-while|do\s*while|loop|loops|vong\s*lap|pointer|pointers|array|arrays|mang|string|strings|struct|scanf|printf|function|ham)\b",
        r"\?",
    )
)

_CRISIS_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\b(tu\s*tu|muon\s*chet|ket\s*thuc\s*cuoc\s*doi)\b",
        r"\b(suicide|kill\s+myself|end\s+my\s+life|self\s*-?\s*harm)\b",
        r"\b(tu\s*lam\s*dau|tu\s*hai)\b",
    )
)


class ChatRouterService:
    def route(self, question: str) -> RouteDecision:
        folded = fold_accents(question or "").lower()
        folded = re.sub(r"\s+", " ", folded).strip()
        if not folded:
            return RouteDecision(route="companion", companion_score=0.0, study_score=0.0)

        companion = sum(1.0 for p in _COMPANION_PATTERNS if p.search(folded))
        study = sum(1.0 for p in _STUDY_PATTERNS if p.search(folded))

        if companion > 0 and study > 0:
            route: ChatRoute = "mixed"
        elif companion > study:
            route = "companion"
        elif study > companion:
            route = "study"
        else:
            # Study-first product: short/ambiguous messages without emotion cues
            # go to study/retrieval, not the companion template.
            route = "study"

        return RouteDecision(
            route=route,
            companion_score=companion,
            study_score=study,
        )

    def is_crisis(self, question: str) -> bool:
        folded = fold_accents(question or "").lower()
        return any(p.search(folded) for p in _CRISIS_PATTERNS)
