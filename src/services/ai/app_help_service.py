"""Match "how do I use Cursus" questions against `app_help_bank.py`.

Same keyword-scoring shape as `FaqService`, generalized to (a) not be scoped
to a subject_code (app features aren't per-course) and (b) return multiple
candidates instead of a single best match, since the chat orchestrator uses
these as grounding context for the LLM rather than as a direct answer.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.knowledge.app_help_bank import HELP_ENTRIES, HelpEntry
from src.services.rag.query_normalization import fold_accents

_MIN_SCORE = 1.2
_MAX_MATCHES = 2


@dataclass(frozen=True)
class HelpMatch:
    entry: HelpEntry
    score: float


class AppHelpService:
    def match(self, question: str, *, limit: int = _MAX_MATCHES) -> list[HelpMatch]:
        folded = fold_accents(question or "").lower()
        if not folded:
            return []

        scored: list[HelpMatch] = []
        for entry in HELP_ENTRIES:
            hits = 0
            weight = 0.0
            for kw in entry.keywords:
                kw_folded = fold_accents(kw).lower().strip()
                if kw_folded and kw_folded in folded:
                    hits += 1
                    weight += 1.0 + min(len(kw_folded), 40) / 40.0
            if hits < entry.min_hits or weight < _MIN_SCORE:
                continue
            scored.append(HelpMatch(entry=entry, score=weight))

        scored.sort(key=lambda m: m.score, reverse=True)
        return scored[:limit]
