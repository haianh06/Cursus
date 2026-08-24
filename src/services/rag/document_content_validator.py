"""LLM08 (OWASP LLM Top 10 — Vector/Embedding Weaknesses, mục 14.2) content
validation for the document-ingest pipeline.

Runs AFTER text extraction, BEFORE chunking/embedding, in both ingest paths
(`document_ingest_service.py::upload_for_student`,
`admin_document_ingest_service.py::ingest_new`/`replace`). Reuses the same
`ignore previous instructions` / `system prompt` / rule-bypass patterns
already enforced live in chat (`guardrail_rules.PROMPT_INJECTION`) as the
single source of truth for that shared vocabulary, and adds a small set of
document-specific patterns (fake `SYSTEM:` line, role-hijack phrasing like
"you are now"/"act as"/"pretend to be"/"developer mode") that don't show up
in a student's own live question but are exactly what a hostile document
would try — matching the same list already named in `qa_v1.md` rule 8's
prompt-level defense, so the ingest-time check and the answer-time defense
describe the same threat consistently.

Deliberately rule-based, not ML/LLM-based — cheap, deterministic, and fast
enough to run on every upload without adding latency or cost. Deliberately
does NOT reject a flagged document: rejecting outright risks false
positives on legitimate academic content (a syllabus section literally
titled "System Design" or a security-course document that discusses prompt
injection as a topic would both trip a naive filter) — so this only flags
for a human to look at, mirroring the draft/review pattern already used for
Mock LMS sync (`mock_lms_sync_service.py`) rather than inventing a new one.
"""
from __future__ import annotations

import re

from src.services.core.guardrail_rules import RULE_GROUPS

# Reuse the exact patterns already enforced live for student chat questions
# -- "ignore previous instructions", "system prompt", "bỏ qua luật", "reveal
# your prompt", etc. Single source of truth: if that list is tuned later,
# this inherits the change automatically.
#
# One pattern is deliberately EXCLUDED here: the bare `api[_\s-]?key` match.
# In a live chat question, a student typing "api key" is genuinely odd and
# worth flagging. In a DOCUMENT, it's common, legitimate technical
# vocabulary -- confirmed by a real false positive during testing (an
# SBA301 syllabus session pointing students at a Spring Boot tutorial URL
# containing "api-key-secret"). Keeping it live-chat-only avoids flooding
# Admin with noise on any course that touches web APIs/auth.
_DOCUMENT_UNSUITABLE_PATTERN_STRINGS = frozenset({r"\bapi[_\s-]?key\b"})
_SHARED_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    pattern
    for group in RULE_GROUPS
    if group.code == "PROMPT_INJECTION"
    for pattern in group.patterns
    if pattern.pattern not in _DOCUMENT_UNSUITABLE_PATTERN_STRINGS
)

# Document-specific additions -- role-hijack phrasing and a fake SYSTEM:
# line are how a hostile document actually tries to redirect the model
# (a live student question phrased as "you are now a different AI" reads as
# nonsensical chat, so the live guardrail never needed these; an *ingested
# document* embedding them is exactly the LLM08 threat this module exists
# for). Named to match qa_v1.md rule 8's own example list verbatim.
_DOCUMENT_SPECIFIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("fake_system_line", re.compile(r"^\s*system\s*:", re.IGNORECASE | re.MULTILINE)),
    (
        "role_hijack",
        re.compile(
            r"\byou\s+are\s+now\b|\bact\s+as\s+(a|an)\b|\bpretend\s+(you\s+are|to\s+be)\b"
            r"|\bdeveloper\s+mode\b|\bnew\s+instructions?\s*:",
            re.IGNORECASE,
        ),
    ),
)


def scan_for_suspicious_patterns(text: str) -> list[dict]:
    """Returns a list of matches, each `{"pattern": label, "excerpt": ...}`.
    Empty list means clean. Never raises, never modifies `text`."""
    matches: list[dict] = []

    for index, pattern in enumerate(_SHARED_INJECTION_PATTERNS):
        match = pattern.search(text)
        if match:
            matches.append(
                {
                    "pattern": f"shared_guardrail_pattern_{index}",
                    "excerpt": _excerpt(text, match),
                }
            )

    for label, pattern in _DOCUMENT_SPECIFIC_PATTERNS:
        match = pattern.search(text)
        if match:
            matches.append({"pattern": label, "excerpt": _excerpt(text, match)})

    return matches


def _excerpt(text: str, match: re.Match[str], *, context_chars: int = 40) -> str:
    start = max(0, match.start() - context_chars)
    end = min(len(text), match.end() + context_chars)
    return text[start:end].strip()
