"""Named guardrail rule groups.

Regex patterns live in code; each group's enabled/disabled state lives in the
database (see ``src.repositories.guardrail_rule_repository``) so an admin can
toggle individual categories without a code change.

Six categories are called out by the product blueprint (§4.2 Guardrail
matrix): ask_knowledge, ask_hint, feedback-on-own-work, graded_deliverable,
out_of_scope, prompt_injection. ask_knowledge/ask_hint/feedback-on-own-work
are affirmatively-answered intents (nothing to block), so only the remaining
three show up here as blocking rule groups: graded_deliverable is covered by
HOMEWORK_VI / FULL_CODE / HOMEWORK_EN, and PROMPT_INJECTION / OUT_OF_SCOPE
were added to cover the last two rows.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailRuleGroup:
    code: str
    name_vi: str
    description_vi: str
    patterns: tuple[re.Pattern[str], ...]


def _compile(*patterns: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)


RULE_GROUPS: tuple[GuardrailRuleGroup, ...] = (
    GuardrailRuleGroup(
        code="HOMEWORK_VI",
        name_vi="Chặn nhờ làm bài hộ (tiếng Việt)",
        description_vi="Chặn yêu cầu trợ lý làm thay bài được chấm điểm bằng tiếng Việt.",
        patterns=_compile(
            r"\bvi[eế]t\s+h[oộ]?\b",
            r"\bviet\s+ho\b",
            r"\bl[àa]m\s+h[oộ]\b",
            r"\blam\s+ho\b",
            r"\bl[àa]m\s+b[àa]i\s+h[oộ]\b",
            r"\blam\s+bai\s+ho\b",
            r"\bbi[eế]t\s+h[oộ]\b",
            r"\bvi[eế]t\s+to[àa]n\s+b[oộ]\b",
            r"\bviet\s+toan\s+bo\b",
            r"\bn[oộ]p\s+h[oộ]\b",
            r"\bnop\s+ho\b",
            r"\bgiai\s+quyet\s+het\s+bai\b",
        ),
    ),
    GuardrailRuleGroup(
        code="FULL_CODE",
        name_vi="Chặn xin code / lời giải hoàn chỉnh",
        description_vi="Chặn yêu cầu nhận trọn bộ code hoặc đáp án thay vì gợi ý.",
        patterns=_compile(
            r"\bcode\s+ho[àa]n\s+ch[ỉi]nh\b",
            r"\bcode\s+hoan\s+chinh\b",
            r"\bwrite\s+the\s+whole\b",
            r"\bcomplete\s+code\b",
            r"\bgive\s+me\s+(the\s+)?(full|complete)\s+(solution|code|answer)\b",
        ),
    ),
    GuardrailRuleGroup(
        code="HOMEWORK_EN",
        name_vi="Chặn nhờ làm bài hộ (tiếng Anh)",
        description_vi="Chặn yêu cầu làm thay bài tập viết bằng tiếng Anh.",
        patterns=_compile(
            r"\bdo\s+my\s+assignment\b",
            r"\bdo\s+my\s+homework\b",
            r"\bwrite\s+(it|this|the\s+code|the\s+whole)\s+for\s+me\b",
            r"\bsolve\s+(the\s+)?(assignment|homework|lab)\s+for\s+me\b",
            r"\bfinish\s+(my\s+)?(assignment|homework|lab)\b",
            r"\b(submit|turn\s+in|hand\s+in)\s+(it\s+)?for\s+me\b",
            # Broader phrasing that doesn't literally say "for me" next to the
            # verb — real students paraphrase (found via live guardrail audit
            # 15/08/2026, see docs/PROJECT_CONTEXT.md mục 14.2).
            r"\b(write|do|complete|finish|solve)\b.{0,80}?\bso\s+(that\s+)?i\s+can\s+(submit|turn\s+in|hand\s+in)\b",
            r"\bso\s+(that\s+)?i\s+can\s+(submit|turn\s+in|hand\s+in)\s+it\b",
            r"\bcan\s+you\s+(write|do|complete|finish|solve)\b.{0,60}?\bfor\s+me\b",
        ),
    ),
    GuardrailRuleGroup(
        code="PROMPT_INJECTION",
        name_vi="Chặn prompt injection / rò rỉ dữ liệu",
        description_vi=(
            "Chặn yêu cầu bỏ qua luật hệ thống, lộ system prompt/API key, hoặc "
            "xin dữ liệu của người học khác."
        ),
        patterns=_compile(
            r"\bb[oỏ]\s+(qua\s+)?(m[oọ]i\s+)?(lu[aậ]t|quy\s*t[aắ]c|rule)",
            r"\bbo\s+qua\s+(moi\s+)?(luat|quy\s*tac|rule)",
            r"\bignore\s+(all\s+)?(previous|prior|above)\s+(instruction|rule|prompt)",
            r"\bsystem\s+prompt\b",
            r"\bin\s+ra\s+prompt\b",
            r"\bl[oộ]\s+prompt\b",
            r"\breveal\s+your\s+(prompt|instructions)\b",
            r"\bd[uữ]\s*li[eệ]u\s+(l[oớ]p|sinh\s*vi[eê]n)\s+kh[aá]c\b",
            r"\bdu\s*lieu\s+(lop|sinh\s*vien)\s+khac\b",
            r"\bother\s+students?'?\s+data\b",
            r"\bapi[_\s-]?key\b",
        ),
    ),
    GuardrailRuleGroup(
        code="OUT_OF_SCOPE",
        name_vi="Chặn câu hỏi ngoài phạm vi tài liệu môn học",
        description_vi=(
            "Chặn câu hỏi về điểm số, học phí, lịch thi toàn trường, thời tiết, "
            "hoặc dữ liệu khác không nằm trong tài liệu môn học."
        ),
        patterns=_compile(
            r"\b[đd]i[eể]m\s+(m[oô]n\s+kh[aá]c|c[uủ]a\s+b[aạ]n)\b",
            r"\bdiem\s+(mon\s+khac|cua\s+ban)\b",
            r"\b[đd]i[eể]m\s+(thi|t[oổ]ng\s*k[eế]t)\s+c[uủ]a\s+em\b",
            r"\bgpa\s+c[uủ]a\s+em\b",
            r"\bmy\s+(grade|gpa|score)\s+(in|for)\s+(another|other)\b",
            r"\bl[iị]ch\s+thi\s+to[aà]n\s+tr[uư][oờ]ng\b",
            r"\bh[oọ]c\s+ph[ií]\b",
            r"\btuition\s+fee\b",
            r"\bth[oờ]i\s+ti[eế]t\b",
            r"\bweather\b",
        ),
    ),
)
