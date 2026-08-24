from __future__ import annotations

import hashlib
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.db import models
from src.services.rag.document_content_validator import scan_for_suspicious_patterns

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_UPLOADS_ROOT = ROOT / "data" / "admin_uploads"
ALLOWED_EXTENSIONS = frozenset({".md", ".txt"})
MAX_UPLOAD_BYTES = 2 * 1024 * 1024
MAX_CHUNKS = 80


@dataclass(frozen=True)
class ValidatedDocument:
    filename: str
    title: str
    text: str
    suffix: str


def validate_admin_document(filename: str, content: bytes) -> ValidatedDocument:
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
    return ValidatedDocument(
        filename=safe_name,
        title=Path(safe_name).stem,
        text=text,
        suffix=suffix,
    )


class AdminDocumentIngestService:
    def __init__(self, db: Session, *, uploads_root: Path = DEFAULT_UPLOADS_ROOT) -> None:
        self._db = db
        self._uploads_root = uploads_root

    def list_documents(self, course_code: str) -> list[dict]:
        course = self._course(course_code)
        documents = self._db.query(models.Document).filter_by(course_id=course.id).order_by(models.Document.title).all()
        return [
            self._serialize(document)
            for document in documents
            if (document.metadata_info or {}).get("source") == "admin_curriculum"
        ]

    def ingest_new(
        self,
        *,
        course_code: str,
        filename: str,
        content: bytes,
        actor_user_id: str | None,
    ) -> dict:
        course = self._course(course_code)
        validated = validate_admin_document(filename, content)
        paragraphs = _validated_paragraphs(validated.text)
        _validate_chunk_limit(paragraphs)
        content_flags = _scan_and_log(validated.text, course_code=course.code, actor_user_id=actor_user_id)
        document_id = f"doc_admin_{uuid.uuid4().hex}"
        path = self._write(document_id, validated)
        checksum = hashlib.sha256(validated.text.encode("utf-8")).hexdigest()
        try:
            document = models.Document(
                id=document_id,
                course_id=course.id,
                title=validated.title,
                file_path=self._stored_path(path),
                doc_type=models.DocType.SYLLABUS.value,
                version="1",
                version_group=document_id,
                checksum=checksum,
                provenance={"course_code": course.code},
                metadata_info={
                    "source": "admin_curriculum",
                    "uploaded_by": actor_user_id,
                    "course_code": course.code,
                    "original_filename": validated.filename,
                    "content_flagged": bool(content_flags),
                    "content_flags": content_flags,
                },
            )
            self._db.add(document)
            self._db.flush()
            chunk_count = self._chunk(document, paragraphs, course.code)
        except Exception:
            _unlink_file(path)
            raise
        result = self._serialize(document)
        result["chunk_count"] = chunk_count
        result["_created_path"] = path
        return result

    def replace(
        self,
        *,
        document_id: str,
        filename: str,
        content: bytes,
        actor_user_id: str | None,
    ) -> dict:
        document = self._admin_document(document_id)
        course = self._db.get(models.Course, document.course_id)
        validated = validate_admin_document(filename, content)
        paragraphs = _validated_paragraphs(validated.text)
        _validate_chunk_limit(paragraphs)
        content_flags = _scan_and_log(validated.text, course_code=course.code, actor_user_id=actor_user_id)
        old_path = self._absolute_path(document.file_path)
        # Always stage replacements under a fresh path so a rollback cannot
        # overwrite the currently committed file. The runner removes the old
        # path only after the database transaction commits.
        new_path = self._write(f"{document.id}_replacement_{uuid.uuid4().hex}", validated)
        try:
            self._db.query(models.DocumentChunk).filter_by(document_id=document.id).delete(synchronize_session=False)
            document.title = validated.title
            document.file_path = self._stored_path(new_path)
            document.version = str(int(document.version or "0") + 1)
            document.checksum = hashlib.sha256(validated.text.encode("utf-8")).hexdigest()
            document.provenance = {**(document.provenance or {}), "course_code": course.code}
            # Content changed -- any prior validation no longer describes
            # what's on disk now. Must be re-validated before it can publish.
            document.validated_at = None
            document.validated_by = None
            document.metadata_info = {
                **(document.metadata_info or {}),
                "uploaded_by": actor_user_id,
                "original_filename": validated.filename,
                "content_flagged": bool(content_flags),
                "content_flags": content_flags,
            }
            chunk_count = self._chunk(document, paragraphs, course.code)
        except Exception:
            _unlink_file(new_path)
            raise
        result = self._serialize(document)
        result["chunk_count"] = chunk_count
        result["_created_path"] = new_path
        result["_cleanup_path"] = old_path if old_path != new_path else None
        return result

    def delete(self, *, document_id: str, actor_user_id: str | None) -> Path:
        del actor_user_id
        document = self._admin_document(document_id)
        path = self._absolute_path(document.file_path)
        self._db.query(models.DocumentChunk).filter_by(document_id=document.id).delete(synchronize_session=False)
        self._db.delete(document)
        self._db.flush()
        return path

    def _course(self, course_code: str) -> models.Course:
        code = course_code.strip().upper()
        # Case-insensitive — some real catalog codes have a lowercase suffix
        # (e.g. "ENW493c"); see chunk_repository.py for the full explanation.
        course = self._db.query(models.Course).filter(func.upper(models.Course.code) == code).first()
        if course is None:
            raise LookupError(f"Course not found: {code}")
        return course

    def _admin_document(self, document_id: str) -> models.Document:
        document = self._db.get(models.Document, document_id)
        if document is None:
            raise LookupError("Document not found")
        if (document.metadata_info or {}).get("source") != "admin_curriculum":
            raise PermissionError("Only Admin curriculum documents can be changed")
        return document

    def _write(self, document_id: str, validated: ValidatedDocument) -> Path:
        destination = self._uploads_root / f"{document_id}_{validated.filename}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        # newline="" disables universal-newline translation: on Windows,
        # write_text() would otherwise turn "\n" into "\r\n" on disk, which
        # would silently break the sha256 checksum computed from the
        # in-memory (untranslated) text.
        destination.write_text(validated.text, encoding="utf-8", newline="")
        return destination

    def _stored_path(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
        except ValueError:
            return str(path.resolve())

    def _absolute_path(self, stored_path: str) -> Path:
        path = Path(stored_path)
        return path if path.is_absolute() else ROOT / path

    def read_source_bytes(self, document: models.Document) -> bytes | None:
        """Read the file this Document's `file_path` points at. Returns
        None (not an exception) on any I/O error -- callers use this for
        the `readable_file`/`checksum_matches_file` validate() checks,
        where "can't read it" is itself the check result, not a crash."""
        try:
            return self._absolute_path(document.file_path).read_bytes()
        except OSError:
            return None

    def _chunk(self, document: models.Document, paragraphs: list[str], course_code: str) -> int:
        for index, paragraph in enumerate(paragraphs):
            section = _section_heading(paragraph)
            self._db.add(
                models.DocumentChunk(
                    id=f"chunk_admin_{document.id}_{index}",
                    document_id=document.id,
                    chunk_index=index,
                    text=paragraph,
                    token_count=max(1, len(paragraph.split())),
                    metadata_info={
                        "course_code": course_code,
                        "doc_type": document.doc_type,
                        "doc_title": document.title,
                        "section": section or None,
                        "source_label": f"{document.title} — {section}" if section else document.title,
                        "source": "admin_curriculum",
                    },
                )
            )
        self._db.flush()
        return len(paragraphs)

    def _serialize(self, document: models.Document) -> dict:
        meta = document.metadata_info or {}
        return {
            "id": document.id,
            "course_code": meta.get("course_code"),
            "title": document.title,
            "filename": meta.get("original_filename"),
            "version": document.version,
            "chunk_count": self._db.query(models.DocumentChunk).filter_by(document_id=document.id).count(),
            "content_flagged": bool(meta.get("content_flagged")),
        }


def _safe_filename(filename: str) -> str:
    name = Path(filename or "document.txt").name
    cleaned = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE).strip("._")
    return cleaned or "document.txt"


def _section_heading(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


def _validated_paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _scan_and_log(text: str, *, course_code: str, actor_user_id: str | None) -> list[dict]:
    """LLM08 (mục 14.2) -- flag, never reject: see document_content_validator.py
    docstring for why an outright reject risks false positives on legitimate
    academic content."""
    flags = scan_for_suspicious_patterns(text)
    if flags:
        logger.warning(
            "document_content_flagged source=admin_curriculum course=%s actor=%s patterns=%s",
            course_code,
            actor_user_id,
            [flag["pattern"] for flag in flags],
        )
    return flags


def _validate_chunk_limit(paragraphs: list[str]) -> None:
    if len(paragraphs) > MAX_CHUNKS:
        raise ValueError(
            f"Document contains {len(paragraphs)} paragraphs; maximum supported is "
            f"{MAX_CHUNKS} paragraphs. Split the document and upload it again."
        )


def _unlink_file(path: Path) -> None:
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
