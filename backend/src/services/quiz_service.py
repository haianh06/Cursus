"""Instructor-authored quizzes: create per class, question bank, auto-grading
for objective questions, per-student progress tracking (thay the cho luong
'Duyet bo on tap' AI-sinh + duyet truoc do)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from src.academic.slots import campus_now
from src.db.models import Quiz, QuizQuestion, Submission
from src.repositories.quiz_repository import QUESTION_TYPES, QuizRepository
from src.services.quiz_generator import generate_questions as _generate_questions


class QuizService:
    def __init__(self, repo: QuizRepository) -> None:
        self._repo = repo

    # ---------------------------------------------------------------- classes

    def list_my_classes(self, *, instructor_id: str) -> list[dict[str, Any]]:
        sections = self._repo.instructor_sections(instructor_id)
        out = []
        for section in sections:
            course = self._repo.get_course(section.course_id)
            out.append(
                {
                    "sectionId": section.id,
                    "courseId": section.course_id,
                    "courseCode": getattr(course, "code", None),
                    "courseName": getattr(course, "name", None),
                    "sectionCode": section.section_code,
                    "term": section.term,
                    "studentCount": self._repo.section_student_count(section.id),
                }
            )
        return out

    # ------------------------------------------------------------------ quiz

    def list_mine(self, *, instructor_id: str, section_id: str | None = None) -> list[dict[str, Any]]:
        sections = self._repo.instructor_sections(instructor_id)
        section_ids = [s.id for s in sections]
        if section_id:
            if section_id not in section_ids:
                return []
            section_ids = [section_id]
        quizzes = self._repo.list_for_sections(section_ids)
        sections_by_id = {s.id: s for s in sections}
        return [self._serialize_summary(q, sections_by_id.get(q.section_id)) for q in quizzes]

    def create(
        self,
        *,
        instructor_id: str,
        section_id: str,
        title: str,
        description: str,
        time_limit_minutes: int,
        due_date: datetime | None,
        opens_at: datetime | None,
    ) -> dict[str, Any]:
        section = self._require_owned_section(instructor_id, section_id)
        if not title.strip():
            raise ValueError("Quiz title is required")
        if opens_at and due_date and opens_at >= due_date:
            raise ValueError("The open time must be earlier than the due date")
        quiz = self._repo.add_quiz(
            section_id=section.id,
            title=title,
            description=description,
            time_limit_minutes=time_limit_minutes,
            due_date=due_date,
            opens_at=opens_at,
            created_by=instructor_id,
        )
        self._repo.commit()
        return self._serialize_detail(quiz, section)

    def get_for_instructor(self, *, instructor_id: str, quiz_id: str) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        return self._serialize_detail(quiz, section)

    def update(
        self,
        *,
        instructor_id: str,
        quiz_id: str,
        title: str | None,
        description: str | None,
        time_limit_minutes: int | None,
        due_date: datetime | None,
        opens_at: datetime | None,
    ) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        if title is not None:
            if not title.strip():
                raise ValueError("Quiz title is required")
            quiz.title = title.strip()
        if description is not None:
            quiz.description = description.strip()
        if time_limit_minutes is not None:
            quiz.time_limit_minutes = time_limit_minutes
        if due_date is not None:
            quiz.due_date = due_date
        if opens_at is not None:
            quiz.opens_at = opens_at
        if quiz.opens_at and quiz.due_date and quiz.opens_at >= quiz.due_date:
            raise ValueError("The open time must be earlier than the due date")
        self._repo.commit()
        return self._serialize_detail(quiz, section)

    def delete(self, *, instructor_id: str, quiz_id: str) -> None:
        quiz, _section = self._require_owned_quiz(instructor_id, quiz_id)
        self._repo.delete_quiz(quiz)
        self._repo.commit()

    def set_published(self, *, instructor_id: str, quiz_id: str, is_published: bool) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        if is_published and not self._repo.list_questions(quiz.id):
            raise ValueError("Add at least one question before assigning this quiz")
        quiz.is_published = is_published
        self._repo.commit()
        return self._serialize_detail(quiz, section)

    # -------------------------------------------------------------- questions

    def add_question(
        self,
        *,
        instructor_id: str,
        quiz_id: str,
        question_text: str,
        question_type: str,
        correct_answer: str,
        options: list[str],
        points: float,
    ) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        if not question_text.strip():
            raise ValueError("Question text is required")
        question_type, correct_answer, options = self._validate_question(
            question_type, correct_answer, options
        )
        order_index = self._repo.next_order_index(quiz.id)
        self._repo.add_question(
            quiz_id=quiz.id,
            question_text=question_text,
            question_type=question_type,
            correct_answer=correct_answer,
            options=options,
            points=points,
            order_index=order_index,
        )
        self._repo.recompute_max_points(quiz)
        self._repo.commit()
        return self._serialize_detail(quiz, section)

    def generate_with_ai(self, *, instructor_id: str, quiz_id: str, count: int) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        chunks = self._repo.course_lecture_chunks(section.course_id)
        if not chunks:
            raise ValueError("This course has no lecture material to generate questions from yet")
        generated = _generate_questions(chunks, count)
        if not generated:
            raise ValueError("Could not generate any questions from this course's material")
        order_index = self._repo.next_order_index(quiz.id)
        for item in generated:
            self._repo.add_question(
                quiz_id=quiz.id,
                question_text=item["question_text"],
                question_type=item["question_type"],
                correct_answer=item["correct_answer"],
                options=item["options"],
                points=item["points"],
                order_index=order_index,
            )
            order_index += 1
        self._repo.recompute_max_points(quiz)
        self._repo.commit()
        return self._serialize_detail(quiz, section)

    def update_question(
        self,
        *,
        instructor_id: str,
        quiz_id: str,
        question_id: str,
        question_text: str,
        question_type: str,
        correct_answer: str,
        options: list[str],
        points: float,
    ) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        question = self._repo.get_question(question_id)
        if question is None or question.quiz_id != quiz.id:
            raise LookupError("Question not found")
        if not question_text.strip():
            raise ValueError("Question text is required")
        question_type, correct_answer, options = self._validate_question(
            question_type, correct_answer, options
        )
        question.question_text = question_text.strip()
        question.question_type = question_type
        question.correct_answer = correct_answer
        question.options = options
        question.points = points
        self._repo.recompute_max_points(quiz)
        self._repo.commit()
        return self._serialize_detail(quiz, section)

    def delete_question(self, *, instructor_id: str, quiz_id: str, question_id: str) -> None:
        quiz, _section = self._require_owned_quiz(instructor_id, quiz_id)
        question = self._repo.get_question(question_id)
        if question is None or question.quiz_id != quiz.id:
            raise LookupError("Question not found")
        self._repo.delete_question(question)
        self._repo.recompute_max_points(quiz)
        self._repo.commit()

    def reorder_questions(
        self, *, instructor_id: str, quiz_id: str, question_ids: list[str]
    ) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        existing = {q.id: q for q in self._repo.list_questions(quiz.id)}
        if set(question_ids) != set(existing.keys()):
            raise ValueError("The reorder list must include every question in this quiz exactly once")
        for index, qid in enumerate(question_ids):
            existing[qid].order_index = index
        self._repo.commit()
        return self._serialize_detail(quiz, section)

    # --------------------------------------------------------------- progress

    def get_progress(self, *, instructor_id: str, quiz_id: str) -> dict[str, Any]:
        quiz, section = self._require_owned_quiz(instructor_id, quiz_id)
        questions = self._repo.list_questions(quiz.id)
        roster = self._repo.roster_for_section(quiz.section_id)
        submissions = {s.student_id: s for s in self._repo.submissions_for_quiz(quiz.id)}

        rows = []
        for student in roster:
            submission = submissions.get(student.id)
            if submission is None:
                rows.append(
                    {
                        "studentId": student.id,
                        "studentName": student.full_name,
                        "studentEmail": student.email,
                        "status": "not_started",
                        "grade": None,
                        "submittedAt": None,
                        "isLate": False,
                        "answers": [],
                    }
                )
                continue
            rows.append(
                {
                    "studentId": student.id,
                    "studentName": student.full_name,
                    "studentEmail": student.email,
                    "submissionId": submission.id,
                    "status": "pending_review" if submission.grading_status == "PENDING" else "graded",
                    "grade": submission.grade,
                    "submittedAt": submission.submitted_at.isoformat() if submission.submitted_at else None,
                    "isLate": submission.is_late,
                    "answers": self._per_question_breakdown(questions, submission),
                }
            )
        submitted_count = sum(1 for r in rows if r["status"] != "not_started")
        return {
            "quiz": self._serialize_detail(quiz, section),
            "roster": rows,
            "totalStudents": len(roster),
            "submittedCount": submitted_count,
        }

    def grade_submission(
        self,
        *,
        instructor_id: str,
        quiz_id: str,
        submission_id: str,
        scores: dict[str, float],
        feedback: str | None,
    ) -> dict[str, Any]:
        quiz, _section = self._require_owned_quiz(instructor_id, quiz_id)
        submission = self._repo.get_submission(submission_id)
        if submission is None or submission.quiz_id != quiz.id:
            raise LookupError("Submission not found")
        questions = {q.id: q for q in self._repo.list_questions(quiz.id)}
        content = dict(submission.content or {})
        results = dict(content.get("results") or {})
        for question_id, awarded in scores.items():
            question = questions.get(question_id)
            if question is None:
                continue
            clamped = max(0.0, min(float(awarded), question.points))
            correct = True if clamped >= question.points else (False if clamped <= 0 else None)
            results[question_id] = {"correct": correct, "points_awarded": clamped}
        content["results"] = results
        submission.content = content
        all_graded = all(
            results.get(qid, {}).get("points_awarded") is not None for qid in questions
        )
        submission.grading_status = "GRADED" if all_graded else "PENDING"
        submission.grade = self._compute_grade(quiz, results)
        if feedback is not None:
            submission.feedback = feedback
        self._repo.commit()
        return self.get_progress(instructor_id=instructor_id, quiz_id=quiz_id)

    # -------------------------------------------------------------- student

    def list_for_student(self, *, student_id: str) -> list[dict[str, Any]]:
        section_ids = self._repo.student_section_ids(student_id)
        quizzes = [q for q in self._repo.list_for_sections(section_ids) if q.is_published]
        out = []
        for quiz in quizzes:
            section = self._repo.get_section(quiz.section_id)
            course = self._repo.get_course(section.course_id) if section else None
            submission = self._repo.get_submission_for_student(quiz.id, student_id)
            out.append(
                {
                    **self._serialize_summary(quiz, section, course),
                    "myStatus": self._student_status(submission),
                    "myGrade": submission.grade if submission else None,
                }
            )
        return out

    def get_for_student(self, *, student_id: str, quiz_id: str) -> dict[str, Any]:
        quiz = self._repo.get(quiz_id)
        if quiz is None or not quiz.is_published:
            raise LookupError("Quiz not found")
        if not self._repo.is_enrolled(student_id, quiz.section_id):
            raise PermissionError("You are not enrolled in this class")
        section = self._repo.get_section(quiz.section_id)
        course = self._repo.get_course(section.course_id) if section else None
        questions = self._repo.list_questions(quiz.id)
        submission = self._repo.get_submission_for_student(quiz.id, student_id)
        base = self._serialize_summary(quiz, section, course)
        if submission is not None:
            base["myStatus"] = self._student_status(submission)
            base["myGrade"] = submission.grade
            base["submittedAt"] = submission.submitted_at.isoformat() if submission.submitted_at else None
            base["questions"] = self._per_question_breakdown(questions, submission, reveal_correct=True)
        else:
            base["myStatus"] = "not_started"
            base["questions"] = [
                {
                    "id": q.id,
                    "questionText": q.question_text,
                    "questionType": q.question_type,
                    "options": q.options,
                    "points": q.points,
                }
                for q in questions
            ]
        return base

    def submit(self, *, student_id: str, quiz_id: str, answers: dict[str, str]) -> dict[str, Any]:
        quiz = self._repo.get(quiz_id)
        if quiz is None or not quiz.is_published:
            raise LookupError("Quiz not found")
        if not self._repo.is_enrolled(student_id, quiz.section_id):
            raise PermissionError("You are not enrolled in this class")
        if self._repo.get_submission_for_student(quiz.id, student_id) is not None:
            raise ValueError("You have already submitted this quiz")
        questions = self._repo.list_questions(quiz.id)
        results: dict[str, Any] = {}
        for question in questions:
            answer = str(answers.get(question.id, "")).strip()
            results[question.id] = self._grade_answer(question, answer)
        content = {"answers": answers, "results": results}
        grading_status = "GRADED" if all(r["points_awarded"] is not None for r in results.values()) else "PENDING"
        grade = self._compute_grade(quiz, results)
        now = campus_now()
        is_late = bool(quiz.due_date and now > quiz.due_date)
        submission = self._repo.add_submission(
            quiz_id=quiz.id,
            student_id=student_id,
            content=content,
            grading_status=grading_status,
            grade=grade,
            is_late=is_late,
        )
        self._repo.commit()
        return self.get_for_student(student_id=student_id, quiz_id=quiz_id) | {
            "submissionId": submission.id,
        }

    # ------------------------------------------------------------------ util

    def _require_owned_section(self, instructor_id: str, section_id: str):
        section = self._repo.get_section(section_id)
        if section is None:
            raise LookupError("Class not found")
        if section.instructor_id != instructor_id:
            raise PermissionError("You can only create quizzes for classes you teach")
        return section

    def _require_owned_quiz(self, instructor_id: str, quiz_id: str) -> tuple[Quiz, Any]:
        quiz = self._repo.get(quiz_id)
        if quiz is None:
            raise LookupError("Quiz not found")
        section = self._repo.get_section(quiz.section_id)
        if section is None or section.instructor_id != instructor_id:
            raise PermissionError("You can only manage quizzes for classes you teach")
        return quiz, section

    @staticmethod
    def _validate_question(
        question_type: str, correct_answer: str, options: list[str]
    ) -> tuple[str, str, list[str]]:
        question_type = question_type.upper().strip()
        if question_type not in QUESTION_TYPES:
            raise ValueError("Question type must be MULTIPLE_CHOICE, TRUE_FALSE, or SHORT_ANSWER")
        if question_type == "MULTIPLE_CHOICE":
            cleaned = [opt.strip() for opt in options if opt.strip()]
            if len(cleaned) < 2:
                raise ValueError("Multiple choice questions need at least 2 options")
            if correct_answer.strip() not in cleaned:
                raise ValueError("The correct answer must match one of the options")
            return question_type, correct_answer.strip(), cleaned
        if question_type == "TRUE_FALSE":
            normalized = correct_answer.strip().lower()
            if normalized not in ("true", "false"):
                raise ValueError("True/False questions need correct_answer of 'true' or 'false'")
            return question_type, "True" if normalized == "true" else "False", ["True", "False"]
        return question_type, correct_answer.strip(), []

    @staticmethod
    def _grade_answer(question: QuizQuestion, answer: str) -> dict[str, Any]:
        if question.question_type == "SHORT_ANSWER":
            return {"correct": None, "points_awarded": None}
        correct = answer.strip().lower() == question.correct_answer.strip().lower()
        return {"correct": correct, "points_awarded": question.points if correct else 0.0}

    @staticmethod
    def _compute_grade(quiz: Quiz, results: dict[str, Any]) -> float:
        if not quiz.max_points:
            return 0.0
        earned = sum(float(r.get("points_awarded") or 0) for r in results.values())
        return round(earned / quiz.max_points * 100, 1)

    @staticmethod
    def _student_status(submission: Submission | None) -> str:
        if submission is None:
            return "not_started"
        return "pending_review" if submission.grading_status == "PENDING" else "graded"

    @staticmethod
    def _per_question_breakdown(
        questions: list[QuizQuestion],
        submission: Submission,
        *,
        reveal_correct: bool = False,
    ) -> list[dict[str, Any]]:
        answers = (submission.content or {}).get("answers") or {}
        results = (submission.content or {}).get("results") or {}
        out = []
        for question in questions:
            result = results.get(question.id) or {}
            row = {
                "id": question.id,
                "questionText": question.question_text,
                "questionType": question.question_type,
                "points": question.points,
                "myAnswer": answers.get(question.id, ""),
                "correct": result.get("correct"),
                "pointsAwarded": result.get("points_awarded"),
            }
            if reveal_correct:
                row["correctAnswer"] = question.correct_answer
                row["options"] = question.options
            out.append(row)
        return out

    @staticmethod
    def _status_for(quiz: Quiz, now: datetime) -> str:
        if quiz.opens_at and now < quiz.opens_at:
            return "scheduled"
        if quiz.due_date and now > quiz.due_date:
            return "closed"
        return "open"

    def _serialize_summary(self, quiz: Quiz, section, course=None) -> dict[str, Any]:
        if course is None and section is not None:
            course = self._repo.get_course(section.course_id)
        return {
            "id": quiz.id,
            "sectionId": quiz.section_id,
            "sectionCode": getattr(section, "section_code", None),
            "courseCode": getattr(course, "code", None),
            "courseName": getattr(course, "name", None),
            "title": quiz.title,
            "description": quiz.description,
            "timeLimitMinutes": quiz.time_limit_minutes,
            "dueDate": quiz.due_date.isoformat() if quiz.due_date else None,
            "opensAt": quiz.opens_at.isoformat() if quiz.opens_at else None,
            "maxPoints": quiz.max_points,
            "isPublished": quiz.is_published,
            "questionCount": len(self._repo.list_questions(quiz.id)),
            "status": self._status_for(quiz, campus_now()),
        }

    def _serialize_detail(self, quiz: Quiz, section) -> dict[str, Any]:
        summary = self._serialize_summary(quiz, section)
        summary["questions"] = [
            {
                "id": q.id,
                "questionText": q.question_text,
                "questionType": q.question_type,
                "correctAnswer": q.correct_answer,
                "options": q.options,
                "points": q.points,
                "orderIndex": q.order_index,
            }
            for q in self._repo.list_questions(quiz.id)
        ]
        return summary
