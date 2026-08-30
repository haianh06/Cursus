"""Named guardrail rule groups.

Regex patterns live in code; each group's enabled/disabled state lives in the
database (see ``src.repositories.guardrail_rule_repository``) so an admin can
toggle individual categories without a code change.

Six categories are called out by the product blueprint (§4.2 Guardrail
matrix): ask_knowledge, ask_hint, feedback-on-own-work, graded_deliverable,
out_of_scope, prompt_injection. ask_knowledge/ask_hint/feedback-on-own-work
are affirmatively-answered intents (nothing to block), so only the remaining
three show up here as blocking rule groups: graded_deliverable is covered by
HOMEWORK_VI / FULL_CODE / HOMEWORK_EN / ROLEPLAY_JAILBREAK, and
PROMPT_INJECTION / OUT_OF_SCOPE were added to cover the last two rows.

Patterns below are written WITHOUT Vietnamese diacritics wherever possible.
``GuardrailService._candidates()`` (guardrail_service.py) already matches
every pattern here against an accent-stripped ("folded") copy of the
question alongside the original, so an unaccented pattern alone already
catches both "đóng vai" and "dong vai" -- no need for the raw/folded pattern
pairs older groups below still carry.
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
            r"\bb[oỏ]\s+(qua\s+)?(m[oọ]i\s+)?(lu[aậ]t|quy\s*t[aắ]c|rule|guardrail)",
            r"\bbo\s+qua\s+(moi\s+)?(luat|quy\s*tac|rule|guardrail)",
            r"\bignore\s+(all\s+)?(previous|prior|above)\s+(instruction|rule|prompt)",
            r"\bsystem\s+prompt\b",
            r"\bin\s+ra\s+prompt\b",
            r"\bl[oộ]\s+prompt\b",
            r"\breveal\s+your\s+(prompt|instructions)\b",
            r"\bd[uữ]\s*li[eệ]u\s+(l[oớ]p|sinh\s*vi[eê]n)\s+kh[aá]c\b",
            r"\bdu\s*lieu\s+(lop|sinh\s*vien)\s+khac\b",
            r"\bother\s+students?'?\s+data\b",
            r"\bapi[_\s-]?key\b",
            r"\bdeveloper\s+mode\b",
            r"\bjailbreak\b",
            # Indirect injection: a course document/chunk itself contains a
            # fake directive ("SYSTEM: ...", "AI: hãy đóng vai admin") and the
            # student is asking whether the assistant follows it -- the
            # planted instruction text still needs to be caught even though
            # it arrives quoted inside a normal question, not as a direct
            # command from the student.
            r"\b(system|ai)\s*:\s*.{0,80}?\b(dong\s+vai|bo\s+guardrail|ignore|bypass)\b",
        ),
    ),
    GuardrailRuleGroup(
        code="ROLEPLAY_JAILBREAK",
        name_vi="Chặn đóng vai để lách guardrail",
        description_vi=(
            "Chặn yêu cầu AI đóng vai giảng viên/quản trị/\"không luật lệ\" để "
            "moi đáp án hoặc bài giải hoàn chỉnh thay vì hỏi thẳng."
        ),
        patterns=_compile(
            # Persona-switch phrasing ("đóng vai", "pretend/act as", "giả sử
            # bạn là") is common in legitimate case-study prompts too, so
            # these only fire when a deliverable-seeking word also shows up
            # nearby (same proximity-window approach as HOMEWORK_EN below).
            r"\bdong\s+vai\b.{0,100}?\b(dap\s*an|giai\s*(het|toan\s*bo)?|code|bai\s*(lam|giai)|full|complete|solution|answer)\b",
            r"\bpretend\b.{0,20}?\byou\s+are\b.{0,100}?\b(answer|solution|code|full|complete)\b",
            r"\bact\s+as\b.{0,60}?\b(instructor|teacher|admin|giao\s*vien|giang\s*vien|tro\s*giang)\b.{0,100}?\b(dap\s*an|giai|code|answer|solution)\b",
            r"\bgia\s*su\s+ban\s+la\b.{0,100}?\b(dap\s*an|giai|code|answer|solution)\b",
            r"\btuong\s+tuong\b.{0,100}?\b(dap\s*an|giai\s*(het)?|doc\s*luon|chep)\b",
            # "AI with no rules at all, solve X for me" -- self-contained
            # enough to fire without a nearby-deliverable check.
            r"\bkhong\s+co\s+luat\s*(gi)?\s*(ca)?\b",
            r"\bno\s+rules?\s+(at\s+all\s+)?(ai|assistant)\b",
        ),
    ),
    GuardrailRuleGroup(
        code="OUT_OF_SCOPE",
        name_vi="Chặn câu hỏi ngoài phạm vi tài liệu môn học",
        description_vi=(
            "Chặn câu hỏi về điểm số, học phí, lịch thi toàn trường, thời tiết, "
            "danh sách/liên hệ/mật khẩu của người khác, hoặc dữ liệu khác "
            "không nằm trong tài liệu môn học."
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
            # Other students' identity / roster / contact / credentials --
            # none of this lives in course-document RAG data, so it's a
            # boundary case (out_of_scope), not a graded-deliverable one.
            r"\bdanh\s*sach\b.{0,30}?\bsinh\s*vien\b",
            r"\blist\s+of\s+students?\b",
            r"\bthong\s*tin\s+lien\s*he\b.{0,40}?\b(giang\s*vien|gv|instructor)\b",
            r"\bcontact\s+info(rmation)?\s+of\b.{0,40}?\binstructor\b",
            r"\bmat\s*khau\b",
            r"\bpassword\b",
            r"\bbai\s*(lam|nop)\s+cua\s+(sinh\s*vien|ban)\s+khac\b",
            r"\b(email|so\s*dien\s*thoai|phone\s*number)\s+(ca\s*nhan\s+)?(cua\s+)?(giang\s*vien|gv|instructor)\b",
        ),
    ),
)
