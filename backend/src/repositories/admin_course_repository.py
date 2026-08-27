from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db.models import AdminCourseOverride, Course, CourseIngestJob


def utc_now_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class AdminCourseRepository:
    def __init__(self, db: Session, *, catalog_codes: set[str]) -> None:
        self._db = db
        self._catalog_codes = {code.strip().upper() for code in catalog_codes}

    def list_overrides(self) -> list[AdminCourseOverride]:
        return self._db.query(AdminCourseOverride).order_by(AdminCourseOverride.subject_code).all()

    def add_course(
        self, code: str, name: str, semester: str, actor_user_id: str | None
    ) -> AdminCourseOverride:
        normalized = code.strip().upper()
        if normalized in self._catalog_codes:
            raise ValueError(f"Course already exists: {normalized}")
        existing_override = self._db.get(AdminCourseOverride, normalized)
        # Case-insensitive for the same reason as chunk_repository.py /
        # api/admin.py's _ensure_visible_course — a mixed-case existing
        # Course row must never be missed here, or this would insert a
        # second, differently-cased duplicate right below.
        existing_course = (
            self._db.query(Course).filter(func.upper(Course.code) == normalized).first()
        )
        if existing_override or existing_course:
            raise ValueError(f"Course already exists: {normalized}")

        self._db.add(
            Course(id=normalized, code=normalized, name=name.strip(), description="")
        )
        override = AdminCourseOverride(
            subject_code=normalized,
            subject_name=name.strip(),
            semester=semester.strip(),
            is_added=True,
            hidden=False,
            updated_at=utc_now_naive(),
            updated_by=actor_user_id,
        )
        self._db.add(override)
        self._db.flush()
        return override

    def hide_course(self, code: str, actor_user_id: str | None) -> AdminCourseOverride:
        normalized = code.strip().upper()
        override = self._db.get(AdminCourseOverride, normalized)
        if override is None:
            if normalized not in self._catalog_codes:
                raise LookupError(f"Course not found: {normalized}")
            override = AdminCourseOverride(
                subject_code=normalized,
                is_added=False,
                hidden=True,
                updated_at=utc_now_naive(),
                updated_by=actor_user_id,
            )
            self._db.add(override)
        else:
            override.hidden = True
            override.updated_at = utc_now_naive()
            override.updated_by = actor_user_id
        self._db.flush()
        return override

    def restore_course(self, code: str, actor_user_id: str | None) -> None:
        normalized = code.strip().upper()
        override = self._db.get(AdminCourseOverride, normalized)
        if override is None:
            raise LookupError(f"Hidden course not found: {normalized}")
        if override.is_added:
            override.hidden = False
            override.updated_at = utc_now_naive()
            override.updated_by = actor_user_id
        else:
            self._db.delete(override)
        self._db.flush()

    def start_job(
        self,
        course_code: str,
        *,
        operation: str,
        document_id: str | None = None,
    ) -> CourseIngestJob:
        job = CourseIngestJob(
            id=f"job_{uuid.uuid4().hex}",
            course_code=course_code.strip().upper(),
            document_id=document_id,
            operation=operation,
            status="processing",
            error=None,
            created_at=utc_now_naive(),
        )
        self._db.add(job)
        self._db.flush()
        return job

    def finish_job(
        self,
        job_id: str,
        *,
        status: str,
        error: str | None = None,
        document_id: str | None = None,
        clear_document_id: bool = False,
    ) -> CourseIngestJob:
        if status not in {"ingested", "failed"}:
            raise ValueError("Invalid terminal job status")
        job = self._db.get(CourseIngestJob, job_id)
        if job is None:
            raise LookupError(f"Ingest job not found: {job_id}")
        job.status = status
        job.error = error
        if clear_document_id:
            job.document_id = None
        elif document_id is not None:
            job.document_id = document_id
        job.completed_at = utc_now_naive()
        self._db.flush()
        return job

    def latest_jobs(self) -> list[CourseIngestJob]:
        jobs = self._db.query(CourseIngestJob).order_by(CourseIngestJob.created_at.desc(), CourseIngestJob.id.desc()).all()
        latest: dict[tuple[str, str | None], CourseIngestJob] = {}
        for job in jobs:
            key = (job.course_code, job.document_id)
            latest.setdefault(key, job)
        return list(latest.values())

    def fail_stale_jobs(self, *, max_age_seconds: int) -> int:
        cutoff = utc_now_naive() - timedelta(seconds=max_age_seconds)
        stale = (
            self._db.query(CourseIngestJob)
            .filter(CourseIngestJob.status == "processing", CourseIngestJob.created_at < cutoff)
            .all()
        )
        for job in stale:
            job.status = "failed"
            job.error = "Ingest job timed out"
            job.completed_at = utc_now_naive()
        self._db.flush()
        return len(stale)
