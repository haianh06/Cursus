"""Admin Data Requests — DSAR (Data Subject Access Request) management.
Spec: docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.5 và 4.2.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles

router = APIRouter(
    prefix="/admin/data-requests",
    tags=["admin-data-requests"],
    dependencies=[Depends(require_roles(models.UserRole.ADMIN))],
)


class DataRequestStatusUpdate(BaseModel):
    notes: str = Field(..., min_length=10, description="Lý do cập nhật (bắt buộc, >=10 ký tự)")


class DeleteConfirmRequest(DataRequestStatusUpdate):
    preview_hash: str = Field(..., description="Mã băm tập dữ liệu đã xem trước")


def _get_request(db: Session, request_id: str, organization_id: str | None) -> models.DataRequest:
    req = db.get(models.DataRequest, request_id)
    # Fail-closed: a NULL org (legacy row, not yet backfilled) or a mismatch
    # is treated the same as "not found" -- never leak another org's DSAR
    # request through a guessed/enumerated request_id.
    if not req or not organization_id or req.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="request_not_found")
    return req


@router.get("")
async def list_data_requests(
    skip: int = 0,
    limit: int = 50,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """List data requests -- scoped to the caller's organization (fail-closed:
    a legacy row with no organization_id is excluded, not shown to everyone)."""
    query = (
        db.query(models.DataRequest)
        .filter(models.DataRequest.organization_id == current_user.organization_id)
        .order_by(desc(models.DataRequest.created_at))
    )
    total = query.count()
    requests = query.offset(skip).limit(limit).all()

    items = []
    for req in requests:
        requester = db.get(models.User, req.requester_id)
        processor = db.get(models.User, req.processed_by) if req.processed_by else None
        items.append({
            "id": req.id,
            "requesterId": req.requester_id,
            "requesterEmail": requester.email if requester else "Unknown",
            "requestType": req.request_type,
            "status": req.status,
            "adminNotes": req.admin_notes,
            "previewSummary": req.preview_summary,
            "resultSummary": req.result_summary,
            "createdAt": req.created_at.isoformat(),
            "updatedAt": req.updated_at.isoformat(),
            "processedBy": processor.email if processor else None,
        })
    return {"items": items, "total": total}


@router.post("/{request_id}/process")
async def process_data_request(
    request_id: str,
    payload: DataRequestStatusUpdate,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Change status from PENDING to IN_PROGRESS."""
    req = _get_request(db, request_id, current_user.organization_id)
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail="Chỉ có thể xử lý yêu cầu đang chờ (PENDING)")

    req.status = "IN_PROGRESS"
    req.admin_notes = payload.notes
    req.processed_by = current_user.id
    req.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}


@router.post("/{request_id}/reject")
async def reject_data_request(
    request_id: str,
    payload: DataRequestStatusUpdate,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Reject a data request."""
    req = _get_request(db, request_id, current_user.organization_id)
    if req.status not in ["PENDING", "IN_PROGRESS"]:
        raise HTTPException(status_code=400, detail="Không thể từ chối yêu cầu đã đóng")

    req.status = "REJECTED"
    req.admin_notes = payload.notes
    req.processed_by = current_user.id
    req.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}


@router.post("/{request_id}/complete")
async def complete_data_request(
    request_id: str,
    payload: DataRequestStatusUpdate,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Complete a non-DELETE data request."""
    req = _get_request(db, request_id, current_user.organization_id)
    if req.status != "IN_PROGRESS":
        raise HTTPException(status_code=400, detail="Chỉ có thể hoàn tất yêu cầu đang xử lý")
    if req.request_type == "DELETE":
        raise HTTPException(status_code=400, detail="Yêu cầu xoá phải thông qua luồng xem trước")

    req.status = "COMPLETED"
    req.admin_notes = payload.notes
    req.processed_by = current_user.id
    req.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}


def _generate_delete_preview(db: Session, requester_id: str) -> dict:
    """Helper to count records to delete and generate stable hash.

    Every model below is a direct student-owned table (own `student_id` FK);
    each one's own children (daily_plans/schedule_blocks/study_tasks under
    weekly_plans, reminder_deliveries under reminders) cascade at the DB
    level via `ondelete="CASCADE"` on their own FK, so they don't need a
    separate count/delete line here — only tables missing from this list
    would be left behind as an incomplete erasure."""
    counts = {
        "enrollments": db.query(models.Enrollment).filter_by(student_id=requester_id).count(),
        "submissions": db.query(models.Submission).filter_by(student_id=requester_id).count(),
        "plans": db.query(models.WeeklyPlan).filter_by(student_id=requester_id).count(),
        "reflections": db.query(models.WeeklyReflection).filter_by(student_id=requester_id).count(),
        "risk_signals": db.query(models.RiskSignal).filter_by(student_id=requester_id).count(),
        "assignment_overrides": db.query(models.AssignmentOverride).filter_by(student_id=requester_id).count(),
        "learning_goals": db.query(models.LearningGoal).filter_by(student_id=requester_id).count(),
        "self_study_sessions": db.query(models.SelfStudySession).filter_by(student_id=requester_id).count(),
        "replan_proposals": db.query(models.ReplanProposal).filter_by(student_id=requester_id).count(),
        "progress_events": db.query(models.ProgressEvent).filter_by(student_id=requester_id).count(),
        "reminders": db.query(models.Reminder).filter_by(student_id=requester_id).count(),
        "resource_access_events": db.query(models.ResourceAccessEvent).filter_by(student_id=requester_id).count(),
        "semester_setups": db.query(models.SemesterSetup).filter_by(student_id=requester_id).count(),
        "exam_session_registrations": db.query(models.CourseExamSessionStudent).filter_by(student_id=requester_id).count(),
        "instructor_notes_about_student": db.query(models.InstructorStudentNote).filter_by(student_id=requester_id).count(),
    }

    # Stable hash based on counts + student id (in reality, would hash IDs of records)
    hash_input = f"{requester_id}:{json.dumps(counts, sort_keys=True)}"
    preview_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    return {"counts": counts, "hash": preview_hash}


@router.post("/{request_id}/delete-preview")
async def preview_delete_data_request(
    request_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Preview records to be deleted and generate a hash."""
    req = _get_request(db, request_id, current_user.organization_id)
    if req.status != "IN_PROGRESS" or req.request_type != "DELETE":
        raise HTTPException(status_code=400, detail="Chỉ áp dụng cho yêu cầu xoá đang xử lý")

    preview = _generate_delete_preview(db, req.requester_id)

    req.preview_summary = preview["counts"]
    req.preview_hash = preview["hash"]
    req.updated_at = datetime.utcnow()
    db.commit()

    return {"success": True, "preview": preview["counts"], "hash": preview["hash"]}


@router.post("/{request_id}/delete-confirm")
async def confirm_delete_data_request(
    request_id: str,
    payload: DeleteConfirmRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Confirm and execute delete if hash matches current state."""
    req = _get_request(db, request_id, current_user.organization_id)
    if req.status != "IN_PROGRESS" or req.request_type != "DELETE":
        raise HTTPException(status_code=400, detail="Chỉ áp dụng cho yêu cầu xoá đang xử lý")

    if not req.preview_hash:
        raise HTTPException(status_code=400, detail="Phải chạy xem trước (preview) trước khi xác nhận")

    if payload.preview_hash != req.preview_hash:
        raise HTTPException(status_code=400, detail="Mã băm không khớp. Vui lòng thử lại quá trình xem trước.")

    # Re-calculate to ensure data hasn't changed
    current_preview = _generate_delete_preview(db, req.requester_id)
    if current_preview["hash"] != req.preview_hash:
        raise HTTPException(status_code=409, detail="Dữ liệu đã thay đổi kể từ lúc xem trước. Yêu cầu xem trước lại.")

    # Perform deletion. ReplanProposal.original_plan_id -> weekly_plans.id has
    # no ondelete=CASCADE (plain FK), so it must be deleted before WeeklyPlan
    # or the bulk delete below raises a FK violation; every other table here
    # is either childless or already ondelete=CASCADE/SET NULL, so order
    # doesn't matter for them.
    db.query(models.ReplanProposal).filter_by(student_id=req.requester_id).delete()
    db.query(models.Enrollment).filter_by(student_id=req.requester_id).delete()
    db.query(models.Submission).filter_by(student_id=req.requester_id).delete()
    db.query(models.WeeklyPlan).filter_by(student_id=req.requester_id).delete()
    db.query(models.WeeklyReflection).filter_by(student_id=req.requester_id).delete()
    db.query(models.RiskSignal).filter_by(student_id=req.requester_id).delete()
    db.query(models.AssignmentOverride).filter_by(student_id=req.requester_id).delete()
    db.query(models.LearningGoal).filter_by(student_id=req.requester_id).delete()
    db.query(models.SelfStudySession).filter_by(student_id=req.requester_id).delete()
    db.query(models.ProgressEvent).filter_by(student_id=req.requester_id).delete()
    db.query(models.Reminder).filter_by(student_id=req.requester_id).delete()
    db.query(models.ResourceAccessEvent).filter_by(student_id=req.requester_id).delete()
    db.query(models.SemesterSetup).filter_by(student_id=req.requester_id).delete()
    db.query(models.CourseExamSessionStudent).filter_by(student_id=req.requester_id).delete()
    db.query(models.InstructorStudentNote).filter_by(student_id=req.requester_id).delete()

    req.status = "COMPLETED"
    req.admin_notes = payload.notes
    req.result_summary = current_preview["counts"]
    req.processed_by = current_user.id
    req.updated_at = datetime.utcnow()

    # Audit log (important for deletes)
    audit_event = models.AuditLog(
        id=f"audit_{uuid.uuid4().hex}",
        actor_user_id=current_user.id,
        organization_id=current_user.organization_id,
        event_type="DSAR_DELETE_COMPLETED",
        resource_type="USER",
        resource_id=req.requester_id,
        decision="ALLOW",
        metadata_info={"counts": current_preview["counts"], "request_id": req.id}
    )
    db.add(audit_event)
    db.commit()

    return {"success": True, "deleted": current_preview["counts"]}
