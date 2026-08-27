"""Unit tests for the Mock LMS source-precedence resolver (mục 6.6/14.3).

Pure unit tests, no DB -- `rank`/`label_for`/`tier_for_content_source`/`winner` are
plain functions.
"""
from __future__ import annotations

from src.services.core import source_precedence as sp


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


