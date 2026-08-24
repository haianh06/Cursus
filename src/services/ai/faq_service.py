"""Match curated FAQ answers before retrieval/LLM (quota-saving path)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from src.knowledge.faq_bank import FAQ_ENTRIES, FaqEntry
from src.schemas.qa import QaCitation
from src.services.ai.qa_answer_service import MOCK_CONTENT_DISCLAIMER as MOCK_FAQ_DISCLAIMER
from src.services.rag.query_normalization import fold_accents

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FaqMatch:
    entry: FaqEntry
    score: float


class FaqService:
    """Keyword FAQ matcher over accent-folded query text."""

    def match(self, *, subject_code: str, question: str) -> FaqMatch | None:
        code = subject_code.strip().upper()
        folded = fold_accents(question).lower()
        folded = re.sub(r"\s+", " ", folded).strip()
        if not folded:
            return None

        best: FaqMatch | None = None
        for entry in FAQ_ENTRIES:
            if entry.subject_code != code:
                continue
            hits = 0
            hit_weight = 0.0
            for kw in entry.keywords:
                kw_folded = fold_accents(kw).lower().strip()
                if not kw_folded:
                    continue
                if kw_folded in folded:
                    hits += 1
                    # Longer phrases rank higher.
                    hit_weight += 1.0 + min(len(kw_folded), 40) / 40.0
            if hits < entry.min_hits:
                continue
            score = hit_weight
            if best is None or score > best.score:
                best = FaqMatch(entry=entry, score=score)

        if best is None:
            return None
        # Require a minimally specific hit (avoid matching lone "c" etc.).
        if best.score < 1.2:
            return None
        logger.info(
            "faq_hit subject=%s id=%s score=%.2f",
            code,
            best.entry.id,
            best.score,
        )
        return best

    def to_response_parts(self, match: FaqMatch) -> tuple[str, list[QaCitation], str]:
        entry = match.entry
        citation = QaCitation(
            sourceLabel=entry.source_label,
            section=None,
            chunkId=f"faq:{entry.id}",
            docTitle=entry.source_label,
            score=round(match.score, 3),
            isMock=entry.is_mock,
        )
        answer = entry.answer
        if entry.is_mock:
            answer = f"{MOCK_FAQ_DISCLAIMER}\n\n{answer}"
        return answer, [citation], "faq"
