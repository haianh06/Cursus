"""Student semester setup: pick active courses + weekly time slots for a term.

Adapted from develop's `src/services/semester_service.py`. Org scope is
resolved once, transitively, from the acting student's own
`User.organization_id` and threaded through every repository call — never
accepted from the request body.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any

from src.db.models import CalendarEvent, Course, SemesterSetup
from src.repositories.academic_term_repository import AcademicTermRepository
from src.repositories.semester_repository import SemesterRepository
from src.services.academic.academic_calendar import exam_week_bounds, slot_datetimes, term_bounds
from src.services.academic.academic_term_service import AcademicTermService

logger = logging.getLogger(__name__)

MAX_COURSES = 8
KIND_HOLIDAY = "HOLIDAY"
KIND_EXAM_WEEK = "EXAM_WEEK"


class SemesterService:
    def __init__(self, repo: SemesterRepository, terms: AcademicTermRepository | None = None) -> None:
        self._repo = repo
        self._terms = terms or AcademicTermRepository(repo._db)
        self._term_service = AcademicTermService(self._terms)

    def catalog(self, *, organization_id: str | None) -> list[dict[str, str]]:
        return [
            {"id": course.id, "code": course.code, "name": course.name}
            for course in self._repo.list_catalog(organization_id)
        ]

    def status(self, *, student_id: str, organization_id: str | None) -> dict[str, Any]:
        active = self._repo.get_active(student_id)
        term = self._terms.get_active(organization_id)
        return {
            "required": active is None,
            "activeSemesterId": active.id if active else None,
            "termConfigured": term is not None,
            "term": self._term_service.serialize_term(term) if term else None,
        }

    def list_semesters(self, student_id: str) -> dict[str, Any]:
        rows = self._repo.list_semesters(student_id)
        active = next((row for row in rows if row.is_active), None)
        return {
            "active_id": active.id if active else None,
            "semesters": [self._serialize_row_with_children(row) for row in rows],
        }

    def _serialize_row_with_children(self, row: SemesterSetup) -> dict[str, Any]:
        return self._serialize_semester(
            row,
            course_ids=[link.course_id for link in self._repo.list_course_links(row.id)],
            weekly_slots=[
                {"weekday": s.weekday, "slot_id": s.slot_id, "course_id": s.course_id}
                for s in self._repo.list_week_slots(row.id)
            ],
            exceptions=[
                {
                    "kind": e.kind,
                    "start_date": e.start_date.isoformat(),
                    "end_date": e.end_date.isoformat(),
                    "label": e.label,
                }
                for e in self._repo.list_exceptions(row.id)
            ],
        )

    def get(self, *, student_id: str, semester_id: str) -> dict[str, Any]:
        semester = self._repo.get_owned(semester_id, student_id)
        return self._serialize_semester(
            semester,
            course_ids=[link.course_id for link in self._repo.list_course_links(semester.id)],
            weekly_slots=[
                {"weekday": s.weekday, "slot_id": s.slot_id, "course_id": s.course_id}
                for s in self._repo.list_week_slots(semester.id)
            ],
            exceptions=[
                {
                    "kind": e.kind,
                    "start_date": e.start_date.isoformat(),
                    "end_date": e.end_date.isoformat(),
                    "label": e.label,
                }
                for e in self._repo.list_exceptions(semester.id)
            ],
        )

    def create(
        self,
        *,
        student_id: str,
        organization_id: str | None,
        name: str,
        start_date: date,
        end_date: date,
        course_ids: list[str],
        weekly_slots: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
        require_term: bool = False,
    ) -> dict[str, Any]:
        name, start_date, end_date, exam_skip = self._resolve_calendar(
            organization_id=organization_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            require_term=require_term,
        )
        self._validate_payload(
            start_date=start_date,
            end_date=end_date,
            course_ids=course_ids,
            weekly_slots=weekly_slots,
            exceptions=exceptions,
        )
        self._assert_exam_slots(organization_id=organization_id, course_ids=course_ids)
        courses = self._repo.get_courses_by_ids(course_ids, organization_id)
        self._repo.deactivate_all(student_id)
        semester = self._repo.add_semester(
            student_id=student_id, name=name, start_date=start_date, end_date=end_date, is_active=True
        )
        self._attach_template(
            semester_id=semester.id, courses=courses, weekly_slots=weekly_slots, exceptions=exceptions
        )
        events = self.generate_weeks(
            semester, courses, weekly_slots, exceptions, organization_id=organization_id, exam_skip=exam_skip
        )
        self._repo.commit()
        logger.info("semester_created id=%s student=%s events=%s", semester.id, student_id, len(events))
        return {
            **self._serialize_semester(
                semester, course_ids=course_ids, weekly_slots=weekly_slots, exceptions=exceptions
            ),
            "events": events,
        }

    def update(
        self,
        *,
        student_id: str,
        organization_id: str | None,
        semester_id: str,
        name: str,
        start_date: date,
        end_date: date,
        course_ids: list[str],
        weekly_slots: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
        require_term: bool = False,
    ) -> dict[str, Any]:
        semester = self._repo.get_owned(semester_id, student_id)
        name, start_date, end_date, exam_skip = self._resolve_calendar(
            organization_id=organization_id,
            name=name,
            start_date=start_date,
            end_date=end_date,
            require_term=require_term,
        )
        self._validate_payload(
            start_date=start_date,
            end_date=end_date,
            course_ids=course_ids,
            weekly_slots=weekly_slots,
            exceptions=exceptions,
        )
        self._assert_exam_slots(organization_id=organization_id, course_ids=course_ids)
        courses = self._repo.get_courses_by_ids(course_ids, organization_id)
        semester.name = name.strip()
        semester.start_date = start_date
        semester.end_date = end_date
        self._repo.replace_template(semester.id)
        self._attach_template(
            semester_id=semester.id, courses=courses, weekly_slots=weekly_slots, exceptions=exceptions
        )
        events = self.generate_weeks(
            semester, courses, weekly_slots, exceptions, organization_id=organization_id, exam_skip=exam_skip
        )
        self._repo.commit()
        logger.info("semester_updated id=%s student=%s events=%s", semester.id, student_id, len(events))
        return {
            **self._serialize_semester(
                semester, course_ids=course_ids, weekly_slots=weekly_slots, exceptions=exceptions
            ),
            "events": events,
        }

    def generate_weeks(
        self,
        semester: SemesterSetup,
        courses: list[Course],
        weekly_slots: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
        *,
        organization_id: str | None,
        exam_skip: tuple[date, date] | None = None,
    ) -> list[dict[str, Any]]:
        self._repo.delete_events(semester.id)
        # No instructor is guessed here anymore (see migration
        # 20260909_section_instructor_nullable + admin_overview_service's
        # UNASSIGNED_SECTION work-queue source): a wizard-created section is
        # left unassigned until an admin picks a real instructor for it.
        course_by_id = {course.id: course for course in courses}
        section_by_course: dict[str, str] = {}
        for course in courses:
            section = self._repo.get_or_create_section(
                semester_id=semester.id, course=course, term=semester.name
            )
            self._repo.ensure_enrollment(student_id=semester.student_id, section_id=section.id)
            section_by_course[course.id] = section.id

        slots_by_day: dict[int, list[dict[str, Any]]] = {}
        for slot in weekly_slots:
            slots_by_day.setdefault(int(slot["weekday"]), []).append(slot)

        if exam_skip is None:
            exam_skip = self._exam_skip_from_term(organization_id)

        created: list[dict[str, Any]] = []
        day = semester.start_date
        while day <= semester.end_date:
            if day.weekday() <= 4 and not self._is_skipped(day, exceptions, exam_skip):
                for slot in slots_by_day.get(day.weekday(), []):
                    course = course_by_id[str(slot["course_id"])]
                    start_dt, end_dt = slot_datetimes(day, int(slot["slot_id"]))
                    event = self._repo.add_lecture_event(
                        semester_id=semester.id,
                        section_id=section_by_course[course.id],
                        title=f"{course.code} Lecture (Slot {int(slot['slot_id'])})",
                        description=f"{course.code} · {semester.name}",
                        start_time=start_dt,
                        end_time=end_dt,
                    )
                    created.append(self._serialize_event(event, course.code, int(slot["slot_id"])))
            day += timedelta(days=1)
        return created

    def _attach_template(
        self,
        *,
        semester_id: str,
        courses: list[Course],
        weekly_slots: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
    ) -> None:
        for course in courses:
            self._repo.add_course_link(semester_id, course.id)
        for slot in weekly_slots:
            self._repo.add_week_slot(
                semester_id=semester_id,
                weekday=int(slot["weekday"]),
                slot_id=int(slot["slot_id"]),
                course_id=str(slot["course_id"]),
            )
        for item in exceptions:
            self._repo.add_exception(
                semester_id=semester_id,
                kind=str(item["kind"]).upper(),
                start_date=item["start_date"],
                end_date=item["end_date"],
                label=str(item.get("label") or ""),
            )

    def _validate_payload(
        self,
        *,
        start_date: date,
        end_date: date,
        course_ids: list[str],
        weekly_slots: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
    ) -> None:
        if end_date < start_date:
            raise ValueError("end_date must be on or after start_date")
        unique_courses = list(dict.fromkeys(course_ids))
        if len(unique_courses) != len(course_ids):
            raise ValueError("course_ids must be unique")
        if not unique_courses or len(unique_courses) > MAX_COURSES:
            raise ValueError(f"Select between 1 and {MAX_COURSES} courses")
        from src.services.academic.academic_calendar import SLOT_TIMES

        seen: set[tuple[int, int]] = set()
        allowed = set(unique_courses)
        for slot in weekly_slots:
            weekday = int(slot["weekday"])
            slot_id = int(slot["slot_id"])
            if weekday < 0 or weekday > 4:
                raise ValueError("Class slots are only allowed Monday-Friday")
            if slot_id not in SLOT_TIMES:
                raise ValueError("Invalid slot_id")
            key = (weekday, slot_id)
            if key in seen:
                raise ValueError("Each weekday slot can hold only one course")
            seen.add(key)
            if str(slot["course_id"]) not in allowed:
                raise ValueError("Slot course must be one of the selected courses")
        for item in exceptions:
            kind = str(item["kind"]).upper()
            if kind not in {KIND_HOLIDAY, KIND_EXAM_WEEK}:
                raise ValueError("Exception kind must be HOLIDAY or EXAM_WEEK")
            if item["end_date"] < item["start_date"]:
                raise ValueError("Exception end_date must be on or after start_date")

    def _resolve_calendar(
        self,
        *,
        organization_id: str | None,
        name: str,
        start_date: date,
        end_date: date,
        require_term: bool,
    ) -> tuple[str, date, date, tuple[date, date] | None]:
        term = self._terms.get_active(organization_id)
        if term is None:
            if require_term:
                raise ValueError("Academic term is not configured")
            return name.strip(), start_date, end_date, None
        start, end = term_bounds(term.start_date, term.study_weeks, term.exam_weeks)
        return term.name, start, end, exam_week_bounds(term.start_date, term.study_weeks, term.exam_weeks)

    def _exam_skip_from_term(self, organization_id: str | None) -> tuple[date, date] | None:
        term = self._terms.get_active(organization_id)
        if term is None:
            return None
        return exam_week_bounds(term.start_date, term.study_weeks, term.exam_weeks)

    def _assert_exam_slots(self, *, organization_id: str | None, course_ids: list[str]) -> None:
        clashes = self._term_service.conflicts_for_student_courses(
            organization_id=organization_id, course_ids=course_ids
        )
        if clashes:
            raise ValueError(
                "Selected courses have overlapping exam slots. "
                "Ask Admin to move one exam, or pick a different course set."
            )

    @staticmethod
    def _is_skipped(
        day: date, exceptions: list[dict[str, Any]], exam_skip: tuple[date, date] | None = None
    ) -> bool:
        if exam_skip is not None and exam_skip[0] <= day <= exam_skip[1]:
            return True
        for item in exceptions:
            if item["start_date"] <= day <= item["end_date"]:
                return True
        return False

    @staticmethod
    def _serialize_event(event: CalendarEvent, course_code: str, slot_id: int) -> dict[str, Any]:
        day = event.start_time.date()
        return {
            "id": event.id,
            "course_code": course_code,
            "slot_id": slot_id,
            "date": day.isoformat(),
            "weekday": day.weekday(),
            "start": event.start_time.strftime("%H:%M"),
            "end": event.end_time.strftime("%H:%M"),
        }

    @staticmethod
    def _serialize_semester(
        row: SemesterSetup,
        *,
        course_ids: list[str],
        weekly_slots: list[dict[str, Any]],
        exceptions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "start_date": row.start_date.isoformat(),
            "end_date": row.end_date.isoformat(),
            "is_active": row.is_active,
            "course_ids": course_ids,
            "weekly_slots": weekly_slots,
            "exceptions": exceptions,
        }
