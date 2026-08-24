"""Admin academic calendar: term weeks, course exam sessions, class activities.

Org-scoped throughout: `AcademicTerm` carries `organization_id` directly, so
every entry point takes the caller's own `organization_id` (resolved by the
API layer from `current_user.organization_id`, never from the request body)
and every course/exam lookup is filtered through it.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from src.db.models import AcademicTerm, ClassActivity, CourseExam
from src.repositories.academic_term_repository import EXAM_KINDS, AcademicTermRepository
from src.services.academic.academic_calendar import SLOT_TIMES, exam_week_bounds, term_bounds

logger = logging.getLogger(__name__)

ACTIVITY_KINDS = frozenset({"LECTURE_HELD", "CANCELLED", "MAKEUP", "NOTE"})


class AcademicTermService:
    def __init__(self, repo: AcademicTermRepository) -> None:
        self._repo = repo

    # ── Terms ────────────────────────────────────────────────────────────
    def get_active(self, organization_id: str | None) -> dict[str, Any] | None:
        term = self._repo.get_active(organization_id)
        return self.serialize_term(term) if term else None

    def list_terms(self, organization_id: str | None) -> list[dict[str, Any]]:
        return [self.serialize_term(term) for term in self._repo.list_terms(organization_id)]

    def upsert_term(
        self,
        *,
        organization_id: str | None,
        name: str,
        start_date: date,
        study_weeks: int = 10,
        exam_weeks: int = 2,
    ) -> dict[str, Any]:
        if not name.strip():
            raise ValueError("Term name is required")
        if study_weeks < 1 or study_weeks > 20:
            raise ValueError("study_weeks must be between 1 and 20")
        if exam_weeks < 1 or exam_weeks > 6:
            raise ValueError("exam_weeks must be between 1 and 6")
        term = self._repo.upsert_active(
            organization_id=organization_id,
            name=name,
            start_date=start_date,
            study_weeks=study_weeks,
            exam_weeks=exam_weeks,
        )
        self._repo.commit()
        logger.info("academic_term_upserted id=%s org=%s", term.id, organization_id)
        return self.serialize_term(term)

    # ── Exams ────────────────────────────────────────────────────────────
    def list_exams(self, organization_id: str | None) -> dict[str, Any]:
        term = self._require_term(organization_id)
        exams = self._repo.list_exams(term.id)
        courses = {course.id: course for course in self._repo.list_courses(organization_id)}
        return {
            "term": self.serialize_term(term),
            "courses": [
                {"id": course.id, "code": course.code, "name": course.name}
                for course in sorted(courses.values(), key=lambda item: item.code)
            ],
            "exams": [self._serialize_exam(exam, courses.get(exam.course_id)) for exam in exams],
            "slots": [
                {
                    "id": slot_id,
                    "start": f"{times[0]:02d}:{times[1]:02d}",
                    "end": f"{times[2]:02d}:{times[3]:02d}",
                }
                for slot_id, times in SLOT_TIMES.items()
            ],
        }

    def upsert_exam(
        self,
        *,
        organization_id: str | None,
        course_id: str,
        kind: str,
        sessions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        term = self._require_term(organization_id)
        kind = kind.upper()
        if kind not in EXAM_KINDS:
            raise ValueError(f"Exam kind must be one of {sorted(EXAM_KINDS)}")
        course = self._require_course(course_id, organization_id)
        if not sessions:
            raise ValueError("At least one exam session is required")
        exam_range = exam_week_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        if exam_range is None:
            raise ValueError("Term has no exam weeks")
        exam_start, exam_end = exam_range
        cleaned: list[dict[str, Any]] = []
        seen: set[tuple[date, int]] = set()
        for index, item in enumerate(sessions, start=1):
            exam_date = item["exam_date"]
            slot_id = int(item["slot_id"])
            if slot_id not in SLOT_TIMES:
                raise ValueError("Invalid slot_id")
            if exam_date.weekday() > 5:
                raise ValueError("Exams can only be scheduled Monday-Saturday")
            if exam_date < exam_start or exam_date > exam_end:
                raise ValueError("Exam date must fall in the term exam weeks")
            key = (exam_date, slot_id)
            if key in seen:
                raise ValueError("Duplicate session on the same date and slot")
            seen.add(key)
            cleaned.append(
                {
                    "exam_date": exam_date,
                    "slot_id": slot_id,
                    "label": str(item.get("label") or f"Ca {index}").strip(),
                }
            )
        exam = self._repo.get_or_create_exam(term_id=term.id, course_id=course.id, kind=kind)
        exam = self._repo.replace_sessions(exam, cleaned)
        conflicts = self._conflicts_for_exam(term, exam)
        if conflicts:
            self._repo.rollback()
            raise ValueError(self._conflict_message(conflicts))
        self._repo.commit()
        return self._serialize_exam(exam, course)

    def delete_exam(self, *, organization_id: str | None, exam_id: str) -> None:
        exam = self._require_exam(exam_id, organization_id)
        self._repo.delete_exam(exam)
        self._repo.commit()

    def conflicts_for_student_courses(
        self, *, organization_id: str | None, course_ids: list[str]
    ) -> list[dict[str, Any]]:
        term = self._repo.get_active(organization_id)
        if term is None or not course_ids:
            return []
        wanted = set(course_ids)
        occupied: dict[tuple[date, int], list[dict[str, Any]]] = {}
        for exam in self._repo.list_exams(term.id):
            if exam.course_id not in wanted:
                continue
            session = self._default_session(exam)
            if session is None:
                continue
            occupied.setdefault((session.exam_date, session.slot_id), []).append(
                {
                    "course_id": exam.course_id,
                    "kind": exam.kind,
                    "date": session.exam_date.isoformat(),
                    "slot_id": session.slot_id,
                }
            )
        clashes: list[dict[str, Any]] = []
        for items in occupied.values():
            if len(items) > 1:
                clashes.extend(items)
        return clashes

    # ── Class activities (instructor logs lecture held/cancelled/makeup) ──
    def log_class_activity(
        self,
        *,
        organization_id: str | None,
        instructor_id: str,
        role: str,
        course_id: str,
        activity_date: date,
        kind: str,
        title: str = "",
    ) -> dict[str, Any]:
        kind = kind.upper()
        if kind not in ACTIVITY_KINDS:
            raise ValueError(f"Activity kind must be one of {sorted(ACTIVITY_KINDS)}")
        course = self._require_course(course_id, organization_id)
        role_value = str(getattr(role, "value", role)).upper()
        if role_value != "ADMIN" and not self._repo.instructor_teaches_course(
            instructor_id=instructor_id, course_id=course.id
        ):
            raise PermissionError("You can only log activity for courses you teach")
        row = self._repo.add_class_activity(
            course_id=course.id,
            activity_date=activity_date,
            kind=kind,
            title=title,
            created_by=instructor_id,
        )
        self._repo.commit()
        return self._serialize_activity(row, course)

    def list_class_activities(
        self, *, organization_id: str | None, course_id: str, instructor_id: str, role: Any
    ) -> list[dict[str, Any]]:
        course = self._require_course(course_id, organization_id)
        role_value = str(getattr(role, "value", role)).upper()
        if role_value != "ADMIN" and not self._repo.instructor_teaches_course(
            instructor_id=instructor_id, course_id=course.id
        ):
            raise PermissionError("You can only view activity for courses you teach")
        rows = self._repo.list_class_activities(course_id=course.id, organization_id=organization_id)
        return [self._serialize_activity(row, course) for row in rows]

    # ── internals ────────────────────────────────────────────────────────
    def _conflicts_for_exam(self, term: AcademicTerm, exam: CourseExam) -> list[dict[str, Any]]:
        session = self._default_session(exam)
        if session is None:
            return []
        students = self._repo.students_taking_course(exam.course_id)
        if not students:
            return []
        others = [item for item in self._repo.list_exams(term.id) if item.id != exam.id]
        conflicts: list[dict[str, Any]] = []
        for student_id in students:
            taking = set(self._repo.student_course_ids(student_id))
            for other in others:
                if other.course_id not in taking:
                    continue
                other_session = self._default_session(other)
                if other_session is None:
                    continue
                if (
                    other_session.exam_date == session.exam_date
                    and other_session.slot_id == session.slot_id
                ):
                    conflicts.append(
                        {
                            "student_id": student_id,
                            "course_id": other.course_id,
                            "kind": other.kind,
                            "date": session.exam_date.isoformat(),
                            "slot_id": session.slot_id,
                        }
                    )
        return conflicts

    def _default_session(self, exam: CourseExam):
        sessions = sorted(self._repo.list_sessions(exam.id), key=lambda item: (item.label, item.id))
        return sessions[0] if sessions else None

    @staticmethod
    def _conflict_message(conflicts: list[dict[str, Any]]) -> str:
        first = conflicts[0]
        return (
            "Exam conflict: a student cannot sit two exams in the same slot "
            f"({first['kind']} vs another exam on {first['date']} slot {first['slot_id']})"
        )

    def _require_term(self, organization_id: str | None) -> AcademicTerm:
        term = self._repo.get_active(organization_id)
        if term is None:
            raise LookupError("Academic term is not configured")
        return term

    def _require_course(self, course_id: str, organization_id: str | None):
        course = self._repo.get_course(course_id, organization_id)
        if course is None:
            raise LookupError("Course not found")
        return course

    def _require_exam(self, exam_id: str, organization_id: str | None) -> CourseExam:
        exam = self._repo.get_exam(exam_id)
        if exam is None:
            raise LookupError("Exam not found")
        # Org boundary: the exam's term must belong to the caller's org.
        term = self._repo.get_term(exam.term_id, organization_id)
        if term is None:
            raise LookupError("Exam not found")
        return exam

    @staticmethod
    def serialize_term(term: AcademicTerm) -> dict[str, Any]:
        start, end = term_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        exam_range = exam_week_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        return {
            "id": term.id,
            "name": term.name,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "study_weeks": term.study_weeks,
            "exam_weeks": term.exam_weeks,
            "exam_start": exam_range[0].isoformat() if exam_range else None,
            "exam_end": exam_range[1].isoformat() if exam_range else None,
            "is_active": term.is_active,
        }

    def _serialize_exam(self, exam: CourseExam, course: Any) -> dict[str, Any]:
        sessions = sorted(self._repo.list_sessions(exam.id), key=lambda item: (item.label, item.id))
        return {
            "id": exam.id,
            "course_id": exam.course_id,
            "course_code": getattr(course, "code", None),
            "course_name": getattr(course, "name", None),
            "kind": exam.kind,
            "sessions": [
                {
                    "id": item.id,
                    "exam_date": item.exam_date.isoformat(),
                    "slot_id": item.slot_id,
                    "label": item.label,
                }
                for item in sessions
            ],
        }

    @staticmethod
    def _serialize_activity(row: ClassActivity, course: Any) -> dict[str, Any]:
        return {
            "id": row.id,
            "course_id": row.course_id,
            "course_code": getattr(course, "code", None),
            "activity_date": row.activity_date.isoformat(),
            "kind": row.kind,
            "title": row.title,
            "created_by": row.created_by,
            "created_at": row.created_at.isoformat(),
        }
