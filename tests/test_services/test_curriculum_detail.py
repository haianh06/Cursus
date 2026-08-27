"""`real_curriculum_service.get_curriculum_detail` — reads a course's parsed
syllabus straight from its `chunks_<CODE>.json` file (no DB, no ingestion
required). Built 22/08 to back the Admin Console curriculum detail view;
these tests assert exactly the structural guarantees that view relies on
(verified against every one of the 44 real course files before the UI was
built — see docs/EVALUATION_2_KETLUAN.md).
"""
from __future__ import annotations

from src.services.mock.real_curriculum_service import discover_real_course_codes, get_curriculum_detail


def test_unknown_code_returns_none():
    assert get_curriculum_detail("NOT_A_REAL_CODE_XYZ") is None


def test_generated_summary_without_parsed_syllabus_contract_returns_none():
    # EXE101 is an illustrative summary file created during planning. It has
    # chunks, but no parsed syllabus meta/session structure, so production
    # discovery and Admin detail must not present it as official curriculum.
    assert get_curriculum_detail("EXE101") is None


def test_ssa101_has_expected_meta_and_grading_note():
    detail = get_curriculum_detail("SSA101")
    assert detail is not None
    assert detail["meta"]["NoCredit"] == "3"
    # The one real course confirmed to carry an assessment-weight breakdown
    # inside `Note` — asserted verbatim, not reformatted into rows, since
    # this field isn't per-line structured across all 44 files.
    assert "Participation: 10%" in detail["meta"]["Note"]


def test_ssa101_clo_list_is_parsed_from_the_clo_chunks():
    detail = get_curriculum_detail("SSA101")
    assert detail["clo_count"] == len(detail["clos"])
    assert detail["clos"][0]["code"] == "CLO1"
    # The "CLOn: " prefix must be stripped off, not left duplicated in the text.
    assert not detail["clos"][0]["text"].startswith("CLO1")


def test_session_text_is_split_into_topic_materials_task():
    detail = get_curriculum_detail("CEA201")
    session_1 = next(s for s in detail["sessions"] if s["number"] == 1)
    assert "Introduction to the course" in session_1["topic"]
    assert session_1["materials"] is not None
    assert "Slide" in session_1["materials"]
    assert session_1["task"] is not None
    assert "chatGPT" in session_1["task"]
    # Sessions are sorted by number, not file order.
    numbers = [s["number"] for s in detail["sessions"]]
    assert numbers == sorted(numbers)


def test_session_without_materials_or_task_degrades_to_none_not_a_crash():
    detail = get_curriculum_detail("CEA201")
    review_session = next(s for s in detail["sessions"] if s["number"] == 59)
    assert review_session["materials"] is None
    assert review_session["task"] is None
    assert review_session["topic"]


def test_every_real_course_file_parses_without_error_and_counts_match():
    # Full-catalog sweep, not a hand-picked sample — this is exactly what
    # gates whether the Admin Console button silently breaks on some course.
    for code in discover_real_course_codes():
        detail = get_curriculum_detail(code)
        assert detail is not None, code
        assert detail["clo_count"] == len(detail["clos"]), code
        assert detail["session_count"] == len(detail["sessions"]), code
        assert isinstance(detail["meta"], dict) and detail["meta"], code
