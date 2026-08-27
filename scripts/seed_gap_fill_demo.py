"""Fill the gaps left in the 'Cursus Demo University' sandbox (org_cursus_demo)
so every screen for all 3 roles has real, varied data to show on a demo
recording — not empty states.

Scope: purely additive. Never deletes or overwrites existing rows (except
flipping a few pre-existing TODO StudyTask rows to COMPLETED/MISSED so their
week has a real completion story, and deactivating the previous
GuardrailPolicyVersion/marking a superseded RiskPolicy — both are the exact
"publish a new version" action those screens exist to demo).

Targets the 3 one-click demo accounts (POST /auth/demo-session, see
src/api/demo.py + DemoSelectRoleScreen.jsx):
  demo.student@cursusdemo.local     (STUDENT_A)
  demo.instructor@cursusdemo.local  (INSTRUCTOR)
  demo.admin@cursusdemo.local       (ADMIN)
plus the 2 named accounts already seeded by scripts/seed_extra_users.py as a
second/third student for contrast:
  studenthaianh@example.com   (STUDENT_B, doing well)
  studenthaidang@example.com  (STUDENT_C, at risk)

Idempotent: every block checks for its own sentinel id(s) before inserting,
so re-running finds nothing to do the second time.

Usage (inside the backend container):
    python scripts/seed_gap_fill_demo.py
"""

from __future__ import annotations

import logging
import sys
import uuid
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed-gap-fill-demo")

ORG_ID = "org_cursus_demo"

# Re-verified 25/08 by reading this exact Supabase project directly (read-only)
# -- the IDs below (an earlier draft of this script guessed at, from a
# different environment) did not match a single row here: 0 of the section/
# assignment/plan IDs existed, and 2 of the 3 demo-account IDs were wrong too.
# See scripts/sql/sync_schema_before_deploy.sql history for the same class of
# gap on this DB. Every constant below was looked up by email/course-code/
# title against production before being pasted in.
STUDENT_A = "user_49d39d8389344420ba4b626f4996fae8"   # demo.student@cursusdemo.local
STUDENT_B = "student_haianh"                          # studenthaianh@example.com
STUDENT_C = "student_haidang"                         # studenthaidang@example.com
INSTRUCTOR = "user_940824b10da6420183f101e6d7659482"  # demo.instructor@cursusdemo.local
ADMIN = "user_97d787e9a4ab4154af12504d86eb63a1"       # demo.admin@cursusdemo.local

# STUDENT_A's own private per-student sections (see
# StudentMockDataService._ensure_student_sections -- deterministic
# sha256(student_id)[:8] suffix, one section per non-SSA101 course).
SEC_CEA201 = "section_mock_cea201_43ae07ae"
SEC_CSI106 = "section_mock_csi106_43ae07ae"
SEC_PRF192 = "section_mock_prf192_43ae07ae"
# SSA101 is the one shared Gate-2 class (Gate2DemoService) -- this is the
# section the real "SSA101 Group Project -- Part 1" assignment belongs to,
# confirmed via GET /student/dashboard on production.
SEC_SSA101 = "section_gate2_ssa101_se_k20"

ASG_LAB02 = "asg_mock_section_mock_prf192_43ae07ae_lab02"
ASG_CPU = "asg_mock_section_mock_cea201_43ae07ae_worksheet_cpu"
ASG_ALGO = "asg_mock_section_mock_csi106_43ae07ae_algo_worksheet"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _monday_on_or_before(d: date) -> date:
    return d - timedelta(days=d.weekday())


def seed_enrollments(db) -> None:
    from src.db import models

    now = _now()
    for student_id in (STUDENT_B, STUDENT_C):
        for section_id in (SEC_CEA201, SEC_CSI106, SEC_PRF192, SEC_SSA101):
            enr_id = f"enr_g3_{student_id}_{section_id}"
            exists = (
                db.query(models.Enrollment)
                .filter_by(student_id=student_id, section_id=section_id)
                .first()
            )
            if exists:
                continue
            db.add(
                models.Enrollment(
                    id=enr_id,
                    student_id=student_id,
                    section_id=section_id,
                    status=models.EnrollmentStatus.ENROLLED.value,
                    enrolled_at=now - timedelta(days=20),
                )
            )
    db.commit()
    logger.info("enrollments_ok")


def seed_academic_term_and_exams(db) -> None:
    from src.db import models

    # Reuse the org's existing active term rather than inserting a second
    # is_active=True row -- production already has one (term_de51bc295185,
    # "Fall 2026", start 2026-07-20); app code that does
    # .filter_by(is_active=True).first() would otherwise become ambiguous.
    term = (
        db.query(models.AcademicTerm)
        .filter_by(organization_id=ORG_ID, is_active=True)
        .first()
    )
    if term is None:
        start = _monday_on_or_before(date.today()) - timedelta(weeks=3)
        term = models.AcademicTerm(
            id="term_cursus_demo_fall2026",
            organization_id=ORG_ID,
            name="Fall 2026",
            start_date=start,
            study_weeks=10,
            exam_weeks=2,
            is_active=True,
            created_at=_now(),
        )
        db.add(term)
        db.commit()
        logger.info("academic_term_created start=%s", start)
    else:
        logger.info("academic_term_exists id=%s", term.id)

    course_ids = ["course_mock_cea201", "course_mock_csi106", "course_mock_prf192", "course_mock_ssa101"]
    existing_exam_courses = {
        row[0] for row in db.query(models.CourseExam.course_id).filter_by(term_id=term.id).all()
    }
    midterm_date = term.start_date + timedelta(weeks=5)
    final_date = term.start_date + timedelta(weeks=9)
    for course_id in course_ids:
        if course_id in existing_exam_courses:
            continue
        midterm = models.CourseExam(id=f"exam_g3_{course_id}_mid", term_id=term.id, course_id=course_id, kind="MIDTERM")
        final = models.CourseExam(id=f"exam_g3_{course_id}_final", term_id=term.id, course_id=course_id, kind="FINAL")
        db.add_all([midterm, final])
        db.flush()
        db.add(
            models.CourseExamSession(
                id=f"exsess_g3_{course_id}_mid", exam_id=midterm.id, exam_date=midterm_date, slot_id=3, label="Ca 1"
            )
        )
        db.add(
            models.CourseExamSession(
                id=f"exsess_g3_{course_id}_final", exam_id=final.id, exam_date=final_date, slot_id=3, label="Ca 1"
            )
        )
    db.commit()
    logger.info("course_exams_ok")


def seed_class_activities(db) -> None:
    from src.db import models

    course_codes = {
        "course_mock_cea201": "CEA201",
        "course_mock_csi106": "CSI106",
        "course_mock_prf192": "PRF192",
    }
    now = _now()
    for course_id, code in course_codes.items():
        marker = f"act_g3_{course_id}_1"
        if db.query(models.ClassActivity).filter_by(id=marker).first():
            continue
        db.add_all(
            [
                models.ClassActivity(
                    id=marker,
                    course_id=course_id,
                    activity_date=(now - timedelta(days=10)).date(),
                    kind="LECTURE_HELD",
                    title=f"{code} — Buổi học tuần 3",
                    created_by=INSTRUCTOR,
                    created_at=now - timedelta(days=10),
                ),
                models.ClassActivity(
                    id=f"act_g3_{course_id}_2",
                    course_id=course_id,
                    activity_date=(now - timedelta(days=3)).date(),
                    kind="LECTURE_HELD",
                    title=f"{code} — Buổi học tuần 4",
                    created_by=INSTRUCTOR,
                    created_at=now - timedelta(days=3),
                ),
                models.ClassActivity(
                    id=f"act_g3_{course_id}_3",
                    course_id=course_id,
                    activity_date=(now + timedelta(days=2)).date(),
                    kind="CANCELLED",
                    title=f"{code} — Nghỉ do lịch trường",
                    created_by=INSTRUCTOR,
                    created_at=now,
                ),
            ]
        )
    db.commit()
    logger.info("class_activities_ok")


def seed_quizzes(db) -> None:
    from src.db import models

    now = _now()

    if not db.query(models.Quiz).filter_by(id="quiz_g3_prf192").first():
        quiz = models.Quiz(
            id="quiz_g3_prf192",
            section_id=SEC_PRF192,
            title="PRF192 — Quiz: Vòng lặp & Mảng",
            description="Ôn tập nhanh về for/while và mảng một chiều trong C.",
            time_limit_minutes=20,
            due_date=now + timedelta(days=5),
            max_points=10.0,
            created_by=INSTRUCTOR,
            is_published=True,
            opens_at=now - timedelta(days=2),
        )
        db.add(quiz)
        db.flush()
        questions = [
            ("Vòng lặp nào phù hợp nhất khi biết trước số lần lặp?",
             {"A": "for", "B": "while", "C": "do-while", "D": "if"}, "A"),
            ("Chỉ số phần tử đầu tiên của mảng trong C là?",
             {"A": "1", "B": "0", "C": "-1", "D": "Tuỳ trình biên dịch"}, "B"),
            ("Khai báo int arr[5]; tạo ra mảng có bao nhiêu phần tử?",
             {"A": "4", "B": "5", "C": "6", "D": "Không xác định"}, "B"),
        ]
        for index, (text, options, correct) in enumerate(questions):
            db.add(
                models.QuizQuestion(
                    id=f"qq_g3_prf192_{index}",
                    quiz_id=quiz.id,
                    question_text=text,
                    question_type="MULTIPLE_CHOICE",
                    correct_answer=correct,
                    options=options,
                    points=2.5,
                    order_index=index,
                )
            )
        db.add(
            models.QuizQuestion(
                id="qq_g3_prf192_3",
                quiz_id=quiz.id,
                question_text="Giải thích ngắn gọn sự khác biệt giữa vòng lặp for và while.",
                question_type="SHORT_ANSWER",
                correct_answer="",
                options={},
                points=2.5,
                order_index=3,
            )
        )
        db.commit()
        logger.info("quiz_prf192_created")

    if not db.query(models.Quiz).filter_by(id="quiz_g3_csi106").first():
        quiz = models.Quiz(
            id="quiz_g3_csi106",
            section_id=SEC_CSI106,
            title="CSI106 — Quiz: Biểu diễn dữ liệu",
            description="Kiểm tra nhanh về hệ nhị phân và đơn vị đo dữ liệu.",
            time_limit_minutes=15,
            due_date=now - timedelta(days=1),
            max_points=10.0,
            created_by=INSTRUCTOR,
            is_published=True,
            opens_at=now - timedelta(days=6),
        )
        db.add(quiz)
        db.flush()
        questions = [
            ("Số nhị phân 1010 tương ứng với số thập phân nào?",
             {"A": "8", "B": "10", "C": "12", "D": "9"}, "B", 3.34),
            ("1 byte bằng bao nhiêu bit?",
             {"A": "4", "B": "8", "C": "16", "D": "32"}, "B", 3.33),
            ("Đơn vị nào thường dùng để đo tốc độ xử lý của CPU?",
             {"A": "Hz", "B": "Byte", "C": "Bit", "D": "Watt"}, "A", 3.33),
        ]
        for index, (text, options, correct, points) in enumerate(questions):
            db.add(
                models.QuizQuestion(
                    id=f"qq_g3_csi106_{index}",
                    quiz_id=quiz.id,
                    question_text=text,
                    question_type="MULTIPLE_CHOICE",
                    correct_answer=correct,
                    options=options,
                    points=points,
                    order_index=index,
                )
            )
        db.commit()
        logger.info("quiz_csi106_created")


def _grade_mc(correct_answer: str, given: str, points: float) -> dict:
    is_correct = given.strip().lower() == correct_answer.strip().lower()
    return {"correct": is_correct, "points_awarded": points if is_correct else 0.0}


def seed_quiz_submissions(db) -> None:
    from src.db import models

    now = _now()

    if not db.query(models.Submission).filter_by(id="sub_g3_prf192_studentA").first():
        prf_questions = (
            db.query(models.QuizQuestion)
            .filter_by(quiz_id="quiz_g3_prf192")
            .order_by(models.QuizQuestion.order_index)
            .all()
        )
        answers = {
            prf_questions[0].id: "A",
            prf_questions[1].id: "B",
            prf_questions[2].id: "B",
            prf_questions[3].id: (
                "for dùng khi biết trước số lần lặp, while dùng khi số lần lặp phụ thuộc điều kiện "
                "chưa biết trước."
            ),
        }
        results = {
            prf_questions[0].id: _grade_mc(prf_questions[0].correct_answer, answers[prf_questions[0].id], prf_questions[0].points),
            prf_questions[1].id: _grade_mc(prf_questions[1].correct_answer, answers[prf_questions[1].id], prf_questions[1].points),
            prf_questions[2].id: _grade_mc(prf_questions[2].correct_answer, answers[prf_questions[2].id], prf_questions[2].points),
            prf_questions[3].id: {"correct": None, "points_awarded": None},  # SHORT_ANSWER — cần GV chấm tay
        }
        earned = sum(r.get("points_awarded") or 0 for r in results.values())
        db.add(
            models.Submission(
                id="sub_g3_prf192_studentA",
                assignment_id=None,
                quiz_id="quiz_g3_prf192",
                student_id=STUDENT_A,
                submitted_at=now - timedelta(days=1),
                content={"answers": answers, "results": results},
                grading_status="PENDING",  # còn câu tự luận chưa chấm
                grade=round(earned / 10.0 * 100, 1),
                is_late=False,
            )
        )
        db.commit()
        logger.info("quiz_submission_prf192_studentA_created")

    csi_questions = (
        db.query(models.QuizQuestion)
        .filter_by(quiz_id="quiz_g3_csi106")
        .order_by(models.QuizQuestion.order_index)
        .all()
    )
    if csi_questions and not db.query(models.Submission).filter_by(id="sub_g3_csi106_studentB").first():
        answers_b = {q.id: q.correct_answer for q in csi_questions}
        results_b = {q.id: {"correct": True, "points_awarded": q.points} for q in csi_questions}
        db.add(
            models.Submission(
                id="sub_g3_csi106_studentB",
                assignment_id=None,
                quiz_id="quiz_g3_csi106",
                student_id=STUDENT_B,
                submitted_at=now - timedelta(days=2),
                content={"answers": answers_b, "results": results_b},
                grading_status="GRADED",
                grade=100.0,
                is_late=False,
            )
        )
        logger.info("quiz_submission_csi106_studentB_created")

    if csi_questions and not db.query(models.Submission).filter_by(id="sub_g3_csi106_studentC").first():
        answers_c = {q.id: q.correct_answer for q in csi_questions}
        wrong_q = csi_questions[0]
        wrong_option = next(k for k in wrong_q.options if k != wrong_q.correct_answer)
        answers_c[wrong_q.id] = wrong_option
        results_c = {}
        earned = 0.0
        for q in csi_questions:
            r = _grade_mc(q.correct_answer, answers_c[q.id], q.points)
            results_c[q.id] = r
            earned += r["points_awarded"]
        db.add(
            models.Submission(
                id="sub_g3_csi106_studentC",
                assignment_id=None,
                quiz_id="quiz_g3_csi106",
                student_id=STUDENT_C,
                submitted_at=now,  # nộp sau hạn (due_date đã qua)
                content={"answers": answers_c, "results": results_c},
                grading_status="GRADED",
                grade=round(earned / 10.0 * 100, 1),
                is_late=True,
            )
        )
        logger.info("quiz_submission_csi106_studentC_created")
    db.commit()


def seed_assignment_submissions(db) -> None:
    from src.db import models

    now = _now()
    rows = [
        dict(
            id="sub_g3_lab02_studentA", assignment_id=ASG_LAB02, student_id=STUDENT_A,
            submitted_at=now - timedelta(days=4),
            content={"text": "Đã hoàn thành vòng lặp đếm và mảng tích lũy, có test với 3 bộ dữ liệu mẫu."},
            grading_status="GRADED", grade=92.0,
            feedback="Code chạy đúng, style rõ ràng. Nhớ kiểm tra biên mảng khi n=0.", is_late=False,
        ),
        dict(
            id="sub_g3_lab02_studentC", assignment_id=ASG_LAB02, student_id=STUDENT_C,
            submitted_at=now - timedelta(days=1),
            content={"text": "Nộp bài, còn thiếu phần vòng lặp lồng nhau nên chưa test kỹ."},
            grading_status="GRADED", grade=55.0,
            feedback="Thiếu xử lý vòng lặp lồng nhau, xem lại ví dụ buổi 3 và nộp lại phần bù nếu được.",
            is_late=True,
        ),
        dict(
            id="sub_g3_cpu_studentB", assignment_id=ASG_CPU, student_id=STUDENT_B,
            submitted_at=now - timedelta(days=2),
            content={"text": "Vẽ đầy đủ datapath, giải thích luồng tín hiệu điều khiển qua từng giai đoạn."},
            grading_status="GRADED", grade=95.0,
            feedback="Giải thích rất mạch lạc, đúng trọng tâm.", is_late=False,
        ),
        dict(
            id="sub_g3_cpu_studentA", assignment_id=ASG_CPU, student_id=STUDENT_A,
            submitted_at=now - timedelta(hours=6),
            content={"text": "Worksheet CPU datapath đã nộp, có sơ đồ kèm giải thích ngắn."},
            grading_status="PENDING", grade=None, feedback=None, is_late=False,
        ),
        dict(
            id="sub_g3_algo_studentA", assignment_id=ASG_ALGO, student_id=STUDENT_A,
            submitted_at=now - timedelta(hours=1),
            content={"text": "Bài tập thuật toán sắp xếp — đã nộp bản giải chi tiết từng bước."},
            grading_status="PENDING", grade=None, feedback=None, is_late=False,
        ),
    ]
    created = 0
    for row in rows:
        if db.query(models.Submission).filter_by(id=row["id"]).first():
            continue
        db.add(models.Submission(**row))
        created += 1
    db.commit()
    logger.info("assignment_submissions_ok created=%s", created)


def seed_reflections_and_tasks(db) -> None:
    from src.db import models

    now = _now()

    # NOTE: the original draft of this function also fabricated a "week 1"
    # completion story and filled 2 empty days on a "current week" plan for
    # STUDENT_A (demo.student), keyed off plan_0ddfe3b0 / plan_ec40bb4427.
    # Neither plan exists on this Supabase project -- STUDENT_A already has
    # a real, organic Plan-Do-Reflect history here (weeks 3/4/34/35/36, with
    # reflections already generated for 3/4/34/35), so that part was dropped
    # rather than bolted onto plan IDs that don't exist here.

    # --- student_haianh (STUDENT_B) week 6 — doing well
    haianh_task = (
        db.query(models.StudyTask)
        .join(models.ScheduleBlock, models.ScheduleBlock.id == models.StudyTask.schedule_block_id)
        .join(models.DailyPlan, models.DailyPlan.id == models.ScheduleBlock.daily_plan_id)
        .filter(models.DailyPlan.weekly_plan_id == "plan_student_haianh_custom_w6")
        .first()
    )
    if haianh_task and not db.query(models.WeeklyReflection).filter_by(id="reflect_g3_studentB_w6").first():
        haianh_task.status = "COMPLETED"
        haianh_task.actual_minutes = (haianh_task.planned_minutes or 60) - 10
        db.add(
            models.WeeklyReflection(
                id="reflect_g3_studentB_w6",
                student_id=STUDENT_B,
                week_number=6,
                content="Tuần 6: hoàn thành đầy đủ nhiệm vụ, nộp bài đúng hạn cho cả 4 môn.",
                generated_at=now - timedelta(days=2),
                metrics={"completionRate": 1.0},
            )
        )
        logger.info("reflection_studentB_w6_created")

    # --- student_haidang (STUDENT_C) week 6 — struggling
    haidang_task = (
        db.query(models.StudyTask)
        .join(models.ScheduleBlock, models.ScheduleBlock.id == models.StudyTask.schedule_block_id)
        .join(models.DailyPlan, models.DailyPlan.id == models.ScheduleBlock.daily_plan_id)
        .filter(models.DailyPlan.weekly_plan_id == "plan_student_haidang_custom_w6")
        .first()
    )
    if haidang_task and not db.query(models.WeeklyReflection).filter_by(id="reflect_g3_studentC_w6").first():
        haidang_task.status = "MISSED"
        db.add(
            models.WeeklyReflection(
                id="reflect_g3_studentC_w6",
                student_id=STUDENT_C,
                week_number=6,
                content=(
                    "Tuần 6: chỉ hoàn thành 1 phần nhỏ kế hoạch. Gặp khó khăn sắp xếp thời gian giữa "
                    "các môn, có bài nộp trễ."
                ),
                generated_at=now - timedelta(days=2),
                metrics={"completionRate": 0.2},
            )
        )
        logger.info("reflection_studentC_w6_created")

    db.commit()


def seed_self_study_sessions(db) -> None:
    from src.db import models

    if db.query(models.SelfStudySession).filter_by(id="sss_g3_studentA_1").first():
        return

    # Original draft hung these off plan_0ddfe3b0, which doesn't exist on
    # this project. week_number=20 is unused by STUDENT_A's real plans
    # (3/4/6/34/35/36), chosen so this doesn't collide with or get read as
    # part of that organic history.
    plan = models.WeeklyPlan(
        id="plan_g3_selfstudy_studentA",
        student_id=STUDENT_A,
        week_number=20,
        goals={"note": "Lich su phien tu hoc mau (demo)"},
        study_hours_allocated=3.0,
    )
    db.add(plan)
    db.flush()

    now = _now()
    week1_start = now - timedelta(days=20)
    for index in range(2):
        day = week1_start + timedelta(days=index)
        daily = models.DailyPlan(
            id=f"dp_g3_selfstudy_{index}",
            weekly_plan_id=plan.id,
            date=day,
            status="COMPLETED",
        )
        db.add(daily)
        db.flush()
        block = models.ScheduleBlock(
            id=f"sb_g3_selfstudy_{index}",
            daily_plan_id=daily.id,
            start_time=day.replace(hour=19, minute=30),
            end_time=day.replace(hour=21, minute=0),
            activity_description="Phiên tự học buổi tối",
        )
        db.add(block)
        db.flush()
        started = day.replace(hour=19, minute=30)
        actual = 75 if index == 0 else 45
        db.add(
            models.SelfStudySession(
                id=f"sss_g3_studentA_{index + 1}",
                student_id=STUDENT_A,
                schedule_block_id=block.id,
                title="Phiên tự học buổi tối",
                planned_minutes=90,
                started_at=started,
                scheduled_end_at=started + timedelta(minutes=90),
                ended_at=started + timedelta(minutes=actual),
                actual_minutes=actual,
                pomodoros_completed=max(1, actual // 25),
                status="COMPLETED",
            )
        )
    db.commit()
    logger.info("self_study_sessions_ok")


def seed_conversations(db) -> None:
    """Chat feature removed -- GuardrailEvent no longer needs a
    Conversation/Message to attach to, it's written with student_id/
    section_id directly (see migrations/versions/
    20260910_remove_chatbot_feature.py)."""
    from src.db import models

    now = _now()

    if not db.query(models.GuardrailEvent).filter_by(id="grail_g3_studentA").first():
        blocked_answer = (
            "Mình không thể viết trọn bài hộ bạn vì bài này được chấm điểm cá nhân — nhưng mình có "
            "thể hướng dẫn từng bước để bạn tự hoàn thành."
        )
        db.add(models.GuardrailEvent(
            id="grail_g3_studentA", student_id=STUDENT_A, section_id=SEC_PRF192,
            classification="BLOCKED",
            safety_evaluation={"reason": "HOMEWORK_VI", "question": "Viết hộ em toàn bộ code bài Lab 2 với, em nộp gấp trong 10 phút nữa."},
            review_status="PENDING",
            block_reason="HOMEWORK_VI", blocked_answer=blocked_answer,
            reviewed_by=None, reviewed_at=None, created_at=now - timedelta(hours=5),
        ))
        logger.info("guardrail_event_studentA_created")

    if not db.query(models.GuardrailEvent).filter_by(id="grail_g3_studentC").first():
        blocked_answer = "Mình không thể làm trọn bài hộ bạn — bài này tính điểm cá nhân theo quy chế."
        db.add(models.GuardrailEvent(
            id="grail_g3_studentC", student_id=STUDENT_C, section_id=SEC_CEA201,
            classification="BLOCKED",
            safety_evaluation={"reason": "FULL_CODE", "question": "Giải hết bài worksheet CPU này cho em với, viết full code luôn nhé."},
            review_status="KEPT_BLOCKED",
            block_reason="FULL_CODE", blocked_answer=blocked_answer,
            reviewed_by=INSTRUCTOR, reviewed_at=now - timedelta(days=2),
            reviewer_note="Đã xác nhận đúng là yêu cầu làm hộ toàn bộ bài. Giữ chặn, đã nhắc SV đến giờ OH.",
            created_at=now - timedelta(days=3),
        ))
        logger.info("guardrail_event_studentC_created")

    db.commit()


def seed_risk_and_notes(db) -> None:
    from src.db import models

    latest_policy = (
        db.query(models.RiskPolicy).order_by(models.RiskPolicy.policy_version.desc()).first()
    )
    policy_version = latest_policy.policy_version if latest_policy else None
    now = _now()

    if not db.query(models.RiskSignal).filter_by(id="risk_g3_studentC_abandon").first():
        db.add(models.RiskSignal(
            id="risk_g3_studentC_abandon", student_id=STUDENT_C, section_id=SEC_CEA201,
            assignment_id=ASG_CPU, risk_type="ABANDONMENT", risk_level="HIGH",
            triggered_rules={"rule": "inactive_7_days"},
            evidence={"note": "Không có hoạt động học tập trong 8 ngày liên tiếp trên CEA201."},
            recommended_action="Liên hệ trực tiếp để tìm hiểu khó khăn và đề xuất kế hoạch bắt kịp.",
            generated_at=now - timedelta(days=1), resolved_at=None, resolution_type=None,
            policy_version=policy_version,
        ))
        db.flush()
        db.add(models.InstructorIntervention(
            id="intv_g3_studentC_abandon", risk_signal_id="risk_g3_studentC_abandon",
            instructor_id=INSTRUCTOR, action_taken="Đã gửi email nhắc nộp bài và đề xuất buổi gặp trực tiếp.",
            status="ACTIVE", created_at=now - timedelta(hours=12),
        ))
        logger.info("risk_studentC_abandon_created")

    if not db.query(models.RiskSignal).filter_by(id="risk_g3_studentA_goal").first():
        db.add(models.RiskSignal(
            id="risk_g3_studentA_goal", student_id=STUDENT_A, section_id=SEC_PRF192,
            assignment_id=None, risk_type="WEEKLY_GOAL_FAILURE", risk_level="LOW",
            triggered_rules={"rule": "completion_rate_below_threshold"},
            evidence={"note": "Hoàn thành 60% nhiệm vụ tuần 1, dưới mục tiêu 80%."},
            recommended_action="Nhắc nhở nhẹ, theo dõi tuần kế tiếp.",
            generated_at=now - timedelta(days=13), resolved_at=now - timedelta(days=10),
            resolved_by=INSTRUCTOR, resolution_type="MONITORED",
            policy_version=policy_version,
            instructor_note="Đã nhắc nhở, SV cải thiện rõ ở tuần sau.",
        ))
        logger.info("risk_studentA_goal_created")

    if not db.query(models.InstructorStudentNote).filter_by(id="note_g3_instructor_studentC").first():
        db.add(models.InstructorStudentNote(
            id="note_g3_instructor_studentC", instructor_id=INSTRUCTOR, student_id=STUDENT_C,
            content="Cần theo dõi sát tuần này — có dấu hiệu quá tải khi học song song nhiều môn.",
            created_at=now - timedelta(hours=10),
        ))
        logger.info("note_created")

    db.commit()


def seed_admin_extras(db) -> None:
    from src.db import models
    from src.repositories.guardrail_rule_repository import GuardrailRuleRepository
    from src.services.ai.risk_engine import DEFAULT_SIGNAL_THRESHOLDS, DEFAULT_SIGNAL_WEIGHTS
    from src.services.core.risk_policy_service import validate_policy_input

    now = _now()

    if not db.query(models.AdminAnnouncement).filter_by(id="ann_g3_1").first():
        db.add_all([
            models.AdminAnnouncement(
                id="ann_g3_1", title="Cập nhật lịch thi giữa kỳ Fall 2026",
                content="Lịch thi giữa kỳ đã được publish trong Term & Exams. Vui lòng rà soát ca thi của lớp mình.",
                created_by=ADMIN, created_at=now - timedelta(days=3),
            ),
            models.AdminAnnouncement(
                id="ann_g3_2", title="Nhắc quy trình rà soát Guardrail hàng tuần",
                content="Đề nghị các giảng viên xử lý hàng chờ Guardrail Review trước cuối tuần.",
                created_by=ADMIN, created_at=now - timedelta(days=1),
            ),
        ])
        logger.info("admin_announcements_created")

    if not db.query(models.DataRequest).filter_by(id="dr_g3_1").first():
        db.add_all([
            models.DataRequest(
                id="dr_g3_1", requester_id=STUDENT_A, organization_id=ORG_ID,
                request_type="ACCESS", status="PENDING", created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1),
            ),
            models.DataRequest(
                id="dr_g3_2", requester_id=STUDENT_B, organization_id=ORG_ID,
                request_type="EXPORT", status="PENDING", created_at=now - timedelta(hours=6),
                updated_at=now - timedelta(hours=6),
            ),
            models.DataRequest(
                id="dr_g3_3", requester_id=STUDENT_C, organization_id=ORG_ID,
                request_type="ACCESS", status="COMPLETED", processed_by=ADMIN,
                admin_notes="Đã gửi bản xuất dữ liệu qua email đăng ký.",
                result_summary={"records_exported": 42},
                created_at=now - timedelta(days=6), updated_at=now - timedelta(days=5),
            ),
        ])
        logger.info("data_requests_created")

    if not db.query(models.RiskPolicy).filter_by(policy_version=2).first():
        v1 = db.query(models.RiskPolicy).filter_by(policy_version=1).first()
        if v1 is not None:
            # v1 comes from migration 20260823, whose hardcoded JSON predates
            # SELF_REPORTED_HIGH_STRESS. Merge the current defaults underneath
            # so validate_policy_input() sees every required code — the same
            # thing GET /admin/risk-policy does before handing over the form.
            new_weights = {**DEFAULT_SIGNAL_WEIGHTS, **v1.signal_weights}
            new_weights["OVERDUE_TASKS_2_PLUS"] = 2.5
            new_thresholds = {**DEFAULT_SIGNAL_THRESHOLDS, **v1.signal_thresholds}
            new_thresholds["COMPLETION_BELOW_40"] = 0.35
            validate_policy_input(new_weights, new_thresholds, v1.severity_bands)
            db.add(models.RiskPolicy(
                policy_version=2, effective_from=now, signal_weights=new_weights,
                signal_thresholds=new_thresholds, severity_bands=v1.severity_bands,
                reason="Tăng trọng số nộp trễ và hạ ngưỡng hoàn thành theo phản hồi GV học kỳ Fall2026.",
                rolled_back_from=None, created_by=ADMIN, created_at=now,
            ))
            logger.info("risk_policy_v2_created")

    guardrail_repo = GuardrailRuleRepository(db)
    guardrail_repo.ensure_seeded()
    db.commit()

    if not db.query(models.GuardrailPolicyVersion).filter_by(version="gpv_g3_2").first():
        prev = db.query(models.GuardrailPolicyVersion).filter_by(is_active=True).first()
        rules = guardrail_repo.list_rules()
        if prev is not None:
            prev.is_active = False
        db.add(models.GuardrailPolicyVersion(
            version="gpv_g3_2",
            rules_snapshot={rule.code: rule.enabled for rule in rules},
            source_version=prev.version if prev else None,
            change_reason="Bổ sung đầy đủ 5 nhóm quy tắc theo blueprint §4.2 (rà soát định kỳ).",
            is_active=True, created_by=ADMIN, created_at=now,
        ))
        for rule in rules:
            rule.current_version = "gpv_g3_2"
        logger.info("guardrail_policy_v2_created")

    db.commit()


def seed_practice_set(db) -> None:
    from src.db.models import Course
    from src.repositories.practice_set_repository import PracticeSetRepository
    from src.services.academic.practice_generator import generate_pack

    repo = PracticeSetRepository(db)
    course = db.query(Course).filter_by(id="course_mock_cea201").first()
    if course is None:
        logger.warning("practice_set_skipped_no_course")
        return
    for week_number in range(1, 11):
        slide_key_guess = f"slot_{week_number:02d}"
        if repo.get_by_slide(course.code, slide_key_guess) is None:
            try:
                specs, slide_key = generate_pack(
                    db=db, subject_code=course.code, week_number=week_number, language="vi"
                )
            except ValueError:
                continue
            row = repo.add_set(
                course_id=course.id, course_code=course.code, slide_key=slide_key,
                week_number=week_number, language="vi", requested_by=STUDENT_A, status="PENDING",
            )
            repo.replace_items(row, specs)
            row.status = "PUBLISHED"
            row.reviewed_by = INSTRUCTOR
            row.reviewed_at = _now()
            repo.commit()
            logger.info("practice_set_created course=%s week=%s items=%s", course.code, week_number, len(specs))
            return
    logger.info("practice_set_skipped_no_free_week")


def main() -> int:
    from src.db.connection import SessionLocal

    db = SessionLocal()
    try:
        seed_enrollments(db)
        seed_academic_term_and_exams(db)
        seed_class_activities(db)
        seed_quizzes(db)
        seed_quiz_submissions(db)
        seed_assignment_submissions(db)
        seed_reflections_and_tasks(db)
        seed_self_study_sessions(db)
        seed_conversations(db)
        seed_risk_and_notes(db)
        seed_admin_extras(db)
        seed_practice_set(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    logger.info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
