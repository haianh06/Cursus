"""Consolidated demo-sandbox dataset for all 3 roles (Student/Instructor/Admin).

Replaces `seed_gap_fill_demo.py`, `seed_instructor_ui_demo.py`,
`seed_extra_users.py`, and `provision_demo_personas.py` -- those four were
written at different times, each hardcoding ids/week-numbers/account
references that silently drifted out of sync with production as the app
evolved (a class of bug that broke the demo sandbox repeatedly on 01/09).
This script is the one place all of that lives now.

Scope: operational/demo data only. NEVER touches courses, course_sections'
curriculum content, documents, document_chunks, curriculum_versions, or
organizations -- those stay exactly as already ingested. Every account this
script targets lives in the existing `org_cursus_demo` sandbox org; account
ids are always resolved by email at runtime (never hardcoded), since the
`/auth/demo-session` auto-provisioned accounts' ids are not stable across a
sandbox re-provision.

Two phases, both idempotent -- safe to run on every boot (same as its three
predecessors were):
  1. `reset_operational_data(db)` -- deletes every row this script (or its
     predecessors) previously created, by explicit id-prefix/list, never by
     a blanket "everything in this org" sweep.
  2. `seed_full_dataset(db)` -- rebuilds everything fresh. Every varied value
     (completion rates, grades, risk severity, submission timing) comes from
     `random.Random(FIXED_SEED)` -- reproducible across redeploys (the same
     numbers every time), but visibly non-uniform per student/day instead of
     a single repeated template value.

Usage (inside the backend container):
    python scripts/seed_demo_dataset.py
"""

from __future__ import annotations

import hashlib
import logging
import random
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed-demo-dataset")

# Fixed seed -- every "random" value below is reproducible across redeploys.
FIXED_SEED = "cursus-demo-dataset-v1"

ORG_ID = "org_cursus_demo"
STUDENT_A_EMAIL = "demo.student@cursusdemo.local"
INSTRUCTOR_EMAIL = "demo.instructor@cursusdemo.local"
ADMIN_EMAIL = "demo.admin@cursusdemo.local"
STUDENT_B = "student_haianh"          # studenthaianh@example.com -- stable literal id
STUDENT_C = "student_haidang"         # studenthaidang@example.com -- stable literal id
SEC_SSA101 = "section_gate2_ssa101_se_k20"  # the one shared Gate-2 class every demo student is in

# Every row this script creates uses this prefix -- makes reset_operational_data()
# safe to scope precisely instead of ever needing an org-wide sweep.
P = "demo_"

# Realistic Vietnamese roster for the synthetic class (instructor needs
# multiple students to review across Risk/Class Activity/Quiz/Submissions
# screens) -- (slug, full name, student code suffix).
ROSTER = [
    ("an", "Nguyễn Văn An", "SV23010123"),
    ("mai", "Trần Thị Mai", "SV23010567"),
    ("nam", "Lê Hoàng Nam", "SV23010288"),
    ("chau", "Phạm Minh Châu", "SV23010611"),
    ("ducanh", "Vũ Đức Anh", "SV23010345"),
    ("ethan", "Ethan Nguyen", "SV23010702"),
    ("tuan", "Đỗ Anh Tuấn", "SV23010815"),
    ("thuha", "Vũ Thu Hà", "SV23010928"),
    ("khanh", "Nguyễn Gia Khánh", "SV23011056"),
    ("minhanh", "Phạm Minh Anh", "SV23011187"),
]

# Legacy fixture accounts from superseded/unused scripts -- deleted here even
# though those scripts' files stay untouched (they target the separate,
# never-logged-into "fpt-university" org and are not called by
# docker_entrypoint.py; purging their leftover rows, if any, is the
# "consolidate to one canonical account set" cleanup). Only ever deletes
# these EXACT emails/id-prefix -- never the fpt-university organization row
# or any course/document that might live under it.
LEGACY_FPT_EMAILS = [
    "student.demo@example.test",
    "instructor.demo@example.test",
    "admin.demo@example.test",
    "nguyen.ducchung@cursusdemo.demo",
]
LEGACY_FPT_ID_PREFIX = "student_se20_"  # seed_fixed_class_demo.py's 60-student roster

# Sentinel id prefixes from the 4 superseded scripts -- deleted on sight so a
# fresh boot of this script cleans up anything they left behind too.
LEGACY_ID_PREFIXES = ("g3_", "uidemo_")

# scripts/seed_cursus_uni_demo.sql (the oldest layer, predates all 4 Python
# scripts above) seeded a 60-student roster as bare `student_01`..`student_60`
# -- confirmed still live in production (2026-09-02: dragged stale week
# 2-4 completion data into the class-wide weekly chart, sitting alongside
# this script's own fresh week 33-36 rows, since these ids never matched
# `_own_or_legacy()` below and stayed enrolled). A prefix match would be
# unsafe here (`student_haianh`/`student_haidang` are real, current accounts
# that also start with `student_`) -- enumerate the exact legacy ids instead.
LEGACY_SQL_STUDENT_IDS = tuple(f"student_{i:02d}" for i in range(1, 61))


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _monday_on_or_before(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _rng(*parts: str) -> random.Random:
    """A Random() instance seeded deterministically from FIXED_SEED + parts
    -- same call site always gets the same sequence, different students/
    weeks/rows get different (but reproducible) sequences."""
    digest = hashlib.sha256((FIXED_SEED + "|" + "|".join(parts)).encode("utf-8")).hexdigest()
    return random.Random(int(digest[:16], 16))


def _resolve_accounts(db) -> dict:
    from src.db import models

    def _id_for(email: str) -> str:
        user = db.query(models.User).filter_by(email=email).first()
        if user is None:
            raise LookupError(f"Demo account not found: {email}")
        return user.id

    return {
        "student_a": _id_for(STUDENT_A_EMAIL),
        "instructor": _id_for(INSTRUCTOR_EMAIL),
        "admin": _id_for(ADMIN_EMAIL),
    }


# ═══════════════════════════════════════════════════════════════════════
# Phase 1 -- reset
# ═══════════════════════════════════════════════════════════════════════

def reset_operational_data(db) -> None:
    """Deletes every row this script (or its 4 predecessors) previously
    created. Scoped to explicit id lists/prefixes -- never a blanket
    "everything in org_cursus_demo" sweep, so courses/course_sections/
    documents/curriculum are never at risk regardless of what else ends up
    sharing that organization row."""
    from sqlalchemy import or_
    from src.db import models

    def _own_or_legacy(column):
        """Matches this script's own ids (always a clean startswith --
        `demo_...`) OR any legacy predecessor's marker *anywhere* in the id
        -- their real ids embed a type prefix before the marker (confirmed
        live: `act_g3_course_mock_csi106_1`, `quiz_g3_csi106`, not a bare
        `g3_...`/`uidemo_...` as first assumed), so a startswith-only check
        silently missed every one of them."""
        return or_(column.like(f"{P}%"), *[column.like(f"%{marker}%") for marker in LEGACY_ID_PREFIXES])

    accounts = _resolve_accounts(db)
    known_ids = [accounts["student_a"], accounts["instructor"], accounts["admin"], STUDENT_B, STUDENT_C]
    known_id_set = set(known_ids)

    # Synthetic roster + legacy-script rows are identified by id marker.
    # `known_ids` is excluded from both: seed_cursus_uni_demo.sql (the
    # oldest layer) happened to give its `student_01` row the exact same
    # email as STUDENT_A_EMAIL, so on a DB where that row was never
    # recreated under a fresh id, `accounts["student_a"]` resolves to
    # `student_01` itself -- without this exclusion the "delete every
    # legacy id" pass below deletes the live canonical account it just
    # resolved, and every downstream step in seed_full_dataset() that
    # re-resolves it by email 404s (confirmed live in production 2026-09-02).
    synthetic_students = (
        db.query(models.User.id)
        .filter(_own_or_legacy(models.User.id), models.User.role == models.UserRole.STUDENT.value)
        .all()
    )
    synthetic_student_ids = [row[0] for row in synthetic_students if row[0] not in known_id_set]

    legacy_sql_students = (
        db.query(models.User.id)
        .filter(models.User.id.in_(LEGACY_SQL_STUDENT_IDS))
        .all()
    )
    legacy_sql_student_ids = [row[0] for row in legacy_sql_students if row[0] not in known_id_set]

    all_student_ids = known_ids + synthetic_student_ids + legacy_sql_student_ids

    def _del(model, *filters):
        q = db.query(model)
        if filters:
            q = q.filter(*filters)
        n = q.delete(synchronize_session=False)
        if n:
            logger.info("deleted %s %s", n, model.__tablename__)

    # Children before parents.
    _del(models.InstructorIntervention, models.InstructorIntervention.risk_signal_id.in_(
        db.query(models.RiskSignal.id).filter(models.RiskSignal.student_id.in_(all_student_ids))
    ))
    _del(models.RiskSignal, models.RiskSignal.student_id.in_(all_student_ids))
    _del(models.InstructorStudentNote, models.InstructorStudentNote.student_id.in_(all_student_ids))
    _del(models.GuardrailEvent, models.GuardrailEvent.student_id.in_(all_student_ids))

    daily_plan_ids = db.query(models.DailyPlan.id).join(
        models.WeeklyPlan, models.WeeklyPlan.id == models.DailyPlan.weekly_plan_id
    ).filter(models.WeeklyPlan.student_id.in_(all_student_ids))
    block_ids = db.query(models.ScheduleBlock.id).filter(models.ScheduleBlock.daily_plan_id.in_(daily_plan_ids))
    _del(models.StudyTask, models.StudyTask.schedule_block_id.in_(block_ids))
    _del(models.SelfStudySession, models.SelfStudySession.schedule_block_id.in_(block_ids))
    _del(models.ScheduleBlock, models.ScheduleBlock.daily_plan_id.in_(daily_plan_ids))
    _del(models.DailyPlan, models.DailyPlan.id.in_(daily_plan_ids))
    _del(models.WeeklyPlan, models.WeeklyPlan.student_id.in_(all_student_ids))
    _del(models.WeeklyReflection, models.WeeklyReflection.student_id.in_(all_student_ids))
    _del(models.Submission, models.Submission.student_id.in_(all_student_ids))
    _del(models.ChatMessage, models.ChatMessage.conversation_id.in_(
        db.query(models.ChatConversation.id).filter(models.ChatConversation.student_id.in_(all_student_ids))
    ))
    _del(models.ChatConversation, models.ChatConversation.student_id.in_(all_student_ids))
    _del(models.ChatBriefingImpression, models.ChatBriefingImpression.student_id.in_(all_student_ids))
    _del(models.ChatActionProposal, models.ChatActionProposal.student_id.in_(all_student_ids))
    _del(models.ProgressEvent, models.ProgressEvent.student_id.in_(all_student_ids))
    _del(models.Enrollment, models.Enrollment.student_id.in_(synthetic_student_ids + legacy_sql_student_ids))

    # Org-scoped governance rows this script owns (id-marked, never org-wide).
    # `admin_notice_w3` is the one announcement seed_cursus_uni_demo.sql
    # created directly (not student-scoped, so the legacy-student cleanup
    # above doesn't reach it).
    _del(models.AdminAnnouncement, or_(_own_or_legacy(models.AdminAnnouncement.id), models.AdminAnnouncement.id == "admin_notice_w3"))
    _del(models.DataRequest, _own_or_legacy(models.DataRequest.id))

    # Assignments/quizzes/practice sets/class activities this script created
    # (id-marked, so a real instructor-authored assignment is never touched).
    # `quiz_w`/`asg_w` additionally catches an even older layer (the
    # historical scripts/seed_cursus_uni_demo.sql, e.g. `quiz_w3_sec_
    # CEA201_SE2001`, `asg_w2_sec_CEA201_SE2001`) found still lingering live.
    quiz_ids = db.query(models.Quiz.id).filter(or_(_own_or_legacy(models.Quiz.id), models.Quiz.id.like("quiz_w%")))
    _del(models.QuizQuestion, models.QuizQuestion.quiz_id.in_(quiz_ids))
    _del(models.Submission, models.Submission.quiz_id.in_(quiz_ids))
    _del(models.Quiz, models.Quiz.id.in_(quiz_ids))
    asg_ids = db.query(models.Assignment.id).filter(
        or_(_own_or_legacy(models.Assignment.id), models.Assignment.id.like("asg_w%"))
    )
    _del(models.Submission, models.Submission.assignment_id.in_(asg_ids))
    _del(models.Assignment, models.Assignment.id.in_(asg_ids))
    _del(models.ClassActivity, _own_or_legacy(models.ClassActivity.id))
    practice_set_ids = db.query(models.PracticeSet.id).filter(_own_or_legacy(models.PracticeSet.id))
    _del(models.PracticeItem, models.PracticeItem.set_id.in_(practice_set_ids))
    _del(models.PracticeSet, models.PracticeSet.id.in_(practice_set_ids))

    # The synthetic roster's own User rows (children already gone above).
    _del(models.User, models.User.id.in_(synthetic_student_ids + legacy_sql_student_ids))

    # Legacy fpt-university fixture accounts (org/course rows left untouched).
    legacy_fpt_users = (
        db.query(models.User.id)
        .filter(or_(
            models.User.email.in_(LEGACY_FPT_EMAILS),
            models.User.id.like(f"{LEGACY_FPT_ID_PREFIX}%"),
        ))
        .all()
    )
    legacy_fpt_ids = [row[0] for row in legacy_fpt_users]
    if legacy_fpt_ids:
        _del(models.Enrollment, models.Enrollment.student_id.in_(legacy_fpt_ids))
        _del(models.OrganizationMembership, models.OrganizationMembership.user_id.in_(legacy_fpt_ids))
        _del(models.User, models.User.id.in_(legacy_fpt_ids))

    db.commit()
    logger.info("reset_ok")


# ═══════════════════════════════════════════════════════════════════════
# Phase 2 -- seed
# ═══════════════════════════════════════════════════════════════════════

def _ensure_roster(db, accounts: dict) -> list[str]:
    """Creates the 10-student synthetic class roster, enrolled in the shared
    SSA101 section alongside the real demo student. Returns their ids."""
    from src.db import models

    org_id = ORG_ID
    ids = []
    for slug, name, code in ROSTER:
        uid = f"{P}std_{slug}"
        ids.append(uid)
        if db.query(models.User).filter_by(id=uid).first() is not None:
            continue
        db.add(models.User(
            id=uid, email=f"{P}std.{slug}@cursusdemo.local", password_hash="!demo-no-login",
            full_name=name, role=models.UserRole.STUDENT.value, is_email_verified=True, is_active=True,
            organization_id=org_id, major="Software Engineering", student_code=code, preferences={},
        ))
        db.add(models.Enrollment(
            id=f"{P}enr_{slug}", student_id=uid, section_id=SEC_SSA101,
            status=models.EnrollmentStatus.ENROLLED.value, enrolled_at=_now() - timedelta(days=30),
        ))
    db.commit()
    logger.info("roster_ok count=%s", len(ids))
    return ids


def _ensure_baseline_risk_policy(db) -> int:
    """RiskPolicy is a global (not org-scoped), immutable-append table --
    never deleted by reset_operational_data(). Confirmed today that this
    table can be genuinely empty on this DB (migration 20260823's baseline
    insert is another instance of the known alembic-drift gap) -- create a
    sane v1 if so, otherwise use whatever the latest version already is."""
    from src.db import models
    from src.services.ai.risk_engine import DEFAULT_SIGNAL_THRESHOLDS, DEFAULT_SIGNAL_WEIGHTS

    latest = db.query(models.RiskPolicy).order_by(models.RiskPolicy.policy_version.desc()).first()
    if latest is not None:
        return latest.policy_version
    policy = models.RiskPolicy(
        policy_version=1, effective_from=_now(),
        signal_weights=dict(DEFAULT_SIGNAL_WEIGHTS), signal_thresholds=dict(DEFAULT_SIGNAL_THRESHOLDS),
        severity_bands=[[0, "normal", "LOW"], [3, "watch", "MEDIUM"], [5, "needs_support", "HIGH"]],
        reason="Baseline policy (seeded -- none existed on this DB).",
        rolled_back_from=None, created_by=None, created_at=_now(),
    )
    db.add(policy)
    db.commit()
    logger.info("baseline_risk_policy_created version=1")
    return 1


def _seed_weekly_history(db, *, student_id: str, weeks_back: int, base_week: int, profile: str) -> None:
    """Seeds `weeks_back` weeks (including the current one) of WeeklyPlan/
    DailyPlan/ScheduleBlock/StudyTask/WeeklyReflection for one student,
    anchored to `base_week` (the REAL current week for that student, from
    current_week_for_student() -- never a hardcoded constant, so this never
    drifts out of sync with "this week" again). `profile` picks a
    completion-rate band (deterministic-random per student+week, not a
    single repeated value) so different students visibly read as doing
    well / average / struggling instead of identical templated numbers."""
    from src.db import models
    from src.services.ai.plan_builder import is_study_plan

    profile_bands = {
        "strong": (0.80, 0.98),
        "average": (0.55, 0.80),
        "struggling": (0.25, 0.55),
    }
    low, high = profile_bands[profile]

    for offset in range(weeks_back, -1, -1):
        week_number = base_week - offset
        if week_number < 1:
            continue
        is_current = offset == 0

        candidates = db.query(models.WeeklyPlan).filter_by(student_id=student_id, week_number=week_number).all()
        if any(is_study_plan(c) for c in candidates):
            continue  # a real (non-timetable-container) plan already covers this week

        rng = _rng(student_id, str(week_number))
        completion_rate = round(rng.uniform(low, high), 2)
        plan_id = f"{P}plan_{student_id}_{week_number}"
        if db.query(models.WeeklyPlan).filter_by(id=plan_id).first() is not None:
            continue

        plan = models.WeeklyPlan(
            id=plan_id, student_id=student_id, week_number=week_number,
            goals={"statement": f"Kế hoạch ôn tập tuần {week_number}."},
            study_hours_allocated=round(rng.uniform(8.0, 14.0), 1),
        )
        db.add(plan)
        db.flush()

        week_monday = _monday_on_or_before(date.today()) - timedelta(weeks=offset)
        today_index = date.today().weekday()
        n_tasks = 7
        n_completed = round(n_tasks * completion_rate) if is_current else round(n_tasks * completion_rate)
        # Which day-slots are "done" -- randomized subset, not always the first N days,
        # so the pattern doesn't look mechanically sequential.
        done_slots = set(rng.sample(range(n_tasks), k=min(n_completed, n_tasks)))

        for day_index in range(n_tasks):
            day_date = datetime.combine(week_monday + timedelta(days=day_index), datetime.min.time())
            if is_current:
                is_future = day_index > today_index
                is_today = day_index == today_index
            else:
                is_future = False
                is_today = False
            task_done = day_index in done_slots and not is_future

            daily = models.DailyPlan(
                id=f"{plan_id}_dp{day_index}", weekly_plan_id=plan.id, date=day_date,
                status="COMPLETED" if task_done else ("IN_PROGRESS" if is_today else ("TODO" if is_future or is_today else "MISSED")),
            )
            db.add(daily)
            db.flush()
            start_hour = rng.choice([18, 19, 20])
            block = models.ScheduleBlock(
                id=f"{plan_id}_sb{day_index}", daily_plan_id=daily.id,
                start_time=day_date.replace(hour=start_hour),
                end_time=day_date.replace(hour=start_hour + 1, minute=rng.choice([0, 15, 30])),
                activity_description=rng.choice(["Ôn tập buổi tối", "Làm bài tập", "Đọc tài liệu", "Luyện đề"]),
            )
            db.add(block)
            db.flush()
            planned = rng.choice([45, 60, 75, 90, 120])
            db.add(models.StudyTask(
                id=f"{plan_id}_task{day_index}", schedule_block_id=block.id,
                title=f"{rng.choice(['Ôn tập', 'Làm bài', 'Đọc trước', 'Luyện đề'])} tuần {week_number} — {day_date.strftime('%a')}",
                planned_minutes=planned,
                actual_minutes=round(planned * rng.uniform(0.7, 1.15)) if task_done else (round(planned * rng.uniform(0.2, 0.6)) if is_today else None),
                priority=rng.choice(["LOW", "MEDIUM", "MEDIUM", "HIGH"]),
                status="COMPLETED" if task_done else ("IN_PROGRESS" if is_today else ("TODO" if is_future or is_today else "MISSED")),
                difficulty=rng.choice(["EASY", "MEDIUM", "MEDIUM", "HARD"]),
            ))

        if not is_current:
            content = {
                "strong": f"Tuần {week_number}: hoàn thành phần lớn kế hoạch, nộp bài đúng hạn.",
                "average": f"Tuần {week_number}: hoàn thành khoảng {int(completion_rate * 100)}% kế hoạch, còn vài việc dồn lại.",
                "struggling": f"Tuần {week_number}: gặp khó khăn sắp xếp thời gian, hoàn thành {int(completion_rate * 100)}% kế hoạch.",
            }[profile]
            db.add(models.WeeklyReflection(
                id=f"{P}refl_{student_id}_{week_number}", student_id=student_id, week_number=week_number,
                content=content, generated_at=week_monday + timedelta(days=6, hours=20),
                metrics={"completionRate": completion_rate},
            ))
        db.commit()
    logger.info("weekly_history_ok student=%s profile=%s weeks=%s", student_id, profile, weeks_back + 1)


def _ensure_semester_setup(db, student_id: str, *, weeks_back: int) -> None:
    """Without an active SemesterSetup, academic_week_number() (src/services/
    academic/academic_calendar.py) falls back to the student's raw ISO
    calendar week (e.g. week 33-36 in September) instead of a week-of-
    semester number -- confirmed live 2026-09-02: every demo screen showing
    "Tuần 33..36" instead of a sane "Tuần 1..4", since none of this script's
    students ever go through the real Student-facing "declare my semester"
    flow that normally creates this row. Pin start_date so `today` always
    lands on week `weeks_back + 1` (matching _seed_weekly_history's own
    weeks_back), recomputed every boot so it never drifts as real time
    passes -- same "never hardcoded" rule as the rest of this script."""
    from src.db import models

    monday = _monday_on_or_before(date.today())
    start_date = monday - timedelta(days=weeks_back * 7)
    end_date = start_date + timedelta(weeks=15)

    existing = (
        db.query(models.SemesterSetup)
        .filter_by(student_id=student_id, is_active=True)
        .order_by(models.SemesterSetup.created_at.desc())
        .first()
    )
    if existing is not None:
        if existing.start_date != start_date:
            existing.start_date = start_date
            existing.end_date = end_date
            db.commit()
        return

    db.add(models.SemesterSetup(
        id=f"{P}sem_{student_id}",
        student_id=student_id,
        name="Học kỳ hiện tại",
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        created_at=_now(),
    ))
    db.commit()


def seed_full_dataset(db) -> None:
    from src.db import models
    from src.services.academic.academic_calendar import current_week_for_student
    from src.services.mock.student_mock_data_service import StudentMockDataService

    accounts = _resolve_accounts(db)
    student_a, instructor, admin = accounts["student_a"], accounts["instructor"], accounts["admin"]
    now = _now()

    # --- Core students: real course/section/enrollment scaffolding ---
    StudentMockDataService(db).ensure_for_student(student_a)

    # --- Weekly Plan/Do/Reflect history: current + 3 past weeks, varied profile per student ---
    for student_id, profile in ((student_a, "average"), (STUDENT_B, "strong"), (STUDENT_C, "struggling")):
        _ensure_semester_setup(db, student_id, weeks_back=3)
        week_number = current_week_for_student(db, student_id)
        _seed_weekly_history(db, student_id=student_id, weeks_back=3, base_week=week_number, profile=profile)

    # --- Synthetic 10-student roster for Instructor/Admin screens ---
    roster_ids = _ensure_roster(db, accounts)
    for uid in roster_ids:
        _ensure_semester_setup(db, uid, weeks_back=3)
    roster_week = current_week_for_student(db, student_a)
    roster_profiles = ["strong", "strong", "average", "average", "average", "struggling", "average", "strong", "struggling", "average"]
    for (uid, profile) in zip(roster_ids, roster_profiles, strict=True):
        _seed_weekly_history(db, student_id=uid, weeks_back=3, base_week=roster_week, profile=profile)

    # --- Assignment + submissions across the roster ---
    rng = _rng("assignment", "prf192")
    asg_id = f"{P}asg_prf192_lab"
    if db.query(models.Assignment).filter_by(id=asg_id).first() is None:
        db.add(models.Assignment(
            id=asg_id, section_id=SEC_SSA101, title="SSA101 — Bài tập nhóm tuần này",
            description="Áp dụng kiến thức đã học để hoàn thành bài tập nhóm.",
            due_date=now + timedelta(days=3), max_points=100, assessment_type="LAB",
        ))
        db.flush()
        for uid in roster_ids + [student_a, STUDENT_B, STUDENT_C]:
            r = _rng("submission", uid)
            submitted = r.random() < 0.85
            if not submitted:
                continue
            late = r.random() < 0.15
            graded = r.random() < 0.7
            db.add(models.Submission(
                id=f"{P}sub_{asg_id}_{uid}", assignment_id=asg_id, student_id=uid,
                submitted_at=now - timedelta(days=r.uniform(0, 2)) + (timedelta(days=1) if late else timedelta(0)),
                content={"summary": "Bài nộp demo."}, grading_status="GRADED" if graded else "PENDING",
                grade=round(r.uniform(55, 98), 1) if graded else None,
                feedback="Đã xem, làm tốt." if graded else None, is_late=late,
            ))
        db.commit()
        logger.info("assignment_submissions_ok")

    # --- Quiz ---
    quiz_id = f"{P}quiz_ssa101_wk"
    if db.query(models.Quiz).filter_by(id=quiz_id).first() is None:
        db.add(models.Quiz(
            id=quiz_id, section_id=SEC_SSA101, title="SSA101 — Kiểm tra nhanh",
            description="Bài kiểm tra ngắn dựa trên nội dung tuần này.",
            time_limit_minutes=20, due_date=now + timedelta(days=5), max_points=10,
            created_by=instructor, is_published=True, opens_at=now - timedelta(days=1),
        ))
        db.flush()
        db.add(models.QuizQuestion(
            id=f"{quiz_id}_q1", quiz_id=quiz_id, question_text="Kỹ năng nào quan trọng nhất khi làm việc nhóm?",
            question_type="MULTIPLE_CHOICE", correct_answer="Giao tiếp hiệu quả",
            options={"options": ["Giao tiếp hiệu quả", "Làm việc một mình", "Bỏ qua deadline", "Không cần lập kế hoạch"]},
            points=10, order_index=1,
        ))
        db.commit()
        logger.info("quiz_ok")

    # --- Class activities (last 2 weeks, varied kind) ---
    # (course_id, activity_date) carries a real UNIQUE constraint in
    # production that predates the current models.py (no longer declared
    # in any current migration/model -- another instance of today's
    # recurring "live schema knows something the ORM doesn't" class of
    # drift) -- check by the actual constraint, not just this script's own
    # id, or a real pre-existing row for that course+day crashes the insert.
    course = db.query(models.Course).filter_by(id="course_mock_prf192").first()
    if course is not None:
        for i in range(6):
            day = date.today() - timedelta(days=i * 2)
            aid = f"{P}activity_{i}"
            already = (
                db.query(models.ClassActivity)
                .filter_by(course_id=course.id, activity_date=day)
                .first()
            )
            if already is not None:
                continue
            r = _rng("activity", str(i))
            kind = r.choice(["LECTURE_HELD", "LECTURE_HELD", "LECTURE_HELD", "NOTE", "MAKEUP"])
            db.add(models.ClassActivity(
                id=aid, course_id=course.id, activity_date=day, kind=kind,
                title={"LECTURE_HELD": "Buổi học bình thường", "NOTE": "Ghi chú lớp học", "MAKEUP": "Buổi học bù"}[kind],
                created_by=instructor, created_at=now - timedelta(days=i * 2),
            ))
        db.commit()
        logger.info("class_activities_ok")

    # --- Risk signals across the roster, varying severity/type/resolution ---
    policy_version = _ensure_baseline_risk_policy(db)
    risk_specs = [
        ("an", "HIGH", "ABANDONMENT", "Nghỉ học liên tiếp, chưa nộp bài tập.", False),
        ("mai", "HIGH", "WEEKLY_GOAL_FAILURE", "Điểm quiz thấp trong 2 lần gần nhất.", False),
        ("nam", "MEDIUM", "LATE_SUBMISSION", "Nộp bài trễ nhiều lần trong tuần.", False),
        ("chau", "MEDIUM", "ACADEMIC_DECLINE", "Tương tác lớp học giảm rõ rệt.", True),
        ("ducanh", "LOW", "ACADEMIC_DECLINE", "Tiến độ chậm hơn kế hoạch.", True),
        ("thuha", "LOW", "LATE_SUBMISSION", "Một lần nộp trễ, đã liên hệ khắc phục.", True),
    ]
    for slug, level, rtype, note, resolved in risk_specs:
        uid = f"{P}std_{slug}"
        rid = f"{P}risk_{slug}"
        if db.query(models.RiskSignal).filter_by(id=rid).first() is not None:
            continue
        r = _rng("risk", slug)
        days_open = r.randint(1, 7)
        db.add(models.RiskSignal(
            id=rid, student_id=uid, section_id=SEC_SSA101, assignment_id=None,
            risk_type=rtype, risk_level=level, triggered_rules={"rule": "seed_demo_dataset"},
            evidence={"note": note}, recommended_action="Liên hệ hỗ trợ và thống nhất kế hoạch bắt kịp.",
            generated_at=now - timedelta(days=days_open),
            resolved_at=now - timedelta(days=max(days_open - 3, 0)) if resolved else None,
            resolved_by=instructor if resolved else None,
            resolution_type="FOLLOW_UP_COMPLETED" if resolved else None,
            policy_version=policy_version,
            instructor_note="Đã trao đổi, sinh viên cam kết cải thiện." if resolved else None,
        ))
    db.commit()
    logger.info("risk_signals_ok")

    # --- Instructor's private note ---
    note_id = f"{P}note_instructor_chau"
    if db.query(models.InstructorStudentNote).filter_by(id=note_id).first() is None:
        db.add(models.InstructorStudentNote(
            id=note_id, instructor_id=instructor, student_id=f"{P}std_chau",
            content="Cần theo dõi sát — có dấu hiệu quá tải khi học song song nhiều môn.",
            created_at=now - timedelta(hours=10),
        ))
        db.commit()

    # --- Guardrail events (mix of pending/reviewed) ---
    _relax_stale_guardrail_message_id_column(db)
    guardrail_specs = [
        ("ethan", "Cho mình đáp án bài tập, mình cần nộp gấp.", "PENDING", None),
        ("khanh", "Viết hộ mình cả bài luận.", "PENDING", None),
        ("tuan", "Tóm tắt hộ mình cả chương để khỏi đọc giáo trình.", "UNBLOCKED", instructor if True else None),
        ("minhanh", "Cho mình đáp án câu 1 thôi cũng được.", "KEPT_BLOCKED", None),
    ]
    for slug, question, status, reviewer in guardrail_specs:
        gid = f"{P}grd_{slug}"
        if db.query(models.GuardrailEvent).filter_by(id=gid).first() is not None:
            continue
        r = _rng("guardrail", slug)
        days_ago = r.uniform(0.2, 5)
        db.add(models.GuardrailEvent(
            id=gid, student_id=f"{P}std_{slug}", section_id=SEC_SSA101, classification="BLOCKED",
            safety_evaluation={"question": question, "reason": "academic_integrity"},
            review_status=status, block_reason="academic_integrity",
            blocked_answer="Mình không thể đưa đáp án trực tiếp, nhưng có thể hướng dẫn cách làm.",
            reviewed_by=reviewer if status != "PENDING" else None,
            reviewed_at=now - timedelta(days=max(days_ago - 0.5, 0)) if status != "PENDING" else None,
            created_at=now - timedelta(days=days_ago),
        ))
    db.commit()
    logger.info("guardrail_events_ok")

    # --- Admin announcements ---
    announcements = [
        ("Cập nhật lịch thi giữa kỳ", "Lịch thi giữa kỳ đã được publish, vui lòng rà soát ca thi của lớp mình."),
        ("Nhắc quy trình rà soát Guardrail", "Đề nghị các giảng viên xử lý hàng chờ Guardrail Review trước cuối tuần."),
    ]
    for i, (title, content) in enumerate(announcements):
        aid = f"{P}ann_{i}"
        if db.query(models.AdminAnnouncement).filter_by(id=aid).first() is not None:
            continue
        db.add(models.AdminAnnouncement(
            id=aid, title=title, content=content, created_by=admin, organization_id=ORG_ID,
            created_at=now - timedelta(days=3 - i),
        ))
    db.commit()

    # --- Data requests (mixed status) ---
    data_requests = [
        (student_a, "ACCESS", "PENDING"),
        (STUDENT_B, "EXPORT", "PENDING"),
        (STUDENT_C, "ACCESS", "COMPLETED"),
    ]
    for i, (requester, rtype, status) in enumerate(data_requests):
        did = f"{P}dr_{i}"
        if db.query(models.DataRequest).filter_by(id=did).first() is not None:
            continue
        completed = status == "COMPLETED"
        db.add(models.DataRequest(
            id=did, requester_id=requester, organization_id=ORG_ID, request_type=rtype, status=status,
            processed_by=admin if completed else None,
            admin_notes="Đã gửi bản xuất dữ liệu qua email đăng ký." if completed else None,
            result_summary={"records_exported": 42} if completed else None,
            created_at=now - timedelta(days=6 - i), updated_at=now - timedelta(days=5 - i),
        ))
    db.commit()
    logger.info("data_requests_ok")

    # --- Guardrail policy: ensure the rule set exists (global table, not deleted by reset) ---
    from src.repositories.guardrail_rule_repository import GuardrailRuleRepository
    GuardrailRuleRepository(db).ensure_seeded()
    db.commit()

    # --- Practice set for one course/week ---
    from src.repositories.practice_set_repository import PracticeSetRepository
    from src.services.academic.practice_generator import generate_pack

    if course is not None:
        repo = PracticeSetRepository(db)
        for week_number in range(1, 6):
            slide_key_guess = f"slot_{week_number:02d}"
            if repo.get_by_slide(course.code, slide_key_guess) is not None:
                continue
            try:
                specs, slide_key = generate_pack(db=db, subject_code=course.code, week_number=week_number, language="vi")
            except ValueError:
                continue
            row = repo.add_set(
                course_id=course.id, course_code=course.code, slide_key=slide_key,
                week_number=week_number, language="vi", requested_by=student_a, status="PENDING",
            )
            repo.replace_items(row, specs)
            row.status = "PUBLISHED"
            row.reviewed_by = instructor
            row.reviewed_at = now
            repo.commit()
            logger.info("practice_set_created course=%s week=%s", course.code, week_number)
            break

    logger.info("done")


def _relax_stale_guardrail_message_id_column(db) -> None:
    """See seed_gap_fill_demo.py's identical helper (this script supersedes
    it, docstring kept here verbatim since the underlying gap is unchanged):
    `GuardrailEvent.message_id` was dropped from the ORM model when the old
    chat feature was removed, but that migration hasn't reached this DB yet
    -- a separately known, documented alembic-drift gap. This only loosens
    the constraint (NOT NULL -> nullable), never drops the column or data.
    `information_schema` is Postgres-specific -- silently no-ops on any other
    backend (e.g. the SQLite test DB) rather than raising."""
    from sqlalchemy import text

    try:
        row = db.execute(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'guardrail_events' AND column_name = 'message_id'"
            )
        ).first()
        if row is not None and row[0] == "NO":
            db.execute(text("ALTER TABLE guardrail_events ALTER COLUMN message_id DROP NOT NULL"))
            db.commit()
    except Exception:
        db.rollback()


def main() -> int:
    from src.db.connection import SessionLocal

    db = SessionLocal()
    try:
        reset_operational_data(db)
        seed_full_dataset(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
