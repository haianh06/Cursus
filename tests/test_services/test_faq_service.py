"""Unit tests for the FAQ matcher."""

from src.services.ai.faq_service import FaqService


def test_faq_matches_ssa101_commitment_map():
    match = FaqService().match(
        subject_code="SSA101",
        question="Weekly Commitment Map là gì?",
    )
    assert match is not None
    assert match.entry.id == "ssa101_commitment_map"
    answer, citations, mode = FaqService().to_response_parts(match)
    assert mode == "faq"
    assert "Commitment Map" in answer or "cam kết" in answer.lower()
    assert citations[0].chunkId.startswith("faq:")


def test_faq_matches_prf192_lab02():
    match = FaqService().match(
        subject_code="PRF192",
        question="Lab 02 loops và arrays yêu cầu gì?",
    )
    assert match is not None
    assert match.entry.id == "prf192_lab02"


def test_faq_is_scoped_to_subject():
    match = FaqService().match(
        subject_code="CSI106",
        question="Weekly Commitment Map là gì?",
    )
    assert match is None
