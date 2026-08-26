"""Unit tests for the Mock LMS source-precedence resolver (mục 6.6/14.3).

Pure unit tests, no DB -- `rank`/`label_for`/`tier_for_content_source`/`winner` are
plain functions, and `_citation_from_chunk` only needs a `RetrievedChunk` built
in-memory.
"""
from __future__ import annotations

from src.repositories.chunk_repository import ChunkRecord
from src.services.ai.chat_answer_service import _citation_from_chunk
from src.services.core import source_precedence as sp
from src.services.rag.retrieval_service import RetrievedChunk


def test_precedence_order_matches_muc_6_6():
    assert sp.PRECEDENCE_ORDER == (
        "mock_lms",
        "instructor_confirmed",
        "syllabus_active",
        "curriculum_static",
        "supplementary",
    )


def test_mock_lms_outranks_everything_else():
    for other in sp.PRECEDENCE_ORDER[1:]:
        assert sp.rank(sp.MOCK_LMS) < sp.rank(other)
        assert sp.winner(sp.MOCK_LMS, other) == sp.MOCK_LMS
        assert sp.winner(other, sp.MOCK_LMS) == sp.MOCK_LMS


def test_unknown_tier_sorts_last_and_labels_as_syllabus():
    assert sp.rank("something_made_up") > sp.rank(sp.SUPPLEMENTARY)
    assert sp.label_for("something_made_up") == sp.label_for(sp.SYLLABUS_ACTIVE)


def test_content_source_mock_is_not_confused_with_mock_lms():
    """`content_source="mock"` (mục 16.1's demo-fabrication flag) must NOT map to
    the MOCK_LMS precedence tier -- they are unrelated concepts that happen to
    share the word "mock". Regression guard for exactly that mix-up."""
    assert sp.tier_for_content_source("mock") != sp.MOCK_LMS
    assert sp.tier_for_content_source("mock") == sp.SYLLABUS_ACTIVE
    assert sp.tier_for_content_source("mock_lms") == sp.MOCK_LMS


def test_curriculum_and_admin_curriculum_map_to_syllabus_active():
    assert sp.tier_for_content_source("curriculum") == sp.SYLLABUS_ACTIVE
    assert sp.tier_for_content_source("admin_curriculum") == sp.SYLLABUS_ACTIVE


def test_missing_content_source_defaults_to_syllabus_active():
    assert sp.tier_for_content_source(None) == sp.SYLLABUS_ACTIVE
    assert sp.tier_for_content_source("") == sp.SYLLABUS_ACTIVE


def _make_retrieved(content_source: str) -> RetrievedChunk:
    chunk = ChunkRecord(
        chunk_id="chunk_test_1",
        text="irrelevant text",
        course_code="TEST101",
        doc_title="Syllabus TEST101",
        doc_type="syllabus",
        source_label="Syllabus TEST101 — Overview",
        section="Overview",
        chunk_index=0,
        content_source=content_source,
    )
    return RetrievedChunk(chunk=chunk, score=0.9)


def test_citation_document_reflects_mock_lms_tier():
    """This is the actual injection point (chat_answer_service.py's shared citation
    builder) -- confirms `document` is no longer a dead field."""
    citation = _citation_from_chunk(_make_retrieved("mock_lms"))
    assert citation.document == sp.label_for(sp.MOCK_LMS)
    assert citation.document == "Mock LMS (nguồn chính thức, đồng bộ gần nhất)"


def test_citation_document_reflects_syllabus_tier_for_curriculum_content():
    citation = _citation_from_chunk(_make_retrieved("curriculum"))
    assert citation.document == sp.label_for(sp.SYLLABUS_ACTIVE)


def test_citation_ismock_flag_unaffected_by_precedence_wiring():
    """Regression guard: the pre-existing `isMock` flag (mục 16 fabricated-content
    disclaimer) must keep working exactly as before -- it's a different concept
    from source precedence and must not be conflated by this change."""
    mock_citation = _citation_from_chunk(_make_retrieved("mock"))
    assert mock_citation.isMock is True
    assert mock_citation.document != sp.label_for(sp.MOCK_LMS)

    real_citation = _citation_from_chunk(_make_retrieved("curriculum"))
    assert real_citation.isMock is False
