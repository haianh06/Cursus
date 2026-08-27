"""Normalize student questions: strip formatting noise and light typo repair."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

# Common student typos / slang → canonical forms (applied on folded text).
_TYPO_MAP: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bxin\s*chao+\b"), "xin chao"),
    (re.compile(r"\bchaoo+\b"), "chao"),
    (re.compile(r"\bhell+o+\b"), "hello"),
    (re.compile(r"\bhii+\b"), "hi"),
    (re.compile(r"\bheyy+\b"), "hey"),
    (re.compile(r"\bcam\s*o+n\b"), "cam on"),
    (re.compile(r"\btom\s*tat\b"), "tom tat"),
    (re.compile(r"\btomtat\b"), "tom tat"),
    (re.compile(r"\bsummariz+e?\b"), "summarize"),
    (re.compile(r"\bsylab+us\b"), "syllabus"),
    (re.compile(r"\bsylabus\b"), "syllabus"),
    (re.compile(r"\bsilab+us\b"), "syllabus"),
    (re.compile(r"\blec+ture?\b"), "lecture"),
    (re.compile(r"\bbai\s*giang\b"), "bai giang"),
    (re.compile(r"\bghi\s*chu\b"), "ghi chu"),
)

# Restore useful surface forms after fold+typo fix (for retrieval / display).
_SURFACE_MAP: dict[str, str] = {
    "xin chao": "xin chào",
    "chao": "chào",
    "cam on": "cảm ơn",
    "tom tat": "tóm tắt",
    "bai giang": "bài giảng",
    "ghi chu": "ghi chú",
    "syllabus": "syllabus",
    "summarize": "summarize",
    "lecture": "lecture",
    "hello": "hello",
    "hi": "hi",
    "hey": "hey",
}


# Vietnamese → English retrieval aliases.
#
# The SSA101 syllabus is written in English while students ask in Vietnamese,
# so a purely lexical retriever scores near zero on "Điều kiện qua môn SSA101
# là gì?" against "Conditions to pass: Final exam >= 4". The Data Contract
# (§2.2) calls this out and prescribes bilingual support / alias normalization;
# this map is that layer. Keys are accent-folded so they match either spelling.
#
# Used only to EXPAND a query before retrieval — it never rewrites what the
# student sees, and it never touches guardrail matching.
_BILINGUAL_ALIASES: tuple[tuple[str, str], ...] = (
    ("dieu kien qua mon", "conditions to pass final exam grade average"),
    ("dieu kien pass", "conditions to pass"),
    ("qua mon", "pass conditions"),
    ("diem qua mon", "conditions to pass mark"),
    ("diem trung binh", "grade average MinAvgMarkToPass"),
    ("diem tong ket", "grade average"),
    ("thi cuoi ky", "final exam"),
    ("bai thi cuoi ky", "final exam"),
    ("chuyen can", "attendance contact slots"),
    ("diem danh", "attendance contact slots"),
    ("tham du", "attend contact slots"),
    ("chuan dau ra", "learning outcome CLO"),
    ("muc tieu mon hoc", "learning outcome CLO"),
    ("buoi hoc", "session"),
    ("buoi cuoi", "session 60 revise final examination"),
    ("buoi cuoi cung", "session 60 revise course content final examination"),
    ("do tin cay", "credibility"),
    ("nguon thong tin", "information sources"),
    ("trach nhiem", "responsible ethical"),
    ("dao duc", "ethical ethics integrity"),
    ("su dung ai", "use of AI"),
    ("tu duy phan bien", "critical thinking"),
    ("tu duy sang tao", "creative thinking"),
    ("quan ly thoi gian", "time management"),
    ("quan ly stress", "manage academic stress well-being"),
    ("giao tiep", "communication"),
    ("kiem tra", "test taking progress test"),
    ("bai kiem tra", "progress test quiz"),
    ("do an", "project"),
    ("du an", "project"),
    ("nhom", "group"),
    ("thuyet trinh", "presentation"),
    ("bao cao", "report"),
    ("on tap", "review revise"),
    ("trong so", "weight percentage marks"),
    ("phan tram", "percentage marks"),
    ("hoc phan", "course"),
    ("tai lieu", "materials"),
)


def expand_bilingual(question: str) -> str:
    """Append English equivalents for Vietnamese phrases found in a query.

    Returns the original text plus any matched English terms, so an English
    corpus becomes reachable from a Vietnamese question without changing how
    the question is displayed back to the student.
    """
    folded = fold_accents(question or "").lower()
    folded = re.sub(r"\s+", " ", folded)
    if not folded:
        return question or ""
    extras: list[str] = []
    for phrase, english in _BILINGUAL_ALIASES:
        if phrase in folded:
            extras.append(english)
    if not extras:
        return question or ""
    return f"{question} {' '.join(extras)}"


@dataclass(frozen=True)
class NormalizedQuery:
    original: str
    cleaned: str
    folded: str


def fold_accents(text: str) -> str:
    """Remove Vietnamese/Latin diacritics for fuzzy matching."""
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


# Common Vietnamese function words in their bare-ASCII (no dấu) form. Used to
# tell "Vietnamese that lost every diacritic" apart from "text that's
# legitimately English/code and therefore accent-free anyway".
_VN_UNACCENTED_MARKERS = (
    " khong ", " duoc ", " cua ", " nhung ", " voi ", " minh ", " ban ",
    " hoc ", " nay ", " mot ", " co the ", " la ", " va ",
)


def looks_like_accent_stripped_vietnamese(text: str) -> bool:
    """True when `text` reads like Vietnamese that lost every diacritic —
    e.g. a weaker fallback LLM degrading Vietnamese under structured-JSON
    output. Requires several common Vietnamese function words in bare ASCII
    form, not just the absence of accents, to avoid flagging genuinely
    English/code text."""
    body = f" {(text or '').lower()} "
    if not body.strip():
        return False
    if fold_accents(body) != body:
        return False  # has a real accented character somewhere -> fine
    hits = sum(1 for marker in _VN_UNACCENTED_MARKERS if marker in body)
    return hits >= 3


def strip_formatting(text: str) -> str:
    """Remove markdown/code fencing and decorative wrappers students often paste."""
    value = text or ""
    value = value.replace("\u200b", "").replace("\ufeff", "")
    # Fenced code blocks ```...```
    value = re.sub(r"```[\s\S]*?```", " ", value)
    # Inline code / backticks
    value = value.replace("`", " ")
    # Bold/italic markers
    value = re.sub(r"[*_~]{1,3}", " ", value)
    # Surrounding quotes / brackets that wrap the whole short message
    value = value.strip()
    value = re.sub(r'^[\s\'"“”‘’\[\]\(\)\{\}<>]+', "", value)
    value = re.sub(r'[\s\'"“”‘’\[\]\(\)\{\}<>]+$', "", value)
    # Collapse whitespace
    value = re.sub(r"\s+", " ", value).strip()
    return value


def repair_typos(folded_text: str) -> str:
    value = folded_text.lower()
    for pattern, replacement in _TYPO_MAP:
        value = pattern.sub(replacement, value)
    return re.sub(r"\s+", " ", value).strip()


def restore_surface(folded_repaired: str) -> str:
    """Map known folded tokens back to accented / canonical retrieval terms."""
    words = folded_repaired.split()
    # Prefer phrase replacements first
    lowered = folded_repaired
    for key, surface in sorted(_SURFACE_MAP.items(), key=lambda item: -len(item[0])):
        lowered = re.sub(rf"\b{re.escape(key)}\b", surface, lowered, flags=re.IGNORECASE)
    if lowered != folded_repaired:
        return lowered
    return " ".join(_SURFACE_MAP.get(word, word) for word in words)


def normalize_query(question: str) -> NormalizedQuery:
    original = question or ""
    cleaned = strip_formatting(original)
    folded = repair_typos(fold_accents(cleaned).lower())
    # Keep a retrieval-friendly cleaned string with accents restored where known.
    restored = restore_surface(folded)
    # If stripping wiped everything, fall back to original stripped spaces.
    if not cleaned and original.strip():
        cleaned = re.sub(r"\s+", " ", original).strip()
    if not restored:
        restored = cleaned or original.strip()
    return NormalizedQuery(original=original, cleaned=restored, folded=folded)
