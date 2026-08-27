"""Repository for course document chunks used by Study Assistant retrieval."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db import models


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    text: str
    course_code: str
    doc_title: str
    doc_type: str
    source_label: str
    section: str | None
    chunk_index: int
    # mục 16 data contract: "mock" (student_mock_data_service.COURSE_DOCUMENTS,
    # fabricated syllabus text) vs "curriculum"/"admin_curriculum" (official_
    # document provenance) vs "student_upload". Consumers (QaAnswerService)
    # use this to disclaim answers grounded only in fabricated content instead
    # of presenting them as "theo syllabus".
    content_source: str = "curriculum"


class ChunkRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def student_enrolled_in_course(self, *, student_id: str, subject_code: str) -> bool:
        code = subject_code.strip().upper()
        return (
            self._db.query(models.Enrollment.id)
            .join(models.CourseSection)
            .join(models.Course)
            .filter(
                models.Enrollment.student_id == student_id,
                # Only count ENROLLED status. Without this filter, a student
                # marked DROPPED can still access course material (this gate),
                # but cannot be bound to a section (conversation_repository
                # requires ENROLLED), creating an unbound conversation visible
                # to all instructors — a cross-instructor leak.
                models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
                # Case-insensitive: some real catalog codes have a lowercase
                # suffix (e.g. "ENW493c", "SWE202c" — a genuine FPT naming
                # convention, not a typo). Course.code is stored with that
                # exact casing, but every caller here normalizes the
                # incoming subject_code to uppercase first — comparing
                # func.upper(Course.code) keeps both sides on equal footing
                # instead of a plain `==` that silently matched 0 rows for
                # any lowercase-suffix course (found via
                # tests/test_services/test_real_curriculum_retrieval.py).
                func.upper(models.Course.code) == code,
            )
            .first()
            is not None
        )

    def list_chunks_for_course(
        self,
        *,
        subject_code: str,
        student_id: str | None = None,
    ) -> list[ChunkRecord]:
        """Return curriculum chunks plus the student's own uploads for the course."""
        code = subject_code.strip().upper()
        rows = (
            self._db.query(models.DocumentChunk, models.Document, models.Course)
            .join(models.Document, models.Document.id == models.DocumentChunk.document_id)
            .join(models.Course, models.Course.id == models.Document.course_id)
            .filter(func.upper(models.Course.code) == code)
            .order_by(models.Document.title, models.DocumentChunk.chunk_index)
            .all()
        )
        results: list[ChunkRecord] = []
        for chunk, document, course in rows:
            doc_meta = document.metadata_info or {}
            chunk_meta = chunk.metadata_info or {}
            source = doc_meta.get("source") or chunk_meta.get("source") or "curriculum"
            uploaded_by = doc_meta.get("uploaded_by") or chunk_meta.get("uploaded_by")

            # Admin curriculum follows an explicit editorial lifecycle. Draft
            # and archived versions are retained for validation/rollback, but
            # only a published version may enter learner retrieval or practice
            # generation.
            if source == "admin_curriculum" and document.publication_status != "PUBLISHED":
                continue

            # Hide other students' personal uploads from this student's RAG context.
            if source == "student_upload" and (
                not student_id or uploaded_by != student_id
            ):
                continue

            section = chunk_meta.get("section") or _heading_from_text(chunk.text)
            source_label = chunk_meta.get("source_label") or (
                f"{document.title} — {section}" if section else document.title
            )
            results.append(
                ChunkRecord(
                    chunk_id=chunk.id,
                    text=chunk.text,
                    course_code=course.code,
                    doc_title=chunk_meta.get("doc_title") or document.title,
                    doc_type=str(chunk_meta.get("doc_type") or document.doc_type),
                    source_label=source_label,
                    section=section or None,
                    chunk_index=chunk.chunk_index,
                    content_source=source,
                )
            )
        return results


def _heading_from_text(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""
