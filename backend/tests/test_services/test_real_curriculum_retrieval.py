"""Phase 2 (21/08): broad retrieval+citation smoke test across EVERY course
ingested via `real_curriculum_service` — not just a hand-picked sample.

Scope: prove the general curriculum loader actually produces courses whose
content is (a) real (never source=mock), (b) retrievable in-scope with a
correctly-labeled citation, and (c) honest about out-of-scope questions
("not found", not a hallucinated answer) — for all 34 courses, looped, per
mục 11 ý5 / mục 16.1's requirement to verify every newly-ingested course,
not a sample.
"""
from __future__ import annotations

import pytest

from src.db.connection import SessionLocal
from src.repositories.chunk_repository import ChunkRepository
from src.services.mock.real_curriculum_service import (
    discover_real_course_codes,
    ingest_all_real_courses,
)
from src.services.rag.retrieval_service import RetrievalService

# Deliberately absurd — no academic syllabus in this catalog could plausibly
# contain these tokens, so scoring 0 here proves the retriever isn't just
# matching everything indiscriminately.
_OUT_OF_SCOPE_QUESTION = (
    "Which bakery in Reykjavik invented pineapple croissant recipes in 1742?"
)


@pytest.fixture(scope="module")
def ingested_codes() -> list[str]:
    db = SessionLocal()
    try:
        ingest_all_real_courses(db)
    finally:
        db.close()
    return discover_real_course_codes()


def test_discovers_the_expected_34_new_real_courses(ingested_codes):
    """Regression guard: catches a future accidental drop/addition to the
    parsed-chunk set without anyone updating this count deliberately."""
    assert len(ingested_codes) == 34
    # None of these should ever be a combo/elective-slot catalog placeholder
    # (the `*` codes) — those are deliberately excluded, see
    # docs/planning/v2/scripts/parse_all_courses.py's module docstring.
    assert all("*" not in code for code in ingested_codes)


@pytest.mark.parametrize("code", discover_real_course_codes())
def test_every_real_course_has_only_real_chunks(code, ingested_codes):
    db = SessionLocal()
    try:
        chunks = ChunkRepository(db).list_chunks_for_course(subject_code=code)
    finally:
        db.close()
    assert chunks, f"{code}: expected at least 1 real chunk after ingestion"
    for chunk in chunks:
        assert chunk.content_source in {"curriculum", "admin_curriculum"}, (
            f"{code}: chunk {chunk.chunk_id} has content_source="
            f"{chunk.content_source!r}, expected real provenance"
        )
        assert chunk.text.strip()


@pytest.mark.parametrize("code", discover_real_course_codes())
def test_every_real_course_answers_in_scope_with_real_citation(code, ingested_codes):
    """"session" is a universal in-scope probe: every parsed syllabus has
    >=1 "Session N — <topic>" chunk (flm_parser.py's session loop), so this
    is a broad reachability check across all 34 courses rather than a
    content-specific assertion about any one syllabus's subject matter."""
    db = SessionLocal()
    try:
        retrieval = RetrievalService(ChunkRepository(db))
        results = retrieval.retrieve(subject_code=code, question="session")
    finally:
        db.close()
    assert results, f"{code}: expected a retrievable chunk for an in-scope question"
    assert results[0].chunk.course_code == code
    assert results[0].chunk.content_source in {"curriculum", "admin_curriculum"}
    assert results[0].chunk.source_label.strip()


@pytest.mark.parametrize("code", discover_real_course_codes())
def test_every_real_course_reports_not_found_when_out_of_scope(code, ingested_codes):
    db = SessionLocal()
    try:
        retrieval = RetrievalService(ChunkRepository(db))
        results = retrieval.retrieve(subject_code=code, question=_OUT_OF_SCOPE_QUESTION)
    finally:
        db.close()
    assert results == [], (
        f"{code}: an unrelated question must retrieve nothing, not a "
        f"confident-but-wrong citation"
    )
