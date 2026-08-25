"""Weekly timetable assembly and self-study block mutations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.academic_term_repository import AcademicTermRepository
from src.repositories.semester_repository import SemesterRepository
from src.services.academic.academic_calendar import SLOT_TIMES, slot_datetimes
from src.services.academic.academic_calendar import monday_of as _semester_monday_of
from src.services.academic.lecture_plan_service import LECTURE_PLAN_SOURCE


@dataclass(frozen=True)
class TimetableBlock:
    id: str
    title: str
    start: datetime
    end: datetime
    kind: str  # CLASS | SELF_STUDY | EXAM
    locked: bool
    description: str | None = None
    course_code: str | None = None
    course_name: str | None = None
    task_id: str | None = None
    task_status: str | None = None
    recurrence_series_id: str | None = None
    is_draft: bool = False

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "kind": self.kind,
            "locked": self.locked,
            "description": self.description,
            "courseCode": self.course_code,
            "courseName": self.course_name,
            "taskId": self.task_id,
            "taskStatus": self.task_status,
            "recurrenceSeriesId": self.recurrence_series_id,
            "isDraft": self.is_draft,
        }


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def week_bounds(week_start: date) -> tuple[datetime, datetime]:
    start = datetime.combine(monday_of(week_start), time.min)
    end = start + timedelta(days=7)
    return start, end


class TimetableService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_week(
        self,
        *,
        student_id: str,
        week_start: date,
        preview_plan_id: str | None = None,
    ) -> dict:
        start, end = week_bounds(week_start)
        monday = start.date()
        blocks = [
            *self._class_blocks(student_id=student_id, start=start, end=end),
            *self._exam_blocks(student_id=student_id, start=start, end=end),
            *self._self_study_blocks(
                student_id=student_id, start=start, end=end, preview_plan_id=preview_plan_id
            ),
        ]
        blocks.sort(key=lambda item: item.start)
        return {
            "weekStart": monday.isoformat(),
            "weekEnd": (monday + timedelta(days=6)).isoformat(),
            "blocks": [block.to_dict() for block in blocks],
            "isEmpty": len(blocks) == 0,
            "semesterMeta": self._semester_meta(student_id=student_id, week_start=monday),
        }

    def bootstrap_demo_week(self, *, student_id: str, week_start: date) -> dict:
        """Ensure the student has class + sample self-study blocks for the week."""
        start, end = week_bounds(week_start)
        monday = start.date()
        section = self._ensure_demo_enrollment(student_id=student_id)
        course = self._db.query(models.Course).filter_by(id=section.course_id).first()
        course_code = course.code if course else "DEMO"
        course_name = course.name if course else "Demo Course"

        lecture_days = (0, 2, 4)  # Mon / Wed / Fri
        for offset in lecture_days:
            day = monday + timedelta(days=offset)
            lecture_start = datetime.combine(day, time(9, 0))
            if not (
                self._db.query(models.CalendarEvent)
                .filter(
                    models.CalendarEvent.section_id == section.id,
                    models.CalendarEvent.start_time == lecture_start,
                )
                .first()
            ):
                self._db.add(
                    models.CalendarEvent(
                        id=f"cal_{uuid.uuid4().hex[:10]}",
                        section_id=section.id,
                        title=f"{course_code} Lecture",
                        description=f"{course_name} · Room A101",
                        start_time=lecture_start,
                        end_time=lecture_start + timedelta(hours=2),
                        event_type="LECTURE",
                    )
                )

        sample_start = datetime.combine(monday + timedelta(days=1), time(19, 0))
        existing_self_study = (
            self._db.query(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(
                models.WeeklyPlan.student_id == student_id,
                models.ScheduleBlock.start_time >= start,
                models.ScheduleBlock.start_time < end,
            )
            .first()
        )
        if not existing_self_study:
            self.create_self_study_block(
                student_id=student_id,
                title="Self-study: review lecture notes",
                start=sample_start,
                end=sample_start + timedelta(hours=1, minutes=30),
            )
        else:
            self._db.commit()

        return self.get_week(student_id=student_id, week_start=monday)

    def schedule_plan_into_gaps(
        self,
        *,
        student_id: str,
        plan_id: str,
        week_start: date | None = None,
    ) -> dict:
        """Place approved plan tasks into free evening slots on the timetable."""
        plan = (
            self._db.query(models.WeeklyPlan)
            .filter_by(id=plan_id, student_id=student_id)
            .first()
        )
        if not plan:
            raise LookupError("Weekly plan not found")

        monday = monday_of(week_start or date.today())
        week = self.get_week(student_id=student_id, week_start=monday)

        task_rows = (
            self._db.query(models.StudyTask, models.ScheduleBlock)
            .join(models.ScheduleBlock)
            .join(models.DailyPlan)
            .filter(models.DailyPlan.weekly_plan_id == plan_id)
            .order_by(models.StudyTask.id.asc())
            .all()
        )
        if not task_rows:
            return self.get_week(student_id=student_id, week_start=monday)

        # Ignore current plan blocks while searching for free gaps.
        plan_block_ids = {block.id for _, block in task_rows}
        occupied = [
            (
                datetime.fromisoformat(block["start"].replace("Z", "")),
                datetime.fromisoformat(block["end"].replace("Z", "")),
            )
            for block in week["blocks"]
            if block["id"] not in plan_block_ids
        ]

        cursor_day = 0
        for task, block in task_rows:
            duration = max(30, int(task.planned_minutes or 60))
            placed = False
            for day_offset in range(cursor_day, 5):  # Mon-Fri
                day = monday + timedelta(days=day_offset)
                slot_start = datetime.combine(day, time(18, 0))
                latest = datetime.combine(day, time(22, 0))
                while slot_start + timedelta(minutes=duration) <= latest:
                    slot_end = slot_start + timedelta(minutes=duration)
                    if not self._overlaps(slot_start, slot_end, occupied):
                        daily = self._ensure_daily_plan(
                            student_id=student_id, day=day, weekly_plan_id=plan_id
                        )
                        block.daily_plan_id = daily.id
                        block.start_time = slot_start
                        block.end_time = slot_end
                        block.activity_description = task.title
                        occupied.append((slot_start, slot_end))
                        cursor_day = day_offset
                        placed = True
                        break
                    slot_start += timedelta(minutes=30)
                if placed:
                    break
            if not placed:
                day = monday + timedelta(days=5)
                slot_start = datetime.combine(day, time(19, 0))
                slot_end = slot_start + timedelta(minutes=duration)
                daily = self._ensure_daily_plan(
                    student_id=student_id, day=day, weekly_plan_id=plan_id
                )
                block.daily_plan_id = daily.id
                block.start_time = slot_start
                block.end_time = slot_end
                block.activity_description = task.title
                occupied.append((slot_start, slot_end))

        # The caller owns the transaction so scheduling and plan approval commit atomically.
        self._db.flush()
        return self.get_week(student_id=student_id, week_start=monday)

    @staticmethod
    def _overlaps(
        start: datetime,
        end: datetime,
        occupied: list[tuple[datetime, datetime]],
    ) -> bool:
        for occupied_start, occupied_end in occupied:
            if start < occupied_end and end > occupied_start:
                return True
        return False

    def _ensure_demo_enrollment(self, *, student_id: str) -> models.CourseSection:
        existing = (
            self._db.query(models.CourseSection)
            .join(models.Enrollment)
            .filter(models.Enrollment.student_id == student_id)
            .first()
        )
        if existing:
            return existing

        course = self._db.query(models.Course).first()
        if not course:
            student = self._db.query(models.User).filter_by(id=student_id).first()
            course = models.Course(
                id="course_demo_ssa101",
                code="SSA101",
                name="Academic Skills",
                description="Demo course for weekly planner",
                organization_id=student.organization_id if student else None,
            )
            self._db.add(course)
            self._db.flush()

        section = (
            self._db.query(models.CourseSection)
            .filter_by(course_id=course.id)
            .first()
        )
        if not section:
            instructor = (
                self._db.query(models.User)
                .filter(models.User.role.in_(["INSTRUCTOR", "ADMIN"]))
                .first()
            )
            instructor_id = instructor.id if instructor else student_id
            section = models.CourseSection(
                id=f"section_demo_{uuid.uuid4().hex[:8]}",
                course_id=course.id,
                instructor_id=instructor_id,
                term="Fall2026",
                section_code="SE1801",
            )
            self._db.add(section)
            self._db.flush()

        enrollment = (
            self._db.query(models.Enrollment)
            .filter_by(student_id=student_id, section_id=section.id)
            .first()
        )
        if not enrollment:
            self._db.add(
                models.Enrollment(
                    id=f"enroll_{uuid.uuid4().hex[:10]}",
                    student_id=student_id,
                    section_id=section.id,
                    status="ENROLLED",
                )
            )
            self._db.flush()
        return section

    def create_self_study_block(
        self,
        *,
        student_id: str,
        title: str,
        start: datetime,
        end: datetime,
        repeat_weekly_until: date | None = None,
    ) -> dict:
        self._validate_range(start, end)
        next_start = start.replace(tzinfo=None)
        next_end = end.replace(tzinfo=None)
        clean_title = title.strip() or "Self-study"

        # Non-repeating: a single occurrence, conflict is fatal (existing
        # behavior, unchanged).
        if repeat_weekly_until is None:
            self._assert_no_class_overlap(student_id=student_id, start=next_start, end=next_end)
            block = self._create_block_row(
                student_id=student_id, title=clean_title, start=next_start, end=next_end
            )
            self._db.commit()
            self._db.refresh(block)
            return self._block_to_dict(block)

        # Recurring: each week is its own attempt (a46db63 §6.3.8) — a
        # conflicting occurrence is skipped, not fatal, unless it's the first
        # (which the caller is directly waiting on a result for).
        series_id = f"rseries_{uuid.uuid4().hex[:10]}"
        occurrence_start = next_start
        occurrence_end = next_end
        first_block: models.ScheduleBlock | None = None
        while occurrence_start.date() <= repeat_weekly_until:
            try:
                self._assert_no_class_overlap(
                    student_id=student_id, start=occurrence_start, end=occurrence_end
                )
            except ValueError:
                if first_block is None:
                    raise
                occurrence_start += timedelta(days=7)
                occurrence_end += timedelta(days=7)
                continue
            block = self._create_block_row(
                student_id=student_id,
                title=clean_title,
                start=occurrence_start,
                end=occurrence_end,
                recurrence_series_id=series_id,
            )
            if first_block is None:
                first_block = block
            occurrence_start += timedelta(days=7)
            occurrence_end += timedelta(days=7)
        self._db.commit()
        self._db.refresh(first_block)
        return self._block_to_dict(first_block)

    def _create_block_row(
        self,
        *,
        student_id: str,
        title: str,
        start: datetime,
        end: datetime,
        recurrence_series_id: str | None = None,
    ) -> models.ScheduleBlock:
        daily_plan = self._ensure_daily_plan(student_id=student_id, day=start.date())
        block = models.ScheduleBlock(
            id=f"sb_{uuid.uuid4().hex[:10]}",
            daily_plan_id=daily_plan.id,
            start_time=start,
            end_time=end,
            activity_description=title,
            recurrence_series_id=recurrence_series_id,
        )
        self._db.add(block)
        self._db.flush()
        return block

    @staticmethod
    def _block_to_dict(block: models.ScheduleBlock) -> dict:
        return TimetableBlock(
            id=block.id,
            title=block.activity_description,
            start=block.start_time,
            end=block.end_time,
            kind="SELF_STUDY",
            locked=False,
            description=None,
            recurrence_series_id=block.recurrence_series_id,
        ).to_dict()

    def update_self_study_block(
        self,
        *,
        student_id: str,
        block_id: str,
        title: str | None,
        start: datetime | None,
        end: datetime | None,
        recurrence_scope: str = "this",
    ) -> dict:
        block = self._owned_block(student_id=student_id, block_id=block_id)
        original_start = block.start_time
        next_start = (start or block.start_time).replace(tzinfo=None)
        next_end = (end or block.end_time).replace(tzinfo=None)
        self._validate_range(next_start, next_end)

        if recurrence_scope == "all" and block.recurrence_series_id:
            delta_start = next_start - original_start
            new_duration = next_end - next_start
            series = (
                self._db.query(models.ScheduleBlock)
                .filter_by(recurrence_series_id=block.recurrence_series_id)
                .all()
            )
            for occurrence in series:
                occ_start = occurrence.start_time + delta_start
                occ_end = occ_start + new_duration
                # Each occurrence is re-validated individually; a conflicting
                # one is skipped rather than blocking the whole series edit.
                try:
                    self._assert_no_class_overlap(
                        student_id=student_id, start=occ_start, end=occ_end
                    )
                except ValueError:
                    continue
                if occ_start.date() != occurrence.start_time.date():
                    daily_plan = self._ensure_daily_plan(student_id=student_id, day=occ_start.date())
                    occurrence.daily_plan_id = daily_plan.id
                occurrence.start_time = occ_start
                occurrence.end_time = occ_end
                if title is not None:
                    occurrence.activity_description = title.strip() or occurrence.activity_description
            self._db.commit()
            self._db.refresh(block)
            return self._block_to_dict(block)

        self._assert_no_class_overlap(
            student_id=student_id,
            start=next_start,
            end=next_end,
        )

        if next_start.date() != block.start_time.date():
            daily_plan = self._ensure_daily_plan(
                student_id=student_id,
                day=next_start.date(),
            )
            block.daily_plan_id = daily_plan.id

        block.start_time = next_start
        block.end_time = next_end
        if title is not None:
            block.activity_description = title.strip() or block.activity_description

        self._db.commit()
        self._db.refresh(block)
        return self._block_to_dict(block)

    def _assert_no_class_overlap(
        self,
        *,
        student_id: str,
        start: datetime,
        end: datetime,
    ) -> None:
        """Reject self-study ranges that collide with fixed class sessions."""
        class_blocks = self._class_blocks(
            student_id=student_id,
            start=start,
            end=end,
        )
        for class_block in class_blocks:
            if start < class_block.end and end > class_block.start:
                label = class_block.course_code or class_block.title
                raise ValueError(
                    f"Self-study cannot overlap fixed class ({label} "
                    f"{class_block.start.strftime('%H:%M')}-"
                    f"{class_block.end.strftime('%H:%M')})"
                )

    def delete_self_study_block(
        self, *, student_id: str, block_id: str, scope: str = "this"
    ) -> None:
        block = self._owned_block(student_id=student_id, block_id=block_id)
        targets = [block]
        if scope == "all" and block.recurrence_series_id:
            targets = (
                self._db.query(models.ScheduleBlock)
                .filter_by(recurrence_series_id=block.recurrence_series_id)
                .all()
            )
        for target in targets:
            tasks = (
                self._db.query(models.StudyTask)
                .filter_by(schedule_block_id=target.id)
                .all()
            )
            for task in tasks:
                self._db.delete(task)
            # SelfStudySession.schedule_block_id has ON DELETE CASCADE at the
            # DB level, but ScheduleBlock's `self_study_sessions` relationship
            # has no `passive_deletes=True` (or explicit delete cascade), so
            # SQLAlchemy's own unit-of-work loads that collection on flush and
            # tries to disassociate it (set schedule_block_id = NULL) instead
            # of just letting Postgres cascade the row away -- and that
            # column is NOT NULL, so every delete of a block with a session
            # crashed with a 500 that the browser only ever saw as a CORS-
            # opaque network failure (found via a live user report: "xoá lịch
            # Tự học không được"). Deleting the session explicitly, the same
            # way tasks already are above, sidesteps that ORM cascade
            # ambiguity entirely.
            self._db.delete(target)
        self._db.commit()

    def _class_blocks(
        self,
        *,
        student_id: str,
        start: datetime,
        end: datetime,
    ) -> list[TimetableBlock]:
        section_ids = [
            row[0]
            for row in self._db.query(models.Enrollment.section_id)
            .filter(models.Enrollment.student_id == student_id)
            .all()
        ]
        if not section_ids:
            return []

        events = (
            self._db.query(models.CalendarEvent, models.Course)
            .join(
                models.CourseSection,
                models.CourseSection.id == models.CalendarEvent.section_id,
            )
            .join(models.Course, models.Course.id == models.CourseSection.course_id)
            .filter(
                models.CalendarEvent.section_id.in_(section_ids),
                models.CalendarEvent.event_type == "LECTURE",
                models.CalendarEvent.start_time >= start,
                models.CalendarEvent.start_time < end,
            )
            .all()
        )

        return [
            TimetableBlock(
                id=event.id,
                title=event.title,
                start=event.start_time,
                end=event.end_time,
                kind="CLASS",
                locked=True,
                description=event.description,
                course_code=course.code,
                course_name=course.name,
            )
            for event, course in events
        ]

    def _exam_blocks(
        self,
        *,
        student_id: str,
        start: datetime,
        end: datetime,
    ) -> list[TimetableBlock]:
        """Exam sessions for the student's currently-linked courses, folded
        in alongside class blocks — locked, non-interactive (a46db63 parity).
        Reuses the same admin-managed CourseExam/CourseExamSession schedule
        `lecture_plan_service.py` already folds into its own task generation."""
        semester = self._semester_repo().get_active(student_id)
        if semester is None:
            return []
        course_ids = [
            link.course_id
            for link in self._semester_repo().list_course_links(semester.id)
        ]
        if not course_ids:
            return []
        courses = {
            course.id: course
            for course in self._db.query(models.Course)
            .filter(models.Course.id.in_(course_ids))
            .all()
        }
        exam_rows = self._academic_term_repo().sessions_in_range_for_courses(
            course_ids, start.date(), end.date()
        )
        blocks: list[TimetableBlock] = []
        for exam_session, exam in exam_rows:
            if exam_session.slot_id not in SLOT_TIMES:
                continue
            slot_start, slot_end = slot_datetimes(exam_session.exam_date, exam_session.slot_id)
            if not (start <= slot_start < end):
                continue
            course = courses.get(exam.course_id)
            course_code = course.code if course else exam.course_id
            blocks.append(
                TimetableBlock(
                    id=exam_session.id,
                    title=f"{course_code} · {exam_session.label}",
                    start=slot_start,
                    end=slot_end,
                    kind="EXAM",
                    locked=True,
                    course_code=course_code,
                    course_name=course.name if course else None,
                )
            )
        return blocks

    def _semester_meta(self, *, student_id: str, week_start: date) -> dict | None:
        semester = self._semester_repo().get_active(student_id)
        if semester is None:
            return None
        semester_monday = _semester_monday_of(semester.start_date)
        week_number = max(1, ((week_start - semester_monday).days // 7) + 1)
        exceptions = self._semester_repo().list_exceptions(semester.id)
        is_exception = any(
            exc.start_date <= week_start <= exc.end_date
            or (exc.start_date <= week_start + timedelta(days=6) and exc.end_date >= week_start)
            for exc in exceptions
        )
        return {
            "semesterId": semester.id,
            "semesterName": semester.name,
            "weekNumber": week_number,
            "isException": is_exception,
        }

    def _semester_repo(self) -> SemesterRepository:
        return SemesterRepository(self._db)

    def _academic_term_repo(self) -> AcademicTermRepository:
        return AcademicTermRepository(self._db)

    def _self_study_blocks(
        self,
        *,
        student_id: str,
        start: datetime,
        end: datetime,
        preview_plan_id: str | None = None,
    ) -> list[TimetableBlock]:
        rows = (
            self._db.query(models.ScheduleBlock, models.StudyTask, models.WeeklyPlan)
            .select_from(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .outerjoin(
                models.StudyTask,
                models.StudyTask.schedule_block_id == models.ScheduleBlock.id,
            )
            .filter(
                models.WeeklyPlan.student_id == student_id,
                models.ScheduleBlock.start_time >= start,
                models.ScheduleBlock.start_time < end,
            )
            .all()
        )

        blocks: dict[str, TimetableBlock] = {}
        for block, task, weekly_plan in rows:
            # `lecture_plan_service` drafts its own independent WeeklyPlan
            # rows (goals.source == "lecture_plan") in these same tables so
            # it can reuse the plan-generation schema. They are a different
            # product surface (timetable-driven review/prep tasks, not
            # assignment-driven self-study) and must never be blended into
            # Gate 2's timetable/self-study rendering — skip them here.
            plan_goals = weekly_plan.goals if isinstance(weekly_plan.goals, dict) else {}
            if plan_goals.get("source") == LECTURE_PLAN_SOURCE:
                continue
            # a46db63 invariant: a DRAFT plan's blocks are invisible on the
            # real timetable except when explicitly requested via
            # `preview_plan_id` (lets Reflection's next-week draft preview
            # itself without leaking into the live timetable before accept).
            is_draft_plan = str(plan_goals.get("status") or "").upper() == "DRAFT"
            if is_draft_plan and weekly_plan.id != preview_plan_id:
                continue
            existing = blocks.get(block.id)
            title = block.activity_description or (task.title if task else "Self-study")
            if existing and task:
                # Prefer the first linked task title if activity is a session label.
                if existing.title.startswith("Khung giờ") and task.title:
                    title = task.title
            blocks[block.id] = TimetableBlock(
                id=block.id,
                title=title if not existing else (title or existing.title),
                start=block.start_time,
                end=block.end_time,
                kind="SELF_STUDY",
                locked=False,
                description=task.title if task else None,
                task_id=task.id if task else (existing.task_id if existing else None),
                task_status=(
                    task.status if task else (existing.task_status if existing else None)
                ),
                recurrence_series_id=block.recurrence_series_id,
                is_draft=is_draft_plan,
            )
        return list(blocks.values())

    def _ensure_daily_plan(
        self,
        *,
        student_id: str,
        day: date,
        weekly_plan_id: str | None = None,
    ) -> models.DailyPlan:
        week_start = monday_of(day)
        week_number = week_start.isocalendar().week
        # When a caller is placing tasks that belong to a specific weekly
        # plan, the day must be created *inside that plan*. Picking the
        # highest-id plan for the week instead (the old behaviour) could
        # re-parent an accepted plan's tasks onto an unrelated timetable
        # plan, which made them vanish from GET /plans/weekly.
        if weekly_plan_id is not None:
            plan = (
                self._db.query(models.WeeklyPlan)
                .filter_by(id=weekly_plan_id, student_id=student_id)
                .first()
            )
            if not plan:
                raise LookupError("Weekly plan not found")

            # Guard against scheduling into a day that doesn't actually
            # belong to this plan's stored week — e.g. a stale/mismatched
            # week_start passed in by the caller.
            goals = plan.goals if isinstance(plan.goals, dict) else {}
            stored_week_start = goals.get("week_start")
            if stored_week_start:
                try:
                    planned_week_start = monday_of(
                        date.fromisoformat(str(stored_week_start))
                    )
                except ValueError as exc:
                    raise LookupError("Weekly plan has invalid week start") from exc
                if planned_week_start != week_start:
                    raise LookupError("Weekly plan does not match selected week")
            elif plan.week_number != week_number:
                raise LookupError("Weekly plan does not match selected week")
        else:
            candidates = (
                self._db.query(models.WeeklyPlan)
                .filter_by(student_id=student_id, week_number=week_number)
                .order_by(models.WeeklyPlan.id.desc())
                .all()
            )
            # Skip `lecture_plan_service` rows (goals.source == "lecture_plan")
            # — a new self-study block must never be re-parented onto that
            # separate product surface's plan. See the matching guard in
            # `_self_study_blocks`.
            plan = next(
                (
                    item
                    for item in candidates
                    if (item.goals if isinstance(item.goals, dict) else {}).get("source")
                    != LECTURE_PLAN_SOURCE
                ),
                None,
            )
        if not plan:
            plan = models.WeeklyPlan(
                id=f"plan_{uuid.uuid4().hex[:10]}",
                student_id=student_id,
                week_number=week_number,
                goals={
                    "kind": "timetable",
                    "week_start": week_start.isoformat(),
                    "status": "ACTIVE",
                },
                study_hours_allocated=12.0,
            )
            self._db.add(plan)
            self._db.flush()

        day_start = datetime.combine(day, time.min)
        daily = (
            self._db.query(models.DailyPlan)
            .filter(
                models.DailyPlan.weekly_plan_id == plan.id,
                models.DailyPlan.date >= day_start,
                models.DailyPlan.date < day_start + timedelta(days=1),
            )
            .first()
        )
        if not daily:
            daily = models.DailyPlan(
                id=f"dp_{uuid.uuid4().hex[:10]}",
                weekly_plan_id=plan.id,
                date=day_start,
                status="TODO",
            )
            self._db.add(daily)
            self._db.flush()
        return daily

    def _owned_block(self, *, student_id: str, block_id: str) -> models.ScheduleBlock:
        row = (
            self._db.query(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(
                models.ScheduleBlock.id == block_id,
                models.WeeklyPlan.student_id == student_id,
            )
            .first()
        )
        if not row:
            raise LookupError("Self-study block not found")
        return row

    @staticmethod
    def _validate_range(start: datetime, end: datetime) -> None:
        if end <= start:
            raise ValueError("End time must be after start time")
        duration = end - start
        if duration < timedelta(minutes=15):
            raise ValueError("Block must be at least 15 minutes")
        if duration > timedelta(hours=8):
            raise ValueError("Block cannot exceed 8 hours")
