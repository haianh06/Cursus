from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from src.db import models
from src.repositories.admin_course_repository import AdminCourseRepository
from src.services.mock.demo_data import load_class_snapshot, load_curriculum


class AdminDataUnavailable(RuntimeError):  # noqa: N818 -- required public API contract
    pass


# mục 16 data contract: a chunk's Document.metadata_info["source"] is the only
# signal admin_read_service has for provenance (DocumentChunk.metadata_info is
# not queried here). "curriculum" (gate2_demo.ingest_official_chunks) and
# "admin_curriculum" (admin_document_ingest_service, an admin-uploaded real
# file) are official_document-provenance content. "mock" (student_mock_data_
# service.COURSE_DOCUMENTS) is fabricated syllabus text and must never be
# counted as, or displayed like, ingested official content — that was the
# bug: this set didn't exist, so a "mock" source fell through to "anything
# not student_upload counts as ingested" and rendered identically to real
# curriculum content in the Admin Console.
_REAL_CONTENT_SOURCES = frozenset({"curriculum", "admin_curriculum"})
_MOCK_CONTENT_SOURCES = frozenset({"mock"})


class AdminReadService:
    def __init__(
        self,
        db: Session,
        *,
        curriculum_loader: Callable[[], dict[str, Any]] = load_curriculum,
        snapshot_loader: Callable[[], dict[str, Any]] = load_class_snapshot,
    ) -> None:
        self._db = db
        self._curriculum_loader = curriculum_loader
        self._snapshot_loader = snapshot_loader

    def fail_stale_ingest_jobs(self, *, max_age_seconds: int = 1800) -> int:
        return AdminCourseRepository(
            self._db, catalog_codes=set()
        ).fail_stale_jobs(max_age_seconds=max_age_seconds)

    def list_courses(self) -> dict[str, Any]:
        payload = self._curriculum_loader()
        subjects = payload.get("subjects") if isinstance(payload, dict) else None
        expected_count = payload.get("subject_count") if isinstance(payload, dict) else None
        if not isinstance(subjects, list) or not subjects:
            raise AdminDataUnavailable("Curriculum catalog is unavailable")
        if not isinstance(expected_count, int) or expected_count != len(subjects):
            raise AdminDataUnavailable("Curriculum catalog count is invalid")

        rows = (
            self._db.query(models.Course.code, models.Document.metadata_info, models.DocumentChunk.id)
            .select_from(models.Course)
            .join(models.Document, models.Document.course_id == models.Course.id)
            .join(models.DocumentChunk, models.DocumentChunk.document_id == models.Document.id)
            .all()
        )
        chunk_counts: Counter[str] = Counter()
        mock_chunk_counts: Counter[str] = Counter()
        unknown_source_counts: Counter[str] = Counter()
        for course_code, metadata_info, _chunk_id in rows:
            metadata = metadata_info if isinstance(metadata_info, dict) else {}
            source = metadata.get("source")
            if source == "student_upload":
                continue
            code = str(course_code).strip().upper()
            if source in _MOCK_CONTENT_SOURCES:
                mock_chunk_counts[code] += 1
            elif source in _REAL_CONTENT_SOURCES:
                chunk_counts[code] += 1
            else:
                # Unrecognized/missing source tag on a non-student-upload
                # document. Treat as real rather than silently dropping it
                # (a document ingested by a path this set doesn't know about
                # yet should still show up as ingested), but track separately
                # so this doesn't mask a future new mock source slipping in
                # unlabeled the way "mock" itself did.
                unknown_source_counts[code] += 1
                chunk_counts[code] += 1

        catalog_rows: dict[str, dict[str, Any]] = {}
        for subject in subjects:
            if not isinstance(subject, dict):
                raise AdminDataUnavailable("Curriculum subject is invalid")
            code = str(subject.get("Subject Code") or "").strip().upper()
            name = str(subject.get("Subject Name") or "").strip()
            semester = str(subject.get("Semester") or "").strip()
            if not code or not name or not semester:
                raise AdminDataUnavailable("Curriculum subject fields are incomplete")
            catalog_rows[code] = {
                "subject_code": code,
                "subject_name": name,
                "semester": semester,
                "is_added": False,
            }

        repository = AdminCourseRepository(self._db, catalog_codes=set(catalog_rows))
        overrides = {item.subject_code: item for item in repository.list_overrides()}

        visible_rows = {
            code: row
            for code, row in catalog_rows.items()
            if not (overrides.get(code) and overrides[code].hidden)
        }
        for code, override in overrides.items():
            if override.is_added and not override.hidden:
                if not override.subject_name or not override.semester:
                    raise AdminDataUnavailable("Added course overlay is incomplete")
                visible_rows[code] = {
                    "subject_code": code,
                    "subject_name": override.subject_name,
                    "semester": override.semester,
                    "is_added": True,
                }

        latest_by_course: dict[str, models.CourseIngestJob] = {}
        jobs = (
            self._db.query(models.CourseIngestJob)
            .order_by(models.CourseIngestJob.created_at.desc(), models.CourseIngestJob.id.desc())
            .all()
        )
        for job in jobs:
            latest_by_course.setdefault(job.course_code, job)

        courses: list[dict[str, Any]] = []
        for code, row in visible_rows.items():
            count = chunk_counts.get(code, 0)
            mock_count = mock_chunk_counts.get(code, 0)
            job = latest_by_course.get(code)
            if count > 0:
                status = "ingested"
            elif mock_count > 0:
                status = "mock_only"
            else:
                status = "not_ingested"
            error = None
            if job and job.status in {"processing", "failed"}:
                status = job.status
                error = job.error if job.status == "failed" else None
            courses.append(
                {
                    **row,
                    "ingest_status": status,
                    "ingest_error": error,
                    "chunk_count": count,
                    "mock_chunk_count": mock_count,
                }
            )

        courses.sort(key=_course_sort_key)
        return {"subject_count": len(courses), "courses": courses}

    def get_kpi(self) -> dict[str, Any]:
        payload = self._snapshot_loader()
        comparison = payload.get("kpi_comparison") if isinstance(payload, dict) else None
        if not isinstance(comparison, dict):
            raise AdminDataUnavailable("KPI snapshot is unavailable")
        with_cursus = _ratio(comparison.get("with_cursus_overall"))
        baseline = _ratio(comparison.get("baseline_overall"))
        note = comparison.get("note")
        if not isinstance(note, str) or not note.strip():
            raise AdminDataUnavailable("KPI method note is unavailable")
        return {
            "with_cursus_overall": with_cursus,
            "baseline_overall": baseline,
            "method_note": f"Dữ liệu mô phỏng minh họa phương pháp đo. {note.strip()}",
        }

    def get_analytics(self, *, organization_id: str | None) -> dict[str, Any]:
        """mục 6.5 expanded Analytics. `total_documents` is intentionally
        NOT org-scoped -- the course/document catalog is shared across
        organizations today (list_courses() above has the same behavior).
        `at_risk_student_count`/`weekly_risk_trend` ARE scoped by the
        student's own organization_id -- students are per-tenant even
        though the catalog is not."""
        total_documents = self._db.query(models.Document).count()

        if not organization_id:
            # No org on the caller -- show zero rather than silently falling
            # through to an unscoped (cross-org) aggregate. Not a live path
            # today (every route that creates a User sets organization_id),
            # but the other org-scoped fields below must fail closed if it
            # ever is.
            return {
                "total_documents": total_documents,
                "at_risk_student_count": 0,
                "weekly_risk_trend": [],
            }

        base_query = self._db.query(models.RiskSignal).join(
            models.User, models.User.id == models.RiskSignal.student_id
        ).filter(models.User.organization_id == organization_id)

        at_risk_student_count = (
            base_query.filter(models.RiskSignal.resolved_at.is_(None))
            .with_entities(models.RiskSignal.student_id)
            .distinct()
            .count()
        )

        weekly_counts: Counter[int] = Counter()
        for (generated_at,) in base_query.with_entities(models.RiskSignal.generated_at).all():
            weekly_counts[generated_at.isocalendar()[1]] += 1
        weekly_risk_trend = [
            {"week": week, "count": count} for week, count in sorted(weekly_counts.items())
        ]

        return {
            "total_documents": total_documents,
            "at_risk_student_count": at_risk_student_count,
            "weekly_risk_trend": weekly_risk_trend,
        }


def _ratio(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AdminDataUnavailable("KPI ratio is invalid")
    ratio = float(value)
    if not 0 <= ratio <= 1:
        raise AdminDataUnavailable("KPI ratio is outside the accepted range")
    return ratio


def _course_sort_key(course: dict[str, Any]) -> tuple[int, int | str, str]:
    semester = course["semester"]
    try:
        return (0, int(semester), course["subject_code"])
    except ValueError:
        return (1, semester, course["subject_code"])
