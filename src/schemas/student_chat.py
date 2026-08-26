"""Pydantic schemas for the unified Cursus student chat (replaces the old
single-shot QaResponse in schemas/qa.py and the per-course thread schemas in
schemas/companion.py with one continuous per-student conversation). Named
student_chat, not chat, to avoid colliding with schemas/chat.py's pre-existing
ChatRequest/ChatResponse used by the unrelated scaffold agent at
src/api/routes.py's POST /api/v1/chat."""

# ruff: noqa: N815 -- camelCase fields to match the frontend's JSON convention.

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CitationKind = Literal["academic", "state", "help"]

ChatMode = Literal[
    "llm",
    "extractive",
    "blocked",
    "no_source",
    "chat",
    "guidance",
    "out_of_scope",
    "companion",
    "companion_crisis",
]


class ChatCitation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    kind: CitationKind
    sourceLabel: str
    section: str | None = None
    docTitle: str | None = None
    document: str | None = None
    excerpt: str | None = None
    score: float | None = None
    isMock: bool = False
    # Frontend route pointer, only set for kind="help" citations (e.g. "/student/planner").
    route: str | None = None


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    sender: str  # USER | ASSISTANT
    content: str
    createdAt: str | None
    mode: ChatMode = "extractive"
    citations: list[ChatCitation] = Field(default_factory=list)
    blocked: bool = False
    blockReason: str | None = None
    guidance: dict = Field(default_factory=dict)
    engine: str = "deterministic"
    subjectCode: str | None = None
    intent: str = "ask_knowledge"
    alternatives: list[str] = Field(default_factory=list)
    # "quota" when the LLM was attempted but rejected for quota/rate-limit
    # (429) and this message fell back to a non-LLM answer; None otherwise.
    degradedReason: str | None = None


class ChatStateOut(BaseModel):
    conversationId: str | None
    messages: list[ChatMessageOut] = Field(default_factory=list)


class SendChatMessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subjectCode: str | None = Field(default=None, max_length=32)
    message: str = Field(..., min_length=1, max_length=4000)


class ChatAnswerPayload(BaseModel):
    """Structured LLM output for the unified chat prompt (chat_v2.md)."""

    answer: str
    cited_ids: list[str] = Field(default_factory=list)
    insufficient_context: bool = False
