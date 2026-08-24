"""Persistence for org-scoped academic terms and course exam sessions.

`AcademicTerm` carries `organization_id` directly (it is the one "root"
table introduced by the semester/practice migration with no course/student
FK to inherit org scope through — see the migration docstring), so every
query here is filtered by an explicit `organization_id` argument. Never
trust a client-supplied org id; callers resolve it from the acting
admin/instructor's own `User.organization_id` (same pattern as commit
0dc036e's `student_mock_data_service.py` / `timetable_service.py` fixes).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from src.db import models

EXAM_KINDS = frozenset({"MIDTERM", "FINAL", "PROGRESS_TEST"})


class AcademicTermRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_active(self, organization_id: str | None) -> models.AcademicTerm | None:
        return (
            self._db.query(models.AcademicTerm)
            .filter_by(organization_id=organization_id, is_active=True)
            .order_by(models.AcademicTerm.created_at.desc())
            .first()
        )

    def get_term(self, term_id: str, organization_id: str | None) -> models.AcademicTerm | None:
        return (
            self._db.query(models.AcademicTerm)
            .filter_by(id=term_id, organization_id=organization_id)
            .first()
        )

    def list_terms(self, organization_id: str | None) -> list[models.AcademicTerm]:
        return (
            self._db.query(models.AcademicTerm)
            .filter_by(organization_id=organization_id)
            .order_by(models.AcademicTerm.created_at.desc())
            .all()
        )

    def upsert_active(
        self,
        *,
        organization_id: str | None,
        name: str,
        start_date: date,
        study_weeks: int,
        exam_weeks: int,
    ) -> models.AcademicTerm:
        row = self.get_active(organization_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        if row is None:
            row = models.AcademicTerm(
                id=f"term_{uuid.uuid4().hex[:12]}",
                organization_id=organization_id,
                name=name.strip(),
                start_date=start_date,
                study_weeks=study_weeks,
                exam_weeks=exam_weeks,
                is_active=True,
                created_at=now,
            )
            self._db.add(row)
        else:
            row.name = name.strip()
            row.start_date = start_date
            row.study_weeks = study_weeks
            row.exam_weeks = exam_weeks
        self._db.flush()
        return row

    def list_exams(self, term_id: str) -> list[models.CourseExam]:
        return self._db.query(models.CourseExam).filter_by(term_id=term_id).all()

    def get_exam(self, exam_id: str) -> models.CourseExam | None:
        return self._db.query(models.CourseExam).filter_by(id=exam_id).first()

    def list_sessions(self, exam_id: str) -> list[models.CourseExamSession]:
        """`CourseExam` has no `.sessions` ORM relationship declared — always
        fetch sessions through this explicit query, never an attribute."""
        return self._db.query(models.CourseExamSession).filter_by(exam_id=exam_id).all()

    def sessions_in_range_for_courses(
        self, course_ids: list[str], start_date: date, end_date: date
    ) -> list[tuple[models.CourseExamSession, models.CourseExam]]:
        """Exam sessions for the given courses whose date falls in
        ``[start_date, end_date]`` inclusive — used by `lecture_plan_service`
        to fold exam blocks into a student's week alongside class sessions."""
        if not course_ids:
            return []
        return (
            self._db.query(models.CourseExamSession, models.CourseExam)
            .join(models.CourseExam, models.CourseExam.id == models.CourseExamSession.exam_id)
            .filter(
                models.CourseExam.course_id.in_(course_ids),
                models.CourseExamSession.exam_date >= start_date,
                models.CourseExamSession.exam_date <= end_date,
            )
            .all()
        )

    def get_or_create_exam(self, *, term_id: str, course_id: str, kind: str) -> models.CourseExam:
        kind = kind.upper()
        row = (
            self._db.query(models.CourseExam)
            .filter_by(term_id=term_id, course_id=course_id, kind=kind)
            .first()
        )
        if row is None:
            row = models.CourseExam(
                id=f"exam_{uuid.uuid4().hex[:12]}",
                term_id=term_id,
                course_id=course_id,
                kind=kind,
            )
            self._db.add(row)
            self._db.flush()
        return row

    def replace_sessions(self, exam: models.CourseExam, sessions: list[dict]) -> models.CourseExam:
        (
            self._db.query(models.CourseExamSession)
            .filter_by(exam_id=exam.id)
            .delete(synchronize_session="fetch")
        )
        self._db.flush()
        for index, item in enumerate(sessions, start=1):
            self._db.add(
                models.CourseExamSession(
                    id=f"exs_{uuid.uuid4().hex[:12]}",
                    exam_id=exam.id,
                    exam_date=item["exam_date"],
                    slot_id=int(item["slot_id"]),
                    label=str(item.get("label") or f"Ca {index}").strip() or f"Ca {index}",
                )
            )
        self._db.flush()
        return self.get_exam(exam.id) or exam

    def delete_exam(self, exam: models.CourseExam) -> None:
        self._db.delete(exam)
        self._db.flush()

    def list_courses(self, organization_id: str | None) -> list[models.Course]:
        # Catalog is shared, not per-org — see semester_repository.py's module
        # docstring (Course.code has a DB-wide unique constraint). Verified
        # live: seed courses and the caller's own org can genuinely differ.
        del organization_id
        return self._db.query(models.Course).order_by(models.Course.code).all()

    def get_course(self, course_id: str, organization_id: str | None) -> models.Course | None:
        del organization_id
        return self._db.query(models.Course).filter(models.Course.id == course_id).first()

    def students_taking_course(self, course_id: str) -> list[str]:
        rows = (
            self._db.query(models.SemesterSetup.student_id)
            .join(models.SemesterCourse, models.SemesterCourse.semester_id == models.SemesterSetup.id)
            .filter(
                models.SemesterSetup.is_active.is_(True),
                models.SemesterCourse.course_id == course_id,
            )
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def student_course_ids(self, student_id: str) -> list[str]:
        semester = (
            self._db.query(models.SemesterSetup)
            .filter_by(student_id=student_id, is_active=True)
            .first()
        )
        if semester is None:
            return []
        # `SemesterSetup` has no `.courses` ORM relationship (see model
        # comment in src/db/models.py) — query the link table explicitly.
        rows = (
            self._db.query(models.SemesterCourse.course_id)
            .filter_by(semester_id=semester.id)
            .all()
        )
        return [row[0] for row in rows]

    def add_class_activity(
        self,
        *,
        course_id: str,
        activity_date: date,
        kind: str,
        title: str,
        created_by: str,
    ) -> models.ClassActivity:
        row = models.ClassActivity(
            id=f"cact_{uuid.uuid4().hex[:12]}",
            course_id=course_id,
            activity_date=activity_date,
            kind=kind.upper(),
            title=title.strip(),
            created_by=created_by,
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        self._db.add(row)
        self._db.flush()
        return row

    def list_class_activities(
        self,
        *,
        course_id: str,
        organization_id: str | None,
    ) -> list[models.ClassActivity]:
        # Course catalog is shared, not per-org (see list_courses docstring
        # above) — access is bounded by the course existing at all
        # (AcademicTermService._require_course) plus, for non-admin callers,
        # AcademicTermService.log_activity's instructor_teaches_course check.
        del organization_id
        return (
            self._db.query(models.ClassActivity)
            .filter(models.ClassActivity.course_id == course_id)
            .order_by(models.ClassActivity.activity_date.desc())
            .all()
        )

    def instructor_teaches_course(self, *, instructor_id: str, course_id: str) -> bool:
        return (
            self._db.query(models.CourseSection.id)
            .filter_by(instructor_id=instructor_id, course_id=course_id)
            .first()
            is not None
        )

    def rollback(self) -> None:
        self._db.rollback()

    def commit(self) -> None:
        self._db.commit()
