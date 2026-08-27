from sqlalchemy.orm import Session

from src.db import models


class OwnershipRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def student_has_course_access(self, student_id: str, course_id: str) -> bool:
        return (
            self._db.query(models.CourseSection.id)
            .join(models.Enrollment)
            .filter(
                models.CourseSection.course_id == course_id,
                models.Enrollment.student_id == student_id,
            )
            .first()
            is not None
        )

    def student_course_if_accessible(
        self,
        student_id: str,
        course_code: str,
    ) -> models.Course | None:
        code = str(course_code or "").strip().upper()
        if not code:
            return None
        course = self._db.query(models.Course).filter_by(code=code).first()
        if course is None:
            return None
        if self.student_has_course_access(student_id, course.id):
            return course
        semester_hit = (
            self._db.query(models.SemesterCourse.id)
            .join(models.SemesterSetup)
            .filter(
                models.SemesterSetup.student_id == student_id,
                models.SemesterSetup.is_active.is_(True),
                models.SemesterCourse.course_id == course.id,
            )
            .first()
        )
        return course if semester_hit is not None else None

    def student_has_assignment_access(
        self,
        student_id: str,
        assignment_id: str,
    ) -> bool:
        return (
            self._db.query(models.Assignment.id)
            .join(models.CourseSection)
            .join(models.Enrollment)
            .filter(
                models.Assignment.id == assignment_id,
                models.Enrollment.student_id == student_id,
            )
            .first()
            is not None
        )

    def student_owns_weekly_plan(self, student_id: str, plan_id: str) -> bool:
        return (
            self._db.query(models.WeeklyPlan.id)
            .filter(
                models.WeeklyPlan.id == plan_id,
                models.WeeklyPlan.student_id == student_id,
            )
            .first()
            is not None
        )

    def student_owns_study_task(self, student_id: str, task_id: str) -> bool:
        return (
            self._db.query(models.StudyTask.id)
            .join(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(
                models.StudyTask.id == task_id,
                models.WeeklyPlan.student_id == student_id,
            )
            .first()
            is not None
        )

    def student_owns_schedule_block(self, student_id: str, block_id: str) -> bool:
        return (
            self._db.query(models.ScheduleBlock.id)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(
                models.ScheduleBlock.id == block_id,
                models.WeeklyPlan.student_id == student_id,
            )
            .first()
            is not None
        )

    def instructor_owns_student(self, instructor_id: str, student_id: str) -> bool:
        return (
            self._db.query(models.Enrollment.id)
            .join(models.CourseSection)
            .filter(
                models.Enrollment.student_id == student_id,
                models.CourseSection.instructor_id == instructor_id,
            )
            .first()
            is not None
        )

    def instructor_owns_assignment(self, instructor_id: str, assignment_id: str) -> bool:
        return (
            self._db.query(models.Assignment.id)
            .join(models.CourseSection)
            .filter(
                models.Assignment.id == assignment_id,
                models.CourseSection.instructor_id == instructor_id,
            )
            .first()
            is not None
        )

    def instructor_owns_risk(self, instructor_id: str, risk_id: str) -> bool:
        return (
            self._db.query(models.RiskSignal.id)
            .join(models.CourseSection)
            .filter(
                models.RiskSignal.id == risk_id,
                models.CourseSection.instructor_id == instructor_id,
            )
            .first()
            is not None
        )

    def instructor_owns_guardrail_event(self, instructor_id: str, event_id: str) -> bool:
        """Case thuoc ve GV neu no gan voi dung lop GV do day, HOAC khong gan
        section nao (cau hoi chung) — cho phep NULL vi khong co tin hieu de
        quy rieng ve 1 GV, an het thi khong ai xu ly duoc case do.

        `GuardrailEvent.section_id` duoc ghi truc tiep luc record_block(),
        chat feature (Conversation/Message) da bi go bo hoan toan nen khong
        con cach nao suy ra section tu conversation cho cac row cu nua — xem
        migrations/versions/20260910_remove_chatbot_feature.py. Phai giu
        dong bo logic voi `_visible_guardrail_events` (src/api/instructor.py)
        — cung mot quy tac loc quyen rieng tu, chi khac noi trien khai.
        """
        event = self._db.query(models.GuardrailEvent).filter_by(id=event_id).first()
        if event is None:
            return False

        if event.section_id is None:
            return True

        return (
            self._db.query(models.CourseSection.id)
            .filter(
                models.CourseSection.id == event.section_id,
                models.CourseSection.instructor_id == instructor_id,
            )
            .first()
            is not None
        )

