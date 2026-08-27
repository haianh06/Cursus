"""Mock LMS sync: preview/publish/rollback (mục 6.6, RiskPolicyService pattern).

`preview()` (Checkpoint 2): reads Mock LMS + Cursus's live data, computes a diff,
writes nothing.

`publish()`/`rollback()` (Checkpoint 3) apply the winning values live and persist a
`MockLmsSyncVersion` snapshot. Important scope note worked out while implementing
this checkpoint (not decided upfront, and different from what Checkpoint 2's
docstring assumed): `QaAnswerService`'s citations are built from RAG chunks
(`ChunkRecord.content_source`), not from the `Assignment` table -- syllabus text and
assignment due-dates are two separate data domains in this codebase today. Writing
only to `Assignment.due_date` would never surface in a citation, no matter how
correct the precedence math is. So `publish()` does two things per changed
assignment:
  1. best-effort update of a live `Assignment` row IF one already exists with a
     matching title (rare in practice -- the 36 Mock LMS courses' synthetic
     assignment names don't match any of the hand-authored SSA101/PRF192/CEA201
     demo fixture assignment titles) -- kept for whatever future data actually
     does line up by name.
  2. ingest a small citable fact chunk (`content_source="mock_lms"`) via the same
     Document/DocumentChunk shape `gate2_demo.ingest_official_chunks` already
     uses elsewhere -- THIS is what makes "Mock LMS says the deadline is X"
     something QaAnswerService can actually retrieve and cite. This is the part
     that makes the source-precedence wiring from Checkpoint 2 demonstrable
     end-to-end instead of a diff nobody can ever see reflected in an answer.
"""
from __future__ import annotations

from datetime import datetime

from src.db import models
from src.integrations.mock_lms_client import MockLmsClient
from src.repositories.mock_lms_sync_repository import MockLmsSyncRepository
from src.services.core import provenance as prov
from src.services.core import source_precedence


def _humanize_due_at(due_at_iso: str) -> str:
    try:
        return datetime.fromisoformat(due_at_iso).strftime("%d/%m/%Y")
    except ValueError:
        return due_at_iso


class MockLmsSyncValidationError(ValueError):
    pass


class MockLmsSyncService:
    def __init__(self, db, client: MockLmsClient | None = None) -> None:
        self._db = db
        self._client = client or MockLmsClient()
        self._repo = MockLmsSyncRepository(db)

    def list_history(self) -> list[models.MockLmsSyncVersion]:
        return self._repo.list_history()

    def _live_assignment_due_dates(self, course_id: str) -> dict[str, models.Assignment]:
        """Assignment title (lowercased) -> the live Assignment row, across every
        section of this course. If a course has multiple sections with
        differently-named assignments, each is compared independently; same-named
        assignments across sections collapse to "last one wins" for this diff view
        -- acceptable for Checkpoint 2 (read-only preview), revisit if Checkpoint 3
        needs per-section publish granularity."""
        rows = (
            self._db.query(models.Assignment)
            .join(models.CourseSection, models.Assignment.section_id == models.CourseSection.id)
            .filter(models.CourseSection.course_id == course_id)
            .all()
        )
        return {a.title.strip().lower(): a for a in rows}

    def _previously_synced_due_at(self, *, code: str, assignment_id: str) -> str | None:
        """What the LAST Mock LMS publish recorded for this exact assignment, read
        back from the fact chunk's own metadata (not its free-text `text`, which
        isn't meant to be re-parsed). This is what makes preview()/publish()
        idempotent: without it, a course with no matching `Assignment` row (the
        common case -- see `_live_assignment_due_dates`) would look "new" on
        every single run forever, even right after a successful publish, because
        the only place the fact actually lives is this chunk, not the
        Assignment table."""
        chunk_id = f"mock_lms_{code.lower()}_{assignment_id}"
        chunk = self._db.query(models.DocumentChunk).filter_by(id=chunk_id).first()
        if not chunk:
            return None
        return (chunk.metadata_info or {}).get("due_at")

    def preview(self) -> dict:
        changes: list[dict] = []
        total_evaluated = 0

        for course in self._client.list_courses():
            code = course["course_code"]
            cursus_course = self._db.query(models.Course).filter_by(code=code).first()
            live_by_title = (
                self._live_assignment_due_dates(cursus_course.id) if cursus_course else {}
            )

            for assignment in self._client.list_assignments(code):
                total_evaluated += 1
                mock_due_at = assignment["due_at"]
                live = live_by_title.get(assignment["name"].strip().lower())
                live_due_at = live.due_date.isoformat() if live else None
                if live_due_at is None:
                    live_due_at = self._previously_synced_due_at(
                        code=code, assignment_id=assignment["id"]
                    )

                if live_due_at == mock_due_at:
                    continue

                live_tier = source_precedence.SYLLABUS_ACTIVE if live else None
                winning_tier = (
                    source_precedence.winner(source_precedence.MOCK_LMS, live_tier)
                    if live_tier
                    else source_precedence.MOCK_LMS
                )
                changes.append(
                    {
                        "courseCode": code,
                        "assignmentId": assignment["id"],
                        "assignmentName": assignment["name"],
                        "field": "due_at",
                        "before": live_due_at,
                        "after": mock_due_at,
                        "winningTier": winning_tier,
                        "winningTierLabel": source_precedence.label_for(winning_tier),
                    }
                )

        return {
            "totalEvaluated": total_evaluated,
            "changedCount": len(changes),
            "changes": changes,
        }

    def _sandbox_organization_id(self) -> str | None:
        """Same convention as `real_curriculum_service._sandbox_organization_id`
        -- anchor any course this loader has to create to the shared demo org
        rather than inventing a second one."""
        org = self._db.query(models.Organization).filter_by(slug="cursus-demo").first()
        if org:
            return org.id
        org = self._db.query(models.Organization).first()
        return org.id if org else None

    def _ensure_course_row(self, *, code: str, name: str) -> models.Course:
        course = self._db.query(models.Course).filter_by(code=code).first()
        if course:
            return course
        course = models.Course(
            id=f"course_mock_lms_{code.lower()}",
            code=code,
            name=name,
            description=name,
            organization_id=self._sandbox_organization_id(),
        )
        self._db.add(course)
        self._db.flush()
        return course

    def _ingest_fact_chunk(self, *, course: models.Course, code: str, change: dict) -> None:
        """Upsert one Document (per course, id stable across syncs) + one
        DocumentChunk (per assignment) so the fact is retrievable as
        `content_source="mock_lms"` -- see module docstring."""
        document_id = f"doc_mock_lms_{code.lower()}_assignments"
        document = self._db.query(models.Document).filter_by(id=document_id).first()
        doc_metadata = {
            "source": "mock_lms",
            "course_code": code,
            "provenance": prov.official(document_id, source_version="mock-lms-sync"),
        }
        if not document:
            document = models.Document(
                id=document_id,
                course_id=course.id,
                title=f"Mock LMS — {code} — Assignments",
                file_path=f"mock-lms:/api/v1/courses/{code}/assignments",
                doc_type=models.DocType.SYLLABUS.value,
                version="mock-lms-sync",
                metadata_info=doc_metadata,
            )
            self._db.add(document)
            self._db.flush()
        else:
            document.metadata_info = doc_metadata

        chunk_id = f"mock_lms_{code.lower()}_{change['assignmentId']}"
        text = (
            f"{change['assignmentName']} ({code}): hạn nộp {_humanize_due_at(change['after'])} "
            f"theo dữ liệu đồng bộ mới nhất từ Mock LMS."
        )
        chunk_meta = {
            "course_code": code,
            "doc_type": models.DocType.SYLLABUS.value,
            "doc_title": document.title,
            "document_id": document_id,
            "section": "Mock LMS Assignments",
            "source_label": f"Mock LMS — {code} — {change['assignmentName']}",
            "provenance": prov.official(chunk_id, source_version="mock-lms-sync"),
            # Structured, re-readable value -- see _previously_synced_due_at().
            # `text` is prose for citations, not meant to be re-parsed for this.
            "due_at": change["after"],
        }
        row = self._db.query(models.DocumentChunk).filter_by(id=chunk_id).first()
        if row:
            row.text = text
            row.metadata_info = chunk_meta
        else:
            self._db.add(
                models.DocumentChunk(
                    id=chunk_id,
                    document_id=document.id,
                    chunk_index=0,
                    text=text,
                    token_count=max(1, len(text.split())),
                    metadata_info=chunk_meta,
                )
            )

    def _apply_change(self, change: dict) -> None:
        code = change["courseCode"]
        mock_course = next(
            (c for c in self._client.list_courses() if c["course_code"] == code), None
        )
        course = self._ensure_course_row(
            code=code, name=mock_course["name"] if mock_course else code
        )

        live_by_title = self._live_assignment_due_dates(course.id)
        live = live_by_title.get(change["assignmentName"].strip().lower())
        if live:
            live.due_date = datetime.fromisoformat(change["after"])

        self._ingest_fact_chunk(course=course, code=code, change=change)

    def publish(self, *, reason: str, actor_user_id: str | None) -> models.MockLmsSyncVersion:
        if not reason or not reason.strip():
            raise MockLmsSyncValidationError("A reason is required to publish a Mock LMS sync")

        diff = self.preview()
        for change in diff["changes"]:
            self._apply_change(change)
        self._db.flush()

        return self._repo.create_version(
            payload=diff["changes"],
            reason=reason.strip(),
            created_by=actor_user_id,
        )

    def rollback(
        self, *, target_version: int, reason: str, actor_user_id: str | None
    ) -> models.MockLmsSyncVersion:
        """Re-applies the pre-sync ("before") value of every field changed by
        `target_version`, then records the rollback as a new version -- same
        append-only "re-publish the old snapshot" pattern as RiskPolicy.rollback().
        A change whose original `before` was None (a brand-new fact, nothing to
        revert to) is skipped -- there's no prior fact to restore, so the newest
        chunk is simply left as-is; noted here rather than silently dropped."""
        if not reason or not reason.strip():
            raise MockLmsSyncValidationError("A reason is required to roll back a Mock LMS sync")
        target = self._repo.get_by_version(target_version)
        if target is None:
            raise LookupError(f"Unknown Mock LMS sync version: {target_version}")

        reverted_changes = []
        for change in target.payload:
            if change["before"] is None:
                continue
            reverted = dict(change, after=change["before"], before=change["after"])
            self._apply_change(reverted)
            reverted_changes.append(reverted)
        self._db.flush()

        return self._repo.create_version(
            payload=reverted_changes,
            reason=reason.strip(),
            created_by=actor_user_id,
            rolled_back_from=target_version,
        )
