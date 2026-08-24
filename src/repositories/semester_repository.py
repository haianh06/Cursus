"""Persistence for a student's semester setup (courses + weekly slots).

Tenant scoping is transitive via `student_id -> User.organization_id` for
the semester rows themselves. Course *catalog* reads (`list_catalog`,
`get_courses_by_ids`) are deliberately NOT filtered by organization_id —
`Course.code` carries a database-wide unique constraint (`src/db/models.py`),
so this schema only ever supports one shared course catalog, not a
per-org duplicate one. `src/api/admin.py`'s `AdminReadService.list_courses()`
already treats the catalog the same way (no org filter); this repository
follows that same, already-proven-live convention instead of introducing a
stricter rule the seed data doesn't actually satisfy (verified live: demo
accounts sit in `org_cursus_demo`, the Gate2 seed courses sit in
`org_fpt_university` — a real, pre-existing seed-data split that strict
catalog filtering here made visible as an empty catalog for the demo
student). The `organization_id` parameters are kept for signature stability
and potential future re-partitioning, but are currently unused for reads.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from src.db import models


class SemesterRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_catalog(self, organization_id: str | None) -> list[models.Course]:
        del organization_id  # see module docstring — catalog is shared, not per-org
        return self._db.query(models.Course).order_by(models.Course.code).all()

    def list_enrolled_courses(self, student_id: str) -> list[models.Course]:
        return (
            self._db.query(models.Course)
            .join(models.CourseSection, models.CourseSection.course_id == models.Course.id)
            .join(models.Enrollment, models.Enrollment.section_id == models.CourseSection.id)
            .filter(models.Enrollment.student_id == student_id)
            .distinct()
            .order_by(models.Course.code)
            .all()
        )

    def get_courses_by_ids(
        self, course_ids: list[str], organization_id: str | None
    ) -> list[models.Course]:
        del organization_id  # see module docstring — catalog is shared, not per-org
        if not course_ids:
            return []
        rows = (
            self._db.query(models.Course)
            .filter(models.Course.id.in_(course_ids))
            .all()
        )
        by_id = {row.id: row for row in rows}
        missing = [item for item in course_ids if item not in by_id]
        if missing:
            raise LookupError(f"Unknown course_ids: {', '.join(missing)}")
        return [by_id[item] for item in course_ids]

    def list_semesters(self, student_id: str) -> list[models.SemesterSetup]:
        return (
            self._db.query(models.SemesterSetup)
            .filter_by(student_id=student_id)
            .order_by(models.SemesterSetup.start_date.desc())
            .all()
        )

    def get_active(self, student_id: str) -> models.SemesterSetup | None:
        return (
            self._db.query(models.SemesterSetup)
            .filter_by(student_id=student_id, is_active=True)
            .order_by(models.SemesterSetup.created_at.desc())
            .first()
        )

    def get_owned(self, semester_id: str, student_id: str) -> models.SemesterSetup:
        row = (
            self._db.query(models.SemesterSetup)
            .filter_by(id=semester_id, student_id=student_id)
            .first()
        )
        if row is None:
            raise LookupError("Semester not found")
        return row

    def deactivate_all(self, student_id: str) -> None:
        rows = (
            self._db.query(models.SemesterSetup)
            .filter_by(student_id=student_id, is_active=True)
            .all()
        )
        for row in rows:
            row.is_active = False
        self._db.flush()

    def add_semester(
        self, *, student_id: str, name: str, start_date: date, end_date: date, is_active: bool
    ) -> models.SemesterSetup:
        row = models.SemesterSetup(
            id=f"sem_{uuid.uuid4().hex[:12]}",
            student_id=student_id,
            name=name.strip(),
            start_date=start_date,
            end_date=end_date,
            is_active=is_active,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self._db.add(row)
        self._db.flush()
        return row

    def add_course_link(self, semester_id: str, course_id: str) -> None:
        self._db.add(
            models.SemesterCourse(
                id=f"sc_{uuid.uuid4().hex[:12]}", semester_id=semester_id, course_id=course_id
            )
        )

    def add_week_slot(self, *, semester_id: str, weekday: int, slot_id: int, course_id: str) -> None:
        self._db.add(
            models.SemesterWeekSlot(
                id=f"ss_{uuid.uuid4().hex[:12]}",
                semester_id=semester_id,
                weekday=weekday,
                slot_id=slot_id,
                course_id=course_id,
            )
        )

    def add_exception(
        self, *, semester_id: str, kind: str, start_date: date, end_date: date, label: str
    ) -> None:
        self._db.add(
            models.SemesterException(
                id=f"sx_{uuid.uuid4().hex[:12]}",
                semester_id=semester_id,
                kind=kind,
                start_date=start_date,
                end_date=end_date,
                label=label.strip(),
            )
        )

    def replace_template(self, semester_id: str) -> None:
        (
            self._db.query(models.SemesterCourse)
            .filter_by(semester_id=semester_id)
            .delete(synchronize_session="fetch")
        )
        (
            self._db.query(models.SemesterWeekSlot)
            .filter_by(semester_id=semester_id)
            .delete(synchronize_session="fetch")
        )
        (
            self._db.query(models.SemesterException)
            .filter_by(semester_id=semester_id)
            .delete(synchronize_session="fetch")
        )
        self._db.flush()

    def first_instructor_id(self, organization_id: str | None) -> str:
        """An instructor from the *same org* to host auto-created sections.

        Never picks an instructor from another org — a cross-org pick would
        let a student's calendar leak into another tenant's roster.
        """
        instructor = (
            self._db.query(models.User)
            .filter(
                models.User.role.in_(["INSTRUCTOR", models.UserRole.INSTRUCTOR.value]),
                models.User.organization_id == organization_id,
            )
            .first()
        )
        if instructor is None:
            raise LookupError("No instructor account available in this organization")
        return instructor.id

    def get_or_create_section(
        self, *, semester_id: str, course: models.Course, instructor_id: str, term: str
    ) -> models.CourseSection:
        section_id = f"sec_sem_{semester_id[-10:]}_{course.code.lower()}"
        section = self._db.query(models.CourseSection).filter_by(id=section_id).first()
        if section:
            return section
        section = models.CourseSection(
            id=section_id,
            course_id=course.id,
            instructor_id=instructor_id,
            term=term[:32],
            section_code=f"SEM-{course.code}",
        )
        self._db.add(section)
        self._db.flush()
        return section

    def ensure_enrollment(self, *, student_id: str, section_id: str) -> None:
        existing = (
            self._db.query(models.Enrollment)
            .filter_by(student_id=student_id, section_id=section_id)
            .first()
        )
        if existing:
            return
        self._db.add(
            models.Enrollment(
                id=f"enr_sem_{uuid.uuid4().hex[:10]}",
                student_id=student_id,
                section_id=section_id,
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        self._db.flush()

    def delete_events(self, semester_id: str) -> None:
        (
            self._db.query(models.CalendarEvent)
            .filter_by(semester_setup_id=semester_id)
            .delete(synchronize_session="fetch")
        )
        self._db.flush()

    def add_lecture_event(
        self,
        *,
        semester_id: str,
        section_id: str,
        title: str,
        description: str,
        start_time: datetime,
        end_time: datetime,
    ) -> models.CalendarEvent:
        event = models.CalendarEvent(
            id=f"cal_sem_{uuid.uuid4().hex[:12]}",
            section_id=section_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            event_type="LECTURE",
            semester_setup_id=semester_id,
        )
        self._db.add(event)
        self._db.flush()
        return event

    # `SemesterSetup` has no ORM relationships declared on it (see
    # `src/db/models.py`) — children are always fetched explicitly here
    # rather than via `.courses` / `.week_slots` / `.exceptions` attributes.
    def list_course_links(self, semester_id: str) -> list[models.SemesterCourse]:
        return self._db.query(models.SemesterCourse).filter_by(semester_id=semester_id).all()

    def list_week_slots(self, semester_id: str) -> list[models.SemesterWeekSlot]:
        return self._db.query(models.SemesterWeekSlot).filter_by(semester_id=semester_id).all()

    def list_exceptions(self, semester_id: str) -> list[models.SemesterException]:
        return self._db.query(models.SemesterException).filter_by(semester_id=semester_id).all()

    def commit(self) -> None:
        self._db.commit()
