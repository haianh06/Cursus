# src/api/instructor.py
import csv
import io
import uuid
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token, get_notification_service
from src.db import models
from src.db.connection import get_db
from src.repositories.academic_term_repository import AcademicTermRepository
from src.repositories.audit_repository import AuditRepository
from src.repositories.class_activity_repository import ClassActivityRepository
from src.repositories.ownership_repository import OwnershipRepository
from src.repositories.quiz_repository import QuizRepository
from src.security.authorization import require_permission, require_roles
from src.security.ownership import (
    require_instructor_assignment_owner,
    require_instructor_guardrail_owner,
    require_instructor_risk_owner,
    require_instructor_student_owner,
)
from src.security.permissions import Permission, Resource
from src.services.class_activity_service import ClassActivityService
from src.services.core.audit_service import AuditService
from src.services.core.notification_service import NotificationService
from src.services.quiz_service import QuizService
from src.services.risk_signal_service import (
    compute_class_metrics,
    detect_declining_completion_risks,
    is_risk_overdue,
    risk_days_open,
)
from src.services.risk_signal_service import (
    student_recent_weekly_rates as _student_recent_weekly_rates,
)

router = APIRouter(
    prefix="/instructor",
    tags=["instructor"],
    dependencies=[
        Depends(require_roles(models.UserRole.INSTRUCTOR, models.UserRole.ADMIN))
    ],
)

@router.get("/announcements")
def list_instructor_announcements(db: Session = Depends(get_db)):
    """Thong bao rong tu Admin — hien trong khoi thong bao tren dashboard GV."""
    rows = (
        db.query(models.AdminAnnouncement)
        .order_by(models.AdminAnnouncement.created_at.desc())
        .limit(5)
        .all()
    )
    result = []
    for row in rows:
        author = db.query(models.User).filter_by(id=row.created_by).first()
        result.append({
            "id": row.id,
            "title": row.title,
            "content": row.content,
            "authorName": author.full_name if author else "Admin",
            "createdAt": row.created_at.isoformat(),
        })
    return {"announcements": result}


class InterventionRequest(BaseModel):
    decision: str  # APPROVE, EDIT, REJECT
    editedIntervention: str | None = None  # noqa: N815
    note: str | None = None  # Ghi chu ly do can thiep, GV tu nhap (khong bat buoc)

def _default_intervention_summary(decision: str) -> str:
    """Dong lich su can thiep (F10) can co noi dung ngay ca khi GV khong go
    ghi chu — khong de trong dong timeline."""
    return {
        "APPROVE": "Đánh dấu đã can thiệp.",
        "EDIT": "Đã chỉnh sửa hành động đề xuất.",
        "REJECT": "Đã bỏ qua cảnh báo.",
    }.get(decision, "Đã cập nhật trạng thái case.")

@router.get("/dashboard")
def get_instructor_dashboard(
    course_id: str | None = None,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    # Tat ca section GV nay day - dung de dung danh sach mon cho bo loc (F9),
    # khong bi anh huong boi course_id dang chon.
    all_sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()

    courses = []
    seen_course_ids = set()
    for s in all_sections:
        c = db.query(models.Course).filter_by(id=s.course_id).first()
        if c and c.id not in seen_course_ids:
            seen_course_ids.add(c.id)
            courses.append({
                "id": c.id,
                "code": c.code,
                "name": c.name
            })

    # Section da loc theo course_id (F9) - moi so lieu ben duoi deu tinh tren
    # tap nay, "ALL"/None nghia la gop het cac lop GV dang day.
    sections = all_sections
    if course_id and course_id != "ALL":
        sections = [s for s in all_sections if s.course_id == course_id]
    section_ids = [s.id for s in sections]

    # A2 — cap nhat canh bao xu huong giam TRUOC khi dem, de highRiskCount/
    # totalActiveWarnings phan anh dung ca case moi phat hien trong lan tai nay.
    detect_declining_completion_risks(db, section_ids)

    # Si so that, dem canh bao, ty le hoan thanh: 1 cong thuc dung chung voi
    # B3 (so sanh nhieu lop) o ham compute_class_metrics, tranh 2 noi lech so.
    metrics = compute_class_metrics(db, section_ids)

    return {
        "classCompletionRate": None,
        "onTimeSubmissions": None,
        "highRiskCount": metrics["highRiskCount"],
        "totalActiveWarnings": metrics["totalActiveWarnings"],
        "overdueCount": metrics["overdueCount"],
        "courses": courses,
        "classSize": metrics["classSize"],
        "classAvgCompletionByWeek": metrics["classAvgCompletionByWeek"],
    }

@router.get("/dashboard/export")
def export_dashboard_report(
    course_id: str | None = None,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """F12 — xuat CSV tu DUNG so lieu da tinh o get_instructor_dashboard (goi
    lai ham do), khong tinh rieng mot lan nua o day de tranh 2 noi lech so."""
    dashboard = get_instructor_dashboard(course_id=course_id, current_user=current_user, db=db)

    buffer = io.StringIO()
    buffer.write("﻿")  # BOM - Excel mo file UTF-8 tieng Viet khong bi loi font
    writer = csv.writer(buffer)
    writer.writerow(["Cursus — Báo cáo lớp", datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")])
    writer.writerow([])
    writer.writerow(["Sĩ số", dashboard["classSize"]])
    writer.writerow(["Số cảnh báo đang mở", dashboard["totalActiveWarnings"]])
    writer.writerow(["Số rủi ro mức cao", dashboard["highRiskCount"]])
    writer.writerow([])
    writer.writerow(["Tuần", "Tỷ lệ hoàn thành (%)"])
    for index, rate in enumerate(dashboard["classAvgCompletionByWeek"], start=1):
        writer.writerow([f"W{index}", round(rate * 100, 1)])

    buffer.seek(0)
    filename = f"cursus-bao-cao-lop-{datetime.now(UTC).strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/classes/compare")
def compare_instructor_classes(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """B3 — so sanh tat ca cac lop GV dang day cung luc, thay vi chi xem duoc
    1 lop/gop het tai 1 thoi diem nhu bo loc F9. Dung chung compute_class_metrics
    voi dashboard (F4) nen so lieu luon khop nhau giua 2 man hinh."""
    all_sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()

    rows = []
    seen_course_ids: set[str] = set()
    for section in all_sections:
        if section.course_id in seen_course_ids:
            continue
        seen_course_ids.add(section.course_id)

        course = db.query(models.Course).filter_by(id=section.course_id).first()
        course_section_ids = [s.id for s in all_sections if s.course_id == section.course_id]
        detect_declining_completion_risks(db, course_section_ids)
        metrics = compute_class_metrics(db, course_section_ids)
        weekly = metrics["classAvgCompletionByWeek"]

        rows.append({
            "courseId": section.course_id,
            "code": course.code if course else section.course_id,
            "name": course.name if course else "",
            "classSize": metrics["classSize"],
            "highRiskCount": metrics["highRiskCount"],
            "totalActiveWarnings": metrics["totalActiveWarnings"],
            "overdueCount": metrics["overdueCount"],
            "latestWeekCompletion": round(weekly[-1] * 100, 1) if weekly else None,
        })

    rows.sort(key=lambda row: row["code"])
    return {"classes": rows}


def _serialize_risk_row(db: Session, r: models.RiskSignal) -> dict:
    """Dung chung boi GET /risks, GET /risks/{id} va ho so SV (A1), de 3 noi
    nay khong bao gio lech shape voi nhau."""
    student = db.query(models.User).filter_by(id=r.student_id).first()
    asg = db.query(models.Assignment).filter_by(id=r.assignment_id).first() if r.assignment_id else None
    sec = db.query(models.CourseSection).filter_by(id=r.section_id).first()

    return {
        "id": r.id,
        "studentId": r.student_id,
        "studentAlias": student.full_name if student else "Unknown Student",
        "courseId": sec.course_id if sec else "",
        "assignmentTitle": asg.title if asg else "General Course Progress",
        "riskLevel": r.risk_level,
        "riskType": r.risk_type,
        "status": "INTERVENTION_APPROVED" if r.resolved_at else "INTERVENTION_PENDING",
        # `status` above only distinguishes resolved-vs-not; it can't tell
        # APPROVE apart from REJECT (both set resolved_at). resolutionType
        # is what the UI needs to render "Intervened" vs "Dismissed".
        "resolutionType": r.resolution_type,
        "evidence": r.evidence,
        "recommendedIntervention": r.recommended_action,
        "instructorNote": r.instructor_note,
        "generatedAt": r.generated_at.isoformat(),
        "policyVersion": r.policy_version,
        # B2 — canh bao SLA noi bo: case mo qua RISK_SLA_DAYS ma chua co
        # quyet dinh. Chi la nhan hien thi, khong doi hanh vi HITL nao.
        "daysOpen": risk_days_open(r),
        "isOverdue": is_risk_overdue(r),
    }


@router.get("/risks")
def get_instructor_risks(
    course_id: str | None = None,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()
    if course_id and course_id != "ALL":
        sections = [s for s in sections if s.course_id == course_id]

    section_ids = [s.id for s in sections]

    # A2 — xem ghi chu trong get_instructor_dashboard.
    detect_declining_completion_risks(db, section_ids)

    risks = db.query(models.RiskSignal).filter(
        models.RiskSignal.section_id.in_(section_ids)
    ).order_by(models.RiskSignal.generated_at.desc()).all()

    return [_serialize_risk_row(db, r) for r in risks]

@router.get("/risks/{risk_id}")
def get_risk_detail(
    risk_id: str,
    _: None = Depends(require_instructor_risk_owner),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    r = db.query(models.RiskSignal).filter_by(id=risk_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Risk case not found")

    return _serialize_risk_row(db, r)

def _apply_intervention_decision(
    db: Session,
    r: models.RiskSignal,
    *,
    decision: str,
    edited_intervention: str | None,
    note: str | None,
    instructor_id: str,
) -> dict:
    """Loi cua submit_intervention, tach ra de dung lai cho ca thao tac don
    (F5) lan thao tac hang loat (B1) — cung 1 duong ghi du lieu, khong co
    duong tat rieng cho bulk co the lech logic voi tung case mot."""
    previous_state = "INTERVENTION_APPROVED" if r.resolved_at else "INTERVENTION_PENDING"

    if decision == "APPROVE" or decision == "EDIT":
        r.resolved_at = datetime.now(UTC)
        r.resolution_type = f"INSTRUCTOR_{decision}"
        if edited_intervention:
            r.recommended_action = edited_intervention
    elif decision == "REJECT":
        r.resolved_at = datetime.now(UTC)
        r.resolution_type = "INSTRUCTOR_REJECTED"

    # Ghi chu la ly do can thiep GV tu nhap - luu du khi note rong de xoa
    # duoc ghi chu cu neu GV sua lai quyet dinh.
    if note is not None:
        r.instructor_note = note

    # F10 — them ban ghi vao dong thoi gian can thiep (khong ghi de len ban
    # ghi truoc, moi lan bam la 1 dong lich su moi). Bang instructor_interventions
    # da co san trong schema tu truoc nhung chua duoc su dung o dau ca.
    intervention_id = f"int_{uuid.uuid4().hex[:6]}"
    db.add(
        models.InstructorIntervention(
            id=intervention_id,
            risk_signal_id=r.id,
            instructor_id=instructor_id,
            action_taken=note or _default_intervention_summary(decision),
            status=decision,
            created_at=datetime.now(UTC),
        )
    )

    return {
        "id": intervention_id,
        "riskId": r.id,
        "decision": decision,
        "status": "INTERVENTION_APPROVED" if r.resolved_at else "INTERVENTION_PENDING",
        "auditMetadata": {
            "actorId": instructor_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "previousState": previous_state,
            "newState": "RESOLVED"
        }
    }


@router.post("/risks/{risk_id}/intervention")
def submit_intervention(
    risk_id: str,
    payload: InterventionRequest,
    _owner: None = Depends(require_instructor_risk_owner),
    _permission: models.User = Depends(
        require_permission(Resource.INTERVENTION, Permission.APPROVE)
    ),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    if payload.decision not in {"APPROVE", "EDIT", "REJECT"}:
        raise HTTPException(status_code=400, detail="decision must be APPROVE, EDIT, or REJECT")

    r = db.query(models.RiskSignal).filter_by(id=risk_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Risk case not found")

    result = _apply_intervention_decision(
        db, r,
        decision=payload.decision,
        edited_intervention=payload.editedIntervention,
        note=payload.note,
        instructor_id=current_user.id,
    )
    db.commit()
    return result


class BulkInterventionRequest(BaseModel):
    riskIds: list[str] = Field(min_length=1, max_length=200)  # noqa: N815
    decision: str  # APPROVE, REJECT (EDIT khong co y nghia hang loat — moi
    # case can 1 hanh dong de xuat rieng, khong dung chung 1 editedIntervention)
    note: str | None = None


@router.post("/risks/bulk-intervention")
async def submit_bulk_intervention(
    payload: BulkInterventionRequest,
    _permission: models.User = Depends(
        require_permission(Resource.INTERVENTION, Permission.APPROVE)
    ),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """B1 — ap 1 quyet dinh + 1 ghi chu cho NHIEU case cung luc (vd: nhac tat
    ca SV hoan thanh <50% tuan nay), thay vi phai mo tung case mot. Moi case
    van di qua dung _apply_intervention_decision (van co dong F10 rieng), chi
    khac la GV bam 1 lan cho ca nhom.

    Bo qua (khong loi ca request) neu 1 risk_id khong ton tai hoac khong
    thuoc lop GV nay day — tra ve ket qua tung dong de FE bao chinh xac case
    nao thanh cong/that bai, giong tinh than cua list nop bai (A4): thieu thi
    bao ro, khong am tham nuot loi.
    """
    if payload.decision not in {"APPROVE", "REJECT"}:
        raise HTTPException(status_code=400, detail="decision must be APPROVE or REJECT")

    is_admin = str(current_user.role) == models.UserRole.ADMIN.value
    ownership = OwnershipRepository(db)

    results = []
    any_applied = False
    # Loai trung ma van giu dung thu tu GV chon, tranh 1 id lap 2 lan ghi 2
    # dong F10 cho cung 1 lan bam.
    seen_ids: set[str] = set()
    for risk_id in payload.riskIds:
        if risk_id in seen_ids:
            continue
        seen_ids.add(risk_id)

        if not is_admin and not ownership.instructor_owns_risk(current_user.id, risk_id):
            results.append({"riskId": risk_id, "ok": False, "error": "not_owned"})
            continue
        r = db.query(models.RiskSignal).filter_by(id=risk_id).first()
        if not r:
            results.append({"riskId": risk_id, "ok": False, "error": "not_found"})
            continue

        outcome = _apply_intervention_decision(
            db, r,
            decision=payload.decision,
            edited_intervention=None,
            note=payload.note,
            instructor_id=current_user.id,
        )
        any_applied = True
        results.append({"riskId": risk_id, "ok": True, "status": outcome["status"]})

    if any_applied:
        db.commit()
        await AuditService(AuditRepository(db)).log_event(
            event_type="BULK_UPDATE_RISKS",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="RISK_SIGNAL",
            resource_id="BULK",
            metadata={"decision": payload.decision, "count": len([r for r in results if r["ok"]])}
        )

    return {
        "results": results,
        "appliedCount": sum(1 for row in results if row["ok"]),
        "failedCount": sum(1 for row in results if not row["ok"]),
    }

@router.get("/risks/{risk_id}/interventions")
def get_intervention_history(
    risk_id: str,
    _owner: None = Depends(require_instructor_risk_owner),
    db: Session = Depends(get_db)
):
    """F10 — toan bo lich su can thiep cua 1 case, moi nhat truoc."""
    logs = (
        db.query(models.InstructorIntervention)
        .filter_by(risk_signal_id=risk_id)
        .order_by(models.InstructorIntervention.created_at.desc())
        .all()
    )
    result = []
    for log in logs:
        instructor = db.query(models.User).filter_by(id=log.instructor_id).first()
        result.append({
            "id": log.id,
            "decision": log.status,
            "note": log.action_taken,
            "instructorName": instructor.full_name if instructor else "Unknown Instructor",
            "createdAt": log.created_at.isoformat(),
        })
    return result

# F8 - nguong ghi nhan tich cuc: SV dat >= KUDOS_THRESHOLD hoan thanh trong
# KUDOS_MIN_STREAK_WEEKS tuan gan nhat co du lieu. Cong thuc co dinh giong F5
# (khong phai AI doan), doi trong voi danh sach rui ro chi toan tin hieu tieu cuc.
KUDOS_THRESHOLD = 0.9
KUDOS_MIN_STREAK_WEEKS = 2

@router.get("/kudos")
def get_instructor_kudos(
    course_id: str | None = None,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db)
):
    """F8 - ghi nhan tich cuc (Kudos), lay cam hung tu Starfish: canh bao rui
    ro (F5) khong nen la tin hieu duy nhat GV thay ve mot SV."""
    all_sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()
    sections = all_sections
    if course_id and course_id != "ALL":
        sections = [s for s in all_sections if s.course_id == course_id]
    section_ids = [s.id for s in sections]

    enrollments = db.query(models.Enrollment).filter(
        models.Enrollment.section_id.in_(section_ids),
        models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
    ).all()

    # 1 dong the ghi nhan / SV, ke ca khi SV hoc nhieu lop cua cung GV nay
    # (vi du day 2 mon khac nhau) - lay section gap dau tien lam course dai dien.
    course_by_student: dict[str, str] = {}
    for enrollment in enrollments:
        course_by_student.setdefault(enrollment.student_id, enrollment.section_id)

    result = []
    for student_id, section_id in course_by_student.items():
        recent = _student_recent_weekly_rates(db, student_id, KUDOS_MIN_STREAK_WEEKS)
        if len(recent) < KUDOS_MIN_STREAK_WEEKS:
            continue
        if not all(rate >= KUDOS_THRESHOLD for _week, rate in recent):
            continue

        student = db.query(models.User).filter_by(id=student_id).first()
        sec = db.query(models.CourseSection).filter_by(id=section_id).first()
        result.append({
            "studentId": student_id,
            "displayName": student.full_name if student else "Unknown Student",
            "courseId": sec.course_id if sec else "",
            "weeks": [week for week, _rate in recent],
            "note": (
                f"Hoàn thành từ {int(KUDOS_THRESHOLD * 100)}% trở lên trong "
                f"{KUDOS_MIN_STREAK_WEEKS} tuần gần nhất"
            ),
        })
    return {"kudos": result}


# ============================================================
# C1 — Digest tuần cho GV
# ============================================================

DIGEST_DEFAULT_DAYS = 7


def _build_instructor_digest(db: Session, current_user: models.User, days: int) -> dict:
    """Dung chung boi ca man xem trong app va email — 1 nguon du lieu duy
    nhat, tranh hai noi lech so voi nhau."""
    all_sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()
    section_ids = [s.id for s in all_sections]
    detect_declining_completion_risks(db, section_ids)

    cutoff = datetime.now(UTC) - timedelta(days=days)

    new_risks = []
    if section_ids:
        new_risks = (
            db.query(models.RiskSignal)
            .filter(
                models.RiskSignal.section_id.in_(section_ids),
                models.RiskSignal.generated_at >= cutoff,
            )
            .order_by(models.RiskSignal.generated_at.desc())
            .all()
        )

    cutoff_naive = cutoff.replace(tzinfo=None)
    guardrail_events = _visible_guardrail_events(db, current_user, limit=200)
    new_guardrail = [
        item for item in guardrail_events
        if item.get("createdAt") and datetime.fromisoformat(item["createdAt"]) >= cutoff_naive
    ]

    kudos_payload = get_instructor_kudos(course_id=None, current_user=current_user, db=db)
    kudos = kudos_payload.get("kudos", [])

    return {
        "sinceDate": cutoff.date().isoformat(),
        "days": days,
        "newRiskCases": [_serialize_risk_row(db, r) for r in new_risks],
        "newGuardrailCases": new_guardrail,
        "kudos": kudos,
        "summary": {
            "newRiskCount": len(new_risks),
            "newGuardrailCount": len(new_guardrail),
            "kudosCount": len(kudos),
        },
    }


@router.get("/digest")
def get_instructor_digest(
    days: int = Query(default=DIGEST_DEFAULT_DAYS, ge=1, le=90),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """C1 — tom tat case moi phat sinh trong N ngay gan nhat, tinh on-demand
    (khong luu bang rieng, giong Kudos). Khong co scheduler/cron gui dinh
    ky tu dong — GV tu mo xem hoac tu bam gui email khi can (xem endpoint
    ben duoi), vi du an nay chua co ha tang lich hen nen."""
    return _build_instructor_digest(db, current_user, days)


@router.post("/digest/email")
async def email_instructor_digest(
    days: int = Query(default=DIGEST_DEFAULT_DAYS, ge=1, le=90),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
    notifications: NotificationService = Depends(get_notification_service),
):
    """C1 — GV tu bam gui ban tom tat nay ve dung email cua minh (khong gui
    cho ai khac). Dung chung EmailService voi luong xac thuc tai khoan —
    moi truong demo (EMAIL_PROVIDER=none) se chi log lai, khong that su gui."""
    digest = _build_instructor_digest(db, current_user, days)
    await notifications.send_instructor_digest(current_user.email, current_user.full_name, digest)
    return {"sent": True, "to": current_user.email}


class GuardrailReviewDecision(BaseModel):
    decision: str  # KEEP | UNBLOCK
    note: str | None = None


def _serialize_guardrail_review(
    event: models.GuardrailEvent,
    *,
    student_name: str,
    question: str,
    student_id: str | None = None,
) -> dict:
    status = event.review_status or "PENDING"
    reason = event.block_reason
    if not reason and isinstance(event.safety_evaluation, dict):
        reason = event.safety_evaluation.get("reason") or event.safety_evaluation.get(
            "block_reason"
        )
    # created_at ghi nhan luc cau hoi bi chan that su dien ra, khong phai luc
    # GV xu ly xong — case con PENDING van can hien "hoi luc nao" duoc.
    return {
        "id": event.id,
        "studentId": student_id,
        "studentAlias": student_name,
        "question": question,
        "blockedAnswer": event.blocked_answer
        or (
            event.safety_evaluation.get("response")
            if isinstance(event.safety_evaluation, dict)
            else None
        ),
        "blockReason": reason or "academic_integrity",
        "classification": event.classification,
        "reviewStatus": status,
        "createdAt": event.created_at.isoformat() if event.created_at else None,
        "messageId": event.message_id,
    }


@router.get("/guardrail-reviews")
def list_guardrail_reviews(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """List blocked Q&A cases awaiting / finished instructor review.

    An case thuoc RO RANG mot lop GV KHAC dang day (Conversation.section_id
    -> CourseSection.instructor_id khac current_user) de tranh lo du lieu cheo
    lop. Case KHONG gan section (cau hoi chung, section_id NULL) van hien cho
    moi GV/ADMIN vi khong co tin hieu nao de quy ve dung 1 lop — an het nhung
    case nay di thi khong ai xu ly duoc, con te hon la khong loc.
    """
    return _visible_guardrail_events(db, current_user)


def _visible_guardrail_events(
    db: Session,
    current_user: models.User,
    *,
    student_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Loi cua list_guardrail_reviews, tach ra de dung lai cho ho so SV (A1) —
    cung 1 quy tac loc theo lop, khong duoc trung lap logic o 2 noi vi day la
    logic nhay cam ve quyen rieng tu (rat de lech nhau khi sua 1 cho ma quen
    cho con lai)."""
    is_admin = str(current_user.role) == models.UserRole.ADMIN.value
    section_ids: set[str] | None = None
    if not is_admin:
        sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()
        section_ids = {s.id for s in sections}

    events = (
        db.query(models.GuardrailEvent)
        .filter(models.GuardrailEvent.classification == "BLOCKED")
        .order_by(models.GuardrailEvent.id.desc())
        .limit(200)
        .all()
    )
    reviews: list[dict] = []
    for event in events:
        message = db.query(models.Message).filter_by(id=event.message_id).first()
        student_name = "Unknown Student"
        question = ""
        conversation = None
        conv_student_id: str | None = None
        if message is not None:
            question = message.content or ""
            conversation = (
                db.query(models.Conversation).filter_by(id=message.conversation_id).first()
                if message.conversation_id
                else None
            )
            conv_student_id = getattr(conversation, "student_id", None)
            if conv_student_id:
                student = db.query(models.User).filter_by(id=conv_student_id).first()
                if student:
                    student_name = student.full_name

        if student_id is not None and conv_student_id != student_id:
            continue

        if section_ids is not None:
            conv_section_id = getattr(conversation, "section_id", None)
            if conv_section_id is not None and conv_section_id not in section_ids:
                continue

        reviews.append(
            _serialize_guardrail_review(
                event, student_name=student_name, question=question, student_id=conv_student_id
            )
        )
        if len(reviews) >= limit:
            break
    return reviews


@router.post("/guardrail-reviews/{case_id}")
def decide_guardrail_review(
    case_id: str,
    payload: GuardrailReviewDecision,
    _owner: None = Depends(require_instructor_guardrail_owner),
    _permission: models.User = Depends(
        require_permission(Resource.GUARDRAIL, Permission.APPROVE)
    ),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """HITL cho appeal: KEEP = giu chan (SV nhan thong bao bi tu choi, do
    tang khac gui - endpoint nay KHONG tu gui gi), UNBLOCK = duyet bo chan."""
    decision = (payload.decision or "").strip().upper()
    if decision not in {"KEEP", "UNBLOCK"}:
        raise HTTPException(status_code=400, detail="decision must be KEEP or UNBLOCK")

    event = db.query(models.GuardrailEvent).filter_by(id=case_id).first()
    if event is None:
        raise HTTPException(status_code=404, detail="Guardrail review case not found")
    if event.classification != "BLOCKED":
        raise HTTPException(status_code=400, detail="Only BLOCKED events can be reviewed")

    previous = event.review_status or "PENDING"
    event.review_status = "KEPT_BLOCKED" if decision == "KEEP" else "UNBLOCKED"
    event.reviewed_by = current_user.id
    event.reviewed_at = datetime.now(UTC).replace(tzinfo=None)
    if payload.note is not None:
        event.reviewer_note = payload.note
    db.commit()

    return {
        "id": event.id,
        "decision": decision,
        "reviewStatus": event.review_status,
        "auditMetadata": {
            "actorId": current_user.id,
            "timestamp": datetime.now(UTC).isoformat(),
            "previousState": previous,
            "newState": event.review_status,
        },
    }


# ============================================================
# A1 — Hồ sơ 360° của 1 SV | A3 — Sổ ghi chú riêng của GV
# ============================================================

def _serialize_note(note: models.InstructorStudentNote) -> dict:
    return {
        "id": note.id,
        "content": note.content,
        "createdAt": note.created_at.isoformat(),
    }


def _serialize_reflection_summary(reflection: models.WeeklyReflection) -> dict:
    """C2 — CHI vai chi so tong hop, KHONG BAO GIO tra ve content/challenge/
    plan (van ban SV tu go). "Reflection chi tiet mac dinh rieng tu; ban tom
    tat chia se phai co consent" (docs/PROJECT_CONTEXT.md muc 14) — chi goi
    ham nay khi student.share_reflection_summary = True."""
    metrics = reflection.metrics if isinstance(reflection.metrics, dict) else {}
    adjustments = metrics.get("adjustments") or []
    return {
        "weekNumber": reflection.week_number,
        "completionRate": metrics.get("completionRate"),
        "completionBand": metrics.get("completionBand"),
        "hoursPlanned": metrics.get("hoursPlanned"),
        "hoursActual": metrics.get("hoursActual"),
        "requestedHelp": "request_help" in adjustments,
    }


@router.get("/students/{student_id}/profile")
async def get_student_profile(
    student_id: str,
    _owner: None = Depends(require_instructor_student_owner),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """A1 — trang tổng hợp 1 SV: chỉ hiện những lớp/case thuộc về GV đang xem
    (không lộ lớp SV học với GV khác), gộp F5 (risk), Guardrail và ghi chú
    riêng (A3) vào một chỗ để GV không phải lật nhiều màn khi cần ngữ cảnh
    đầy đủ trước một cuộc gặp hay quyết định can thiệp."""
    student = db.query(models.User).filter_by(id=student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    await AuditService(AuditRepository(db)).log_event(
        event_type="READ_STUDENT_PROFILE",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="STUDENT_PROFILE",
        resource_id=student_id,
        metadata={"reason": "Instructor accessing student profile for intervention context"}
    )

    my_sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()
    my_section_by_id = {s.id: s for s in my_sections}

    enrollments = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.student_id == student_id,
            models.Enrollment.section_id.in_(my_section_by_id.keys()),
            models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
        )
        .all()
    )
    courses = []
    for e in enrollments:
        sec = my_section_by_id.get(e.section_id)
        if not sec:
            continue
        c = db.query(models.Course).filter_by(id=sec.course_id).first()
        if c:
            courses.append({"id": c.id, "code": c.code, "name": c.name, "sectionId": sec.id})

    weekly_history = [
        {"week": week, "rate": round(rate * 100, 1)}
        for week, rate in reversed(_student_recent_weekly_rates(db, student_id, 12))
    ]

    my_section_ids = list(my_section_by_id.keys())
    risks = (
        db.query(models.RiskSignal)
        .filter(
            models.RiskSignal.student_id == student_id,
            models.RiskSignal.section_id.in_(my_section_ids),
        )
        .order_by(models.RiskSignal.generated_at.desc())
        .all()
    )

    notes = (
        db.query(models.InstructorStudentNote)
        .filter_by(instructor_id=current_user.id, student_id=student_id)
        .order_by(models.InstructorStudentNote.created_at.desc())
        .all()
    )

    # C2 — chi tra ban tom tat khi SV da bat consent (mac dinh tat). Khong co
    # consent thi tra mang rong, KHONG bao gio suy doan/bo qua co che nay.
    reflection_summary: list[dict] = []
    if student.share_reflection_summary:
        reflections = (
            db.query(models.WeeklyReflection)
            .filter_by(student_id=student_id)
            .order_by(models.WeeklyReflection.week_number.desc())
            .limit(8)
            .all()
        )
        reflection_summary = [
            _serialize_reflection_summary(r) for r in reversed(reflections)
        ]

    return {
        "studentId": student.id,
        "displayName": student.full_name,
        "email": student.email,
        "courses": courses,
        "weeklyCompletionHistory": weekly_history,
        "riskHistory": [_serialize_risk_row(db, r) for r in risks],
        "guardrailHistory": _visible_guardrail_events(db, current_user, student_id=student_id, limit=50),
        "notes": [_serialize_note(n) for n in notes],
        "reflectionSharingEnabled": bool(student.share_reflection_summary),
        "reflectionSummary": reflection_summary,
    }


class StudentNoteCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


@router.get("/students/{student_id}/notes")
def list_student_notes(
    student_id: str,
    _owner: None = Depends(require_instructor_student_owner),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """A3 — sổ ghi chú riêng của GV về 1 SV, độc lập với risk case. Chỉ tác
    giả đọc được ghi chú của chính mình, kể cả khi 2 GV cùng dạy 1 SV."""
    notes = (
        db.query(models.InstructorStudentNote)
        .filter_by(instructor_id=current_user.id, student_id=student_id)
        .order_by(models.InstructorStudentNote.created_at.desc())
        .all()
    )
    return {"notes": [_serialize_note(n) for n in notes]}


@router.post("/students/{student_id}/notes", status_code=201)
def create_student_note(
    student_id: str,
    payload: StudentNoteCreateRequest,
    _owner: None = Depends(require_instructor_student_owner),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    note = models.InstructorStudentNote(
        id=f"note_{uuid.uuid4().hex[:8]}",
        instructor_id=current_user.id,
        student_id=student_id,
        content=payload.content.strip(),
        created_at=datetime.now(UTC),
    )
    db.add(note)
    db.commit()
    return _serialize_note(note)


@router.delete("/students/{student_id}/notes/{note_id}", status_code=204)
def delete_student_note(
    student_id: str,
    note_id: str,
    _owner: None = Depends(require_instructor_student_owner),
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    # Chi xoa dung ghi chu cua chinh minh - khong dung require_instructor_student_owner
    # de phan biet quyen xoa, vi guard do chi kiem tra GV co day SV nay khong,
    # khong kiem tra ai la tac gia ghi chu.
    note = (
        db.query(models.InstructorStudentNote)
        .filter_by(id=note_id, instructor_id=current_user.id, student_id=student_id)
        .first()
    )
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()


# ============================================================
# A4 — Danh sách nộp bài chi tiết theo assignment
# ============================================================

@router.get("/assignments")
def list_instructor_assignments(
    course_id: str | None = None,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    sections = db.query(models.CourseSection).filter_by(instructor_id=current_user.id).all()
    if course_id and course_id != "ALL":
        sections = [s for s in sections if s.course_id == course_id]
    section_by_id = {s.id: s for s in sections}

    assignments = (
        db.query(models.Assignment)
        .filter(models.Assignment.section_id.in_(section_by_id.keys()))
        .order_by(models.Assignment.due_date.desc())
        .all()
    )
    result = []
    for a in assignments:
        sec = section_by_id.get(a.section_id)
        result.append({
            "id": a.id,
            "title": a.title,
            "dueDate": a.due_date.isoformat(),
            "courseId": sec.course_id if sec else "",
        })
    return {"assignments": result}


@router.get("/assignments/{assignment_id}/submissions")
def get_assignment_submissions(
    assignment_id: str,
    _owner: None = Depends(require_instructor_assignment_owner),
    _permission: models.User = Depends(
        require_permission(Resource.ASSIGNMENT, Permission.READ)
    ),
    db: Session = Depends(get_db),
):
    """A4 — ai đã nộp / chưa nộp cho 1 assignment, thay vì chỉ có % hoàn
    thành gộp cả lớp (F4). SV chưa nộp gì cũng phải hiện — thiếu dòng nghĩa
    là "chưa nộp", không phải xoá SV khỏi danh sách."""
    assignment = db.query(models.Assignment).filter_by(id=assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    enrollments = (
        db.query(models.Enrollment)
        .filter(
            models.Enrollment.section_id == assignment.section_id,
            models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
        )
        .all()
    )
    student_ids = [e.student_id for e in enrollments]
    submissions_by_student = {
        s.student_id: s
        for s in db.query(models.Submission).filter(
            models.Submission.assignment_id == assignment_id,
            models.Submission.student_id.in_(student_ids),
        ).all()
    }

    roster = []
    for student_id in student_ids:
        student = db.query(models.User).filter_by(id=student_id).first()
        sub = submissions_by_student.get(student_id)
        roster.append({
            "studentId": student_id,
            "displayName": student.full_name if student else "Unknown Student",
            "submitted": sub is not None,
            "submittedAt": sub.submitted_at.isoformat() if sub else None,
            "isLate": sub.is_late if sub else None,
            "gradingStatus": sub.grading_status if sub else None,
            "grade": sub.grade if sub else None,
            "content": sub.content if sub else None,
            "feedback": sub.feedback if sub else None,
        })
    # SV chua nop len dau — do la nhung dong GV can nhac truoc tien.
    roster.sort(key=lambda row: (row["submitted"], row["displayName"]))

    return {
        "assignmentId": assignment.id,
        "assignmentTitle": assignment.title,
        "dueDate": assignment.due_date.isoformat(),
        "submissions": roster,
    }


class ClassActivityCreateRequest(BaseModel):
    course_id: str = Field(min_length=1, max_length=64)
    activity_date: date
    kind: str = Field(min_length=1, max_length=32)
    title: str = Field(default="", max_length=120)
    opens_at: datetime | None = None
    closes_at: datetime | None = None


class ClassActivityUpdateRequest(BaseModel):
    activity_date: date | None = None
    kind: str | None = Field(default=None, max_length=32)
    title: str | None = Field(default=None, max_length=120)
    opens_at: datetime | None = None
    closes_at: datetime | None = None


def get_class_activity_service(db: Session = Depends(get_db)) -> ClassActivityService:
    return ClassActivityService(ClassActivityRepository(db), AcademicTermRepository(db))


@router.get("/class-activities")
def list_class_activities(
    start: date | None = Query(default=None),
    end: date | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    service: ClassActivityService = Depends(get_class_activity_service),
):
    return {
        "activities": service.list_mine(
            user_id=current_user.id,
            role=str(current_user.role),
            organization_id=current_user.organization_id,
            start=start,
            end=end,
        ),
        "window": service.get_scheduling_window(current_user.organization_id),
    }


@router.post("/class-activities", status_code=201)
def create_class_activity(
    payload: ClassActivityCreateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: ClassActivityService = Depends(get_class_activity_service),
):
    try:
        return service.create(
            user_id=current_user.id,
            role=str(current_user.role),
            organization_id=current_user.organization_id,
            course_id=payload.course_id,
            activity_date=payload.activity_date,
            kind=payload.kind,
            title=payload.title,
            opens_at=payload.opens_at,
            closes_at=payload.closes_at,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/class-activities/{activity_id}")
def update_class_activity(
    activity_id: str,
    payload: ClassActivityUpdateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: ClassActivityService = Depends(get_class_activity_service),
):
    try:
        return service.update(
            user_id=current_user.id,
            role=str(current_user.role),
            organization_id=current_user.organization_id,
            activity_id=activity_id,
            kind=payload.kind,
            title=payload.title,
            activity_date=payload.activity_date,
            opens_at=payload.opens_at,
            closes_at=payload.closes_at,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/class-activities/{activity_id}", status_code=204)
def delete_class_activity(
    activity_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: ClassActivityService = Depends(get_class_activity_service),
):
    try:
        service.delete(
            user_id=current_user.id,
            role=str(current_user.role),
            organization_id=current_user.organization_id,
            activity_id=activity_id,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class QuizCreateRequest(BaseModel):
    section_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=2000)
    time_limit_minutes: int = Field(default=15, ge=1, le=180)
    due_date: datetime | None = None
    opens_at: datetime | None = None


class QuizUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    time_limit_minutes: int | None = Field(default=None, ge=1, le=180)
    due_date: datetime | None = None
    opens_at: datetime | None = None


class QuizQuestionRequest(BaseModel):
    question_text: str = Field(min_length=1, max_length=2000)
    question_type: str = Field(min_length=1, max_length=32)
    correct_answer: str = Field(default="", max_length=2000)
    options: list[str] = Field(default_factory=list)
    points: float = Field(default=1, ge=0, le=100)


class QuizQuestionReorderRequest(BaseModel):
    question_ids: list[str]


class QuizGenerateRequest(BaseModel):
    count: int = Field(default=5, ge=1, le=20)


class QuizGradeRequest(BaseModel):
    scores: dict[str, float] = Field(default_factory=dict)
    feedback: str | None = Field(default=None, max_length=2000)


def get_quiz_service(db: Session = Depends(get_db)) -> QuizService:
    return QuizService(QuizRepository(db))


@router.get("/quizzes/classes")
def list_quiz_classes(
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    """Danh sach lop (section) GV dang day, dung cho dropdown mon -> lop khi
    tao quiz moi (giao theo tung lop, khong phai theo mon chung chung)."""
    return {"classes": service.list_my_classes(instructor_id=current_user.id)}


@router.get("/quizzes")
def list_quizzes(
    section_id: str | None = Query(default=None),
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    return {"quizzes": service.list_mine(instructor_id=current_user.id, section_id=section_id)}


@router.post("/quizzes", status_code=201)
def create_quiz(
    payload: QuizCreateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.create(
            instructor_id=current_user.id,
            section_id=payload.section_id,
            title=payload.title,
            description=payload.description,
            time_limit_minutes=payload.time_limit_minutes,
            due_date=payload.due_date,
            opens_at=payload.opens_at,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/quizzes/{quiz_id}")
def get_quiz(
    quiz_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.get_for_instructor(instructor_id=current_user.id, quiz_id=quiz_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/quizzes/{quiz_id}")
def update_quiz(
    quiz_id: str,
    payload: QuizUpdateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.update(
            instructor_id=current_user.id,
            quiz_id=quiz_id,
            title=payload.title,
            description=payload.description,
            time_limit_minutes=payload.time_limit_minutes,
            due_date=payload.due_date,
            opens_at=payload.opens_at,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(
    quiz_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        service.delete(instructor_id=current_user.id, quiz_id=quiz_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/quizzes/{quiz_id}/publish")
def publish_quiz(
    quiz_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.set_published(instructor_id=current_user.id, quiz_id=quiz_id, is_published=True)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/quizzes/{quiz_id}/unpublish")
def unpublish_quiz(
    quiz_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.set_published(instructor_id=current_user.id, quiz_id=quiz_id, is_published=False)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/quizzes/{quiz_id}/questions", status_code=201)
def add_quiz_question(
    quiz_id: str,
    payload: QuizQuestionRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.add_question(
            instructor_id=current_user.id,
            quiz_id=quiz_id,
            question_text=payload.question_text,
            question_type=payload.question_type,
            correct_answer=payload.correct_answer,
            options=payload.options,
            points=payload.points,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/quizzes/{quiz_id}/questions/generate")
def generate_quiz_questions(
    quiz_id: str,
    payload: QuizGenerateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    """Sinh cau hoi bang AI tu giao trinh/slide bai giang cua mon hoc (LLM
    khi co API key that, fallback tat dinh khi khong co — xem quiz_generator.py)."""
    try:
        return service.generate_with_ai(instructor_id=current_user.id, quiz_id=quiz_id, count=payload.count)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/quizzes/{quiz_id}/questions/{question_id}")
def update_quiz_question(
    quiz_id: str,
    question_id: str,
    payload: QuizQuestionRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.update_question(
            instructor_id=current_user.id,
            quiz_id=quiz_id,
            question_id=question_id,
            question_text=payload.question_text,
            question_type=payload.question_type,
            correct_answer=payload.correct_answer,
            options=payload.options,
            points=payload.points,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/quizzes/{quiz_id}/questions/{question_id}", status_code=204)
def delete_quiz_question(
    quiz_id: str,
    question_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        service.delete_question(instructor_id=current_user.id, quiz_id=quiz_id, question_id=question_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/quizzes/{quiz_id}/questions/reorder")
def reorder_quiz_questions(
    quiz_id: str,
    payload: QuizQuestionReorderRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    try:
        return service.reorder_questions(
            instructor_id=current_user.id,
            quiz_id=quiz_id,
            question_ids=payload.question_ids,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/quizzes/{quiz_id}/progress")
def get_quiz_progress(
    quiz_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    """Theo doi chi tiet tien do lam bai cua tung sinh vien: da nop chua,
    diem, dung/sai tung cau — dung cho GV xem sau khi giao quiz."""
    try:
        return service.get_progress(instructor_id=current_user.id, quiz_id=quiz_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/quizzes/{quiz_id}/submissions/{submission_id}/grade")
def grade_quiz_submission(
    quiz_id: str,
    submission_id: str,
    payload: QuizGradeRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    service: QuizService = Depends(get_quiz_service),
):
    """Cham tay cac cau SHORT_ANSWER (MC/True-False da tu dong cham luc SV nop)."""
    try:
        return service.grade_submission(
            instructor_id=current_user.id,
            quiz_id=quiz_id,
            submission_id=submission_id,
            scores=payload.scores,
            feedback=payload.feedback,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
