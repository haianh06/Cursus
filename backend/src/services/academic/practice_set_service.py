"""Shared course practice packs: student request, instructor review, reuse.

Adapted from develop's `src/services/practice_set_service.py`. Status names
follow THIS branch's migration/model comment (`DRAFT, PENDING_REVIEW,
PUBLISHED, REJECTED`), not develop's `APPROVED`. Org scope is transitive via
`course_id`; `_allowed_course_ids` is always resolved from the caller's own
org/teaching relationship, never a client-supplied filter.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db import models
from src.repositories.chunk_repository import ChunkRepository
from src.repositories.practice_set_repository import (
    PENDING,
    PUBLISHED,
    REJECTED,
    PracticeSetRepository,
)
from src.services.academic.academic_calendar import clamp_study_week, slide_key_for_week
from src.services.academic.practice_generator import generate_pack

logger = logging.getLogger(__name__)


class PracticeSetService:
    def __init__(self, db: Session, repo: PracticeSetRepository) -> None:
        self._db = db
        self._repo = repo
        self._chunks = ChunkRepository(db)

    def get_for_student(self, *, student_id: str, course_code: str, week_number: int) -> dict[str, Any]:
        course = self._require_student_course(student_id, course_code)
        week = clamp_study_week(week_number)
        slide_key = slide_key_for_week(week)
        row = self._repo.get_by_slide(course.code, slide_key)
        if row is None:
            raise LookupError("Practice set not found")
        if row.status != PUBLISHED:
            raise LookupError("Practice set not found")
        return self._serialize(row, reveal_answers=True)

    def request_for_student(
        self,
        *,
        student_id: str,
        course_code: str,
        week_number: int,
        language: str = "vi",
    ) -> dict[str, Any]:
        course = self._require_student_course(student_id, course_code)
        week = clamp_study_week(week_number)
        preferred_key = slide_key_for_week(week)
        existing = self._repo.get_by_slide(course.code, preferred_key)
        if existing is not None and existing.status in {PENDING, PUBLISHED}:
            return self._serialize(existing, reveal_answers=existing.status == PUBLISHED)

        specs, slide_key = generate_pack(
            db=self._db,
            subject_code=course.code,
            week_number=week,
            student_id=student_id,
            language=language,
        )
        row = self._repo.get_by_slide(course.code, slide_key)
        if row is None:
            row = self._repo.add_set(
                course_id=course.id,
                course_code=course.code,
                slide_key=slide_key,
                week_number=week,
                language=language,
                requested_by=student_id,
                status=PENDING,
            )
        elif row.status == PUBLISHED:
            return self._serialize(row, reveal_answers=True)
        elif row.status == PENDING:
            return self._serialize(row, reveal_answers=False)

        self._repo.replace_items(row, specs)
        row.status = PENDING
        row.week_number = week
        row.language = language
        row.requested_by = row.requested_by or student_id
        row.reviewed_by = None
        row.reviewed_at = None
        self._repo.commit()
        logger.info("practice_set_queued id=%s course=%s slide=%s", row.id, course.code, slide_key)
        return self._serialize(row, reveal_answers=False)

    def list_for_instructor(
        self, *, user_id: str, role: str, organization_id: str | None, status: str | None = None
    ) -> list[dict[str, Any]]:
        course_ids = self._allowed_course_ids(user_id, role, organization_id)
        rows = self._repo.list_by_status(course_ids=course_ids, status=status)
        return [self._serialize(row, reveal_answers=True) for row in rows]

    def get_for_instructor(
        self, *, user_id: str, role: str, organization_id: str | None, set_id: str
    ) -> dict[str, Any]:
        row = self._require_instructor_set(set_id, user_id, role, organization_id)
        return self._serialize(row, reveal_answers=True)

    def update_item(
        self,
        *,
        user_id: str,
        role: str,
        organization_id: str | None,
        set_id: str,
        item_id: str,
        prompt: str | None = None,
        options: list[dict[str, Any]] | None = None,
        correct_key: str | None = None,
        answer: str | None = None,
        explanation: str | None = None,
        source_label: str | None = None,
    ) -> dict[str, Any]:
        row = self._require_instructor_set(set_id, user_id, role, organization_id)
        if row.status == PUBLISHED:
            raise ValueError("Published sets cannot be edited; reject to regenerate")
        item = self._repo.get_item(item_id)
        if item is None or item.set_id != row.id:
            raise LookupError("Practice item not found")
        if prompt is not None:
            item.prompt = prompt.strip()
        if options is not None:
            item.options = options
        if correct_key is not None:
            item.correct_key = correct_key.strip().upper()[:1] or item.correct_key
        if answer is not None:
            item.answer = answer
        if explanation is not None:
            item.explanation = explanation
        if source_label is not None:
            item.source_label = source_label.strip()
        if item.kind == "MCQ" and item.options and item.correct_key:
            for option in item.options:
                if str(option.get("key") or "").upper() == item.correct_key:
                    item.answer = str(option.get("text") or item.answer)
                    break
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self._repo.commit()
        return self._serialize(row, reveal_answers=True)

    def review(
        self,
        *,
        user_id: str,
        role: str,
        organization_id: str | None,
        set_id: str,
        decision: str,
    ) -> dict[str, Any]:
        """`decision` is PUBLISHED or REJECTED — the F5-style instructor review gate."""
        decision = decision.upper()
        if decision not in {PUBLISHED, REJECTED}:
            raise ValueError("decision must be PUBLISHED or REJECTED")
        row = self._require_instructor_set(set_id, user_id, role, organization_id)
        row.status = decision
        row.reviewed_by = user_id
        row.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        row.updated_at = row.reviewed_at
        self._repo.commit()
        logger.info("practice_set_reviewed id=%s by=%s decision=%s", row.id, user_id, decision)
        return self._serialize(row, reveal_answers=True)

    def regenerate(self, *, user_id: str, role: str, organization_id: str | None, set_id: str) -> dict[str, Any]:
        row = self._require_instructor_set(set_id, user_id, role, organization_id)
        specs, slide_key = generate_pack(
            db=self._db,
            subject_code=row.course_code,
            week_number=row.week_number,
            language=row.language,
        )
        row.slide_key = slide_key
        self._repo.replace_items(row, specs)
        row.status = PENDING
        row.reviewed_by = user_id
        row.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
        self._repo.commit()
        logger.info("practice_set_regenerated id=%s by=%s", row.id, user_id)
        return self._serialize(row, reveal_answers=True)

    def _require_student_course(self, student_id: str, course_code: str) -> models.Course:
        code = course_code.strip().upper()
        if not self._chunks.student_enrolled_in_course(student_id=student_id, subject_code=code):
            raise PermissionError("Course not found")
        # Case-insensitive — some real catalog codes have a lowercase suffix
        # (e.g. "ENW493c"); see chunk_repository.py for the full explanation.
        course = self._db.query(models.Course).filter(func.upper(models.Course.code) == code).first()
        if course is None:
            raise PermissionError("Course not found")
        return course

    def _allowed_course_ids(self, user_id: str, role: str, organization_id: str | None) -> list[str]:
        value = str(getattr(role, "value", role)).upper()
        if value == "ADMIN":
            return self._repo.org_course_ids(organization_id)
        # Instructor: courses they teach, intersected with their own org so
        # an instructor can never enumerate another org's practice queue
        # even if a stale section id leaked in.
        taught = set(self._repo.instructor_course_ids(user_id))
        return [cid for cid in self._repo.org_course_ids(organization_id) if cid in taught]

    def _require_instructor_set(
        self, set_id: str, user_id: str, role: str, organization_id: str | None
    ) -> models.PracticeSet:
        row = self._repo.get(set_id)
        if row is None:
            raise LookupError("Practice set not found")
        allowed = set(self._allowed_course_ids(user_id, role, organization_id))
        if row.course_id not in allowed:
            raise PermissionError("You can only review practice sets for courses you teach")
        return row

    def _serialize(self, row: models.PracticeSet, *, reveal_answers: bool) -> dict[str, Any]:
        items = self._repo.list_items(row.id)
        payload_items = []
        for item in items:
            entry: dict[str, Any] = {
                "id": item.id,
                "kind": item.kind,
                "sortOrder": item.sort_order,
                "prompt": item.prompt,
                "sourceLabel": item.source_label,
            }
            if item.kind == "MCQ":
                entry["options"] = item.options or []
            else:
                entry["answer"] = item.answer if reveal_answers else None
            if reveal_answers:
                entry["correctKey"] = item.correct_key
                entry["answer"] = item.answer
                entry["explanation"] = item.explanation
            payload_items.append(entry)
        return {
            "id": row.id,
            "courseId": row.course_id,
            "courseCode": row.course_code,
            "slideKey": row.slide_key,
            "weekNumber": row.week_number,
            "status": row.status,
            "language": row.language,
            "reviewedBy": row.reviewed_by,
            "reviewedAt": row.reviewed_at.isoformat() if row.reviewed_at else None,
            "itemCount": len(items),
            "items": payload_items if reveal_answers else [],
        }
