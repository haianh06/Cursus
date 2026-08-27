import hashlib
from datetime import date, datetime
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.api.auth import (
    get_current_user_from_token,
    get_org_invite_service,
    get_password_reset_service,
)
from src.db import models
from src.db.connection import get_db
from src.db.models import GuardrailRule, OrgInvite, User, UserRole
from src.repositories.academic_term_repository import AcademicTermRepository
from src.repositories.access_request_repository import AccessRequestRepository
from src.repositories.admin_course_repository import AdminCourseRepository
from src.repositories.audit_repository import AuditRepository
from src.repositories.guardrail_rule_repository import (
    CoreGuardrailLockedError,
    GuardrailRuleRepository,
)
from src.schemas.admin_schemas import (
    AcademicTermOut,
    AcademicTermUpsertRequest,
    AccessRequestResponse,
    AdminAnalyticsResponse,
    AdminAnalyticsSummaryResponse,
    AdminCourseCreateRequest,
    AdminCoursesResponse,
    AdminDocumentContentResponse,
    AdminDocumentMutationResponse,
    AdminDocumentsResponse,
    AdminDocumentVersionsResponse,
    AdminGuardrailHistoryResponse,
    AdminGuardrailRestoreRequest,
    AdminGuardrailRollbackRequest,
    AdminGuardrailRollbackResponse,
    AdminGuardrailRulePreviewRequest,
    AdminGuardrailRulePreviewResponse,
    AdminGuardrailRulesResponse,
    AdminGuardrailRuleUpdateRequest,
    AdminGuardrailRuleUpdateResponse,
    AdminIngestJobResponse,
    AdminKpiResponse,
    AdminUserOut,
    ClassActivityOut,
    ClassActivityRequest,
    CourseExamOut,
    CourseExamUpsertRequest,
    CreateInviteRequest,
    CurriculumDetailResponse,
    InviteResponse,
    UpdateUserStatusRequest,
)
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.academic.academic_term_service import AcademicTermService
from src.services.auth.org_invite_service import (
    InviteNotFoundError,
    OrgInviteError,
    OrgInviteService,
)
from src.services.auth.password_reset_service import PasswordResetService
from src.services.core.admin_ingest_runner import run_admin_ingest_job
from src.services.core.admin_read_service import AdminDataUnavailable, AdminReadService
from src.services.core.audit_service import AuditService
from src.services.core.guardrail_rules import RULE_GROUPS
from src.services.mock.demo_data import load_curriculum
from src.services.mock.real_curriculum_service import get_curriculum_detail
from src.services.rag.admin_document_ingest_service import (
    MAX_CHUNKS,
    MAX_UPLOAD_BYTES,
    AdminDocumentIngestService,
    _unlink_file,
    validate_admin_document,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


def get_admin_read_service(db: Session = Depends(get_db)) -> AdminReadService:
    return AdminReadService(db)


def get_guardrail_rule_repository(
    db: Session = Depends(get_db),
) -> GuardrailRuleRepository:
    return GuardrailRuleRepository(db)


_GROUP_BY_CODE = {group.code: group for group in RULE_GROUPS}


def _serialize_guardrail_rule(rule: GuardrailRule) -> dict:
    group = _GROUP_BY_CODE[rule.code]
    return {
        "code": rule.code,
        "name": group.name_vi,
        "description": group.description_vi,
        "enabled": rule.enabled,
        "core_locked": rule.core_locked,
        "current_version": rule.current_version,
        "pattern_count": len(group.patterns),
        "updated_at": rule.updated_at.isoformat(),
        "updated_by": rule.updated_by,
    }


def _rules_payload(rules: list[GuardrailRule]) -> dict:
    serialized = [_serialize_guardrail_rule(rule) for rule in rules]
    return {
        "rules": serialized,
        "any_disabled": any(not rule["enabled"] for rule in serialized),
    }


def _catalog_subjects() -> dict[str, dict]:
    payload = load_curriculum()
    subjects = payload.get("subjects") if isinstance(payload, dict) else None
    if not isinstance(subjects, list):
        raise HTTPException(status_code=503, detail="Curriculum catalog is unavailable")
    return {
        str(subject.get("Subject Code") or "").strip().upper(): subject
        for subject in subjects
        if isinstance(subject, dict) and str(subject.get("Subject Code") or "").strip()
    }


def _course_repository(db: Session) -> AdminCourseRepository:
    return AdminCourseRepository(db, catalog_codes=set(_catalog_subjects()))


def _demo_organization_id(db: Session) -> str | None:
    """Single-org demo scope: any already-seeded user/organization is right."""
    user = (
        db.query(models.User)
        .filter(models.User.organization_id.isnot(None))
        .order_by(models.User.created_at.asc())
        .first()
    )
    if user:
        return user.organization_id
    from src.db.models import Organization

    org = db.query(Organization).first()
    return org.id if org else None


def _ensure_visible_course(db: Session, code: str) -> models.Course:
    normalized = code.strip().upper()
    visible_codes = {
        item["subject_code"]
        for item in AdminReadService(db).list_courses()["courses"]
    }
    if normalized not in visible_codes:
        raise HTTPException(status_code=404, detail=f"Course not found: {normalized}")
    # Case-insensitive: real catalog codes can have a lowercase suffix (e.g.
    # "ENW493c") while `normalized` is always uppercase — an exact filter_by
    # would silently miss the existing row and fall through to creating a
    # SECOND, differently-cased duplicate Course below (found via
    # tests/test_services/test_real_curriculum_retrieval.py).
    course = (
        db.query(models.Course).filter(func.upper(models.Course.code) == normalized).first()
    )
    if course is None:
        subject = _catalog_subjects()[normalized]
        course = models.Course(
            id=normalized,
            code=normalized,
            name=str(subject.get("Subject Name") or normalized).strip(),
            description="",
            organization_id=_demo_organization_id(db),
        )
        db.add(course)
        db.flush()
    return course


async def _audit_admin_mutation(
    db: Session,
    *,
    event_type: str,
    actor_user_id: str,
    resource_type: str,
    resource_id: str,
    metadata: dict,
) -> None:
    await AuditService(AuditRepository(db)).log_event(
        event_type=event_type,
        decision="ALLOW",
        actor_user_id=actor_user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        commit=False,
    )


@router.get(
    "/courses",
    response_model=AdminCoursesResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.READ))],
)
def get_admin_courses(
    service: AdminReadService = Depends(get_admin_read_service),
    db: Session = Depends(get_db),
):
    try:
        stale_count = service.fail_stale_ingest_jobs()
        data = service.list_courses()
        if stale_count:
            db.commit()
        return {"success": True, "data": data}
    except AdminDataUnavailable as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="Admin data is temporarily unavailable") from exc


@router.get(
    "/courses/{code}/curriculum",
    response_model=CurriculumDetailResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.READ))],
)
def get_course_curriculum_detail(code: str):
    """CLO list + session-by-session breakdown + syllabus metadata, read
    straight from the course's parsed `chunks_<CODE>.json` (not the DB --
    see `real_curriculum_service.get_curriculum_detail` docstring). 404 for
    a course with no parsed syllabus file (e.g. one added manually through
    the "add course" form) rather than a misleading empty 200.

    Deliberately NOT `.upper()`-ed: 7 of the 44 real catalog codes have a
    significant lowercase suffix (e.g. `ENW493c`, `SWE202c`) matching their
    exact `chunks_<CODE>.json` filename -- uppercasing would 404 all of
    them. The frontend always passes the course's own `subject_code`
    string verbatim, so this only needs to strip incidental whitespace.
    """
    detail = get_curriculum_detail(code.strip())
    if detail is None:
        raise HTTPException(
            status_code=404,
            detail=f"No parsed curriculum data for {code} (course may have been added manually, without a real syllabus)",
        )
    return {"success": True, "data": detail}


@router.get(
    "/kpi",
    response_model=AdminKpiResponse,
    dependencies=[Depends(require_permission(Resource.KPI, Permission.READ))],
)
def get_admin_kpi(service: AdminReadService = Depends(get_admin_read_service)):
    try:
        return {"success": True, "data": service.get_kpi()}
    except AdminDataUnavailable as exc:
        raise HTTPException(status_code=503, detail="Admin data is temporarily unavailable") from exc


@router.get(
    "/analytics/summary",
    response_model=AdminAnalyticsSummaryResponse,
    dependencies=[Depends(require_permission(Resource.KPI, Permission.READ))],
)
def get_admin_analytics_summary(
    current_user: User = Depends(get_current_user_from_token),
    service: AdminReadService = Depends(get_admin_read_service),
):
    try:
        return {
            "success": True,
            "data": service.get_analytics_summary(
                organization_id=current_user.organization_id,
            ),
        }
    except AdminDataUnavailable as exc:
        raise HTTPException(status_code=503, detail="Admin data is temporarily unavailable") from exc


@router.get(
    "/analytics",
    response_model=AdminAnalyticsResponse,
    dependencies=[Depends(require_permission(Resource.KPI, Permission.READ))],
)
def get_admin_analytics(
    current_user: User = Depends(get_current_user_from_token),
    service: AdminReadService = Depends(get_admin_read_service),
):
    return {"success": True, "data": service.get_analytics(organization_id=current_user.organization_id)}


@router.get(
    "/guardrail-rules",
    response_model=AdminGuardrailRulesResponse,
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.READ))],
)
def get_guardrail_rules(
    repository: GuardrailRuleRepository = Depends(get_guardrail_rule_repository),
):
    return {"success": True, "data": _rules_payload(repository.list_rules())}


@router.get(
    "/guardrail-rules/history",
    response_model=AdminGuardrailHistoryResponse,
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.READ))],
)
def get_guardrail_rules_history(
    repository: GuardrailRuleRepository = Depends(get_guardrail_rule_repository),
):
    repository.ensure_seeded()
    versions = [
        {
            "version": version.version,
            "rules_snapshot": version.rules_snapshot,
            "source_version": version.source_version,
            "change_reason": version.change_reason,
            "rolled_back_from": (
                version.change_reason[len("Rollback to ") :].split(":", 1)[0]
                if (version.change_reason or "").startswith("Rollback to ")
                else None
            ),
            "is_active": version.is_active,
            "created_by": version.created_by,
            "created_at": version.created_at.isoformat(),
        }
        for version in repository.list_policy_history()
    ]
    return {"success": True, "data": {"versions": versions}}


@router.post(
    "/guardrail-rules/{code}/preview",
    response_model=AdminGuardrailRulePreviewResponse,
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.MANAGE))],
)
def preview_guardrail_rule(
    code: str,
    payload: AdminGuardrailRulePreviewRequest,
    repository: GuardrailRuleRepository = Depends(get_guardrail_rule_repository),
):
    try:
        return {"success": True, "data": repository.preview_set_enabled(
            code,
            enabled=payload.enabled,
            reason=payload.reason,
        )}
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown guardrail rule: {code}") from exc
    except CoreGuardrailLockedError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Guardrail rule {exc.code} is core-locked and cannot be disabled",
        ) from exc


@router.patch(
    "/guardrail-rules/{code}",
    response_model=AdminGuardrailRuleUpdateResponse,
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.MANAGE))],
)
async def update_guardrail_rule(
    code: str,
    payload: AdminGuardrailRuleUpdateRequest,
    current_user: User = Depends(get_current_user_from_token),
    repository: GuardrailRuleRepository = Depends(get_guardrail_rule_repository),
    db: Session = Depends(get_db),
):
    try:
        rule = repository.set_enabled(
            code, enabled=payload.enabled, actor_user_id=current_user.id, reason=payload.reason
        )
        await AuditService(AuditRepository(db)).log_event(
            event_type="guardrail_rule_updated",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="GUARDRAIL_RULE",
            resource_id=code,
            metadata={"enabled": payload.enabled, "reason": payload.reason},
            commit=False,
        )
        rules = repository.list_rules()
        db.commit()
        db.refresh(rule)
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=f"Unknown guardrail rule: {code}") from exc
    except CoreGuardrailLockedError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Guardrail rule {code} is core-locked and cannot be disabled",
        ) from exc
    except Exception:
        db.rollback()
        raise

    return {
        "success": True,
        "data": {
            "rule": _serialize_guardrail_rule(rule),
            "any_disabled": any(not item.enabled for item in rules),
        },
    }


@router.post(
    "/guardrail-rules/restore-defaults",
    response_model=AdminGuardrailRulesResponse,
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.MANAGE))],
)
async def restore_guardrail_defaults(
    payload: AdminGuardrailRestoreRequest,
    current_user: User = Depends(get_current_user_from_token),
    repository: GuardrailRuleRepository = Depends(get_guardrail_rule_repository),
    db: Session = Depends(get_db),
):
    try:
        rules = repository.restore_defaults(current_user.id, reason=payload.reason or None)
        await AuditService(AuditRepository(db)).log_event(
            event_type="guardrail_rule_updated",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="GUARDRAIL_RULE",
            resource_id="ALL",
            metadata={"restore_defaults": True, "reason": payload.reason or None},
            commit=False,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {"success": True, "data": _rules_payload(rules)}


@router.post(
    "/guardrail-rules/versions/{policy_version}/rollback",
    response_model=AdminGuardrailRollbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.MANAGE))],
)
async def rollback_guardrail_policy(
    policy_version: str,
    payload: AdminGuardrailRollbackRequest,
    current_user: User = Depends(get_current_user_from_token),
    repository: GuardrailRuleRepository = Depends(get_guardrail_rule_repository),
    db: Session = Depends(get_db),
):
    try:
        published, target = repository.rollback(
            policy_version,
            actor_user_id=current_user.id,
            reason=payload.reason,
        )
        await AuditService(AuditRepository(db)).log_event(
            event_type="guardrail_rule_updated",
            decision="ALLOW",
            actor_user_id=current_user.id,
            resource_type="GUARDRAIL_POLICY",
            resource_id=published.version,
            metadata={
                "rollback_from": target.version,
                "reason": payload.reason,
                "version": published.version,
            },
            commit=False,
        )
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except CoreGuardrailLockedError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Guardrail rule {exc.code} is core-locked and cannot be disabled",
        ) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise

    snapshot = {str(code): bool(enabled) for code, enabled in published.rules_snapshot.items()}
    return {
        "success": True,
        "data": {
            "version": published.version,
            "rolled_back_from": target.version,
            "rules": snapshot,
            "any_disabled": any(not value for value in snapshot.values()),
        },
    }


@router.post(
    "/courses",
    response_model=AdminCoursesResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def create_admin_course(
    payload: AdminCourseCreateRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    code = payload.subject_code.upper()
    try:
        _course_repository(db).add_course(
            code, payload.subject_name, payload.semester, current_user.id
        )
        await _audit_admin_mutation(
            db,
            event_type="admin_course_added",
            actor_user_id=current_user.id,
            resource_type="COURSE",
            resource_id=code,
            metadata={"semester": payload.semester},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {"success": True, "data": AdminReadService(db).list_courses()}


@router.delete(
    "/courses/{code}",
    response_model=AdminCoursesResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def hide_admin_course(
    code: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    normalized = code.strip().upper()
    try:
        _course_repository(db).hide_course(normalized, current_user.id)
        await _audit_admin_mutation(
            db,
            event_type="admin_course_hidden",
            actor_user_id=current_user.id,
            resource_type="COURSE",
            resource_id=normalized,
            metadata={"hidden": True},
        )
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {"success": True, "data": AdminReadService(db).list_courses()}


@router.post(
    "/courses/{code}/restore",
    response_model=AdminCoursesResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def restore_admin_course(
    code: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    normalized = code.strip().upper()
    try:
        _course_repository(db).restore_course(normalized, current_user.id)
        await _audit_admin_mutation(
            db,
            event_type="admin_course_restored",
            actor_user_id=current_user.id,
            resource_type="COURSE",
            resource_id=normalized,
            metadata={"hidden": False},
        )
        db.commit()
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    return {"success": True, "data": AdminReadService(db).list_courses()}


@router.get(
    "/courses/{code}/documents",
    response_model=AdminDocumentsResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.READ))],
)
def list_admin_course_documents(code: str, db: Session = Depends(get_db)):
    _ensure_visible_course(db, code)
    documents = AdminDocumentIngestService(db).list_documents(code)
    return {"success": True, "data": {"documents": documents}}


@router.get(
    "/courses/{code}/documents/{document_id}/content",
    response_model=AdminDocumentContentResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.READ))],
)
def get_admin_course_document_content(
    code: str,
    document_id: str,
    db: Session = Depends(get_db),
):
    _owned_document(db, code, document_id)
    try:
        content = AdminDocumentIngestService(db).get_content(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"success": True, "data": content}


@router.post(
    "/courses/{code}/documents",
    response_model=AdminIngestJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def upload_admin_course_document(
    code: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Form(default=models.DocType.SYLLABUS.value),
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    course = _ensure_visible_course(db, code)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    filename = file.filename or "document.txt"
    normalized_doc_type = (doc_type or "").strip().upper()
    allowed_doc_types = {item.value for item in models.DocType}
    if normalized_doc_type not in allowed_doc_types:
        raise HTTPException(
            status_code=400,
            detail=f"doc_type must be one of {sorted(allowed_doc_types)}",
        )
    try:
        validate_admin_document(filename, content)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = _course_repository(db).start_job(course.code, operation="upload")
    db.commit()
    background_tasks.add_task(
        run_admin_ingest_job,
        job_id=job.id,
        operation="upload",
        payload={
            "course_code": course.code,
            "filename": filename,
            "content": content,
            "actor_user_id": current_user.id,
            "doc_type": normalized_doc_type,
        },
    )
    return {"success": True, "data": {"job_id": job.id, "status": "processing"}}


def _owned_document(db: Session, code: str, document_id: str) -> models.Document:
    course = _ensure_visible_course(db, code)
    document = db.get(models.Document, document_id)
    if (
        document is None
        or document.course_id != course.id
        or (document.metadata_info or {}).get("source") != "admin_curriculum"
    ):
        raise HTTPException(status_code=404, detail="Admin curriculum document not found")
    return document


@router.put(
    "/courses/{code}/documents/{document_id}",
    response_model=AdminIngestJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def replace_admin_course_document(
    code: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, code, document_id)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    filename = file.filename or "document.txt"
    try:
        validate_admin_document(filename, content)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    job = _course_repository(db).start_job(
        code, operation="replace", document_id=document.id
    )
    db.commit()
    background_tasks.add_task(
        run_admin_ingest_job,
        job_id=job.id,
        operation="replace",
        payload={
            "document_id": document.id,
            "filename": filename,
            "content": content,
            "actor_user_id": current_user.id,
        },
    )
    return {"success": True, "data": {"job_id": job.id, "status": "processing"}}


@router.delete(
    "/courses/{code}/documents/{document_id}",
    response_model=AdminIngestJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
def delete_admin_course_document(
    code: str,
    document_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, code, document_id)
    if document.publication_status in {"PUBLISHED", "ARCHIVED"}:
        raise HTTPException(
            status_code=409,
            detail="Published or archived document versions are immutable",
        )
    dependent = db.query(models.Document.id).filter(models.Document.previous_version_id == document.id).first()
    if dependent is not None:
        raise HTTPException(status_code=409, detail="A later version depends on this document")
    job = _course_repository(db).start_job(
        code, operation="delete", document_id=document.id
    )
    db.commit()
    background_tasks.add_task(
        run_admin_ingest_job,
        job_id=job.id,
        operation="delete",
        payload={"document_id": document.id, "actor_user_id": current_user.id},
    )
    return {"success": True, "data": {"job_id": job.id, "status": "processing"}}


class DocumentLifecyclePayload(BaseModel):
    change_reason: str = Field(..., min_length=5, max_length=500)


@router.post(
    "/courses/{code}/documents/{document_id}/validate",
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
def validate_admin_course_document(
    code: str,
    document_id: str,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, code, document_id)
    course = db.get(models.Course, document.course_id)
    meta = document.metadata_info or {}

    ingest_service = AdminDocumentIngestService(db)
    source_bytes = ingest_service.read_source_bytes(document)
    readable_file = False
    file_text: str | None = None
    if source_bytes is not None:
        try:
            file_text = source_bytes.decode("utf-8")
            readable_file = True
        except UnicodeDecodeError:
            readable_file = False

    # Documents ingested before checksum tracking existed have no stored
    # checksum to compare against -- back-fill it from the file on disk now
    # (self-healing) rather than permanently failing validation for content
    # nobody has tampered with, same "legacy" leniency chung's own
    # AdminDocumentLifecycleService applies (docs/branch-audit/chung-admin-
    # backend.md §3.4).
    if document.checksum is None and file_text is not None:
        document.checksum = hashlib.sha256(file_text.encode("utf-8")).hexdigest()

    checksum_matches_file = bool(
        readable_file
        and document.checksum
        and hashlib.sha256(file_text.encode("utf-8")).hexdigest() == document.checksum
    )

    chunk_count = db.query(models.DocumentChunk).filter_by(document_id=document.id).count()

    results = {
        "official_scope": document.scope == "OFFICIAL",
        "admin_source": meta.get("source") == "admin_curriculum",
        "checksum_matches_file": checksum_matches_file,
        "readable_file": readable_file,
        "has_chunks": 0 < chunk_count <= MAX_CHUNKS,
        "course_provenance": bool(course) and meta.get("course_code") == course.code,
    }
    passed = all(results.values())
    if passed:
        document.validated_at = datetime.utcnow()
        document.validated_by = current_user.id
        if document.publication_status == "DRAFT":
            document.publication_status = "READY_FOR_REVIEW"
    else:
        document.validated_at = None
        document.validated_by = None
        if document.publication_status == "READY_FOR_REVIEW":
            document.publication_status = "DRAFT"
    db.commit()

    return {"success": True, "data": {"valid": passed, "checks": results, "chunk_count": chunk_count}}


@router.post(
    "/courses/{code}/documents/{document_id}/publish",
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def publish_admin_course_document(
    code: str,
    document_id: str,
    payload: DocumentLifecyclePayload,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, code, document_id)
    if document.publication_status not in ["DRAFT", "READY_FOR_REVIEW"]:
        raise HTTPException(status_code=400, detail="Only DRAFT or READY_FOR_REVIEW can be published")
    if document.validated_at is None:
        raise HTTPException(status_code=400, detail="Document must pass validation before it can be published")

    group = document.version_group or document.id
    currently_published = db.query(models.Document).filter(
        models.Document.course_id == document.course_id,
        models.Document.version_group == group,
        models.Document.publication_status == "PUBLISHED",
    ).all()
    now = datetime.utcnow()
    try:
        for published in currently_published:
            if published.id != document.id:
                published.publication_status = "ARCHIVED"
                published.archived_at = now
                published.change_reason = "Auto-archived due to new publication"
        document.publication_status = "PUBLISHED"
        document.published_at = now
        document.published_by = current_user.id
        document.archived_at = None
        document.change_reason = payload.change_reason
        await _audit_admin_mutation(
            db,
            event_type="curriculum_published",
            actor_user_id=current_user.id,
            resource_type="DOCUMENT",
            resource_id=document.id,
            metadata={"course_code": code, "version": document.version, "change_reason": payload.change_reason},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "success": True,
        "data": {"document": AdminDocumentIngestService(db).serialize_document(document)},
    }


@router.post(
    "/courses/{code}/documents/{document_id}/archive",
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def archive_admin_course_document(
    code: str,
    document_id: str,
    payload: DocumentLifecyclePayload,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    document = _owned_document(db, code, document_id)
    if document.publication_status != "PUBLISHED":
        raise HTTPException(status_code=400, detail="Only PUBLISHED documents can be archived")

    try:
        document.publication_status = "ARCHIVED"
        document.archived_at = datetime.utcnow()
        document.change_reason = payload.change_reason
        await _audit_admin_mutation(
            db,
            event_type="curriculum_archived",
            actor_user_id=current_user.id,
            resource_type="DOCUMENT",
            resource_id=document.id,
            metadata={"course_code": code, "version": document.version, "change_reason": payload.change_reason},
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "success": True,
        "data": {"document": AdminDocumentIngestService(db).serialize_document(document)},
    }


@router.get(
    "/courses/{code}/documents/{document_id}/versions",
    response_model=AdminDocumentVersionsResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.READ))],
)
def list_admin_course_document_versions(
    code: str,
    document_id: str,
    db: Session = Depends(get_db),
):
    _owned_document(db, code, document_id)
    versions = AdminDocumentIngestService(db).list_versions(document_id)
    return {"success": True, "data": {"versions": versions}}


@router.post(
    "/courses/{code}/documents/{document_id}/rollback",
    response_model=AdminDocumentMutationResponse,
    dependencies=[Depends(require_permission(Resource.COURSE, Permission.MANAGE))],
)
async def rollback_admin_course_document(
    code: str,
    document_id: str,
    payload: DocumentLifecyclePayload,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _owned_document(db, code, document_id)
    service = AdminDocumentIngestService(db)
    cleanup_on_failure = None
    try:
        rolled_back = service.rollback(
            document_id=document_id,
            actor_user_id=current_user.id,
            change_reason=payload.change_reason,
        )
        cleanup_on_failure = rolled_back.pop("_created_path", None)
        await _audit_admin_mutation(
            db,
            event_type="curriculum_rolled_back",
            actor_user_id=current_user.id,
            resource_type="DOCUMENT",
            resource_id=rolled_back["id"],
            metadata={
                "course_code": code,
                "rollback_of": document_id,
                "version": rolled_back["version"],
                "change_reason": payload.change_reason,
            },
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        if cleanup_on_failure is not None:
            _unlink_file(cleanup_on_failure)
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        if cleanup_on_failure is not None:
            _unlink_file(cleanup_on_failure)
        raise
    return {"success": True, "data": {"document": rolled_back}}


# ── Org invites / access requests (B2B2C onboarding, pre-dates develop's
#    Admin Console rewrite — develop never had the multi-tenancy pivot, so
#    these endpoints are ported forward as-is rather than lost on merge) ──
@router.post(
    "/invites",
    response_model=InviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_invite(
    payload: CreateInviteRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    invite_service: OrgInviteService = Depends(get_org_invite_service),
    db: Session = Depends(get_db),
) -> InviteResponse:
    """Only path (besides seed/provisioning scripts) that grants any role —
    Student, Instructor, or Admin — access to Cursus. Always scoped to the
    inviting admin's own organization; never accepts an organization id
    from the client."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account is not attached to an organization",
        )
    try:
        invite = await invite_service.create_invite(
            organization_id=current_user.organization_id,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            invited_by_user_id=current_user.id,
        )
    except OrgInviteError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    await _audit_admin_mutation(
        db,
        event_type="invitation_created",
        actor_user_id=current_user.id,
        resource_type="INVITATION",
        resource_id=invite.id,
        metadata={"email": invite.email, "role": invite.role},
    )
    db.commit()
    return _serialize_invite(invite)


@router.get("/invites", response_model=list[InviteResponse])
async def list_invites(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    invite_service: OrgInviteService = Depends(get_org_invite_service),
) -> list[InviteResponse]:
    if not current_user.organization_id:
        return []
    invites = invite_service.list_for_org(current_user.organization_id)
    return [_serialize_invite(invite) for invite in invites]


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    invite_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    invite_service: OrgInviteService = Depends(get_org_invite_service),
    db: Session = Depends(get_db),
) -> None:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    try:
        invite = invite_service.revoke(invite_id, organization_id=current_user.organization_id)
    except InviteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        ) from exc
    await _audit_admin_mutation(
        db,
        event_type="invitation_revoked",
        actor_user_id=current_user.id,
        resource_type="INVITATION",
        resource_id=invite.id,
        metadata={"email": invite.email},
    )
    db.commit()


@router.post("/invites/{invite_id}/resend", response_model=InviteResponse)
async def resend_invite(
    invite_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    invite_service: OrgInviteService = Depends(get_org_invite_service),
    db: Session = Depends(get_db),
) -> InviteResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")
    try:
        invite = await invite_service.resend(
            invite_id,
            organization_id=current_user.organization_id,
        )
    except InviteNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        ) from exc
    except OrgInviteError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    await _audit_admin_mutation(
        db=db,
        event_type="invitation_resent",
        actor_user_id=current_user.id,
        resource_type="INVITATION",
        resource_id=invite.id,
        metadata={"email": invite.email, "resend_count": invite.resend_count},
    )
    db.commit()
    return _serialize_invite(invite)


def _serialize_user(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=str(getattr(user.role, "value", user.role)),
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_org_users(
    current_user: User = Depends(require_permission(Resource.USER, Permission.MANAGE)),
    db: Session = Depends(get_db),
) -> list[AdminUserOut]:
    if not current_user.organization_id:
        return []
    rows = (
        db.query(User)
        .filter_by(organization_id=current_user.organization_id)
        .order_by(User.created_at.desc())
        .all()
    )
    return [_serialize_user(row) for row in rows]


@router.patch("/users/{user_id}/status", response_model=AdminUserOut)
async def update_user_status(
    user_id: str,
    payload: UpdateUserStatusRequest,
    current_user: User = Depends(require_permission(Resource.USER, Permission.MANAGE)),
    db: Session = Depends(get_db),
) -> AdminUserOut:
    """Lock/unlock an org member. `User.is_active` is already enforced at
    login (auth_service.py) -- this is the only piece that was missing."""
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot lock your own account",
        )
    target = (
        db.query(User)
        .filter_by(id=user_id, organization_id=current_user.organization_id)
        .first()
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_active = target.is_active
    target.is_active = payload.is_active

    # Audit log
    await AuditService(AuditRepository(db)).log_event(
        event_type="UPDATE_USER_STATUS",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="USER",
        resource_id=target.id,
        metadata={
            "old_active": old_active,
            "new_active": payload.is_active,
            "reason": payload.reason
        },
        commit=False
    )

    db.commit()
    db.refresh(target)
    return _serialize_user(target)


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    current_user: User = Depends(require_permission(Resource.USER, Permission.MANAGE)),
    db: Session = Depends(get_db),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
):
    """Gửi lại link đặt mật khẩu cho một thành viên trong cùng tổ chức.

    Admin KHÔNG đặt mật khẩu thay người dùng -- chỉ phát hành token đặt lại,
    người dùng tự chọn mật khẩu mới. Dùng lại đúng `PasswordResetService`
    của luồng "Quên mật khẩu" công khai (`POST /auth/password/forgot` trong
    `src/api/auth.py`) qua `get_password_reset_service`, để không tồn tại 2
    cơ chế phát hành token song song. (Brief này giả định 1 hàm rời
    `issue_password_reset(db, user=target)` trong 1 module chưa từng tồn tại
    -- thực tế `password_reset_service.py` đã có sẵn class `PasswordResetService`
    với `request_password_reset(email)`, nên route dưới đây tái sử dụng thẳng
    class đó thay vì tạo hàm mới.)
    """
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization_required")
    target = (
        db.query(User)
        .filter_by(id=user_id, organization_id=current_user.organization_id)
        .first()
    )
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    result = await password_reset_service.request_password_reset(target.email)
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_password_reset_issued",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="USER",
        resource_id=target.id,
        metadata={"issued": result.issued},
    )
    return {"success": True, "emailSent": bool(result.issued)}


class AnnouncementRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)


@router.post("/announcements", status_code=status.HTTP_201_CREATED)
async def create_announcement(
    payload: AnnouncementRequest,
    current_user: User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Publish a notice to every instructor in the caller's organization.

    `admin_announcements` was already read by `GET /instructor/announcements`
    and rendered on the instructor dashboard, but nothing ever wrote to it,
    so that panel was permanently empty. This is the missing writer.

    Stamps `organization_id` -- see the column's note in `src/db/models.py`:
    the reader had no organization filter, which only became a cross-tenant
    leak once rows started existing.
    """
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="organization_required"
        )

    announcement = models.AdminAnnouncement(
        id=f"ann_{uuid4().hex}",
        title=payload.title.strip(),
        content=payload.content.strip(),
        created_by=current_user.id,
        organization_id=current_user.organization_id,
    )
    db.add(announcement)
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_announcement_published",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="ADMIN_ANNOUNCEMENT",
        resource_id=announcement.id,
    )
    return {
        "id": announcement.id,
        "title": announcement.title,
        "content": announcement.content,
        "createdAt": announcement.created_at.isoformat(),
    }


@router.get("/access-requests", response_model=list[AccessRequestResponse])
async def list_access_requests(
    db: Session = Depends(get_db),
) -> list[AccessRequestResponse]:
    requests = AccessRequestRepository(db).list_all()
    return [
        AccessRequestResponse(
            id=r.id,
            institution_name=r.institution_name,
            contact_name=r.contact_name,
            email=r.email,
            role_interested=r.role_interested,
            message=r.message,
            created_at=r.created_at.isoformat(),
        )
        for r in requests
    ]


def _serialize_invite(invite: OrgInvite) -> InviteResponse:
    return InviteResponse(
        id=invite.id,
        email=invite.email,
        full_name=invite.full_name,
        role=invite.role,
        expires_at=invite.expires_at.isoformat(),
        used_at=invite.used_at.isoformat() if invite.used_at else None,
        revoked_at=invite.revoked_at.isoformat() if invite.revoked_at else None,
        delivery_status=invite.delivery_status or "sent",
        resend_count=invite.resend_count or 0,
        last_sent_at=invite.last_sent_at.isoformat() if invite.last_sent_at else None,
        created_at=invite.created_at.isoformat(),
    )


# ── Academic term + course exam scheduling (Admin) ──────────────────────
# `AcademicTerm` carries `organization_id` directly (the one "root" table
# from the semester/practice migration with no course/student FK to inherit
# scope through), so every call below is resolved from the acting admin's
# own `current_user.organization_id` — never a client-supplied value.


def get_academic_term_service(db: Session = Depends(get_db)) -> AcademicTermService:
    return AcademicTermService(AcademicTermRepository(db))


@router.get("/academic-terms/active", response_model=AcademicTermOut | None)
def get_active_academic_term(
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> AcademicTermOut | None:
    payload = service.get_active(current_user.organization_id)
    return AcademicTermOut(**payload) if payload else None


@router.get("/academic-terms", response_model=list[AcademicTermOut])
def list_academic_terms(
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> list[AcademicTermOut]:
    return [AcademicTermOut(**item) for item in service.list_terms(current_user.organization_id)]


@router.put("/academic-terms/active", response_model=AcademicTermOut)
def upsert_academic_term(
    payload: AcademicTermUpsertRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> AcademicTermOut:
    try:
        result = service.upsert_term(
            organization_id=current_user.organization_id,
            name=payload.name,
            start_date=payload.start_date,
            study_weeks=payload.studyWeeks,
            exam_weeks=payload.examWeeks,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AcademicTermOut(**result)


@router.get("/course-exams")
def list_course_exams(
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> dict:
    try:
        return service.list_exams(current_user.organization_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/course-exams", response_model=CourseExamOut)
def upsert_course_exam(
    payload: CourseExamUpsertRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> CourseExamOut:
    try:
        result = service.upsert_exam(
            organization_id=current_user.organization_id,
            course_id=payload.courseId,
            kind=payload.kind,
            sessions=[
                {
                    "exam_date": session.exam_date,
                    "slot_id": session.slotId,
                    "label": session.label,
                }
                for session in payload.sessions
            ],
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CourseExamOut(**result)


@router.delete("/course-exams/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course_exam(
    exam_id: str,
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> None:
    try:
        service.delete_exam(organization_id=current_user.organization_id, exam_id=exam_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ── Class activities (Instructor + Admin) ────────────────────────────────
# Separate router: the module-level `router` above gates ADMIN only, but
# logging a held/cancelled/makeup lecture is an instructor action too. A
# second APIRouter with its own role gate is the smallest change that keeps
# "one file for admin/academic surfaces" without loosening the ADMIN-only
# router above.
academic_router = APIRouter(
    prefix="/admin",
    tags=["class-activities"],
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.INSTRUCTOR))],
)


@academic_router.post("/class-activities", response_model=ClassActivityOut, status_code=status.HTTP_201_CREATED)
def log_class_activity(
    payload: ClassActivityRequest,
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> ClassActivityOut:
    try:
        result = service.log_class_activity(
            organization_id=current_user.organization_id,
            instructor_id=current_user.id,
            role=current_user.role,
            course_id=payload.courseId,
            activity_date=date.fromisoformat(payload.activityDate),
            kind=payload.kind,
            title=payload.title,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ClassActivityOut(**result)


@academic_router.get("/class-activities", response_model=list[ClassActivityOut])
def list_class_activities(
    course_id: str,
    current_user: User = Depends(get_current_user_from_token),
    service: AcademicTermService = Depends(get_academic_term_service),
) -> list[ClassActivityOut]:
    try:
        return [
            ClassActivityOut(**item)
            for item in service.list_class_activities(
                organization_id=current_user.organization_id,
                course_id=course_id,
                instructor_id=current_user.id,
                role=current_user.role,
            )
        ]
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
