"""Regression test for a lexical-scoring false positive: a plain emotional/
conversational message ("Nay tôi buồn" -- "I'm sad today") was surfacing a
course-syllabus citation, because "nay" ("hiện nay" = "nowadays") is common
enough in ordinary Vietnamese prose to exact-match almost any chunk while
not being filtered as a stopword. Fixed by adding it (and similar function
words) to retrieval_service._STOPWORDS -- see that module for the full list.
"""
from __future__ import annotations

from src.repositories.chunk_repository import ChunkRecord
from src.services.rag.retrieval_service import score_chunk, tokenize


def _chunk(text: str) -> ChunkRecord:
    return ChunkRecord(
        chunk_id="c1", course_code="PRF192", doc_title="PRF192 Syllabus",
        doc_type="SYLLABUS", source_label="PRF192", section="Overview",
        chunk_index=0, content_source="real", text=text,
    )


def test_emotional_message_scores_zero_against_unrelated_syllabus_chunk():
    tokens = tokenize("Nay tôi buồn")
    chunk = _chunk(
        "Môn học này giới thiệu các khái niệm lập trình cơ bản. "
        "Hiện nay ngôn ngữ C được sử dụng rộng rãi."
    )
    assert score_chunk(tokens, chunk) == 0.0


def test_real_course_question_still_scores_above_zero():
    tokens = tokenize("PRF192 dạy những khái niệm lập trình nào?")
    chunk = _chunk(
        "Môn học này giới thiệu các khái niệm lập trình cơ bản. "
        "Hiện nay ngôn ngữ C được sử dụng rộng rãi."
    )
    assert score_chunk(tokens, chunk) > 0.0
