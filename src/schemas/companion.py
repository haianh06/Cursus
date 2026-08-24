"""Pydantic schemas for companion chat (per-course conversational Q&A)."""

# ruff: noqa: N815 -- camelCase fields to match this branch's JSON convention.

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CreateThreadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    subjectCode: str = Field(..., min_length=2, max_length=32)
    title: str = Field(default="", max_length=120)


class ThreadOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    subjectCode: str | None
    title: str
    createdAt: str | None
    updatedAt: str | None


class MessageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    conversationId: str
    sender: str
    content: str
    createdAt: str | None
    metadata: dict = Field(default_factory=dict)


class ThreadDetailOut(ThreadOut):
    messages: list[MessageOut] = Field(default_factory=list)


class SendMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
