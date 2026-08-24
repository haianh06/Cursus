"""Instructor one-off in-class overlays (not PE/FE)."""

from __future__ import annotations

import logging
from datetime import date, datetime, time
from typing import Any

from src.academic.slots import campus_now, exam_week_bounds, term_bounds
from src.db.models import ClassActivity
from src.repositories.academic_term_repository import AcademicTermRepository
from src.repositories.class_activity_repository import ACTIVITY_KINDS, ClassActivityRepository

logger = logging.getLogger(__name__)

KIND_LABELS = {
    "ASSIGNMENT": "Assignment",
    "PROGRESS_TEST": "Progress Test",
    "LAB": "Lab",
    "OTHER": "Other",
}


class ClassActivityService:
    def __init__(
        self,
        repo: ClassActivityRepository,
        terms: AcademicTermRepository,
    ) -> None:
        self._repo = repo
        self._terms = terms

    def list_mine(
        self,
        *,
        user_id: str,
        role: str,
        start: date | None = None,
        end: date | None = None,
    ) -> list[dict[str, Any]]:
        course_ids = self._allowed_course_ids(user_id, role)
        rows = self._repo.list_for_courses(course_ids, start=start, end=end)
        courses = {course.id: course for course in self._terms.list_courses()}
        return [self._serialize(row, courses.get(row.course_id)) for row in rows]

    def create(
        self,
        *,
        user_id: str,
        role: str,
        course_id: str,
        activity_date: date,
        kind: str,
        title: str,
        opens_at: datetime | None = None,
        closes_at: datetime | None = None,
    ) -> dict[str, Any]:
        kind = kind.upper()
        if kind not in ACTIVITY_KINDS:
            raise ValueError("Activity kind must be ASSIGNMENT, PROGRESS_TEST, LAB, or OTHER")
        if kind == "OTHER" and not title.strip():
            raise ValueError("Title is required for Other activities")
        allowed = set(self._allowed_course_ids(user_id, role))
        if course_id not in allowed:
            raise PermissionError("You can only add activities for courses you teach")
        course = self._terms.get_course(course_id)
        if course is None:
            raise LookupError("Course not found")
        self._validate_date(activity_date)
        existing = self._repo.get_on_day(course_id, activity_date)
        if existing is not None:
            raise ValueError("This course already has an in-class activity on that date")
        opens_at, closes_at = self._resolve_window(activity_date, opens_at, closes_at)
        label = title.strip() or KIND_LABELS[kind]
        row = self._repo.add(
            course_id=course_id,
            activity_date=activity_date,
            kind=kind,
            title=label,
            created_by=user_id,
            opens_at=opens_at,
            closes_at=closes_at,
        )
        self._repo.commit()
        logger.info("class_activity_created id=%s course=%s date=%s", row.id, course.code, activity_date)
        return self._serialize(row, course)

    def update(
        self,
        *,
        user_id: str,
        role: str,
        activity_id: str,
        kind: str | None = None,
        title: str | None = None,
        activity_date: date | None = None,
        opens_at: datetime | None = None,
        closes_at: datetime | None = None,
    ) -> dict[str, Any]:
        row = self._require_owned(activity_id, user_id, role)
        if kind is not None:
            kind = kind.upper()
            if kind not in ACTIVITY_KINDS:
                raise ValueError("Activity kind must be ASSIGNMENT, PROGRESS_TEST, LAB, or OTHER")
            row.kind = kind
        if title is not None:
            row.title = title.strip()
        if activity_date is not None:
            self._validate_date(activity_date)
            clash = self._repo.get_on_day(row.course_id, activity_date)
            if clash is not None and clash.id != row.id:
                raise ValueError("This course already has an in-class activity on that date")
            row.activity_date = activity_date
        if opens_at is not None or closes_at is not None:
            next_opens = opens_at if opens_at is not None else row.opens_at
            next_closes = closes_at if closes_at is not None else row.closes_at
            next_opens, next_closes = self._resolve_window(row.activity_date, next_opens, next_closes)
            row.opens_at = next_opens
            row.closes_at = next_closes
        if row.kind == "OTHER" and not row.title:
            raise ValueError("Title is required for Other activities")
        if not row.title:
            row.title = KIND_LABELS.get(row.kind, row.kind)
        self._repo.commit()
        course = self._terms.get_course(row.course_id)
        return self._serialize(row, course)

    def delete(self, *, user_id: str, role: str, activity_id: str) -> None:
        row = self._require_owned(activity_id, user_id, role)
        self._repo.delete(row)
        self._repo.commit()

    def _allowed_course_ids(self, user_id: str, role: str) -> list[str]:
        value = str(getattr(role, "value", role)).upper()
        if value == "ADMIN":
            return [course.id for course in self._terms.list_courses()]
        if value == "STUDENT":
            return self._repo.student_course_ids(user_id)
        return self._repo.instructor_course_ids(user_id)

    def _require_owned(self, activity_id: str, user_id: str, role: str) -> ClassActivity:
        row = self._repo.get(activity_id)
        if row is None:
            raise LookupError("Class activity not found")
        allowed = set(self._allowed_course_ids(user_id, role))
        if row.course_id not in allowed:
            raise PermissionError("You can only edit activities for courses you teach")
        return row

    def _validate_date(self, activity_date: date) -> None:
        if activity_date.weekday() > 4:
            raise ValueError("In-class activities are only allowed Monday–Friday")
        term = self._terms.get_active()
        if term is None:
            return
        start, _end = term_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        exam_range = exam_week_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        if activity_date < start:
            raise ValueError(
                f"Activity date is before the academic term (earliest allowed date: {start.isoformat()})"
            )
        if exam_range and activity_date >= exam_range[0]:
            raise ValueError(
                f"In-class activities cannot be placed in exam weeks (must be before {exam_range[0].isoformat()})"
            )

    @staticmethod
    def _resolve_window(
        activity_date: date,
        opens_at: datetime | None,
        closes_at: datetime | None,
    ) -> tuple[datetime, datetime]:
        resolved_opens = opens_at or datetime.combine(activity_date, time.min)
        resolved_closes = closes_at or datetime.combine(activity_date, time.max.replace(microsecond=0))
        if resolved_opens >= resolved_closes:
            raise ValueError("The open time must be earlier than the close time")
        return resolved_opens, resolved_closes

    def get_scheduling_window(self) -> dict[str, Any] | None:
        term = self._terms.get_active()
        if term is None:
            return None
        start, end = term_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        exam_range = exam_week_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        return {
            "term_name": term.name,
            "term_start": start.isoformat(),
            "term_end": end.isoformat(),
            "exam_week_start": exam_range[0].isoformat() if exam_range else None,
            "last_activity_date": (exam_range[0] - date.resolution).isoformat() if exam_range else end.isoformat(),
        }

    @staticmethod
    def _serialize(row: ClassActivity, course: Any) -> dict[str, Any]:
        now = campus_now()
        status = "scheduled"
        if row.opens_at and now < row.opens_at:
            status = "scheduled"
        elif row.closes_at and now > row.closes_at:
            status = "closed"
        elif row.opens_at or row.closes_at:
            status = "open"
        return {
            "id": row.id,
            "course_id": row.course_id,
            "course_code": getattr(course, "code", None),
            "course_name": getattr(course, "name", None),
            "activity_date": row.activity_date.isoformat(),
            "kind": row.kind,
            "kind_label": KIND_LABELS.get(row.kind, row.kind),
            "title": row.title,
            "opens_at": row.opens_at.isoformat() if row.opens_at else None,
            "closes_at": row.closes_at.isoformat() if row.closes_at else None,
            "status": status,
        }
