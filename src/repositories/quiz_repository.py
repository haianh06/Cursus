"""Persistence for instructor-authored quizzes (per class/section)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db import models

QUESTION_TYPES = frozenset({"MULTIPLE_CHOICE", "TRUE_FALSE", "SHORT_ANSWER"})


class QuizRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def instructor_sections(self, instructor_id: str) -> list[models.CourseSection]:
        return (
            self._db.query(models.CourseSection)
            .filter_by(instructor_id=instructor_id)
            .all()
        )

    def get_section(self, section_id: str) -> models.CourseSection | None:
        return self._db.query(models.CourseSection).filter_by(id=section_id).first()

    def get_course(self, course_id: str) -> models.Course | None:
        return self._db.query(models.Course).filter_by(id=course_id).first()

    def course_lecture_chunks(self, course_id: str) -> list[tuple[models.DocumentChunk, models.Document]]:
        rows = (
            self._db.query(models.DocumentChunk, models.Document)
            .join(models.Document, models.Document.id == models.DocumentChunk.document_id)
            .filter(models.Document.course_id == course_id, models.Document.doc_type == "LECTURE")
            .order_by(models.Document.title.asc(), models.DocumentChunk.chunk_index.asc())
            .all()
        )
        return [(chunk, doc) for chunk, doc in rows]

    def section_student_count(self, section_id: str) -> int:
        return (
            self._db.query(models.Enrollment)
            .filter_by(section_id=section_id)
            .count()
        )

    def roster_for_section(self, section_id: str) -> list[models.User]:
        return (
            self._db.query(models.User)
            .join(models.Enrollment, models.Enrollment.student_id == models.User.id)
            .filter(models.Enrollment.section_id == section_id)
            .order_by(models.User.full_name)
            .all()
        )

    def list_for_sections(self, section_ids: list[str]) -> list[models.Quiz]:
        if not section_ids:
            return []
        return (
            self._db.query(models.Quiz)
            .filter(models.Quiz.section_id.in_(section_ids))
            .order_by(models.Quiz.due_date.asc().nullslast())
            .all()
        )

    def get(self, quiz_id: str) -> models.Quiz | None:
        return self._db.query(models.Quiz).filter_by(id=quiz_id).first()

    def add_quiz(
        self,
        *,
        section_id: str,
        title: str,
        description: str,
        time_limit_minutes: int,
        due_date: datetime | None,
        opens_at: datetime | None,
        created_by: str,
    ) -> models.Quiz:
        row = models.Quiz(
            id=f"quiz_{uuid.uuid4().hex[:12]}",
            section_id=section_id,
            title=title.strip(),
            description=description.strip(),
            time_limit_minutes=time_limit_minutes,
            due_date=due_date,
            opens_at=opens_at,
            max_points=0,
            created_by=created_by,
            is_published=False,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def delete_quiz(self, quiz: models.Quiz) -> None:
        self._db.delete(quiz)
        self._db.flush()

    def list_questions(self, quiz_id: str) -> list[models.QuizQuestion]:
        return (
            self._db.query(models.QuizQuestion)
            .filter_by(quiz_id=quiz_id)
            .order_by(models.QuizQuestion.order_index.asc())
            .all()
        )

    def get_question(self, question_id: str) -> models.QuizQuestion | None:
        return self._db.query(models.QuizQuestion).filter_by(id=question_id).first()

    def next_order_index(self, quiz_id: str) -> int:
        existing = self.list_questions(quiz_id)
        return (max((q.order_index for q in existing), default=-1)) + 1

    def add_question(
        self,
        *,
        quiz_id: str,
        question_text: str,
        question_type: str,
        correct_answer: str,
        options: list[str],
        points: float,
        order_index: int,
    ) -> models.QuizQuestion:
        row = models.QuizQuestion(
            id=f"qq_{uuid.uuid4().hex[:12]}",
            quiz_id=quiz_id,
            question_text=question_text.strip(),
            question_type=question_type,
            correct_answer=correct_answer,
            options=options,
            points=points,
            order_index=order_index,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def delete_question(self, question: models.QuizQuestion) -> None:
        self._db.delete(question)
        self._db.flush()

    def recompute_max_points(self, quiz: models.Quiz) -> None:
        total = sum(q.points for q in self.list_questions(quiz.id))
        quiz.max_points = total
        self._db.flush()

    def submissions_for_quiz(self, quiz_id: str) -> list[models.Submission]:
        return self._db.query(models.Submission).filter_by(quiz_id=quiz_id).all()

    def get_submission_for_student(self, quiz_id: str, student_id: str) -> models.Submission | None:
        return (
            self._db.query(models.Submission)
            .filter_by(quiz_id=quiz_id, student_id=student_id)
            .first()
        )

    def get_submission(self, submission_id: str) -> models.Submission | None:
        return self._db.query(models.Submission).filter_by(id=submission_id).first()

    def add_submission(
        self,
        *,
        quiz_id: str,
        student_id: str,
        content: dict,
        grading_status: str,
        grade: float,
        is_late: bool,
    ) -> models.Submission:
        row = models.Submission(
            id=f"sub_{uuid.uuid4().hex[:12]}",
            assignment_id=None,
            quiz_id=quiz_id,
            student_id=student_id,
            submitted_at=datetime.now(UTC).replace(tzinfo=None),
            content=content,
            grading_status=grading_status,
            grade=grade,
            is_late=is_late,
        )
        self._db.add(row)
        self._db.flush()
        return row

    def student_section_ids(self, student_id: str) -> list[str]:
        rows = (
            self._db.query(models.Enrollment.section_id)
            .filter_by(student_id=student_id)
            .distinct()
            .all()
        )
        return [row[0] for row in rows]

    def is_enrolled(self, student_id: str, section_id: str) -> bool:
        return (
            self._db.query(models.Enrollment)
            .filter_by(student_id=student_id, section_id=section_id)
            .first()
            is not None
        )

    def commit(self) -> None:
        self._db.commit()
