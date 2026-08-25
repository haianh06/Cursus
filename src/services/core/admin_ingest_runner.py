from __future__ import annotations

import logging

from src.db.connection import SessionLocal
from src.repositories.admin_course_repository import AdminCourseRepository
from src.repositories.audit_repository import AuditRepository
from src.services.core.audit_service import AuditService
from src.services.rag.admin_document_ingest_service import AdminDocumentIngestService, _unlink_file

logger = logging.getLogger(__name__)


def run_admin_ingest_job(*, job_id: str, operation: str, payload: dict) -> None:
    db = SessionLocal()
    repository = AdminCourseRepository(db, catalog_codes=set())
    cleanup_after_commit = None
    cleanup_on_failure = None
    try:
        service = AdminDocumentIngestService(db)
        if operation == "upload":
            result = service.ingest_new(**payload)
            cleanup_on_failure = result.pop("_created_path", None)
            event_type = "admin_document_uploaded"
        elif operation == "replace":
            result = service.replace(**payload)
            cleanup_on_failure = result.pop("_created_path", None)
            cleanup_after_commit = result.pop("_cleanup_path", None)
            event_type = "admin_document_replaced"
        elif operation == "delete":
            cleanup_after_commit = service.delete(**payload)
            result = {"id": payload["document_id"], "chunk_count": 0}
            event_type = "admin_document_deleted"
        else:
            raise ValueError(f"Unknown ingest operation: {operation}")

        # A delete job must not reattach its FK to the document that was just
        # removed. PostgreSQL enforces this immediately (SQLite test databases
        # may not), so retain the audit resource id but leave the job FK null.
        job_document_id = None if operation == "delete" else result.get("id")
        job = repository.finish_job(
            job_id,
            status="ingested",
            document_id=job_document_id,
            clear_document_id=operation == "delete",
        )
        _log_event(
            db,
            event_type=event_type,
            decision="ALLOW",
            actor_user_id=payload.get("actor_user_id"),
            document_id=result.get("id"),
            metadata={"course_code": job.course_code, "chunk_count": result.get("chunk_count", 0)},
        )
        db.commit()
        if cleanup_after_commit is not None:
            _unlink_file(cleanup_after_commit)
    except Exception as exc:
        db.rollback()
        if cleanup_on_failure is not None:
            _unlink_file(cleanup_on_failure)
        try:
            job = repository.finish_job(job_id, status="failed", error=_safe_error(exc))
            _log_event(
                db,
                event_type=f"admin_document_{operation}_failed",
                decision="DENY",
                actor_user_id=payload.get("actor_user_id"),
                document_id=payload.get("document_id"),
                metadata={"course_code": job.course_code, "error": _safe_error(exc)},
            )
            db.commit()
        except Exception:
            db.rollback()
            logger.exception(
                "admin_ingest_failure_recording_failed job_id=%s operation=%s",
                job_id,
                operation,
            )
    finally:
        db.close()


def _log_event(db, *, event_type, decision, actor_user_id, document_id, metadata) -> None:
    import asyncio

    asyncio.run(
        AuditService(AuditRepository(db)).log_event(
            event_type=event_type,
            decision=decision,
            actor_user_id=actor_user_id,
            resource_type="DOCUMENT",
            resource_id=document_id,
            metadata=metadata,
            commit=False,
        )
    )


def _safe_error(exc: Exception) -> str:
    if isinstance(exc, (ValueError, LookupError, PermissionError)):
        return str(exc)[:300]
    return "Document processing failed"
