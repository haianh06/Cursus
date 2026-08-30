"""Academic-integrity guardrail for Study Assistant (runs before the LLM).

Implements the intents from the Blueprint §4.2 matrix that the Gate-2 demo
actually exercises:

    ask_knowledge      → normal grounded answer (no interception here)
    ask_hint           → Socratic step-by-step guidance, NOT blocked
    graded_deliverable → block the deliverable, redirect to guidance
    out_of_scope       → say the data is not available, never guess
    prompt_injection   → ignore conflicting instructions, reveal nothing

A block is never a dead end. Per §4.2 / §0 ("Không biến guardrail thành ngõ
cụt") a blocked answer must still carry: the concept explanation, a Socratic
question, and an empty template the student fills in themselves.

Unlike the previous revision, the regex pattern groups behind
graded_deliverable / prompt_injection / out_of_scope are no longer hardcoded
module constants: they come from ``src.services.guardrail_rules.RULE_GROUPS``,
and whether each named group is active is looked up per-request from
``GuardrailRuleRepository`` (DB-backed, admin-toggleable). This lets an admin
disable a specific rule group (e.g. FULL_CODE) without a deploy, while the
outer intent-classification behavior — Socratic guidance payloads instead of
a flat allow/block — stays the same. If the rule store cannot be read, the
guardrail fails CLOSED (blocks) rather than silently letting everything
through. Every decision also carries ``rule_code`` (the specific named rule
that fired, or None) alongside ``intent`` (the coarse-grained classification)
so downstream consumers such as the guardrail review queue can see exactly
which rule triggered.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from src.repositories.guardrail_rule_repository import GuardrailRuleRepository
from src.services.core.guardrail_rules import RULE_GROUPS
from src.services.rag.query_normalization import fold_accents, normalize_query

logger = logging.getLogger(__name__)

INTENT_KNOWLEDGE = "ask_knowledge"
INTENT_HINT = "ask_hint"
INTENT_BLOCKED = "graded_deliverable"
INTENT_OUT_OF_SCOPE = "out_of_scope"
INTENT_INJECTION = "prompt_injection"

GUARDRAIL_VERSION = "guardrail_rules_v4"

# Rule-group codes (from guardrail_rules.RULE_GROUPS) that map to each intent.
_GRADED_DELIVERABLE_CODES = ("HOMEWORK_VI", "FULL_CODE", "HOMEWORK_EN", "ROLEPLAY_JAILBREAK")
_INJECTION_CODES = ("PROMPT_INJECTION",)
_OUT_OF_SCOPE_CODES = ("OUT_OF_SCOPE",)


@dataclass(frozen=True)
class GuardrailDecision:
    blocked: bool
    reason: str | None = None
    answer: str | None = None
    alternatives: tuple[str, ...] = ()
    intent: str = INTENT_KNOWLEDGE
    guidance: dict = field(default_factory=dict)
    rule_code: str | None = None


# ── hint request ("xin gợi ý") — allowed, answered Socratically ──────────
# Not backed by an admin-toggleable rule group: ask_hint is an affirmatively
# answered intent (never blocked), so there's nothing here for an admin to
# disable — it only shapes which guidance payload comes back.
_HINT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        # Allow words between the verb and the question tail, so
        # "bắt đầu phân tích stakeholder từ đâu" matches as well as the bare
        # "bắt đầu từ đâu".
        r"\bb[aắ]t\s+đ[aầ]u\b.{0,60}?\bt[uừ]\s+đ[aâ]u\b",
        r"\bbat\s+dau\b.{0,60}?\btu\s+dau\b",
        r"\bb[aắ]t\s+đ[aầ]u\s+nh[uư]\s+th[eế]\s+n[aà]o\b",
        r"\bbat\s+dau\s+nhu\s+the\s+nao\b",
        r"\bg[oợ]i\s+[yý]\b",
        r"\bgoi\s+y\b",
        r"\bn[eê]n\s+l[aà]m\s+g[iì]\s+tr[uư][oớ]c\b",
        r"\bnen\s+lam\s+gi\s+truoc\b",
        r"\bh[uư][oớ]ng\s+d[aẫ]n\s+t[uừ]ng\s+b[uư][oớ]c\b",
        r"\bhuong\s+dan\s+tung\s+buoc\b",
        r"\bwhere\s+(do|should)\s+i\s+(start|begin)\b",
        r"\bgive\s+me\s+a\s+hint\b",
        r"\bstep[\s-]?by[\s-]?step\s+guidance\b",
    )
)


_BLOCK_ANSWER_VI = (
    "Mình không viết hộ phần bài được tính điểm — đó là phần bạn phải tự làm "
    "để bài nộp còn là của bạn. Nhưng mình không bỏ bạn ở đây: dưới đây là "
    "khái niệm, một câu hỏi để bạn tự bật ý, và một khung trống để bạn điền."
)

_BLOCK_GUIDANCE: dict = {
    "concept": (
        "Problem statement là đoạn nêu rõ: vấn đề đang tồn tại là gì, nó ảnh "
        "hưởng đến ai, tại sao đáng giải quyết, và phạm vi bạn chọn xử lý. Nó "
        "không phải phần mô tả giải pháp — giải pháp thuộc các phần sau."
    ),
    "socraticQuestions": [
        "Nếu phải nói vấn đề này trong đúng một câu cho người ngoài ngành, bạn sẽ nói gì?",
        "Ai là người chịu thiệt nhiều nhất khi vấn đề này không được giải quyết?",
        "Đâu là ranh giới bạn sẽ KHÔNG xử lý trong Part 1, và vì sao?",
    ],
    "template": (
        "Bối cảnh: ...\n"
        "Vấn đề cụ thể: ...\n"
        "Ai bị ảnh hưởng: ...\n"
        "Hệ quả nếu không giải quyết: ...\n"
        "Phạm vi Part 1 sẽ xử lý: ...\n"
        "Ngoài phạm vi: ..."
    ),
    "nextSteps": [
        "Điền khung trên bằng ngôn ngữ của bạn (chưa cần đẹp).",
        "Quay lại hỏi mình: 'Bảng này thiếu stakeholder nào?' — mình nhận xét được.",
    ],
}

_HINT_GUIDANCE: dict = {
    "concept": (
        "Phân tích stakeholder bắt đầu từ việc liệt kê ai *chạm* vào hệ thống "
        "hoặc *chịu ảnh hưởng* bởi nó, rồi mới xét mức độ quan tâm và quyền lực "
        "của từng nhóm."
    ),
    "steps": [
        "Bước 1 — Liệt kê thô: viết ra mọi người/nhóm liên quan, chưa lọc.",
        "Bước 2 — Phân loại: ai dùng trực tiếp, ai ra quyết định, ai bị ảnh hưởng gián tiếp.",
        "Bước 3 — Với mỗi nhóm, ghi 1 nhu cầu và 1 nỗi lo cụ thể.",
        "Bước 4 — Đánh dấu 2–3 nhóm quan trọng nhất và giải thích vì sao.",
    ],
    "socraticQuestions": [
        "Nhóm nào sẽ phản đối dự án này, và họ phản đối vì lý do gì?",
        "Có nhóm nào bạn đang bỏ sót vì họ không lên tiếng không?",
    ],
}

_OUT_OF_SCOPE_ANSWER = (
    "Mình không có dữ liệu này trong tài liệu môn học nên mình không đoán. "
    "Thông tin về điểm số, học phí hay lịch thi toàn trường nằm ngoài phạm vi "
    "của trợ lý môn — bạn nên tra trên hệ thống của trường hoặc hỏi phòng đào tạo."
)

_INJECTION_ANSWER = (
    "Mình bỏ qua yêu cầu thay đổi quy tắc và không hiển thị prompt hệ thống, "
    "khóa API hay dữ liệu của người học khác. Mình vẫn sẵn sàng trả lời câu "
    "hỏi về nội dung môn học."
)

_UNAVAILABLE_ANSWER = (
    "Hệ thống kiểm soát học thuật đang tạm thời gián đoạn. "
    "Vui lòng thử lại sau để bảo đảm an toàn học thuật."
)

_ALTERNATIVES = (
    "Hỏi trợ lý giải thích khái niệm liên quan trong tài liệu môn.",
    "Nhờ nhận xét bản nháp bạn tự viết thay vì xin bài làm sẵn.",
    "Hỏi 'em nên bắt đầu từ đâu?' để nhận hướng dẫn từng bước.",
)


class GuardrailService:
    """Rule-based guardrail. Runs before any LLM call, so a BLOCK costs
    nothing and cannot be talked around by the model.

    Regex rule groups (graded_deliverable / prompt_injection / out_of_scope)
    come from ``guardrail_rules.RULE_GROUPS`` and are only applied when their
    code is enabled in the DB-backed rule store, so an admin can toggle each
    category independently. If the rule store cannot be read, evaluation
    fails CLOSED.
    """

    def __init__(self, db: Session) -> None:
        self._rules = GuardrailRuleRepository(db)

    def evaluate(self, question: str) -> GuardrailDecision:
        try:
            enabled_codes = self._rules.enabled_codes()
        except Exception:
            logger.exception("guardrail_rule_storage_unavailable")
            return GuardrailDecision(
                blocked=True,
                reason="guardrail_unavailable",
                answer=_UNAVAILABLE_ANSWER,
                intent=INTENT_BLOCKED,
                rule_code=None,
            )

        candidates = self._candidates(question)
        if not candidates:
            return GuardrailDecision(blocked=False)

        # Order matters: injection first (most severe), then graded-deliverable,
        # then the two allowed-but-shaped intents.
        injection_match = self._match_codes(candidates, enabled_codes, _INJECTION_CODES)
        if injection_match is not None:
            return GuardrailDecision(
                blocked=True,
                reason="prompt_injection",
                answer=_INJECTION_ANSWER,
                alternatives=_ALTERNATIVES,
                intent=INTENT_INJECTION,
                guidance={},
                rule_code=injection_match,
            )

        deliverable_match = self._match_codes(
            candidates, enabled_codes, _GRADED_DELIVERABLE_CODES
        )
        if deliverable_match is not None:
            return GuardrailDecision(
                blocked=True,
                reason="graded_deliverable",
                answer=_BLOCK_ANSWER_VI,
                alternatives=_ALTERNATIVES,
                intent=INTENT_BLOCKED,
                guidance=dict(_BLOCK_GUIDANCE),
                rule_code=deliverable_match,
            )

        out_of_scope_match = self._match_codes(
            candidates, enabled_codes, _OUT_OF_SCOPE_CODES
        )
        if out_of_scope_match is not None:
            return GuardrailDecision(
                blocked=False,
                reason="out_of_scope",
                answer=_OUT_OF_SCOPE_ANSWER,
                alternatives=(),
                intent=INTENT_OUT_OF_SCOPE,
                guidance={},
                rule_code=out_of_scope_match,
            )

        if self._matches(candidates, _HINT_PATTERNS):
            return GuardrailDecision(
                blocked=False,
                reason="ask_hint",
                answer=None,
                alternatives=(),
                intent=INTENT_HINT,
                guidance=dict(_HINT_GUIDANCE),
                rule_code=None,
            )

        return GuardrailDecision(blocked=False, intent=INTENT_KNOWLEDGE, rule_code=None)

    @staticmethod
    def _candidates(question: str) -> set[str]:
        normalized = normalize_query(question)
        candidates = {
            (question or "").strip(),
            normalized.cleaned,
            normalized.folded,
            fold_accents((question or "").strip()).lower(),
        }
        candidates.discard("")
        return candidates

    @staticmethod
    def _matches(
        candidates: set[str], patterns: tuple[re.Pattern[str], ...]
    ) -> bool:
        return any(
            pattern.search(text) for text in candidates for pattern in patterns
        )

    @staticmethod
    def _match_codes(
        candidates: set[str],
        enabled_codes: frozenset[str],
        codes: tuple[str, ...],
    ) -> str | None:
        """Return the code of the first enabled rule group (among ``codes``)
        whose patterns match, or None if none match."""
        for group in RULE_GROUPS:
            if group.code not in codes:
                continue
            if group.code not in enabled_codes:
                continue
            if GuardrailService._matches(candidates, group.patterns):
                return group.code
        return None
