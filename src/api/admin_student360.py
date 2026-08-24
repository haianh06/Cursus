"""Admin Student 360 — audited raw-data reads for one student (spec: docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.3).

Fail-closed audit model: every raw-data route here runs the loader, then
writes an audit event and commits it BEFORE the caller ever sees a row of
real data. If the audit write fails, the transaction rolls back and the
route 503s -- the data is never released. This intentionally mirrors the
existing risk/guardrail "preview vs publish" discipline already used
elsewhere in this codebase (mục 14.1), applied here to *reads* instead of
writes: an unaudited read of a real student's data is not an option.

Every raw-read route below additionally requires Permission.READ_SENSITIVE
on its specific Resource (src/security/permissions.py), on top of the
router-level `require_roles(ADMIN)` gate -- the two are independent
layers: the permission check is a declarative statement of what each route
needs, the audit-then-release wrapper is what actually enforces fail-closed
behavior regardless of how the permission check evolves. Assignments are
the one exception (plain READ): they're course material, not the student's
own private data (see that route's own comment).

"Sessions" (self-study sessions) tab from the source spec is NOT included
-- this branch has no `self_study_sessions` table (that table only exists
on chung's own, incompatible migration chain, see
docs/AUDIT_NHANH_CHUNG_ADMIN_23AUG.md). Fabricating a new table for it in
this pass would be exactly the kind of unreviewed schema change the
standing project rules ask to avoid this close to a deadline.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.audit_repository import AuditRepository
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.core.audit_service import AuditService

router = APIRouter(
    prefix="/admin/students",
    tags=["admin-student-360"],
    dependencies=[Depends(require_roles(models.UserRole.ADMIN))],
)

SENSITIVE_READ_EVENT = "ADMIN_SENSITIVE_READ"


class SensitiveAuditUnavailableError(Exception):
    """Raised when the audit event for a raw read could not be committed.
    The caller must not receive any of the data that was loaded."""


def _require_student(db: Session, current_user: models.User, student_id: str) -> models.User:
    student = db.get(models.User, student_id)
    if (
        not student
        or student.role != models.UserRole.STUDENT.value
        or student.organization_id != current_user.organization_id
    ):
        # Same 404 whether the id doesn't exist, belongs to a non-student, or
        # belongs to another organization -- never disclose which case it was.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="student_not_found")
    return student


def _collection_resource_id(resource: str, student_id: str) -> str:
    return f"collection:{resource}:{student_id}"


async def _audited_read(
    db: Session,
    *,
    actor_id: str,
    resource_type: str,
    resource_id: str,
    items: list,
    extra_metadata: dict | None = None,
):
    """Runs the fail-closed audit-then-release pattern around already-loaded
    `items`. Returns `items` only after the audit commit succeeds."""
    try:
        await AuditService(AuditRepository(db)).log_event(
            event_type=SENSITIVE_READ_EVENT,
            decision="ALLOW",
            actor_user_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            metadata={"resourceCount": len(items), **(extra_metadata or {})},
            commit=False,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 -- any failure here must fail closed
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="sensitive_audit_unavailable",
        ) from exc
    return items


def _paginate(query, page: int, page_size: int):
    return query.offset((page - 1) * page_size).limit(page_size)


PageQuery = Query(default=1, ge=1)
PageSizeQuery = Query(default=25, ge=1, le=100)


@router.get("/{student_id}/summary")
async def get_student_summary(
    student_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Aggregate counts only -- NOT a raw-read route (no audit event), same
    as the spec's distinction between the summary tab and the 8 raw tabs."""
    student = _require_student(db, current_user, student_id)

    total_tasks = db.scalar(
        select(func.count(models.StudyTask.id))
        .join(models.ScheduleBlock, models.ScheduleBlock.id == models.StudyTask.schedule_block_id)
        .join(models.DailyPlan, models.DailyPlan.id == models.ScheduleBlock.daily_plan_id)
        .join(models.WeeklyPlan, models.WeeklyPlan.id == models.DailyPlan.weekly_plan_id)
        .where(models.WeeklyPlan.student_id == student_id)
    ) or 0
    completed_tasks = db.scalar(
        select(func.count(models.StudyTask.id))
        .join(models.ScheduleBlock, models.ScheduleBlock.id == models.StudyTask.schedule_block_id)
        .join(models.DailyPlan, models.DailyPlan.id == models.ScheduleBlock.daily_plan_id)
        .join(models.WeeklyPlan, models.WeeklyPlan.id == models.DailyPlan.weekly_plan_id)
        .where(models.WeeklyPlan.student_id == student_id, models.StudyTask.status == "COMPLETED")
    ) or 0
    open_risk = db.scalar(
        select(func.count(models.RiskSignal.id)).where(
            models.RiskSignal.student_id == student_id,
            models.RiskSignal.resolved_at.is_(None),
        )
    ) or 0
    enrollments = (
        db.query(models.Enrollment, models.CourseSection)
        .join(models.CourseSection, models.CourseSection.id == models.Enrollment.section_id)
        .filter(models.Enrollment.student_id == student_id)
        .all()
    )

    return {
        "student": {
            "id": student.id,
            "fullName": student.full_name,
            "email": student.email,
            "role": student.role.value if hasattr(student.role, "value") else str(student.role),
            "isActive": student.is_active,
        },
        "activity": {"totalTasks": total_tasks, "completedTasks": completed_tasks},
        "riskSummary": {"openSignals": open_risk},
        "enrollments": [
            {"sectionCode": section.section_code, "status": enrollment.status}
            for enrollment, section in enrollments
        ],
    }


@router.get(
    "/{student_id}/plans",
    dependencies=[Depends(require_permission(Resource.PLAN, Permission.READ_SENSITIVE))],
)
async def get_student_plans(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.WeeklyPlan).filter_by(student_id=student_id).order_by(models.WeeklyPlan.week_number.desc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": p.id,
            "weekNumber": p.week_number,
            "studyHoursAllocated": p.study_hours_allocated,
            "goals": p.goals,
        }
        for p in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="PLAN",
        resource_id=_collection_resource_id("plans", student_id), items=items,
    )}


@router.get(
    "/{student_id}/tasks",
    dependencies=[Depends(require_permission(Resource.PLAN, Permission.READ_SENSITIVE))],
)
async def get_student_tasks(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.StudyTask)
        .join(models.ScheduleBlock, models.ScheduleBlock.id == models.StudyTask.schedule_block_id)
        .join(models.DailyPlan, models.DailyPlan.id == models.ScheduleBlock.daily_plan_id)
        .join(models.WeeklyPlan, models.WeeklyPlan.id == models.DailyPlan.weekly_plan_id)
        .filter(models.WeeklyPlan.student_id == student_id)
        .order_by(models.ScheduleBlock.start_time.desc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": t.id,
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "plannedMinutes": t.planned_minutes,
            "actualMinutes": t.actual_minutes,
        }
        for t in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="PLAN",
        resource_id=_collection_resource_id("tasks", student_id), items=items,
    )}


@router.get(
    "/{student_id}/progress-events",
    dependencies=[Depends(require_permission(Resource.PLAN, Permission.READ_SENSITIVE))],
)
async def get_student_progress_events(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.ProgressEvent).filter_by(student_id=student_id).order_by(models.ProgressEvent.occurred_at.desc()),
        page,
        page_size,
    ).all()
    items = [
        {"id": e.id, "eventType": e.event_type, "occurredAt": e.occurred_at.isoformat(), "taskId": e.task_id}
        for e in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="PLAN",
        resource_id=_collection_resource_id("progress-events", student_id), items=items,
    )}


@router.get(
    "/{student_id}/reminders",
    dependencies=[Depends(require_permission(Resource.PLAN, Permission.READ_SENSITIVE))],
)
async def get_student_reminders(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.Reminder).filter_by(student_id=student_id).order_by(models.Reminder.scheduled_time.desc()),
        page,
        page_size,
    ).all()
    items = [
        {"id": r.id, "title": r.title, "message": r.message, "channel": r.channel, "scheduledTime": r.scheduled_time.isoformat()}
        for r in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="PLAN",
        resource_id=_collection_resource_id("reminders", student_id), items=items,
    )}


@router.get(
    "/{student_id}/assignments",
    dependencies=[Depends(require_permission(Resource.ASSIGNMENT, Permission.READ))],
)
async def get_student_assignments(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    # Assignment definitions are course material, not the student's own
    # private data -- reads here still go through the same audit trail for
    # a consistent tab experience, but this is the one resource where a
    # future finer-grained permission split would use plain READ rather
    # than READ_SENSITIVE (see file docstring re: scope of this pass).
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.Assignment)
        .join(models.Enrollment, models.Enrollment.section_id == models.Assignment.section_id)
        .filter(models.Enrollment.student_id == student_id)
        .order_by(models.Assignment.due_date.desc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": a.id,
            "title": a.title,
            "dueDate": a.due_date.isoformat(),
            "maxPoints": a.max_points,
            "assessmentType": a.assessment_type,
        }
        for a in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="ASSIGNMENT",
        resource_id=_collection_resource_id("assignments", student_id), items=items,
    )}


@router.get(
    "/{student_id}/submissions",
    dependencies=[Depends(require_permission(Resource.SUBMISSION, Permission.READ_SENSITIVE))],
)
async def get_student_submissions(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.Submission).filter_by(student_id=student_id).order_by(models.Submission.submitted_at.desc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": s.id,
            "assignmentId": s.assignment_id,
            "submittedAt": s.submitted_at.isoformat(),
            "gradingStatus": s.grading_status,
            "grade": s.grade,
            "isLate": s.is_late,
        }
        for s in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="SUBMISSION",
        resource_id=_collection_resource_id("submissions", student_id), items=items,
    )}


@router.get(
    "/{student_id}/reflections",
    dependencies=[Depends(require_permission(Resource.REFLECTION, Permission.READ_SENSITIVE))],
)
async def get_student_reflections(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.WeeklyReflection).filter_by(student_id=student_id).order_by(models.WeeklyReflection.week_number.desc()),
        page,
        page_size,
    ).all()
    items = [
        {"id": r.id, "weekNumber": r.week_number, "content": r.content, "generatedAt": r.generated_at.isoformat()}
        for r in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="REFLECTION",
        resource_id=_collection_resource_id("reflections", student_id), items=items,
    )}


@router.get(
    "/{student_id}/conversations",
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.READ_SENSITIVE))],
)
async def get_student_conversations(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.Conversation).filter_by(student_id=student_id).order_by(models.Conversation.created_at.desc()),
        page,
        page_size,
    ).all()
    items = [
        {"id": c.id, "title": c.title, "subjectCode": c.subject_code, "createdAt": c.created_at.isoformat()}
        for c in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="CHAT",
        resource_id=_collection_resource_id("conversations", student_id), items=items,
    )}


@router.get(
    "/{student_id}/conversations/{conversation_id}",
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.READ_SENSITIVE))],
)
async def get_student_conversation_detail(
    student_id: str,
    conversation_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    conversation = db.get(models.Conversation, conversation_id)
    if not conversation or conversation.student_id != student_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation_not_found")
    rows = _paginate(
        db.query(models.Message).filter_by(conversation_id=conversation_id).order_by(models.Message.created_at.asc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": m.id,
            "sender": m.sender,
            "content": m.content,
            "createdAt": m.created_at.isoformat(),
        }
        for m in rows
    ]
    # Detail read: resource_id names the exact conversation, not a
    # collection id -- an investigation should see exactly which
    # conversation was opened, not just "some conversations tab was viewed."
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="CHAT",
        resource_id=conversation_id, items=items,
    )}


@router.get(
    "/{student_id}/documents",
    dependencies=[Depends(require_permission(Resource.STUDENT_DOCUMENT, Permission.READ_SENSITIVE))],
)
async def get_student_documents(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    # `documents` here has no student_id column and no doc_type value marks
    # a student upload -- student-uploaded files are tagged purely inside
    # metadata_info (source=student_upload, uploaded_by=<id>), see
    # src/services/rag/document_ingest_service.py. Filtering in Python since
    # JSON-field predicates aren't portable across SQLite/Postgres.
    candidates = db.query(models.Document).all()
    matching = [
        d for d in candidates
        if (d.metadata_info or {}).get("source") == "student_upload"
        and (d.metadata_info or {}).get("uploaded_by") == student_id
    ]
    start = (page - 1) * page_size
    page_items = matching[start:start + page_size]
    items = [{"id": d.id, "title": d.title, "version": d.version} for d in page_items]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="STUDENT_DOCUMENT",
        resource_id=_collection_resource_id("documents", student_id), items=items,
    )}


@router.get(
    "/{student_id}/risk",
    dependencies=[Depends(require_permission(Resource.RISK_CASE, Permission.READ_SENSITIVE))],
)
async def get_student_risk(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.RiskSignal).filter_by(student_id=student_id).order_by(models.RiskSignal.generated_at.desc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": r.id,
            "riskType": r.risk_type,
            "riskLevel": r.risk_level,
            "generatedAt": r.generated_at.isoformat(),
            "resolvedAt": r.resolved_at.isoformat() if r.resolved_at else None,
            "recommendedAction": r.recommended_action,
        }
        for r in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="RISK_CASE",
        resource_id=_collection_resource_id("risk", student_id), items=items,
    )}


@router.get(
    "/{student_id}/interventions",
    dependencies=[Depends(require_permission(Resource.INTERVENTION, Permission.READ_SENSITIVE))],
)
async def get_student_interventions(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.InstructorIntervention)
        .join(models.RiskSignal, models.RiskSignal.id == models.InstructorIntervention.risk_signal_id)
        .filter(models.RiskSignal.student_id == student_id)
        .order_by(models.InstructorIntervention.created_at.desc()),
        page,
        page_size,
    ).all()
    items = [
        {"id": i.id, "actionTaken": i.action_taken, "status": i.status, "createdAt": i.created_at.isoformat()}
        for i in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="INTERVENTION",
        resource_id=_collection_resource_id("interventions", student_id), items=items,
    )}


@router.get("/{student_id}/access-history")
async def get_student_access_history(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Who has read this student's raw data, and when -- metadata only, no
    content. This route itself is NOT audited as a sensitive read (reading
    *who read what* is not the same as reading the underlying data)."""
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.AuditLog)
        .filter(models.AuditLog.event_type == SENSITIVE_READ_EVENT, models.AuditLog.resource_id.like(f"%{student_id}%"))
        .order_by(models.AuditLog.created_at.desc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": a.id,
            "actorUserId": a.actor_user_id,
            "resourceType": a.resource_type,
            "resourceId": a.resource_id,
            "createdAt": a.created_at.isoformat(),
        }
        for a in rows
    ]
    return {"success": True, "data": items}
