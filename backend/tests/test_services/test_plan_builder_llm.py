"""Unit tests for the LLM plan-generation fallback path (non-demo assignments).

The Gate-2 demo assignment never reaches `_llm_generated_tasks` (verified by
`test_gate2_flow.py` continuing to use the deterministic template) — these
tests cover the fallback in isolation: no key configured, LLM success,
insufficient-context, and LLM error, all via monkeypatch so no real network
call happens.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.schemas.plan import LlmPlanPayload, LlmPlanTaskPayload
from src.services.ai import plan_builder
from src.services.rag.retrieval_service import RetrievedChunk


def _fake_assignment() -> SimpleNamespace:
    return SimpleNamespace(
        id="assignment_not_demo",
        title="Viết báo cáo phân tích yêu cầu",
        description="Phân tích yêu cầu hệ thống cho dự án nhóm.",
        due_date=SimpleNamespace(isoformat=lambda: "2026-08-20T00:00:00"),
        section_id="section_1",
    )


def _fake_retrieved_chunk(chunk_id: str) -> RetrievedChunk:
    chunk = SimpleNamespace(
        chunk_id=chunk_id,
        source_label="SSA101 - Session 3",
        text="Nội dung syllabus mẫu về phân tích yêu cầu.",
    )
    return RetrievedChunk(chunk=chunk, score=1.0)


def test_no_configured_llm_returns_none(monkeypatch):
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: False)
    tasks, trace = plan_builder._llm_generated_tasks(db=MagicMock(), assignment=_fake_assignment())
    assert tasks is None
    assert trace == {"retrieval_empty": False, "llm_success": False}


def test_no_subject_code_returns_none(monkeypatch):
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: True)
    monkeypatch.setattr(plan_builder, "_subject_code_for_assignment", lambda db, a: None)
    tasks, trace = plan_builder._llm_generated_tasks(db=MagicMock(), assignment=_fake_assignment())
    assert tasks is None
    assert trace == {"retrieval_empty": False, "llm_success": False}


def test_no_retrieved_chunks_returns_none_and_marks_retrieval_empty(monkeypatch):
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: True)
    monkeypatch.setattr(plan_builder, "_subject_code_for_assignment", lambda db, a: "SSA101")
    monkeypatch.setattr(
        plan_builder.RetrievalService, "retrieve", lambda self, **kwargs: []
    )
    tasks, trace = plan_builder._llm_generated_tasks(db=MagicMock(), assignment=_fake_assignment())
    assert tasks is None
    # This is the one case retrieval_empty must be True -- distinguishes
    # "nothing to ground the LLM in" from an actual LLM failure/decline.
    assert trace == {"retrieval_empty": True, "llm_success": False}


def test_llm_success_maps_to_generated_tasks_grounded_in_retrieved_chunks(monkeypatch):
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: True)
    monkeypatch.setattr(plan_builder, "_subject_code_for_assignment", lambda db, a: "SSA101")
    retrieved = [_fake_retrieved_chunk("SSA101-c1"), _fake_retrieved_chunk("SSA101-c2")]
    monkeypatch.setattr(
        plan_builder.RetrievalService, "retrieve", lambda self, **kwargs: retrieved
    )

    payload = LlmPlanPayload(
        tasks=[
            LlmPlanTaskPayload(
                key="understand",
                title="Đọc đề bài",
                estimated_minutes=30,
                weekday=0,
                priority="HIGH",
                suggestion_reason="Hiểu yêu cầu trước khi làm.",
                source_chunk_ids=["SSA101-c1", "SSA101-not-in-context"],
            ),
        ],
        insufficient_context=False,
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = payload
    monkeypatch.setattr(plan_builder, "get_llm", lambda: mock_llm)
    monkeypatch.setattr(
        plan_builder.Path, "read_text", lambda self, encoding=None: "system prompt"
    )

    tasks, trace = plan_builder._llm_generated_tasks(db=MagicMock(), assignment=_fake_assignment())

    assert tasks is not None
    assert len(tasks) == 1
    task = tasks[0]
    assert task.title == "Đọc đề bài"
    # Only the chunk id that was actually retrieved survives — no fabricated citation.
    assert task.source_refs == ("SSA101-c1",)
    assert trace == {"retrieval_empty": False, "llm_success": True}


def test_accent_stripped_titles_trigger_retry_and_recover(monkeypatch):
    """A weaker fallback model can drop every Vietnamese diacritic under
    structured-JSON output — one retry with an explicit reminder must be
    attempted, and the recovered (properly-accented) payload used."""
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: True)
    monkeypatch.setattr(plan_builder, "_subject_code_for_assignment", lambda db, a: "SSA101")
    monkeypatch.setattr(
        plan_builder.RetrievalService,
        "retrieve",
        lambda self, **kwargs: [_fake_retrieved_chunk("SSA101-c1")],
    )
    monkeypatch.setattr(
        plan_builder.Path, "read_text", lambda self, encoding=None: "system prompt"
    )

    broken_payload = LlmPlanPayload(
        tasks=[
            LlmPlanTaskPayload(
                key="review",
                title="On tap CSI106 - Bieu dien du lieu",
                estimated_minutes=60,
                weekday=0,
                priority="HIGH",
                suggestion_reason="on tap truoc khi lam bai",
                source_chunk_ids=["SSA101-c1"],
            ),
        ],
        insufficient_context=False,
    )
    fixed_payload = LlmPlanPayload(
        tasks=[
            LlmPlanTaskPayload(
                key="review",
                title="Ôn tập CSI106 - Biểu diễn dữ liệu",
                estimated_minutes=60,
                weekday=0,
                priority="HIGH",
                suggestion_reason="Ôn tập trước khi làm bài.",
                source_chunk_ids=["SSA101-c1"],
            ),
        ],
        insufficient_context=False,
    )
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.side_effect = [
        broken_payload,
        fixed_payload,
    ]
    monkeypatch.setattr(plan_builder, "get_llm", lambda: mock_llm)

    tasks, trace = plan_builder._llm_generated_tasks(db=MagicMock(), assignment=_fake_assignment())

    assert tasks is not None
    assert tasks[0].title == "Ôn tập CSI106 - Biểu diễn dữ liệu"
    assert trace == {"retrieval_empty": False, "llm_success": True}
    assert mock_llm.with_structured_output.return_value.invoke.call_count == 2


def test_insufficient_context_returns_none(monkeypatch):
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: True)
    monkeypatch.setattr(plan_builder, "_subject_code_for_assignment", lambda db, a: "SSA101")
    monkeypatch.setattr(
        plan_builder.RetrievalService,
        "retrieve",
        lambda self, **kwargs: [_fake_retrieved_chunk("SSA101-c1")],
    )
    payload = LlmPlanPayload(tasks=[], insufficient_context=True)
    mock_llm = MagicMock()
    mock_llm.with_structured_output.return_value.invoke.return_value = payload
    monkeypatch.setattr(plan_builder, "get_llm", lambda: mock_llm)
    monkeypatch.setattr(
        plan_builder.Path, "read_text", lambda self, encoding=None: "system prompt"
    )

    tasks, trace = plan_builder._llm_generated_tasks(db=MagicMock(), assignment=_fake_assignment())
    assert tasks is None
    # Retrieval succeeded (had chunks) but the model declined -- must not be
    # confused with retrieval_empty.
    assert trace == {"retrieval_empty": False, "llm_success": False}


def test_llm_exception_falls_back_to_none(monkeypatch):
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: True)
    monkeypatch.setattr(plan_builder, "_subject_code_for_assignment", lambda db, a: "SSA101")
    monkeypatch.setattr(
        plan_builder.RetrievalService,
        "retrieve",
        lambda self, **kwargs: [_fake_retrieved_chunk("SSA101-c1")],
    )

    def _boom():
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(plan_builder, "get_llm", _boom)
    monkeypatch.setattr(
        plan_builder.Path, "read_text", lambda self, encoding=None: "system prompt"
    )

    tasks, trace = plan_builder._llm_generated_tasks(db=MagicMock(), assignment=_fake_assignment())
    assert tasks is None
    assert trace == {"retrieval_empty": False, "llm_success": False}


def test_demo_assignment_never_calls_llm_path(monkeypatch):
    """generate() must route the Gate-2 demo assignment straight to the
    deterministic template — never through _llm_generated_tasks — regardless
    of whether an LLM key is configured."""
    monkeypatch.setattr(plan_builder, "has_configured_llm", lambda: True)
    called = {"llm_path": False}

    def _spy(*args, **kwargs):
        called["llm_path"] = True
        return None, {"retrieval_empty": False, "llm_success": False}

    monkeypatch.setattr(plan_builder, "_llm_generated_tasks", _spy)

    assignment = SimpleNamespace(id=plan_builder.gate2_demo.PART1_ASSIGNMENT_ID)
    if assignment.id == plan_builder.gate2_demo.PART1_ASSIGNMENT_ID:
        tasks = plan_builder._templates_for_assignment(assignment)
    else:
        tasks, _trace = plan_builder._llm_generated_tasks(None, assignment)

    assert not called["llm_path"]
    assert len(tasks) == len(plan_builder.gate2_demo.PART1_TASK_TEMPLATES)
