"""P0#8 trace (mục 9 ý8, Option B, docs/PENDING_DECISIONS.md #1) — confirms
`QaAnswerService.answer()` emits a structured `qa_answer_trace` log line with
llm_attempted/llm_success/fallback_used/retrieval_empty, covering the one
shared entry point both callers (Companion, standalone /api/v1/qa) use.
No DB row is written here by design -- see the docstring on `answer()`.

Captures the log call by monkeypatching the module logger directly rather
than pytest's `caplog` -- `src.security.logging.configure_logging()`
replaces the root logger's handler list wholesale at `src.main` import time
(module-level side effect), which drops caplog's own root handler once any
earlier test in the suite has imported the app; monkeypatching sidesteps
that entirely and doesn't depend on global logging-handler state at all.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.schemas.qa import LlmQaPayload
from src.services.ai import qa_answer_service
from src.services.rag.retrieval_service import RetrievedChunk

COMPLEX_QUESTION = "So sánh 2 phương pháp này khác nhau thế nào?"


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
        qa_answer_service.logger,
        "info",
        lambda msg, *args, **kwargs: calls.append((msg, args)),
    )
    return calls


def _assert_trace(calls, *, llm_attempted, llm_success, fallback_used, retrieval_empty):
    trace_calls = [c for c in calls if c[0].startswith("qa_answer_trace")]
    assert len(trace_calls) == 1, f"expected exactly 1 qa_answer_trace log call, got {len(trace_calls)}"
    _msg, args = trace_calls[0]
    # args = (subject_code, mode, llm_attempted, llm_success, fallback_used, retrieval_empty)
    assert args[2] is llm_attempted, args
    assert args[3] is llm_success, args
    assert args[4] is fallback_used, args
    assert args[5] is retrieval_empty, args


def test_retrieval_empty_is_logged(monkeypatch):
    calls = _capture_trace_log(monkeypatch)
    service = qa_answer_service.QaAnswerService()

    service.answer(question="Câu hỏi bất kỳ", subject_code="SSA101", retrieved=[])

    _assert_trace(calls, llm_attempted=False, llm_success=False, fallback_used=False, retrieval_empty=True)


def test_a_simple_question_still_attempts_llm_when_one_is_configured(monkeypatch):
    """The LLM decides relevance now, not a keyword-pattern gate — even a
    plain factual question must reach it when retrieval found something and
    a model is configured, so it can catch a low-scoring, off-topic match
    extractive excerpting would just quote as if it answered the question."""
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(qa_answer_service.QaAnswerService, "_llm_available", lambda self: True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = LlmQaPayload(
        answer="Điều kiện qua môn là điểm trung bình >= 5.", cited_chunk_ids=["C1"], insufficient_context=False
    )
    monkeypatch.setattr(qa_answer_service, "get_llm", lambda: mock_llm)

    service = qa_answer_service.QaAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]
    service.answer(question="Điều kiện qua môn là gì?", subject_code="SSA101", retrieved=retrieved)

    _assert_trace(calls, llm_attempted=True, llm_success=True, fallback_used=False, retrieval_empty=False)


def test_extractive_only_path_used_when_no_llm_configured(monkeypatch):
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(qa_answer_service.QaAnswerService, "_llm_available", lambda self: False)
    service = qa_answer_service.QaAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]

    service.answer(question="Điều kiện qua môn là gì?", subject_code="SSA101", retrieved=retrieved)

    _assert_trace(calls, llm_attempted=False, llm_success=False, fallback_used=False, retrieval_empty=False)


def test_llm_success_is_logged(monkeypatch):
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(qa_answer_service.QaAnswerService, "_llm_available", lambda self: True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = LlmQaPayload(
        answer="Câu trả lời tổng hợp.", cited_chunk_ids=["C1"], insufficient_context=False
    )
    monkeypatch.setattr(qa_answer_service, "get_llm", lambda: mock_llm)

    service = qa_answer_service.QaAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]
    answer, _citations, mode = service.answer(
        question=COMPLEX_QUESTION, subject_code="SSA101", retrieved=retrieved
    )

    assert mode == "llm"
    _assert_trace(calls, llm_attempted=True, llm_success=True, fallback_used=False, retrieval_empty=False)


def test_llm_exception_fallback_is_logged(monkeypatch):
    """Simulated Gemini failure (e.g. quota exhausted) -- this is exactly the
    case P0#8 exists to distinguish from a quality problem."""
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(qa_answer_service.QaAnswerService, "_llm_available", lambda self: True)

    def _boom():
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(qa_answer_service, "get_llm", _boom)

    service = qa_answer_service.QaAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]
    answer, _citations, mode = service.answer(
        question=COMPLEX_QUESTION, subject_code="SSA101", retrieved=retrieved
    )

    # Falls back to the extractive path -- still answers, just not via LLM.
    assert mode != "llm"
    _assert_trace(calls, llm_attempted=True, llm_success=False, fallback_used=True, retrieval_empty=False)


def test_llm_insufficient_context_counts_as_fallback(monkeypatch):
    """The LLM was genuinely called and declined (not an error) -- still a
    fallback in the trace's sense: llm_attempted=True, llm_success=False."""
    calls = _capture_trace_log(monkeypatch)
    monkeypatch.setattr(qa_answer_service.QaAnswerService, "_llm_available", lambda self: True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = LlmQaPayload(
        answer="", cited_chunk_ids=[], insufficient_context=True
    )
    monkeypatch.setattr(qa_answer_service, "get_llm", lambda: mock_llm)

    service = qa_answer_service.QaAnswerService()
    retrieved = [RetrievedChunk(chunk=_fake_chunk(), score=0.9)]
    answer, citations, mode = service.answer(
        question=COMPLEX_QUESTION, subject_code="SSA101", retrieved=retrieved
    )

    assert mode == "no_source"
    _assert_trace(calls, llm_attempted=True, llm_success=False, fallback_used=True, retrieval_empty=False)
