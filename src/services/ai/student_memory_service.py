"""Cross-session companion-chat memory: student-visible, opt-in, student-owned.

Scope note (see docs/planning/STUDENT_ROLE_RESTORE_SPEC.md section 8/9): this
service only owns consent + storage + manual management of memory entries. It
deliberately does NOT read/write into the live QA/companion answer pipeline
(src/services/ai/qa_answer_service.py, companion_service.py) -- that pipeline
is a shared, carefully-scoped entry point for both the standalone /qa route
and companion chat ("deliberately with no caller-specific branching", per its
own docstring), and splicing memory context into it risks skewing retrieval
for an unverified benefit. `build_context_block` is provided ready for a
future, deliberate integration decision, not wired to anything yet.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.db import models

_MAX_UPDATES_PER_TURN = 2
_MAX_CONTEXT_ENTRIES = 6
_MAX_CONTENT_LENGTH = 500


class StudentMemoryService:
    def __init__(self, db: Session) -> None:
        self._db = db

    # ── Consent ──────────────────────────────────────────────────────────
    def has_consent(self, student_id: str) -> bool:
        row = self._db.query(models.StudentMemoryConsent).filter_by(student_id=student_id).first()
        return bool(row and row.granted)

    def set_consent(self, student_id: str, granted: bool) -> bool:
        row = self._db.query(models.StudentMemoryConsent).filter_by(student_id=student_id).first()
        now = datetime.utcnow()
        if row is None:
            row = models.StudentMemoryConsent(student_id=student_id, granted=granted, updated_at=now)
            self._db.add(row)
        else:
            row.granted = granted
            row.updated_at = now
        if not granted:
            # Withdrawing consent is a "right to be forgotten" trigger, not
            # just a stop-future-writes gate.
            self._db.query(models.StudentMemoryEntry).filter_by(student_id=student_id).delete()
        self._db.commit()
        return granted

    # ── Entries ──────────────────────────────────────────────────────────
    def list_entries(self, student_id: str, subject_code: str | None = None) -> list[dict]:
        query = self._db.query(models.StudentMemoryEntry).filter_by(student_id=student_id)
        if subject_code:
            code = subject_code.strip().upper()
            query = query.filter(
                (models.StudentMemoryEntry.subject_code == code)
                | (models.StudentMemoryEntry.subject_code.is_(None))
            )
        rows = query.order_by(models.StudentMemoryEntry.last_reinforced_at.desc()).all()
        return [self._serialize(row) for row in rows]

    def delete_entry(self, student_id: str, entry_id: str) -> bool:
        row = (
            self._db.query(models.StudentMemoryEntry)
            .filter_by(id=entry_id, student_id=student_id)
            .first()
        )
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

    def forget_all(self, student_id: str) -> int:
        deleted = self._db.query(models.StudentMemoryEntry).filter_by(student_id=student_id).delete()
        self._db.commit()
        return deleted

    # ── Write path (not currently invoked by any caller — see module
    #    docstring; kept ready for a deliberate future integration) ────────
    def record_updates(
        self,
        *,
        student_id: str,
        subject_code: str | None,
        conversation_id: str | None,
        updates: list[dict],
    ) -> list[dict]:
        if not self.has_consent(student_id):
            return []
        applied: list[dict] = []
        for update in updates[:_MAX_UPDATES_PER_TURN]:
            kind = (update.get("kind") or "").strip()
            content = (update.get("content") or "").strip()[:_MAX_CONTENT_LENGTH]
            if kind not in {"preference", "weak_topic", "strength_topic"} or not content:
                continue
            entry_subject = None if kind == "preference" else (subject_code or "").strip().upper() or None
            existing = self._find_similar(student_id, entry_subject, kind, content)
            if existing:
                existing.reinforce_count += 1
                existing.last_reinforced_at = datetime.utcnow()
                applied.append(self._serialize(existing))
                continue
            row = models.StudentMemoryEntry(
                id=f"mem_{uuid.uuid4().hex[:10]}",
                student_id=student_id,
                subject_code=entry_subject,
                kind=kind,
                content=content,
                source_conversation_id=conversation_id,
                reinforce_count=1,
                created_at=datetime.utcnow(),
                last_reinforced_at=datetime.utcnow(),
            )
            self._db.add(row)
            applied.append(self._serialize(row))
        self._db.commit()
        return applied

    def build_context_block(self, student_id: str, subject_code: str | None) -> str | None:
        if not self.has_consent(student_id):
            return None
        code = (subject_code or "").strip().upper() or None
        subject_entries = (
            self._db.query(models.StudentMemoryEntry)
            .filter_by(student_id=student_id, subject_code=code)
            .order_by(models.StudentMemoryEntry.last_reinforced_at.desc())
            .all()
            if code
            else []
        )
        preference_entries = (
            self._db.query(models.StudentMemoryEntry)
            .filter_by(student_id=student_id, subject_code=None, kind="preference")
            .order_by(models.StudentMemoryEntry.last_reinforced_at.desc())
            .all()
        )
        combined = (subject_entries + preference_entries)[:_MAX_CONTEXT_ENTRIES]
        if not combined:
            return None
        lines = ["Ghi nhớ từ các lần trò chuyện trước (chỉ là ngữ cảnh nền, câu hỏi hiện tại vẫn ưu tiên hơn):"]
        lines.extend(f"- {row.content}" for row in combined)
        return "\n".join(lines)

    def _find_similar(
        self, student_id: str, subject_code: str | None, kind: str, content: str
    ) -> models.StudentMemoryEntry | None:
        normalized = " ".join(content.lower().split())
        candidates = (
            self._db.query(models.StudentMemoryEntry)
            .filter_by(student_id=student_id, subject_code=subject_code, kind=kind)
            .all()
        )
        for row in candidates:
            if " ".join(row.content.lower().split()) == normalized:
                return row
        return None

    @staticmethod
    def _serialize(row: models.StudentMemoryEntry) -> dict:
        return {
            "id": row.id,
            "subjectCode": row.subject_code,
            "kind": row.kind,
            "content": row.content,
            "reinforceCount": row.reinforce_count,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "lastReinforcedAt": row.last_reinforced_at.isoformat() if row.last_reinforced_at else None,
        }
