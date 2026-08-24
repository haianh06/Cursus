"""Persistence for per-course companion chat threads.

Ownership is always scoped by `student_id` (a `Conversation` row is never
readable/writable without matching `student_id` — see `get_owned`), so a
course/thread from another student (and transitively another org, since
enrollment itself is org-scoped) can never surface through this repository.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.db import models

MAX_THREADS_PER_COURSE = 10


class ConversationRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_for_student_course(self, *, student_id: str, subject_code: str) -> list[models.Conversation]:
        code = subject_code.strip().upper()
        return (
            self._db.query(models.Conversation)
            .filter(models.Conversation.student_id == student_id, models.Conversation.subject_code == code)
            .order_by(models.Conversation.updated_at.desc(), models.Conversation.created_at.desc())
            .all()
        )

    def get_owned(self, *, conversation_id: str, student_id: str) -> models.Conversation | None:
        return (
            self._db.query(models.Conversation)
            .filter(models.Conversation.id == conversation_id, models.Conversation.student_id == student_id)
            .first()
        )

    def count_for_course(self, *, student_id: str, subject_code: str) -> int:
        code = subject_code.strip().upper()
        return (
            self._db.query(models.Conversation)
            .filter(models.Conversation.student_id == student_id, models.Conversation.subject_code == code)
            .count()
        )

    def create(self, *, student_id: str, subject_code: str, title: str) -> models.Conversation:
        code = subject_code.strip().upper()
        now = datetime.utcnow()
        conversation = models.Conversation(
            id=f"conv_{uuid.uuid4().hex[:16]}",
            student_id=student_id,
            subject_code=code,
            section_id=None,
            title=title.strip()[:120] or f"Chat {code}",
            created_at=now,
            updated_at=now,
        )
        self._db.add(conversation)
        self._db.flush()
        return conversation

    def touch(self, conversation: models.Conversation) -> None:
        conversation.updated_at = datetime.utcnow()
        self._db.flush()

    def delete_owned(self, *, conversation_id: str, student_id: str) -> bool:
        row = self.get_owned(conversation_id=conversation_id, student_id=student_id)
        if row is None:
            return False
        self._db.delete(row)
        self._db.flush()
        return True

    def delete_oldest_for_course(self, *, student_id: str, subject_code: str) -> None:
        code = subject_code.strip().upper()
        oldest = (
            self._db.query(models.Conversation)
            .filter(models.Conversation.student_id == student_id, models.Conversation.subject_code == code)
            .order_by(models.Conversation.updated_at.asc(), models.Conversation.created_at.asc())
            .first()
        )
        if oldest is not None:
            self._db.delete(oldest)
            self._db.flush()

    def list_messages(self, *, conversation_id: str, limit: int | None = None) -> list[models.Message]:
        if limit is not None:
            rows = (
                self._db.query(models.Message)
                .filter(models.Message.conversation_id == conversation_id)
                .order_by(models.Message.created_at.desc())
                .limit(limit)
                .all()
            )
            return list(reversed(rows))
        return (
            self._db.query(models.Message)
            .filter(models.Message.conversation_id == conversation_id)
            .order_by(models.Message.created_at.asc())
            .all()
        )

    def add_message(
        self, *, conversation_id: str, sender: str, content: str, metadata: dict | None = None
    ) -> models.Message:
        message = models.Message(
            id=f"msg_{uuid.uuid4().hex[:16]}",
            conversation_id=conversation_id,
            sender=sender,
            content=content,
            created_at=datetime.utcnow(),
            metadata_info=metadata or {},
        )
        self._db.add(message)
        self._db.flush()
        return message
