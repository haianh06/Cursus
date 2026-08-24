"""Pydantic schemas for Study Assistant Q&A (Playbook F3)."""

# ruff: noqa: N815 -- field names are intentionally camelCase to match the
# JSON shape the frontend already consumes (see frontend/src/lib/api.js).

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QaRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subjectCode: str = Field(
        ...,
        min_length=2,
        max_length=32,
        description="Course code, e.g. SSA101",
    )
    question: str = Field(..., min_length=1, max_length=4000)

    @property
    def subject_code(self) -> str:
        return self.subjectCode


class QaCitation(BaseModel):
    """Citation contract (Blueprint §4.3): document + section + excerpt +
    internal chunk id, so a citation chip can open the exact source text."""

    model_config = ConfigDict(populate_by_name=True)

    sourceLabel: str
    section: str | None = None
    chunkId: str
    docTitle: str | None = None
    document: str | None = None
    excerpt: str | None = None
    score: float | None = None
    # mục 16 data contract: True when this citation's source content is
    # fabricated (student_mock_data_service.COURSE_DOCUMENTS), not an
    # official_document — the citation UI must not present it the same way
    # as a real syllabus source.
    isMock: bool = False


class QaResponse(BaseModel):
    blocked: bool
    answer: str
    blockReason: str | None = None
    citations: list[QaCitation] = Field(default_factory=list)
    mode: Literal[
        "llm",
        "extractive",
        "blocked",
        "no_source",
        "chat",
        "faq",
        "guidance",
        "out_of_scope",
    ] = "extractive"
    alternatives: list[str] = Field(default_factory=list)
    # Guardrail intent from the §4.2 matrix (ask_knowledge / ask_hint /
    # graded_deliverable / out_of_scope / prompt_injection).
    intent: str = "ask_knowledge"
    # Concept + Socratic questions + empty template for a redirected request.
    guidance: dict = Field(default_factory=dict)
    followUpQuestions: list[str] = Field(default_factory=list)
    # Honest engine label — the UI must not imply a live LLM when it was a
    # deterministic path. Set by QaService.
    engine: str = "deterministic"

    def to_api_dict(self) -> dict:
        return self.model_dump(mode="json")


class LlmQaPayload(BaseModel):
    """Structured LLM output for grounded answers."""

    answer: str
    cited_chunk_ids: list[str] = Field(default_factory=list)
    insufficient_context: bool = False
