"""One-time seed of 4 named demo accounts (2 contrasting students, 1
instructor, 1 admin) with enough real data to demo every role's flow.

Run scripts/ingest_subject_data.py first — this script enrolls the two
students in real courses from that catalog and generates a real PracticeSet
per course via the same generator the live app uses, so it needs actual
content to draw from.

Idempotent: bails out immediately if student_haianh already exists (mirrors
tests/support/api_demo_dataset.py's guard), so re-running is a no-op rather
than a duplicate-row error.

Usage:
    DATABASE_URL=postgresql://postgres:postgres@localhost:55432/appdb \
        python scripts/provision_demo_personas.py
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("provision-demo-personas")

DEMO_PASSWORD = "test123@"

SHARED_COURSE_CODES = ["CEA201", "SSA101", "CSI106", "PRF192", "DBI202", "SWD392"]

# Mon-Fri task titles, reused across weeks for both personas (only the
# completion outcome differs).
DAILY_TASK_TITLES = [
    ("Đọc tài liệu buổi học", "MEDIUM", "MEDIUM"),
    ("Làm bài tập / worksheet", "HIGH", "MEDIUM"),
]


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def main() -> None:
    from src.db import models
    from src.db.connection import SessionLocal
    from src.repositories.practice_set_repository import PracticeSetRepository
    from src.security.passwords import hash_password
    from src.services.practice_generator import generate_pack

    db = SessionLocal()
    try:
        if db.query(models.User).filter_by(id="student_haianh").first() is not None:
            logger.info("student_haianh already exists — nothing to do (idempotent no-op).")
            return

        now = _now()
        password_hash = hash_password(DEMO_PASSWORD)

        instructor = models.User(
            id="instructor_binh",
            email="instructor@example.com",
            password_hash=password_hash,
            full_name="Nguyễn Thanh Bình",
            role=models.UserRole.INSTRUCTOR.value,
            is_email_verified=True,
            is_active=True,
            created_at=now - timedelta(days=120),
        )
        admin = models.User(
            id="admin_chung",
            email="admin@example.com",
            password_hash=password_hash,
            full_name="Nguyễn Đức Chung",
            role=models.UserRole.ADMIN.value,
            is_email_verified=True,
            is_active=True,
            created_at=now - timedelta(days=120),
        )
        haianh = models.User(
            id="student_haianh",
            email="studenthaianh@example.com",
            password_hash=password_hash,
            full_name="Nguyễn Hải Anh",
            role=models.UserRole.STUDENT.value,
            is_email_verified=True,
            is_active=True,
            created_at=now - timedelta(days=60),
        )
        haidang = models.User(
            id="student_haidang",
            email="studenthaidang@example.com",
            password_hash=password_hash,
            full_name="Trịnh Hải Đăng",
            role=models.UserRole.STUDENT.value,
            is_email_verified=True,
            is_active=True,
            created_at=now - timedelta(days=60),
        )
        db.add_all([instructor, admin, haianh, haidang])
        db.flush()

        sections: dict[str, models.CourseSection] = {}
        for code in SHARED_COURSE_CODES:
            course = db.query(models.Course).filter_by(code=code).first()
            if course is None:
                logger.warning("course=%s not found — run ingest_subject_data.py first, skipping", code)
                continue
            section = models.CourseSection(
                id=f"sec_demo_{code.lower()}",
                course_id=course.id,
                instructor_id=instructor.id,
                term="Fall2026",
                section_code="DEMO01",
            )
            db.add(section)
            sections[code] = section
        db.flush()

        for code, section in sections.items():
            for student in (haianh, haidang):
                db.add(
                    models.Enrollment(
                        id=f"enr_demo_{student.id}_{code.lower()}",
                        student_id=student.id,
                        section_id=section.id,
                        status=models.EnrollmentStatus.ENROLLED.value,
                        enrolled_at=now - timedelta(days=45),
                    )
                )

        assignments: dict[str, models.Assignment] = {}
        for code, section in sections.items():
            assignment = models.Assignment(
                id=f"asg_demo_{code.lower()}",
                section_id=section.id,
                title=f"{code} — Weekly worksheet",
                description="Demo assignment seeded for the persona-demo accounts.",
                due_date=now + timedelta(days=5),
                max_points=100.0,
                assessment_type="ASSIGNMENT",
            )
            db.add(assignment)
            assignments[code] = assignment
        db.flush()

        for code, section in sections.items():
            db.add(
                models.ClassActivity(
                    id=f"act_demo_{code.lower()}",
                    course_id=section.course_id,
                    activity_date=(now + timedelta(days=3)).date(),
                    kind="ASSIGNMENT",
                    title=f"{code} — Nộp worksheet tuần",
                    created_by=instructor.id,
                )
            )

        # --- Weekly plan history: 3 weeks, contrasting completion rates ---
        weeks = [4, 5, 6]  # 6 = current week
        personas = {
            haianh.id: {"complete_ratio": 0.9, "on_track": True},
            haidang.id: {"complete_ratio": 0.3, "on_track": False},
        }

        for student in (haianh, haidang):
            persona = personas[student.id]
            for week_number in weeks:
                week_start = now - timedelta(weeks=(weeks[-1] - week_number))
                is_current_week = week_number == weeks[-1]
                plan_id = f"wplan_demo_{student.id}_w{week_number}"
                db.add(
                    models.WeeklyPlan(
                        id=plan_id,
                        student_id=student.id,
                        week_number=week_number,
                        goals={"statement": "Hoàn thành worksheet và ôn tập các môn trong tuần."},
                        study_hours_allocated=12.0,
                    )
                )
                total_tasks = 0
                completed_tasks = 0
                for day_index in range(5):  # Mon-Fri
                    day_date = week_start + timedelta(days=day_index)
                    daily_id = f"dplan_demo_{student.id}_w{week_number}_d{day_index}"
                    db.add(
                        models.DailyPlan(
                            id=daily_id,
                            weekly_plan_id=plan_id,
                            date=day_date,
                            status="IN_PROGRESS" if is_current_week else "COMPLETED",
                        )
                    )
                    block_id = f"block_demo_{student.id}_w{week_number}_d{day_index}"
                    db.add(
                        models.ScheduleBlock(
                            id=block_id,
                            daily_plan_id=daily_id,
                            start_time=day_date.replace(hour=19, minute=0),
                            end_time=day_date.replace(hour=21, minute=0),
                            activity_description="Buổi tự học buổi tối",
                        )
                    )
                    for task_index, (title, priority, difficulty) in enumerate(DAILY_TASK_TITLES):
                        total_tasks += 1
                        should_complete = total_tasks <= round(persona["complete_ratio"] * 10)
                        if is_current_week and not should_complete:
                            status = "TODO"
                        elif should_complete:
                            status = "COMPLETED"
                            completed_tasks += 1
                        else:
                            status = "MISSED"
                        planned = 60
                        db.add(
                            models.StudyTask(
                                id=f"task_demo_{student.id}_w{week_number}_d{day_index}_t{task_index}",
                                schedule_block_id=block_id,
                                assignment_id=assignments.get("CEA201").id if "CEA201" in assignments else None,
                                title=f"{title} ({list(sections)[0] if sections else 'chung'})",
                                planned_minutes=planned,
                                actual_minutes=planned - 5 if status == "COMPLETED" else None,
                                priority=priority,
                                status=status,
                                difficulty=difficulty,
                            )
                        )
                completion_rate = completed_tasks / total_tasks if total_tasks else 0.0
                reflection_text = (
                    (
                        f"Tuần {week_number}: hoàn thành {completed_tasks}/{total_tasks} nhiệm vụ. "
                        "Điểm sáng của tuần: giữ được nhịp học đều, nộp bài đúng hạn."
                    )
                    if persona["on_track"]
                    else (
                        f"Tuần {week_number}: chỉ hoàn thành {completed_tasks}/{total_tasks} nhiệm vụ. "
                        "Gặp khó khăn trong việc sắp xếp thời gian, có bài nộp trễ."
                    )
                )
                db.add(
                    models.WeeklyReflection(
                        id=f"reflect_demo_{student.id}_w{week_number}",
                        student_id=student.id,
                        week_number=week_number,
                        content=reflection_text,
                        generated_at=week_start + timedelta(days=6),
                        metrics={"completionRate": round(completion_rate, 2)},
                    )
                )
                db.flush()

                # One self-study Pomodoro session anchored to Monday's block.
                monday_block_id = f"block_demo_{student.id}_w{week_number}_d0"
                sss_status = "COMPLETED" if persona["on_track"] or not is_current_week else "ABANDONED"
                started = week_start.replace(hour=19, minute=0)
                db.add(
                    models.SelfStudySession(
                        id=f"sss_demo_{student.id}_w{week_number}",
                        student_id=student.id,
                        schedule_block_id=monday_block_id,
                        title="Phiên tự học buổi tối",
                        planned_minutes=60,
                        started_at=started,
                        scheduled_end_at=started + timedelta(minutes=60),
                        ended_at=started + timedelta(minutes=60 if sss_status == "COMPLETED" else 20),
                        actual_minutes=60 if sss_status == "COMPLETED" else 20,
                        pomodoros_completed=2 if sss_status == "COMPLETED" else 1,
                        status=sss_status,
                    )
                )

        # --- Risk signals (Hải Đăng only) — real DB rows so the instructor
        # queue and /admin/analytics/summary have something genuine to show.
        active_policy = (
            db.query(models.RiskPolicy).filter_by(is_active=True).first()
        )
        policy_version = active_policy.policy_version if active_policy else "v1"
        risk_section = sections.get("CEA201") or next(iter(sections.values()))
        db.add(
            models.RiskSignal(
                id="risk_demo_haidang_1",
                student_id=haidang.id,
                section_id=risk_section.id,
                assignment_id=assignments.get(next(iter(sections))).id if sections else None,
                risk_type="WEEKLY_GOAL_FAILURE",
                risk_level="HIGH",
                triggered_rules={"rule": "completion_rate_below_threshold"},
                evidence={"note": "Tỷ lệ hoàn thành nhiệm vụ dưới 50% trong nhiều tuần liên tiếp."},
                recommended_action="Liên hệ sinh viên để tìm hiểu khó khăn và lên kế hoạch hỗ trợ.",
                generated_at=now - timedelta(days=2),
                resolved_at=None,
                resolution_type=None,
                policy_version=policy_version,
            )
        )
        second_section = (
            sections.get("SSA101") or [s for s in sections.values() if s.id != risk_section.id][0]
        )
        db.add(
            models.RiskSignal(
                id="risk_demo_haidang_2",
                student_id=haidang.id,
                section_id=second_section.id,
                assignment_id=None,
                risk_type="LATE_SUBMISSION",
                risk_level="MEDIUM",
                triggered_rules={"rule": "late_submission_streak"},
                evidence={"note": "Nộp bài trễ 2 lần liên tiếp."},
                recommended_action="Nhắc nhở deadline và đề xuất chia nhỏ công việc.",
                generated_at=now - timedelta(days=5),
                resolved_at=None,
                resolution_type=None,
                policy_version=policy_version,
            )
        )

        # Hải Đăng trips the academic-integrity guardrail (feeds the
        # instructor Appeal queue). Chat feature removed -- GuardrailEvent no
        # longer needs a Conversation/Message to attach to, it's written
        # with student_id/section_id directly.
        db.add(
            models.GuardrailEvent(
                id="grail_demo_haidang",
                student_id=haidang.id,
                section_id=sections.get("CSI106").id if "CSI106" in sections else None,
                classification="BLOCKED",
                safety_evaluation={"reason": "academic_integrity"},
                review_status="PENDING",
                block_reason="academic_integrity",
                blocked_answer=(
                    "Mình không thể giải trọn bài hộ bạn vì điều đó vi phạm liêm chính học thuật — "
                    "nhưng mình có thể hướng dẫn từng bước để bạn tự làm."
                ),
                reviewed_by=None,
                reviewed_at=None,
            )
        )

        db.commit()
        logger.info(
            "Seeded users: %s, %s, %s, %s across %s shared course sections.",
            instructor.id, admin.id, haianh.id, haidang.id, len(sections),
        )

        # --- Practice sets: one real, generated pack per shared course ---
        practice_repo = PracticeSetRepository(db)
        for code, section in sections.items():
            course = db.query(models.Course).filter_by(id=section.course_id).first()
            existing_week = None
            for week_number in range(1, 11):
                slide_key_guess = f"slot_{week_number:02d}"
                if practice_repo.get_by_slide(course.code, slide_key_guess) is None:
                    existing_week = week_number
                    break
            if existing_week is None:
                logger.warning("course=%s has no free week slot for a demo practice set, skipping", code)
                continue
            try:
                specs, slide_key = generate_pack(
                    subject_code=course.code, week_number=existing_week, language="vi"
                )
            except ValueError as exc:
                logger.warning("course=%s practice generation skipped: %s", code, exc)
                continue
            row = practice_repo.add_set(
                course_id=course.id,
                course_code=course.code,
                slide_key=slide_key,
                week_number=existing_week,
                language="vi",
                requested_by=haianh.id,
                status="PENDING",
            )
            practice_repo.replace_items(row, specs)
            row.status = "APPROVED"
            row.reviewed_by = instructor.id
            row.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
            practice_repo.commit()
            logger.info("practice set seeded course=%s week=%s items=%s", code, existing_week, len(specs))

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
