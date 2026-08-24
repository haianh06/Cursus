"""Source precedence for Mock LMS sync conflicts (PROJECT_CONTEXT.md mục 6.6).

When two sources disagree about the same fact (e.g. an assignment due date), this
module decides which one wins and what label a citation should show for it. This is
a different axis from `provenance.py`'s `source_type` (official_document/simulated/
user_entered/...), which describes what KIND of data a record is. A fact sourced from
Mock LMS is still `official_document` in provenance terms -- this module only says
WHICH official source takes priority when two of them conflict.

Order (mục 6.6, đã chốt): Mock LMS ("sổ cái", cập nhật gần nhất) > giảng viên xác nhận
thủ công > syllabus phiên bản đang hiệu lực > curriculum reference tĩnh > tài liệu bổ
trợ khác.
"""
from __future__ import annotations

from typing import Final

MOCK_LMS: Final = "mock_lms"
INSTRUCTOR_CONFIRMED: Final = "instructor_confirmed"
SYLLABUS_ACTIVE: Final = "syllabus_active"
CURRICULUM_STATIC: Final = "curriculum_static"
SUPPLEMENTARY: Final = "supplementary"

# Index = rank, lower is higher priority.
PRECEDENCE_ORDER: Final = (
    MOCK_LMS,
    INSTRUCTOR_CONFIRMED,
    SYLLABUS_ACTIVE,
    CURRICULUM_STATIC,
    SUPPLEMENTARY,
)

_LABEL_VI: Final = {
    MOCK_LMS: "Mock LMS (nguồn chính thức, đồng bộ gần nhất)",
    INSTRUCTOR_CONFIRMED: "Giảng viên đã xác nhận",
    SYLLABUS_ACTIVE: "Syllabus (phiên bản hiệu lực)",
    CURRICULUM_STATIC: "Curriculum tham khảo",
    SUPPLEMENTARY: "Tài liệu bổ trợ",
}

# `content_source` values already flowing through Document.metadata_info["source"]
# (mục 16.1) that this module knows how to rank. Chunks/records with an unrecognized
# or missing content_source fall back to SYLLABUS_ACTIVE (today's default behavior --
# see qa_answer_service.py before this change, which treated everything as syllabus).
_CONTENT_SOURCE_TO_TIER: Final = {
    "mock_lms": MOCK_LMS,
    "instructor_confirmed": INSTRUCTOR_CONFIRMED,
    "curriculum": SYLLABUS_ACTIVE,
    "admin_curriculum": SYLLABUS_ACTIVE,
    "curriculum_static": CURRICULUM_STATIC,
    "student_upload": SUPPLEMENTARY,
}


def rank(tier: str) -> int:
    """Lower is higher priority. Unknown tiers sort last (safest default)."""
    try:
        return PRECEDENCE_ORDER.index(tier)
    except ValueError:
        return len(PRECEDENCE_ORDER)


def label_for(tier: str) -> str:
    return _LABEL_VI.get(tier, _LABEL_VI[SYLLABUS_ACTIVE])


def tier_for_content_source(content_source: str | None) -> str:
    """Map a chunk/document's existing `content_source` metadata value to a
    precedence tier. `content_source="mock"` (the demo-fabrication flag from mục
    16.1) is deliberately NOT mapped to MOCK_LMS here -- that flag means "invented
    for demo", not "sourced from the Mock LMS integration"; those are unrelated
    concepts that happen to share the word "mock"."""
    if not content_source:
        return SYLLABUS_ACTIVE
    return _CONTENT_SOURCE_TO_TIER.get(content_source, SYLLABUS_ACTIVE)


def winner(tier_a: str, tier_b: str) -> str:
    """Given two tiers describing the same fact from two sources, return the
    winning tier (lower rank = higher precedence)."""
    return tier_a if rank(tier_a) <= rank(tier_b) else tier_b
