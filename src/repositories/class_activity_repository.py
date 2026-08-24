"""Persistence for instructor in-class activity overlays."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from src.db import models

ACTIVITY_KINDS = frozenset({"ASSIGNMENT", "PROGRESS_TEST", "LAB", "OTHER"})


class ClassActivityRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def instructor_course_ids(self, instructor_id: str) -> list[str]:
        rows = (
            self._db.query(models.CourseSection.course_id)
            .filter_by(instructor_id=instructor_id)
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def student_course_ids(self, student_id: str) -> list[str]:
        rows = (
            self._db.query(models.CourseSection.course_id)
            .join(models.Enrollment, models.Enrollment.section_id == models.CourseSection.id)
            .filter(models.Enrollment.student_id == student_id)
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def list_for_courses(
        self,
        course_ids: list[str],
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> list[models.ClassActivity]:
        if not course_ids:
            return []
        query = self._db.query(models.ClassActivity).filter(
            models.ClassActivity.course_id.in_(course_ids)
        )
        if start is not None:
            query = query.filter(models.ClassActivity.activity_date >= start)
        if end is not None:
            query = query.filter(models.ClassActivity.activity_date <= end)
        return query.order_by(models.ClassActivity.activity_date.asc()).all()

    def get(self, activity_id: str) -> models.ClassActivity | None:
        return self._db.query(models.ClassActivity).filter_by(id=activity_id).first()

    def get_on_day(self, course_id: str, activity_date: date) -> models.ClassActivity | None:
        return (
            self._db.query(models.ClassActivity)
            .filter_by(course_id=course_id, activity_date=activity_date)
            .first()
        )

    def add(
        self,
        *,
        course_id: str,
        activity_date: date,
        kind: str,
        title: str,
        created_by: str,
        opens_at: datetime | None = None,
        closes_at: datetime | None = None,
    ) -> models.ClassActivity:
        row = models.ClassActivity(
            id=f"act_{uuid.uuid4().hex[:12]}",
            course_id=course_id,
            activity_date=activity_date,
            kind=kind.upper(),
            title=title.strip(),
            opens_at=opens_at,
            closes_at=closes_at,
            created_by=created_by,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self._db.add(row)
        self._db.flush()
        return row

    def delete(self, row: models.ClassActivity) -> None:
        self._db.delete(row)
        self._db.flush()

    def commit(self) -> None:
        self._db.commit()
