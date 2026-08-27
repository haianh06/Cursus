"""Unit tests for the LLM-drafted reflection summary (preview endpoint only).

`save_reflection` never calls `build_summary_llm` — its own fallback stays on
the deterministic `build_summary` directly, so these tests only cover the
preview path. Also covers P0#8 trace (mục 9 ý8, Option B,
docs/PENDING_DECISIONS.md #1) — see test_reflection_engine_trace.py for the
`save()` -> `WeeklyReflection.metrics` side of this.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.schemas.reflection import LlmReflectionSummaryPayload
from src.services.ai import reflection_engine
from src.services.ai.reflection_engine import ReflectionEngine


def _facts() -> dict:
    return {
        "weekNumber": 4,
        "totalTasks": 5,
        "completedTasks": 4,
        "deferredTasks": 1,
        "estimatedMinutes": 300,
        "actualMinutes": 340,
        "completionRate": 0.8,
    }


def test_no_configured_llm_returns_deterministic_summary(monkeypatch):
    monkeypatch.setattr(reflection_engine, "has_configured_llm", lambda: False)
    engine = ReflectionEngine(db=MagicMock())
    summary, trace = engine.build_summary_llm(facts=_facts(), answers=[], adjustments=[])
    expected = engine.build_summary(facts=_facts(), answers=[], adjustments=[])
    assert summary == expected
    assert trace == {"llm_attempted": False, "llm_success": False, "retrieval_empty": False}


def test_llm_success_returns_llm_summary(monkeypatch):
    monkeypatch.setattr(reflection_engine, "has_configured_llm", lambda: True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = (
        LlmReflectionSummaryPayload(summary="Tuần này bạn hoàn thành tốt, giữ nhịp ổn định.")
    )
    monkeypatch.setattr(reflection_engine, "get_llm", lambda: mock_llm)
    monkeypatch.setattr(
        reflection_engine.Path, "read_text", lambda self, encoding=None: "system prompt"
    )

    engine = ReflectionEngine(db=MagicMock())
    summary, trace = engine.build_summary_llm(facts=_facts(), answers=[], adjustments=[])
    assert summary == "Tuần này bạn hoàn thành tốt, giữ nhịp ổn định."
    assert trace == {"llm_attempted": True, "llm_success": True, "retrieval_empty": False}


def test_llm_blank_summary_falls_back_to_deterministic(monkeypatch):
    monkeypatch.setattr(reflection_engine, "has_configured_llm", lambda: True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = LlmReflectionSummaryPayload(
        summary="   "
    )
    monkeypatch.setattr(reflection_engine, "get_llm", lambda: mock_llm)
    monkeypatch.setattr(
        reflection_engine.Path, "read_text", lambda self, encoding=None: "system prompt"
    )

    engine = ReflectionEngine(db=MagicMock())
    summary, trace = engine.build_summary_llm(facts=_facts(), answers=[], adjustments=[])
    expected = engine.build_summary(facts=_facts(), answers=[], adjustments=[])
    assert summary == expected
    # LLM WAS attempted (a call was made) but declined/returned nothing usable
    # -- distinct from "no key configured" (llm_attempted=False above).
    assert trace == {"llm_attempted": True, "llm_success": False, "retrieval_empty": False}


def test_llm_exception_falls_back_to_deterministic(monkeypatch):
    monkeypatch.setattr(reflection_engine, "has_configured_llm", lambda: True)

    def _boom():
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(reflection_engine, "get_llm", _boom)
    monkeypatch.setattr(
        reflection_engine.Path, "read_text", lambda self, encoding=None: "system prompt"
    )

    engine = ReflectionEngine(db=MagicMock())
    summary, trace = engine.build_summary_llm(facts=_facts(), answers=[], adjustments=[])
    expected = engine.build_summary(facts=_facts(), answers=[], adjustments=[])
    assert summary == expected
    assert trace == {"llm_attempted": True, "llm_success": False, "retrieval_empty": False}
