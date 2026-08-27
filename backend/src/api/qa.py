"""Source-drawer lookup for a citation chip. The Q&A orchestration that used
to live in this file (`POST /qa`) has been removed; this route is a pure
per-chunk lookup unrelated to that orchestration, so it stays put
unchanged."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.security.authorization import require_roles

router = APIRouter(
    prefix="/qa",
    tags=["qa"],
    dependencies=[Depends(require_roles(models.UserRole.STUDENT))],
)


@router.get("/sources/{chunk_id}")
def get_source_chunk(
    chunk_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Open the exact source behind a citation chip (Blueprint §4.3).

    Access is scoped to courses the student is enrolled in, and another
    student's personal upload is never returned.
    """
    from src.repositories.chunk_repository import ChunkRepository

    chunk = db.query(models.DocumentChunk).filter_by(id=chunk_id).first()
    if chunk is None:
        raise HTTPException(status_code=404, detail="Source not found")
    document = db.query(models.Document).filter_by(id=chunk.document_id).first()
    course = (
        db.query(models.Course).filter_by(id=document.course_id).first()
        if document
        else None
    )
    if course is None:
        raise HTTPException(status_code=404, detail="Source not found")

    if not ChunkRepository(db).student_enrolled_in_course(
        student_id=current_user.id, subject_code=course.code
    ):
        raise HTTPException(status_code=404, detail="Source not found")

    doc_meta = document.metadata_info or {}
    chunk_meta = chunk.metadata_info or {}
    source = doc_meta.get("source") or chunk_meta.get("source")
    if source == "student_upload" and doc_meta.get("uploaded_by") != current_user.id:
        raise HTTPException(status_code=404, detail="Source not found")

    # mục 16 data contract: a chunk without explicit provenance metadata must
    # never default to "official_document" — that's only true for real
    # curriculum content. Fabricated demo content (source=mock, see
    # student_mock_data_service.COURSE_DOCUMENTS) must default to "simulated"
    # so this drawer never presents a made-up lecture note as a real syllabus.
    default_source_type = "simulated" if source == "mock" else "official_document"

    return {
        "chunkId": chunk.id,
        "document": document.title,
        "documentId": document.id,
        "courseCode": course.code,
        "version": document.version,
        "section": chunk_meta.get("section"),
        "page": chunk_meta.get("page"),
        "sourceLabel": chunk_meta.get("source_label") or document.title,
        "excerpt": chunk.text,
        "provenance": chunk_meta.get("provenance")
        or {"source_type": default_source_type, "source_id": chunk.id},
    }
