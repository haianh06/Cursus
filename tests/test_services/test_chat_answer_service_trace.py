"""Trace log contract for `ChatAnswerService.answer()` — successor to
test_qa_answer_service_trace.py after the chatbot rebuild. Confirms a
structured `chat_answer_trace` log line covering llm_attempted/llm_success,
now across the wider set of context inputs (academic/state/help/faq) the
new service accepts.

Captures the log call by monkeypatching the module logger directly rather
than pytest's `caplog` -- see the original test's docstring for why
(src.security.logging.configure_logging() replaces the root logger's handler
list wholesale at src.main import time).
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.schemas.student_chat import ChatAnswerPayload
from src.services.ai import chat_answer_service
from src.services.rag.retrieval_service import RetrievedChunk


def _fake_chunk(chunk_id: str = "C1") -> SimpleNamespace:
    return SimpleNamespace(
        chunk_id=chunk_id,
        source_label="SSA101 - Session 1",
        section="Session 1",
        doc_title="SSA101 Syllabus",
        text="Nội dung syllabus mẫu.",
        content_source="curriculum",
    )


def _capture_trace_log(monkeypatch):
    calls: list[tuple] = []
    monkeypatch.setattr(
        chat_answer_service.logger,
        "info",
        lambda msg, *args, **kwargs: calls.append((msg, args)),
    )
    return calls


def _assert_trace(calls, *, llm_attempted, llm_success):
    trace_calls = [c for c in calls if c[0].startswith("chat_answer_trace")]
    assert len(trace_calls) == 1, f"expected exactly 1 chat_answer_trace log call, got {len(trace_calls)}"
    _msg, args = trace_calls[0]
    # args = (subject_code, mode, llm_attempted, llm_success, academic_count, has_state, help_count, faq_count)
    assert args[2] is llm_attempted, args
    assert args[3] is llm_success, args


def test_no_context_at_all_is_logged_as_no_source(monkeypatch):
    calls = _capture_trace_log(monkeypatch)
    service = chat_answer_service.ChatAnswerService()

    answer, citations, mode, degraded_reason = service.answer(
        question="Câu hỏi bất kỳ", subject_code="SSA101",
        academic_chunks=[], student_context=None, help_matches=[], faq_matches=[],
    )

    assert mode == "no_source"
    assert citations == []
    _assert_trace(calls, llm_attempted=False, llm_success=False)


def test_academic_chunk_attempts_llm_when_one_is_configured(monkeypatch):
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(chat_answer_service.ChatAnswerService, "_llm_available", lambda self: True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = ChatAnswerPayload(
        answer="Điều kiện qua môn là điểm trung bình >= 5.", cited_ids=["C1"], insufficient_context=False
    )
    monkeypatch.setattr(chat_answer_service, "get_llm", lambda: mock_llm)

    service = chat_answer_service.ChatAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]
    answer, citations, mode, degraded_reason = service.answer(
        question="Điều kiện qua môn là gì?", subject_code="SSA101",
        academic_chunks=retrieved, student_context=None, help_matches=[], faq_matches=[],
    )

    assert mode == "llm"
    assert citations[0].id == "C1"
    assert citations[0].kind == "academic"
    _assert_trace(calls, llm_attempted=True, llm_success=True)


def test_state_only_context_used_when_no_llm_configured(monkeypatch):
    """No academic/help match, only the student's own state -- extractive
    fallback must still surface it (last-resort priority, see
    ChatAnswerService._answer_fallback)."""
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(chat_answer_service.ChatAnswerService, "_llm_available", lambda self: False)
    service = chat_answer_service.ChatAnswerService()

    answer, citations, mode, degraded_reason = service.answer(
        question="Kế hoạch tuần này của em là gì?", subject_code=None,
        academic_chunks=[], student_context={"text": "Tuần 5: chưa có kế hoạch."},
        help_matches=[], faq_matches=[],
    )

    assert mode == "extractive"
    assert "Tuần 5" in answer
    assert citations[0].kind == "state"
    _assert_trace(calls, llm_attempted=False, llm_success=False)


def test_llm_exception_falls_back_to_extractive(monkeypatch):
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(chat_answer_service.ChatAnswerService, "_llm_available", lambda self: True)

    def _boom():
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(chat_answer_service, "get_llm", _boom)

    service = chat_answer_service.ChatAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]
    answer, citations, mode, degraded_reason = service.answer(
        question="So sánh 2 phương pháp này khác nhau thế nào?", subject_code="SSA101",
        academic_chunks=retrieved, student_context=None, help_matches=[], faq_matches=[],
    )

    assert mode != "llm"
    assert degraded_reason == "quota"
    _assert_trace(calls, llm_attempted=True, llm_success=False)


def test_llm_insufficient_context_counts_as_no_source(monkeypatch):
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(chat_answer_service.ChatAnswerService, "_llm_available", lambda self: True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = ChatAnswerPayload(
        answer="", cited_ids=[], insufficient_context=True
    )
    monkeypatch.setattr(chat_answer_service, "get_llm", lambda: mock_llm)

    service = chat_answer_service.ChatAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]
    answer, citations, mode, degraded_reason = service.answer(
        question="So sánh 2 phương pháp này khác nhau thế nào?", subject_code="SSA101",
        academic_chunks=retrieved, student_context=None, help_matches=[], faq_matches=[],
    )

    assert mode == "no_source"
    assert degraded_reason is None
    _assert_trace(calls, llm_attempted=True, llm_success=False)
