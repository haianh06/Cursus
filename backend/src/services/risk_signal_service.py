"""Tính rủi ro trễ tiến độ của sinh viên theo công thức đã chốt (Playbook F5).

Công thức (không phải AI đoán, thuần rule-based trên số liệu thật):
- LATE_SUBMISSION: trễ ≥2 deadline liên tiếp trong 2 tuần gần nhất.
- WEEKLY_GOAL_FAILURE: hoàn thành <50% task trong 3 tuần liên tiếp gần nhất.

Tính on-demand mỗi lần gọi (không ghi bảng `risk_signals`) — kết quả luôn phản
ánh dữ liệu mới nhất, không cần cron/job riêng. Vì không persist, các rủi ro
này KHÔNG xuất hiện trong hàng đợi HITL của giảng viên (bảng đó vẫn đọc thẳng
`risk_signals` — nằm ngoài phạm vi thay đổi này).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.risk_policy_repository import RiskPolicyRepository

LATE_WINDOW_DAYS = 14
LATE_CONSECUTIVE_THRESHOLD = 2
GOAL_FAILURE_WEEKS = 3
GOAL_FAILURE_RATE_THRESHOLD = 50.0

# A2 — canh bao SOM theo xu huong, khac WEEKLY_GOAL_FAILURE (chi bao khi ty le
# DA thap). O day bao ngay khi ty le hoan thanh giam LIEN TUC qua tung tuan,
# ke ca khi con tren nguong "thap", de GV can thiep truoc khi SV roi vao nhom
# rui ro cao.
DECLINE_TREND_WEEKS = 3
DECLINE_TREND_DROP_POINTS = 0.20  # giam >=20 diem % tu tuan xa nhat den gan nhat
DECLINE_TREND_HIGH_DROP_POINTS = 0.40

# B2 — canh bao SLA noi bo: case rui ro mo qua RISK_SLA_DAYS ma chua co quyet
# dinh (resolved_at con rong) thi tinh la "qua han", de GV khong bo sot case
# roi khoi tam mat. Chi la nhan hien thi/sap xep, KHONG doi hanh vi HITL nao.
RISK_SLA_DAYS = 3


def _as_aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def risk_days_open(risk: models.RiskSignal, *, now: datetime | None = None) -> int:
    now = now or datetime.now(UTC)
    return max(0, (now - _as_aware_utc(risk.generated_at)).days)


def is_risk_overdue(risk: models.RiskSignal, *, now: datetime | None = None) -> bool:
    if risk.resolved_at:
        return False
    return risk_days_open(risk, now=now) >= RISK_SLA_DAYS


def _weekly_plan_completion_batch(
    db: Session, weekly_plan_ids: list[str]
) -> dict[str, tuple[int, int]]:
    """(so task hoan thanh, tong so task) cho NHIEU WeeklyPlan cung luc, bang
    1 query join DailyPlan -> ScheduleBlock -> StudyTask thay vi lap tung
    plan/daily_plan/block roi query rieng (N+1+1+1 cu — vai chuc query cho
    1 lop hoc, la nguyen nhan dashboard GV load cham). Plan nao khong co
    task thi khong xuat hien trong dict tra ve (bo qua, khong tinh 0%)."""
    if not weekly_plan_ids:
        return {}

    rows = (
        db.query(models.DailyPlan.weekly_plan_id, models.StudyTask.status)
        .join(models.ScheduleBlock, models.ScheduleBlock.daily_plan_id == models.DailyPlan.id)
        .join(models.StudyTask, models.StudyTask.schedule_block_id == models.ScheduleBlock.id)
        .filter(models.DailyPlan.weekly_plan_id.in_(weekly_plan_ids))
        .all()
    )

    totals: dict[str, int] = {}
    completed_counts: dict[str, int] = {}
    for weekly_plan_id, status in rows:
        totals[weekly_plan_id] = totals.get(weekly_plan_id, 0) + 1
        if status == "COMPLETED":
            completed_counts[weekly_plan_id] = completed_counts.get(weekly_plan_id, 0) + 1

    return {
        weekly_plan_id: (completed_counts.get(weekly_plan_id, 0), total)
        for weekly_plan_id, total in totals.items()
    }


def weekly_plan_completion(db: Session, weekly_plan_id: str) -> tuple[int, int]:
    """(so task hoan thanh, tong so task) cua 1 WeeklyPlan. Giu lai cho code
    goi tung plan rieng le; cac ham lay theo lop/nhieu tuan ben duoi dung
    _weekly_plan_completion_batch truc tiep de tranh N+1."""
    return _weekly_plan_completion_batch(db, [weekly_plan_id]).get(weekly_plan_id, (0, 0))


def class_weekly_completion(db: Session, student_ids: list[str]) -> list[float]:
    """Ty le hoan thanh task trung binh ca lop, gom theo week_number."""
    if not student_ids:
        return []

    plans = db.query(models.WeeklyPlan).filter(
        models.WeeklyPlan.student_id.in_(student_ids)
    ).all()
    completion_by_plan = _weekly_plan_completion_batch(db, [p.id for p in plans])

    rates_by_week: dict[int, list[float]] = {}
    for plan in plans:
        completed, total = completion_by_plan.get(plan.id, (0, 0))
        # Khong co task nao thi bo qua tuan do cho SV nay, khong tinh la 0%
        # (0% that va "chua co du lieu" la hai y nghia khac nhau).
        if total == 0:
            continue
        rates_by_week.setdefault(plan.week_number, []).append(completed / total)

    return [
        round(sum(rates) / len(rates), 4)
        for _week, rates in sorted(rates_by_week.items())
    ]


def student_recent_weekly_rates(db: Session, student_id: str, limit: int) -> list[tuple[int, float]]:
    """`limit` cap ty le hoan thanh gan nhat cua 1 SV, moi nhat truoc, chi
    tinh cac tuan THAT SU co task (bo qua tuan rong)."""
    return _recent_weekly_rates_batch(db, [student_id], limit).get(student_id, [])


def _recent_weekly_rates_batch(
    db: Session, student_ids: list[str], limit: int
) -> dict[str, list[tuple[int, float]]]:
    """Ban nhieu-SV cua student_recent_weekly_rates — 2 query cho CA LOP thay
    vi 2 query CHO MOI SV (goc cua N+1 khi detect_declining_completion_risks
    goi lai ham don-SV cho tung enrollment)."""
    if not student_ids:
        return {}

    plans = (
        db.query(models.WeeklyPlan)
        .filter(models.WeeklyPlan.student_id.in_(student_ids))
        .order_by(models.WeeklyPlan.student_id, models.WeeklyPlan.week_number.desc())
        .all()
    )
    completion_by_plan = _weekly_plan_completion_batch(db, [p.id for p in plans])

    rates_by_student: dict[str, list[tuple[int, float]]] = {sid: [] for sid in student_ids}
    for plan in plans:
        rates = rates_by_student[plan.student_id]
        if len(rates) >= limit:
            continue
        completed, total = completion_by_plan.get(plan.id, (0, 0))
        if total == 0:
            continue
        rates.append((plan.week_number, completed / total))
    return rates_by_student


def detect_declining_completion_risks(db: Session, section_ids: list[str]) -> None:
    """A2 — cham dut viec cho toi khi ty le hoan thanh da thap moi bao (do la
    viec cua WEEKLY_GOAL_FAILURE): ghi RiskSignal that (risk_type=
    ACADEMIC_DECLINE, da co san trong models.py/RISK_TYPE_KEYS frontend nhung
    truoc gio chua co gi tao ca) ngay khi phat hien ty le hoan thanh giam LIEN
    TUC qua DECLINE_TREND_WEEKS tuan gan nhat.

    Tinh on-demand moi lan GV mo danh sach rui ro (giong cach Kudos/F8 tinh),
    nhung CO persist (khac compute_student_risks o tren) vi case nay phai vao
    duoc hang doi HITL. Idempotent: khong tao them neu con 1 case
    ACADEMIC_DECLINE nao CHUA xu ly cho dung SV+lop do, tranh spam case moi
    moi lan GV bam F5.
    """
    if not section_ids:
        return

    enrollments = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.section_id.in_(section_ids),
            models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
        )
        .all()
    )
    if not enrollments:
        return

    student_ids = [e.student_id for e in enrollments]

    already_open_pairs = {
        (student_id, section_id)
        for student_id, section_id in db.query(
            models.RiskSignal.student_id, models.RiskSignal.section_id
        ).filter(
            models.RiskSignal.section_id.in_(section_ids),
            models.RiskSignal.risk_type == "ACADEMIC_DECLINE",
            models.RiskSignal.resolved_at.is_(None),
        )
    }
    recent_rates_by_student = _recent_weekly_rates_batch(db, student_ids, DECLINE_TREND_WEEKS)

    policy_version: str | None = None
    created_any = False
    for enrollment in enrollments:
        student_id = enrollment.student_id
        section_id = enrollment.section_id

        if (student_id, section_id) in already_open_pairs:
            continue

        recent = recent_rates_by_student.get(student_id, [])
        if len(recent) < DECLINE_TREND_WEEKS:
            continue

        rates = [rate for _week, rate in recent]  # moi nhat truoc
        is_monotonic_decline = all(rates[i] < rates[i + 1] for i in range(len(rates) - 1))
        drop = rates[-1] - rates[0]  # tuan xa nhat - tuan gan nhat (duong = giam)
        if not is_monotonic_decline or drop < DECLINE_TREND_DROP_POINTS:
            continue

        if policy_version is None:
            active_policy = RiskPolicyRepository(db).get_active()
            policy_version = active_policy.policy_version if active_policy else 1

        week_numbers_oldest_first = [week for week, _rate in reversed(recent)]
        rates_oldest_first = list(reversed(rates))
        db.add(
            models.RiskSignal(
                id=f"risk_{uuid.uuid4().hex[:8]}",
                student_id=student_id,
                section_id=section_id,
                assignment_id=None,
                risk_type="ACADEMIC_DECLINE",
                risk_level="HIGH" if drop >= DECLINE_TREND_HIGH_DROP_POINTS else "MEDIUM",
                triggered_rules={
                    "rule": "declining_completion_trend",
                    "consecutiveWeeks": DECLINE_TREND_WEEKS,
                },
                evidence={
                    "weekNumbers": week_numbers_oldest_first,
                    "completionRates": [round(r * 100, 1) for r in rates_oldest_first],
                    "reason": (
                        f"Tỷ lệ hoàn thành giảm liên tục {DECLINE_TREND_WEEKS} tuần gần nhất "
                        f"({round(rates_oldest_first[0] * 100)}% → {round(rates_oldest_first[-1] * 100)}%)."
                    ),
                },
                recommended_action=(
                    "Liên hệ sớm với sinh viên trước khi tình trạng trở nên nghiêm trọng hơn."
                ),
                generated_at=datetime.now(UTC),
                resolved_at=None,
                resolution_type=None,
                policy_version=policy_version,
            )
        )
        created_any = True

    if created_any:
        db.commit()


def compute_class_metrics(db: Session, section_ids: list[str]) -> dict:
    """B3 — mot cong thuc duy nhat cho ca dashboard tong hop (F4) lan so sanh
    nhieu lop cung luc (B3), de 2 man hinh khong bao gio lech so voi nhau."""
    if not section_ids:
        return {
            "classSize": 0,
            "highRiskCount": 0,
            "totalActiveWarnings": 0,
            "overdueCount": 0,
            "classAvgCompletionByWeek": [],
        }

    risks = db.query(models.RiskSignal).filter(
        models.RiskSignal.section_id.in_(section_ids)
    ).all()
    now = datetime.now(UTC)
    active_risks = [r for r in risks if not r.resolved_at]
    high_risks = [r for r in active_risks if r.risk_level == "HIGH"]
    overdue_risks = [r for r in active_risks if is_risk_overdue(r, now=now)]

    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.section_id.in_(section_ids),
        models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
    ).all()
    student_ids = sorted({e.student_id for e in enrollments})

    return {
        "classSize": len(student_ids),
        "highRiskCount": len(high_risks),
        "totalActiveWarnings": len(active_risks),
        "overdueCount": len(overdue_risks),
        "classAvgCompletionByWeek": class_weekly_completion(db, student_ids),
    }


def compute_student_risks(db: Session, student_id: str) -> list[dict]:
    """Trả về danh sách rủi ro dạng dict, cùng shape với `GET /student/risks`."""
    sections = (
        db.query(models.CourseSection)
        .join(models.Enrollment)
        .filter(models.Enrollment.student_id == student_id)
        .all()
    )
    if not sections:
        return []
    primary_section_id = sections[0].id

    risks: list[dict] = []

    late_risk = _late_submission_risk(db, student_id, sections)
    if late_risk:
        risks.append(late_risk)

    goal_risk = _weekly_goal_failure_risk(db, student_id, primary_section_id)
    if goal_risk:
        risks.append(goal_risk)

    return risks


def _late_submission_risk(db: Session, student_id: str, sections: list) -> dict | None:
    section_ids = [s.id for s in sections]
    cutoff = datetime.now(UTC) - timedelta(days=LATE_WINDOW_DAYS)
    now = datetime.now(UTC)

    assignments = (
        db.query(models.Assignment)
        .filter(
            models.Assignment.section_id.in_(section_ids),
            models.Assignment.due_date >= cutoff,
            models.Assignment.due_date <= now,
        )
        .order_by(models.Assignment.due_date.asc())
        .all()
    )
    if not assignments:
        return None

    submissions_by_assignment = {
        row.assignment_id: row
        for row in (
            db.query(models.Submission)
            .filter(
                models.Submission.student_id == student_id,
                models.Submission.assignment_id.in_([a.id for a in assignments]),
            )
            .all()
        )
    }

    consecutive_late: list[str] = []
    best_run: list[str] = []
    for assignment in assignments:
        submission = submissions_by_assignment.get(assignment.id)
        is_late = submission.is_late if submission else True
        if is_late:
            consecutive_late.append(assignment.id)
            if len(consecutive_late) > len(best_run):
                best_run = list(consecutive_late)
        else:
            consecutive_late = []

    if len(best_run) < LATE_CONSECUTIVE_THRESHOLD:
        return None

    section_id = assignments[0].section_id
    risk_level = "HIGH" if len(best_run) >= 3 else "MEDIUM"
    return {
        "id": f"risk_late_{section_id}",
        "courseId": next((s.course_id for s in sections if s.id == section_id), ""),
        "assignmentId": best_run[-1],
        "riskType": "LATE_SUBMISSION",
        "riskLevel": risk_level,
        "evidence": {
            "consecutiveLateAssignmentIds": best_run,
            "windowDays": LATE_WINDOW_DAYS,
        },
        "resolvedAt": None,
        "resolutionType": None,
        "generatedAt": datetime.now(UTC).isoformat(),
    }


def _weekly_goal_failure_risk(db: Session, student_id: str, section_id: str) -> dict | None:
    plans = (
        db.query(models.WeeklyPlan)
        .filter_by(student_id=student_id)
        .order_by(models.WeeklyPlan.week_number.desc())
        .limit(GOAL_FAILURE_WEEKS)
        .all()
    )
    if len(plans) < GOAL_FAILURE_WEEKS:
        return None

    rates: list[float] = []
    for plan in plans:
        completed = 0
        total = 0
        daily_plans = db.query(models.DailyPlan).filter_by(weekly_plan_id=plan.id).all()
        for dp in daily_plans:
            blocks = db.query(models.ScheduleBlock).filter_by(daily_plan_id=dp.id).all()
            for block in blocks:
                tasks = db.query(models.StudyTask).filter_by(schedule_block_id=block.id).all()
                for task in tasks:
                    total += 1
                    if task.status == "COMPLETED":
                        completed += 1
        rate = (completed / total * 100) if total > 0 else 0.0
        rates.append(round(rate, 1))

    if any(rate >= GOAL_FAILURE_RATE_THRESHOLD for rate in rates):
        return None

    week_numbers = [plan.week_number for plan in plans]
    risk_level = "HIGH" if max(rates) < 30 else "MEDIUM"
    return {
        "id": f"risk_goal_{section_id}",
        "courseId": next(
            (
                s.course_id
                for s in db.query(models.CourseSection).filter_by(id=section_id).all()
            ),
            "",
        ),
        "assignmentId": None,
        "riskType": "WEEKLY_GOAL_FAILURE",
        "riskLevel": risk_level,
        "evidence": {
            "weekNumbers": week_numbers,
            "completionRates": rates,
        },
        "resolvedAt": None,
        "resolutionType": None,
        "generatedAt": datetime.now(UTC).isoformat(),
    }


def create_self_reported_help_alert(
    db: Session, student_id: str, week_number: int, note: str | None
) -> list[models.RiskSignal]:
    """Ghi 1 RiskSignal thật (không phải tính on-demand) khi SV tự chọn "Yêu cầu hỗ
    trợ" trong Reflection (PROJECT_CONTEXT.md §13.3) — khác các risk on-demand ở
    trên vì đây PHẢI xuất hiện trong hàng đợi HITL của giảng viên (`RiskSignal`
    là bảng thật mà `GET /instructor/risks` đọc). Tạo 1 signal cho mỗi lớp SV
    đang theo học để mọi giảng viên phụ trách đều thấy được.

    Idempotent per (student, section): nếu đã có 1 signal loại này còn mở
    (chưa resolved), cập nhật lại tuần/ghi chú thay vì tạo thêm bản mới —
    tránh việc sinh viên lưu lại Phản tư nhiều lần trong tuần làm hàng đợi
    HITL của giảng viên bị spam nhiều cảnh báo trùng nhau.
    """
    sections = (
        db.query(models.CourseSection)
        .join(models.Enrollment)
        .filter(models.Enrollment.student_id == student_id)
        .all()
    )

    # SV tu bao (khong qua RiskPolicyService.generate_signal) van phai gan
    # dung policy_version dang active - risk_signals.policy_version la NOT NULL.
    active_policy = RiskPolicyRepository(db).get_active()
    policy_version = active_policy.policy_version if active_policy else 1

    recommended_action = (
        f"Sinh viên chủ động chọn 'Yêu cầu hỗ trợ' trong Phản tư tuần {week_number}. "
        "Xem chi tiết phản tư và cân nhắc liên hệ trực tiếp."
    )
    evidence = {
        "weekNumber": week_number,
        "note": note,
        "source": "reflection_adjustment",
    }

    rows: list[models.RiskSignal] = []
    for section in sections:
        existing = (
            db.query(models.RiskSignal)
            .filter_by(
                student_id=student_id,
                section_id=section.id,
                risk_type="SELF_REPORTED_HELP_REQUEST",
                resolved_at=None,
            )
            .first()
        )
        if existing is not None:
            existing.evidence = evidence
            existing.recommended_action = recommended_action
            existing.generated_at = datetime.now(UTC)
            existing.policy_version = policy_version
            rows.append(existing)
            continue

        signal = models.RiskSignal(
            id=f"risk_{uuid.uuid4().hex[:8]}",
            student_id=student_id,
            section_id=section.id,
            assignment_id=None,
            risk_type="SELF_REPORTED_HELP_REQUEST",
            risk_level="HIGH",
            triggered_rules=["student_requested_help_in_reflection"],
            evidence=evidence,
            recommended_action=recommended_action,
            generated_at=datetime.now(UTC),
            resolved_at=None,
            resolution_type=None,
            policy_version=policy_version,
        )
        db.add(signal)
        rows.append(signal)

    if rows:
        db.commit()
    return rows
