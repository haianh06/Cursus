"""Institution-managed recurring class meetings and date-specific exceptions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from src.db import models


@dataclass(frozen=True)
class ClassMeeting:
    id: str
    section_id: str
    title: str
    course_code: str
    course_name: str
    start: datetime
    end: datetime
    room: str | None
    note: str | None
    kind: str = "CLASS"


def _clock(minutes: int) -> time:
    return time(hour=minutes // 60, minute=minutes % 60)


class ClassScheduleService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def student_meetings(self, *, student_id: str, start: datetime, end: datetime) -> list[ClassMeeting]:
        section_ids = [row[0] for row in self._db.query(models.Enrollment.section_id).filter(
            models.Enrollment.student_id == student_id,
            models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
        ).all()]
        if not section_ids:
            return []
        return self._meetings(section_ids=section_ids, start=start, end=end)

    def instructor_meetings(self, *, instructor_id: str, start: datetime, end: datetime) -> list[ClassMeeting]:
        section_ids = [row[0] for row in self._db.query(models.CourseSection.id).filter_by(instructor_id=instructor_id).all()]
        return self._meetings(section_ids=section_ids, start=start, end=end) if section_ids else []

    def _meetings(self, *, section_ids: list[str], start: datetime, end: datetime) -> list[ClassMeeting]:
        schedules = self._db.query(models.FixedClassSchedule, models.CourseSection, models.Course).join(
            models.CourseSection, models.CourseSection.id == models.FixedClassSchedule.section_id
        ).join(models.Course, models.Course.id == models.CourseSection.course_id).filter(
            models.FixedClassSchedule.section_id.in_(section_ids),
            models.FixedClassSchedule.effective_from <= end.date(),
            models.FixedClassSchedule.effective_to >= start.date(),
        ).all()
        exceptions = self._db.query(models.ClassScheduleException).filter(
            models.ClassScheduleException.section_id.in_(section_ids),
            models.ClassScheduleException.event_date >= start.date(),
            models.ClassScheduleException.event_date <= end.date(),
        ).all()
        cancelled = {(row.schedule_id, row.event_date) for row in exceptions if row.kind == "CANCELLED"}
        result: list[ClassMeeting] = []
        for schedule, section, course in schedules:
            day = max(start.date(), schedule.effective_from)
            day += timedelta(days=(schedule.weekday - day.weekday()) % 7)
            while day <= min(end.date(), schedule.effective_to):
                if (schedule.id, day) not in cancelled:
                    meeting_start = datetime.combine(day, _clock(schedule.start_minute))
                    meeting_end = datetime.combine(day, _clock(schedule.end_minute))
                    if meeting_start < end and meeting_end > start:
                        result.append(ClassMeeting(
                            id=f"class:{schedule.id}:{day.isoformat()}", section_id=section.id,
                            title=f"{course.code} · {section.section_code}", course_code=course.code,
                            course_name=course.name, start=meeting_start, end=meeting_end,
                            room=schedule.room, note=schedule.note,
                        ))
                day += timedelta(days=7)
        sections = {row.id: row for row in self._db.query(models.CourseSection).filter(models.CourseSection.id.in_(section_ids)).all()}
        courses = {row.id: row for row in self._db.query(models.Course).filter(models.Course.id.in_([s.course_id for s in sections.values()])).all()}
        for exception in exceptions:
            if exception.kind != "MAKEUP":
                continue
            section = sections[exception.section_id]
            course = courses[section.course_id]
            meeting_start = datetime.combine(exception.event_date, _clock(exception.start_minute))
            result.append(ClassMeeting(
                id=f"makeup:{exception.id}", section_id=section.id,
                title=f"{course.code} · {section.section_code} (Buổi bù)", course_code=course.code,
                course_name=course.name, start=meeting_start,
                end=datetime.combine(exception.event_date, _clock(exception.end_minute)),
                room=exception.room, note=exception.note or exception.reason, kind="MAKEUP",
            ))
        return sorted(result, key=lambda item: item.start)

    def ensure_no_section_overlap(self, *, section_id: str, start: datetime, end: datetime, exclude_exception_id: str | None = None) -> None:
        for item in self._meetings(section_ids=[section_id], start=start, end=end):
            if start < item.end and end > item.start and item.id != f"makeup:{exclude_exception_id}":
                raise ValueError("Class meeting overlaps an existing class meeting")

    def notify_exception(self, exception: models.ClassScheduleException) -> None:
        recipients = self._db.query(models.Enrollment.student_id).filter(
            models.Enrollment.section_id == exception.section_id,
            models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
        ).all()
        action = "đã bị hủy" if exception.kind == "CANCELLED" else "có buổi bù"
        for (student_id,) in recipients:
            self._db.add(models.ClassScheduleNotification(
                id=f"sched_note_{uuid.uuid4().hex[:16]}", recipient_id=student_id,
                exception_id=exception.id, title=f"Cập nhật lịch lớp: {action}",
                body=f"Ngày {exception.event_date.isoformat()}. {exception.reason}",
            ))
