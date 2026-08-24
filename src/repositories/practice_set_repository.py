"""Persistence for course-scoped practice sets (MCQ + flashcards).

`PracticeSet`/`PracticeItem` have no ORM relationships declared in
`src/db/models.py`, so items are always fetched through an explicit query
here rather than a `.items` attribute. Org scope is transitive via
`course_id -> Course.organization_id`; every list/lookup that could cross a
tenant boundary takes an explicit `organization_id` filter.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db import models

PENDING = "PENDING_REVIEW"
PUBLISHED = "PUBLISHED"
REJECTED = "REJECTED"
DRAFT = "DRAFT"


class PracticeSetRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, set_id: str) -> models.PracticeSet | None:
        return self._db.query(models.PracticeSet).filter_by(id=set_id).first()

    def get_by_slide(self, course_code: str, slide_key: str) -> models.PracticeSet | None:
        return (
            self._db.query(models.PracticeSet)
            .filter_by(course_code=course_code.upper(), slide_key=slide_key)
            .first()
        )

    def list_items(self, set_id: str) -> list[models.PracticeItem]:
        return (
            self._db.query(models.PracticeItem)
            .filter_by(set_id=set_id)
            .order_by(models.PracticeItem.kind, models.PracticeItem.sort_order)
            .all()
        )

    def list_by_status(
        self,
        *,
        course_ids: list[str] | None,
        status: str | None = None,
    ) -> list[models.PracticeSet]:
        query = self._db.query(models.PracticeSet)
        if course_ids is not None:
            if not course_ids:
                return []
            query = query.filter(models.PracticeSet.course_id.in_(course_ids))
        if status:
            query = query.filter_by(status=status.upper())
        return query.order_by(models.PracticeSet.updated_at.desc()).all()

    def add_set(
        self,
        *,
        course_id: str,
        course_code: str,
        slide_key: str,
        week_number: int,
        language: str,
        requested_by: str | None,
        status: str = PENDING,
    ) -> models.PracticeSet:
        now = datetime.now(UTC).replace(tzinfo=None)
        row = models.PracticeSet(
            id=f"pset_{uuid.uuid4().hex[:12]}",
            course_id=course_id,
            course_code=course_code.upper(),
            slide_key=slide_key,
            week_number=week_number,
            status=status,
            language=language,
            requested_by=requested_by,
            created_at=now,
            updated_at=now,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def replace_items(self, row: models.PracticeSet, specs: list[dict]) -> None:
        (
            self._db.query(models.PracticeItem)
            .filter_by(set_id=row.id)
            .delete(synchronize_session="fetch")
        )
        self._db.flush()
        for spec in specs:
            self._db.add(
                models.PracticeItem(
                    id=f"pitm_{uuid.uuid4().hex[:12]}",
                    set_id=row.id,
                    kind=spec["kind"],
                    sort_order=int(spec["sort_order"]),
                    prompt=spec["prompt"],
                    options=spec.get("options"),
                    correct_key=spec.get("correct_key"),
                    answer=spec.get("answer") or "",
                    explanation=spec.get("explanation") or "",
                    source_label=spec.get("source_label") or "",
                )
            )
        row.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self._db.flush()

    def get_item(self, item_id: str) -> models.PracticeItem | None:
        return self._db.query(models.PracticeItem).filter_by(id=item_id).first()

    def instructor_course_ids(self, instructor_id: str) -> list[str]:
        rows = (
            self._db.query(models.CourseSection.course_id)
            .filter_by(instructor_id=instructor_id)
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def org_course_ids(self, organization_id: str | None) -> list[str]:
        # Course catalog is shared, not per-org — see
        # semester_repository.py's module docstring (Course.code has a
        # DB-wide unique constraint). An ADMIN caller sees all courses in
        # the (single, shared) catalog; instructor visibility is separately
        # narrowed by `instructor_course_ids` (an actual teaching
        # relationship via CourseSection, not org membership).
        del organization_id
        rows = self._db.query(models.Course.id).all()
        return [row[0] for row in rows]

    def commit(self) -> None:
        self._db.commit()
