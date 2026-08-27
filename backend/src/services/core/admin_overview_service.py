"""Admin Console "Overview" dashboard — school pulse, work queue, recent
critical changes. Ported from the `chung` branch's Admin Console design
(docs/branch-audit/chung-admin-backend.md section 3.8/3.9) but rewritten
against this branch's own multi-tenant schema: everything below is scoped to
the calling admin's `organization_id`, which `chung` never had to do.

Pure read/aggregate — no mutation, no audit-before-release gate (that
pattern is reserved for T2 raw-data reads on individual students/instructors,
not aggregate dashboard counts).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db import models
from src.services.core.admin_section_service import _course_belongs_to

# Whitelisted event types shown on the Overview "recent critical changes"
# feed -- kept in sync by hand with what src/api/admin*.py actually emits
# (see docs/branch-audit/chung-admin-backend.md 5.3 for the `chung`
# precedent of testing this list against real emitters).
CRITICAL_CHANGE_EVENTS: frozenset[str] = frozenset(
    {
        "UPDATE_USER_STATUS",
        "guardrail_rule_updated",
        "risk_policy_published",
        "risk_policy_rolled_back",
        "admin_settings_updated",
        "admin_course_added",
        "admin_course_hidden",
        "admin_course_restored",
        "mock_lms_sync_published",
        "mock_lms_sync_rolled_back",
        "DSAR_DELETE_COMPLETED",
        "BULK_UPDATE_RISKS",
        "GUARDRAIL_REVIEW_DECIDED",
        "SUBMIT_INTERVENTION",
        "SELF_SERVICE_DATA_DELETE",
    }
)

_WORK_QUEUE_SOURCE_LIMIT = 100
_RECENT_CHANGES_LIMIT = 10

_PRIORITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _metric(numerator: int, denominator: int, method_note: str) -> dict[str, Any]:
    """A rate plus its provenance. `value` is None (not a fabricated 0%)
    when there is nothing to divide by yet."""
    return {
        "value": (numerator / denominator) if denominator > 0 else None,
        "numerator": numerator,
        "denominator": denominator,
        "period": {"as_of": datetime.utcnow().isoformat()},
        "measured_at": datetime.utcnow().isoformat(),
        "method_note": method_note,
    }


def build_overview(db: Session, *, organization_id: str | None) -> dict[str, Any]:
    org_filter_user = models.User.organization_id == organization_id
    org_filter_course = models.Course.organization_id == organization_id

    active_students = (
        db.query(func.count(models.User.id))
        .filter(org_filter_user, models.User.role == "STUDENT", models.User.is_active.is_(True))
        .scalar()
    ) or 0
    active_instructors = (
        db.query(func.count(models.User.id))
        .filter(org_filter_user, models.User.role == "INSTRUCTOR", models.User.is_active.is_(True))
        .scalar()
    ) or 0
    courses = (
        db.query(func.count(models.Course.id)).filter(org_filter_course).scalar()
    ) or 0
    sections = (
        db.query(func.count(models.CourseSection.id))
        .join(models.Course, models.CourseSection.course_id == models.Course.id)
        .filter(org_filter_course)
        .scalar()
    ) or 0

    unresolved_risk_students = (
        db.query(func.count(func.distinct(models.RiskSignal.student_id)))
        .join(models.User, models.RiskSignal.student_id == models.User.id)
        .filter(
            org_filter_user,
            models.RiskSignal.resolved_at.is_(None),
            models.RiskSignal.risk_level == "HIGH",
        )
        .scalar()
    ) or 0

    sent_invites = (
        db.query(func.count(models.OrgInvite.id))
        .filter(models.OrgInvite.organization_id == organization_id, models.OrgInvite.revoked_at.is_(None))
        .scalar()
    ) or 0
    accepted_invites = (
        db.query(func.count(models.OrgInvite.id))
        .filter(
            models.OrgInvite.organization_id == organization_id,
            models.OrgInvite.revoked_at.is_(None),
            models.OrgInvite.used_at.isnot(None),
        )
        .scalar()
    ) or 0

    # Scoped to this organization: unfiltered, one school's broken ingest
    # turned every other school's banner to DEGRADED. `course_ingest_jobs`
    # holds a `course_code` string rather than an FK, so this joins through
    # `Course.code` -- upper-cased on both sides because
    # `admin_course_repository.start_job` stores `course_code.upper()` while
    # the real catalog has lower-case tails ("ENW493c"), same reason spelled
    # out in `conversation_repository.section_id_for`.
    failed_jobs = (
        db.query(func.count(models.CourseIngestJob.id))
        .join(
            models.Course,
            func.upper(models.Course.code) == func.upper(models.CourseIngestJob.course_code),
        )
        .filter(
            models.CourseIngestJob.status == "failed",
            models.Course.organization_id == organization_id,
        )
        .scalar()
    ) or 0

    work_queue = build_work_queue(db, organization_id=organization_id)
    by_type: dict[str, int] = {}
    for item in work_queue:
        by_type[item["trigger_type"]] = by_type.get(item["trigger_type"], 0) + 1

    recent_changes = (
        db.query(models.AuditLog)
        .filter(
            models.AuditLog.event_type.in_(CRITICAL_CHANGE_EVENTS),
            models.AuditLog.organization_id == organization_id,
        )
        .order_by(models.AuditLog.created_at.desc())
        .limit(_RECENT_CHANGES_LIMIT)
        .all()
    )

    return {
        "system_status": "DEGRADED" if failed_jobs > 0 else "HEALTHY",
        "last_updated": datetime.utcnow().isoformat(),
        "school_pulse": {
            "active_students": active_students,
            "active_instructors": active_instructors,
            "courses": courses,
            "sections": sections,
            "unresolved_risk": _metric(
                unresolved_risk_students,
                active_students,
                "distinct active students with an unresolved HIGH risk signal / active students",
            ),
            "invitation_activation": _metric(
                accepted_invites,
                sent_invites,
                "invites with used_at set / invites sent (revoked excluded)",
            ),
        },
        "work_queue": {"items": work_queue, "by_type": by_type},
        "recent_critical_changes": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "decision": event.decision,
                "actor_user_id": event.actor_user_id,
                "subject_user_id": getattr(event, "subject_user_id", None),
                "resource_type": event.resource_type,
                "resource_id": event.resource_id,
                "created_at": event.created_at.isoformat() if event.created_at else None,
            }
            for event in recent_changes
        ],
    }


def build_work_queue(db: Session, *, organization_id: str | None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    risk_rows = (
        db.query(models.RiskSignal)
        .join(models.User, models.RiskSignal.student_id == models.User.id)
        .filter(
            models.User.organization_id == organization_id,
            models.RiskSignal.resolved_at.is_(None),
            models.RiskSignal.risk_level == "HIGH",
        )
        .order_by(models.RiskSignal.generated_at.asc())
        .limit(_WORK_QUEUE_SOURCE_LIMIT)
        .all()
    )
    for row in risk_rows:
        items.append(
            {
                "trigger_type": "RISK_SIGNAL",
                "trigger_id": row.id,
                "priority": "HIGH",
                "subject_user_id": row.student_id,
                "summary": f"{row.risk_type} risk at {row.risk_level} level",
                "occurred_at": row.generated_at,
            }
        )

    # GuardrailEvent.student_id is the self-contained field record_block()
    # writes at block time (chat feature removed, no Conversation/Message to
    # join through any more -- see
    # migrations/versions/20260910_remove_chatbot_feature.py). Events written
    # with no student_id (unscoped general questions) have no subject to
    # route a work-queue item to, so they're skipped here and surfaced only
    # in the dedicated guardrail review queue (src/api/instructor.py).
    guardrail_rows = (
        db.query(models.GuardrailEvent)
        .filter(
            models.GuardrailEvent.classification == "BLOCKED",
            (models.GuardrailEvent.review_status.is_(None)) | (models.GuardrailEvent.review_status == "PENDING"),
        )
        .order_by(models.GuardrailEvent.created_at.asc())
        .limit(_WORK_QUEUE_SOURCE_LIMIT)
        .all()
    )
    for event in guardrail_rows:
        if not event.student_id:
            continue
        student = db.query(models.User).filter_by(id=event.student_id).first()
        if student is None or student.organization_id != organization_id:
            continue
        items.append(
            {
                "trigger_type": "GUARDRAIL_EVENT",
                "trigger_id": event.id,
                "priority": "HIGH",
                "subject_user_id": event.student_id,
                "summary": "Guardrail safety event blocked",
                "occurred_at": event.created_at,
            }
        )

    data_request_rows = (
        db.query(models.DataRequest)
        .filter(
            models.DataRequest.organization_id == organization_id,
            models.DataRequest.status.in_(["PENDING", "IN_PROGRESS"]),
        )
        .order_by(models.DataRequest.created_at.asc())
        .limit(_WORK_QUEUE_SOURCE_LIMIT)
        .all()
    )
    for row in data_request_rows:
        items.append(
            {
                "trigger_type": "DATA_REQUEST",
                "trigger_id": row.id,
                "priority": "MEDIUM",
                "subject_user_id": row.requester_id,
                "summary": f"{row.request_type} request is {row.status}",
                "occurred_at": row.created_at,
            }
        )

    ingest_rows = (
        db.query(models.CourseIngestJob)
        .filter(models.CourseIngestJob.status == "failed")
        .order_by(models.CourseIngestJob.created_at.asc())
        .limit(_WORK_QUEUE_SOURCE_LIMIT)
        .all()
    )
    for row in ingest_rows:
        items.append(
            {
                "trigger_type": "INGEST_JOB",
                "trigger_id": row.id,
                "priority": "MEDIUM",
                "subject_user_id": None,
                "summary": f"Ingest {row.operation} failed for {row.course_code}",
                "occurred_at": row.created_at,
            }
        )

    # Sections the student semester wizard (or an admin) left without an
    # instructor -- see src/repositories/semester_repository.py's removed
    # `first_instructor_id`: it used to guess an arbitrary instructor in the
    # org instead of leaving this to a human. Course.organization_id can be
    # NULL (shared catalogue), so this reuses admin_section_service's own
    # `_course_belongs_to` org-scoping rule rather than re-deriving it here
    # -- a second, drifted copy of that rule is exactly the kind of bug this
    # task exists to remove elsewhere.
    unassigned_rows = (
        db.query(models.CourseSection, models.Course)
        .join(models.Course, models.Course.id == models.CourseSection.course_id)
        .filter(models.CourseSection.instructor_id.is_(None))
        .order_by(models.Course.code)
        .all()
    )
    unassigned_sections = [
        (section, course)
        for section, course in unassigned_rows
        if _course_belongs_to(course, organization_id)
    ][:_WORK_QUEUE_SOURCE_LIMIT]
    for section, course in unassigned_sections:
        items.append(
            {
                "trigger_type": "UNASSIGNED_SECTION",
                "trigger_id": section.id,
                "priority": "MEDIUM",
                "subject_user_id": None,
                # English, structured summary -- like the other four sources
                # (DATA_REQUEST/INGEST_JOB above), this is a data carrier the
                # frontend regex-matches and re-localizes
                # (adminDisplay.js::adminWorkQueueSummary), not text shown as-is.
                "summary": f"Section {course.code}/{section.section_code or section.id} has no instructor assigned",
                "occurred_at": None,
            }
        )

    now = datetime.utcnow()

    def _age_seconds(occurred_at: datetime | None) -> int:
        if occurred_at is None:
            return 0
        return max(0, int((now - occurred_at).total_seconds()))

    for item in items:
        item["age_seconds"] = _age_seconds(item.pop("occurred_at", None))

    items.sort(key=lambda item: (_PRIORITY_RANK.get(item["priority"], 9), -item["age_seconds"]))
    return items
