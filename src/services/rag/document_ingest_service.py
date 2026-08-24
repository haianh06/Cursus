"""Student personal document upload + chunking for Study Assistant RAG."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from src.db import models
from src.services.rag.document_content_validator import scan_for_suspicious_patterns

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
UPLOADS_ROOT = ROOT / "data" / "uploads"

ALLOWED_EXTENSIONS = frozenset({".md", ".txt"})
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_CHUNKS = 40


class DocumentIngestService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def upload_for_student(
        self,
        *,
        student_id: str,
        course_id: str,
        filename: str,
        content: bytes,
        title: str | None = None,
    ) -> dict:
        course = self._db.query(models.Course).filter_by(id=course_id).first()
        if not course:
            raise LookupError("Course not found")

        safe_name = _safe_filename(filename)
        suffix = Path(safe_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError("Only .md and .txt files are supported")
        if not content:
            raise ValueError("Uploaded file is empty")
        if len(content) > MAX_UPLOAD_BYTES:
            raise ValueError("File exceeds 2MB limit")

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("File must be UTF-8 text") from exc

        text = text.strip()
        if not text:
            raise ValueError("Uploaded file has no readable text")

        # LLM08 (mục 14.2) -- flag, never reject: a false positive here would
        # block a student's own legitimate notes over a coincidental phrase
        # match. See document_content_validator.py docstring.
        content_flags = scan_for_suspicious_patterns(text)
        if content_flags:
            logger.warning(
                "document_content_flagged source=student_upload student=%s course=%s patterns=%s",
                student_id,
                course_id,
                [flag["pattern"] for flag in content_flags],
            )

        document_id = f"doc_up_{uuid.uuid4().hex[:12]}"
        dest_dir = UPLOADS_ROOT / student_id / course_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / f"{document_id}_{safe_name}"
        dest_path.write_text(text, encoding="utf-8")
        relative_path = str(dest_path.relative_to(ROOT)).replace("\\", "/")

        doc_title = (title or Path(safe_name).stem).strip() or safe_name
        document = models.Document(
            id=document_id,
            course_id=course.id,
            title=doc_title,
            file_path=relative_path,
            doc_type=models.DocType.NOTES.value,
            version="1.0",
            metadata_info={
                "source": "student_upload",
                "uploaded_by": student_id,
                "course_code": course.code,
                "original_filename": safe_name,
                "content_flagged": bool(content_flags),
                "content_flags": content_flags,
            },
        )
        self._db.add(document)
        self._db.flush()

        chunk_count = self._chunk_document(
            document=document,
            text=text,
            course_code=course.code,
            student_id=student_id,
        )
        self._db.commit()
        self._db.refresh(document)

        logger.info(
            "student_upload student=%s course=%s doc=%s chunks=%s",
            student_id,
            course.code,
            document.id,
            chunk_count,
        )
        return {
            "id": document.id,
            "title": document.title,
            "docType": document.doc_type,
            "filePath": document.file_path,
            "chunkCount": chunk_count,
            "source": "student_upload",
            "uploadedBy": student_id,
            "contentFlagged": bool(content_flags),
        }

    def delete_for_student(self, *, student_id: str, document_id: str) -> None:
        document = (
            self._db.query(models.Document).filter_by(id=document_id).first()
        )
        if not document:
            raise LookupError("Document not found")
        meta = document.metadata_info or {}
        if meta.get("source") != "student_upload" or meta.get("uploaded_by") != student_id:
            raise PermissionError("You can only delete your own uploaded documents")

        (
            self._db.query(models.DocumentChunk)
            .filter_by(document_id=document.id)
            .delete(synchronize_session=False)
        )
        file_path = ROOT / document.file_path
        self._db.delete(document)
        self._db.commit()

        if file_path.exists() and file_path.is_file():
            try:
                file_path.unlink()
            except OSError:
                logger.warning("Failed to delete upload file %s", file_path)

    def _chunk_document(
        self,
        *,
        document: models.Document,
        text: str,
        course_code: str,
        student_id: str,
    ) -> int:
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
        if not paragraphs:
            paragraphs = [text]

        count = 0
        for index, paragraph in enumerate(paragraphs[:MAX_CHUNKS]):
            section = _section_heading(paragraph)
            source_label = (
                f"{document.title} — {section}" if section else document.title
            )
            self._db.add(
                models.DocumentChunk(
                    id=f"chunk_up_{document.id}_{index}",
                    document_id=document.id,
                    chunk_index=index,
                    text=paragraph,
                    token_count=max(1, len(paragraph.split())),
                    metadata_info={
                        "course_code": course_code,
                        "doc_type": document.doc_type,
                        "doc_title": document.title,
                        "section": section or None,
                        "source_label": source_label,
                        "source": "student_upload",
                        "uploaded_by": student_id,
                    },
                )
            )
            count += 1
        self._db.flush()
        return count


def _safe_filename(filename: str) -> str:
    name = Path(filename or "notes.txt").name
    cleaned = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE).strip("._")
    return cleaned or "notes.txt"


def _section_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""
