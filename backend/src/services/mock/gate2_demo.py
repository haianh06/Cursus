"""Canonical Gate-2 demo state (``gate2_demo_v1``).

This is the ONE place the Plan → Do → Reflect → Next-Plan demo story and the
Do → Alert → Intervention story are defined. Frontend never invents its own
copy; it reads this through the API.

What is real vs. what is made up (Data Contract §3 — this distinction is the
whole point of the module):

* The 72 SSA101 syllabus chunks in ``docs/planning/v2/data/chunks_SSA101.json``
  are **official_document**. They are ingested verbatim, keeping their
  canonical ``chunk_id`` (``SSA101-overview``, ``SSA101-session-13`` ...), so a
  citation chip can open the exact source text.
* "SSA101 Group Project — Part 1", its Sunday 23:59 deadline and its four
  deliverables are **simulated**. The syllabus only proves a Part-1 project
  exists in sessions 13–15 (see ``PART1_SOURCE_REFS``); it does NOT prove the
  four deliverables. The UI must therefore show this assignment with a demo
  badge and must never cite it "theo syllabus".
* Task decomposition and every duration is **ai_suggested** ("Ước tính của
  Curi").
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from src.db import models
from src.services.academic.timetable_service import monday_of
from src.services.core import provenance as prov

_UNSET = object()
_CLASS_CACHE = None

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[4]
SSA101_CHUNKS_PATH = ROOT / "docs" / "planning" / "v2" / "data" / "chunks_SSA101.json"

FIXTURE_VERSION = prov.FIXTURE_VERSION

# ── Identity of the single Gate-2 class ──────────────────────────────────
CLASS_SECTION_ID = "section_gate2_ssa101_se_k20"
CLASS_SECTION_CODE = "SE-K20"
CLASS_TERM = "Fall2026"
SSA101_CODE = "SSA101"
SSA101_COURSE_ID = "course_mock_ssa101"

SSA101_DOC_ID = "doc_ssa101_syllabus_13785"
SSA101_DOC_TITLE = "Syllabus SSA101 — Kỹ năng học thuật"
SSA101_SYLLABUS_VERSION = "13785-2025-11-27"

# The hosted Cursus Uni showcase is seeded from real course/syllabus records.
# It must never be mixed with the older, self-provisioning Gate-2 SSA101
# fixture that is still useful for isolated local development.
HOSTED_DEMO_ORG_SLUG = "cursus-demo"

# ── Demo personas (Blueprint §7) ─────────────────────────────────────────
# Đăng is whoever signs in through the Student demo role; the seed only fixes
# the display name so the story reads consistently on screen.
DEMO_STUDENT_EMAIL = "demo.student@cursusdemo.local"
DEMO_INSTRUCTOR_EMAIL = "demo.instructor@cursusdemo.local"
DEMO_ADMIN_EMAIL = "admin@demo.com"

PERSONA_NAMES = {
    DEMO_STUDENT_EMAIL: "Trịnh Hải Đăng",
    DEMO_INSTRUCTOR_EMAIL: "Cô Hương",
    DEMO_ADMIN_EMAIL: "Thầy Nam",
}

# Second demo student — exists only to produce the lecturer alert.
MINH_USER_ID = "stu_minh_demo"
MINH_EMAIL = "minh.demo@cursusdemo.local"
MINH_NAME = "Nguyễn Minh"

# ── The one assignment that runs through the whole demo ──────────────────
PART1_ASSIGNMENT_ID = "asg_ssa101_part1_demo"
PART1_TITLE = "SSA101 Group Project — Part 1"
PART1_DELIVERABLES = (
    "Problem statement",
    "Stakeholder analysis",
    "Functional requirements",
    "Draft use-case diagram",
)
# These prove only that a Part-1 project appears on the schedule.
PART1_SOURCE_REFS = (
    "SSA101-session-13",
    "SSA101-session-14",
    "SSA101-session-15",
)
PART1_DESCRIPTION = (
    "Nhóm hoàn thành Part 1 của Group Project: xác định vấn đề, phân tích "
    "bên liên quan, liệt kê yêu cầu chức năng và phác thảo sơ đồ use-case. "
    "Nộp trước 23:59 Chủ nhật."
)


@dataclass(frozen=True)
class TaskTemplate:
    """One row of the Blueprint §7 initial-plan table."""

    key: str
    title: str
    estimated_minutes: int
    weekday: int  # 0 = Monday
    priority: str
    deliverable: str | None
    source_refs: tuple[str, ...]
    source_fact: str | None
    suggestion_reason: str


# Blueprint §7 "Kế hoạch ban đầu" — 6 tasks, 420 minutes total.
PART1_TASK_TEMPLATES: tuple[TaskTemplate, ...] = (
    TaskTemplate(
        key="read_rubric",
        title="Đọc rubric + viết nháp problem statement",
        estimated_minutes=45,
        weekday=0,
        priority="HIGH",
        deliverable="Problem statement",
        source_refs=("SSA101-session-13",),
        source_fact=(
            "Session 13 — Part1 Project - Topic selection and planning "
            "(tài liệu: Project Guidelines)"
        ),
        suggestion_reason=(
            "Đây là nền tảng cho mọi phần phân tích tiếp theo; làm sớm để phát "
            "hiện hiểu sai đề ngay đầu tuần."
        ),
    ),
    TaskTemplate(
        key="stakeholder",
        title="Lập bảng stakeholder analysis",
        estimated_minutes=90,
        weekday=2,
        priority="HIGH",
        deliverable="Stakeholder analysis",
        source_refs=("SSA101-session-14",),
        source_fact="Session 14 — Part1 Project - Research and preparation",
        suggestion_reason=(
            "Cần danh sách bên liên quan trước khi viết yêu cầu chức năng."
        ),
    ),
    TaskTemplate(
        key="requirements",
        title="Viết functional requirements",
        estimated_minutes=90,
        weekday=2,
        priority="HIGH",
        deliverable="Functional requirements",
        source_refs=("SSA101-session-14", "SSA101-session-15"),
        source_fact="Session 14–15 — Part1 Project - Research and preparation",
        suggestion_reason=(
            "Yêu cầu chức năng suy ra trực tiếp từ nhu cầu của các stakeholder "
            "vừa liệt kê."
        ),
    ),
    TaskTemplate(
        key="use_case",
        title="Phác thảo sơ đồ use-case",
        estimated_minutes=120,
        weekday=5,
        priority="MEDIUM",
        deliverable="Draft use-case diagram",
        source_refs=("SSA101-session-15",),
        source_fact="Session 15 — Part1 Project - Research and preparation",
        suggestion_reason=(
            "Sơ đồ là phần tốn thời gian nhất; đặt vào cuối tuần khi đã có đủ "
            "yêu cầu chức năng."
        ),
    ),
    TaskTemplate(
        key="review_rubric",
        title="Rà soát toàn bộ bài theo rubric",
        estimated_minutes=60,
        weekday=5,
        priority="MEDIUM",
        deliverable=None,
        source_refs=("SSA101-session-13",),
        source_fact="Session 13 — Project Guidelines (rubric)",
        suggestion_reason="Đối chiếu rubric trước khi nộp để không mất điểm hình thức.",
    ),
    TaskTemplate(
        key="submit",
        title="Nộp bài Part 1",
        estimated_minutes=15,
        weekday=6,
        priority="HIGH",
        deliverable=None,
        source_refs=(),
        source_fact=None,
        suggestion_reason="Chừa Chủ nhật làm buffer phòng khi phần trước bị trễ.",
    ),
)

# Blueprint §7 "Kết quả demo" — used by the demo fast-forward so a rehearsal
# does not need 6 manual clicks to reach the Reflect step.
DEMO_OUTCOMES: dict[str, dict] = {
    "read_rubric": {"status": "COMPLETED", "actual_minutes": 55},
    "stakeholder": {"status": "COMPLETED", "actual_minutes": 100},
    "requirements": {
        "status": "DEFERRED",
        "reason_code": "underestimated_time",
        "progress": 0.4,
    },
    "use_case": {"status": "DEFERRED", "reason_code": "underestimated_time"},
    "review_rubric": {"status": "TODO"},
    "submit": {"status": "TODO"},
}

# Minh's story: completion 25%, 3 overdue, deadline in 36h → risk score 5.
MINH_TASK_TEMPLATES: tuple[tuple[str, int, int, str], ...] = (
    ("Đọc Project Guidelines Part 1", 45, -5, "COMPLETED"),
    ("Lập bảng stakeholder analysis", 90, -4, "TODO"),
    ("Viết functional requirements", 90, -3, "TODO"),
    ("Phác thảo sơ đồ use-case", 120, -2, "TODO"),
)

DEFER_REASON_CODES: tuple[tuple[str, str], ...] = (
    ("underestimated_time", "Ước tính thiếu thời gian"),
    ("blocked_by_dependency", "Chờ phần việc khác xong trước"),
    ("low_energy", "Không đủ sức tập trung hôm nay"),
    ("schedule_conflict", "Trùng lịch học/việc khác"),
    ("need_help", "Cần hỏi giảng viên/nhóm trước"),
)


def deliverables_payload() -> list[dict]:
    """The four deliverables, each explicitly flagged as simulated."""
    return [
        {
            "id": f"del_{index}",
            "title": title,
            "provenance": prov.simulated(f"{PART1_ASSIGNMENT_ID}:deliverable:{index}"),
        }
        for index, title in enumerate(PART1_DELIVERABLES, start=1)
    ]


def load_official_chunks(subject_code: str, *, fallback_title: str = "") -> list[dict]:
    """Read parsed syllabus chunks for any course from
    ``docs/planning/v2/data/chunks_<CODE>.json`` (produced by
    ``docs/planning/v2/scripts/flm_parser.py``). Raw file stays immutable."""
    path = ROOT / "docs" / "planning" / "v2" / "data" / f"chunks_{subject_code}.json"
    if not path.exists():
        logger.warning("%s chunk file missing at %s", subject_code, path)
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    chunks = payload.get("chunks") or []
    normalized: list[dict] = []
    for index, chunk in enumerate(chunks):
        chunk_id = str(chunk.get("chunk_id") or "").strip()
        text = str(chunk.get("text") or "").strip()
        if not chunk_id or not text:
            continue
        normalized.append(
            {
                "chunk_id": chunk_id,
                "text": text,
                "section": (chunk.get("section") or "").strip() or None,
                "source_label": (chunk.get("source_label") or "").strip()
                or f"{fallback_title or subject_code} — {chunk_id}",
                "chunk_index": index,
            }
        )
    return normalized


def load_ssa101_chunks() -> list[dict]:
    """Back-compat wrapper (imported directly by eval/run_eval.py and
    tests/test_services/test_gate2_services.py) — read the official SSA101
    syllabus chunks."""
    return load_official_chunks(SSA101_CODE, fallback_title=SSA101_DOC_TITLE)


def ingest_official_chunks(
    db: Session,
    *,
    course: models.Course,
    subject_code: str,
    document_id: str,
    title: str,
    version: str,
    chunks: list[dict],
) -> int:
    """Upsert a course's official syllabus chunks as Document + DocumentChunk
    rows with ``official_document`` provenance, keeping canonical chunk ids
    so citation chips open the exact source text. Generalized from the
    SSA101-only version of this logic; safe to call on every request — skips
    the per-row sync once the id set already matches (cheap for a pooled
    remote Postgres)."""
    if not chunks:
        return 0

    document = db.query(models.Document).filter_by(id=document_id).first()
    metadata = {
        "source": "curriculum",
        "course_code": subject_code,
        "document_id": document_id,
        "syllabus_version": version,
        "provenance": prov.official(document_id),
    }
    if not document:
        document = models.Document(
            id=document_id,
            course_id=course.id,
            title=title,
            file_path=f"docs/planning/v2/data/chunks_{subject_code}.json",
            doc_type=models.DocType.SYLLABUS.value,
            version=version,
            metadata_info=metadata,
        )
        db.add(document)
        db.flush()
    else:
        document.course_id = course.id
        document.title = title
        document.metadata_info = metadata

    existing_ids = {
        row[0]
        for row in db.query(models.DocumentChunk.id)
        .filter_by(document_id=document.id)
        .all()
    }
    wanted_ids = {chunk["chunk_id"] for chunk in chunks}

    if existing_ids == wanted_ids:
        return len(chunks)

    for stale_id in existing_ids - wanted_ids:
        stale = db.query(models.DocumentChunk).filter_by(id=stale_id).first()
        if stale:
            db.delete(stale)

    for chunk in chunks:
        meta = {
            "course_code": subject_code,
            "doc_type": models.DocType.SYLLABUS.value,
            "doc_title": title,
            "document_id": document_id,
            "section": chunk["section"],
            "source_label": chunk["source_label"],
            "provenance": prov.official(chunk["chunk_id"]),
        }
        row = db.query(models.DocumentChunk).filter_by(id=chunk["chunk_id"]).first()
        if row:
            row.document_id = document.id
            row.chunk_index = chunk["chunk_index"]
            row.text = chunk["text"]
            row.token_count = max(1, len(chunk["text"].split()))
            row.metadata_info = meta
        else:
            db.add(
                models.DocumentChunk(
                    id=chunk["chunk_id"],
                    document_id=document.id,
                    chunk_index=chunk["chunk_index"],
                    text=chunk["text"],
                    token_count=max(1, len(chunk["text"].split())),
                    metadata_info=meta,
                )
            )
    db.flush()
    return len(chunks)


def sunday_2359(week_start: date) -> datetime:
    """23:59 of the Sunday closing the week that starts on ``week_start``."""
    return datetime.combine(week_start + timedelta(days=6), time(23, 59))


class Gate2DemoService:
    """Idempotent seed/reset for ``gate2_demo_v1``.

    Every method is safe to call repeatedly — the demo can be reset before
    each rehearsal without ever dropping a table.
    """

    def __init__(self, db: Session) -> None:
        self._db = db
        self._org_id_cache: str | None | object = _UNSET

    def _demo_organization_id(self) -> str | None:
        """Organization new demo rows (course/instructor) get scoped to.

        Gate 2 is single-org ("một tổ chức demo") so any already-seeded user
        or organization is the right answer; there is deliberately no
        hardcoded org id here since seed_demo_accounts.py / provisioning
        scripts decide which organization is "the" demo org.
        """
        if self._org_id_cache is not _UNSET:
            return self._org_id_cache  # type: ignore[return-value]
        user = (
            self._db.query(models.User)
            .filter(models.User.organization_id.isnot(None))
            .order_by(models.User.created_at.asc())
            .first()
        )
        org_id = user.organization_id if user else None
        if org_id is None:
            org = self._db.query(models.Organization).first()
            org_id = org.id if org else None
        self._org_id_cache = org_id
        return org_id

    # ── public entry points ──────────────────────────────────────────
    def ensure_class(self, *, week_start: date | None = None) -> dict:
        """Course + official sources + shared class section + assignment.

        Called on every student/instructor read path, so returning students
        pick up content fixes without re-registering.
        """
        global _CLASS_CACHE
        monday = monday_of(week_start or date.today())

        if _CLASS_CACHE is not None:
            return {**_CLASS_CACHE, "weekStart": monday.isoformat()}

        course = self._ensure_course()
        chunk_count = self._ensure_official_sources(course)
        instructor_id = self._ensure_instructor()
        section = self._ensure_class_section(course, instructor_id)
        assignment = self._ensure_part1_assignment(section, monday)
        # Bug fixed 21/08: this used to be `flush()` only. `get_db()` never
        # auto-commits at request end (src/db/connection.py), and 2 of this
        # method's 3 call sites (instructor.py's `_sections_for`, demo.py's
        # ensure-class endpoint) never commit afterward either — so a
        # flush-only write here was silently rolled back on every read-only
        # request that happened to be the first to populate `_CLASS_CACHE`
        # in a given process. Root-caused via a returning demo student whose
        # SSA101 syllabus Document had 0 rows despite this reporting
        # `officialChunks: 72` every time.
        self._db.commit()

        _CLASS_CACHE = {
            "fixtureVersion": FIXTURE_VERSION,
            "courseId": course.id,
            "sectionId": section.id,
            "assignmentId": assignment.id,
            "officialChunks": chunk_count,
        }
        return {**_CLASS_CACHE, "weekStart": monday.isoformat()}

    def reset(self, *, student_id: str, week_start: date | None = None) -> dict:
        """Return the demo to its opening state for ``student_id``.

        Deletes only Gate-2 owned rows (this student's SSA101 plans/tasks/
        events/reflections/risk rows and Minh's), never other people's data.
        """
        global _CLASS_CACHE
        _CLASS_CACHE = None
        monday = monday_of(week_start or date.today())
        info = self.ensure_class(week_start=monday)

        self._rename_persona(student_id)
        self._clear_student_plan_state(student_id)
        self._clear_student_plan_state(MINH_USER_ID)
        self._enroll(student_id)

        minh = self._ensure_minh()
        self._enroll(minh.id)
        self._seed_minh_week(monday)
        self._db.commit()

        logger.info("gate2_demo_reset student=%s week_start=%s", student_id, monday)
        return {
            **info,
            "reset": True,
            "students": [student_id, MINH_USER_ID],
        }

    def ensure_student(self, student_id: str) -> dict:
        """Light-weight per-request hook: class exists + student enrolled."""
        student = self._db.query(models.User).filter_by(id=student_id).first()
        if (
            student is not None
            and student.organization is not None
            and student.organization.slug == HOSTED_DEMO_ORG_SLUG
        ):
            return {
                "fixtureVersion": "cursus_uni_seed_v1",
                "courseId": "course_mock_cea201",
                "sectionId": "sec_CEA201_SE2001",
                "assignmentId": "asg_w3_sec_CEA201_SE2001",
                "officialChunks": 0,
            }

        existing_enrollment = (
            self._db.query(models.Enrollment.id)
            .filter_by(student_id=student_id, section_id=CLASS_SECTION_ID)
            .first()
        )
        if existing_enrollment:
            return self.ensure_class()

        info = self.ensure_class()
        self._enroll(student_id)
        minh = self._ensure_minh()
        self._enroll(minh.id)
        self._db.commit()
        return info

    # ── course / sources ─────────────────────────────────────────────
    def _ensure_course(self) -> models.Course:
        course = self._db.query(models.Course).filter_by(code=SSA101_CODE).first()
        description = (
            "Kỹ năng học thuật (Academic Skills) — 3 tín chỉ. Học phần rèn "
            "thói quen học tập, tư duy phản biện, giao tiếp học thuật và sử "
            "dụng AI có trách nhiệm."
        )
        if not course:
            course = models.Course(
                id=SSA101_COURSE_ID,
                code=SSA101_CODE,
                name="Kỹ năng học thuật / Academic Skills",
                description=description,
                syllabus=f"Syllabus SSA101 · version {SSA101_SYLLABUS_VERSION}",
                organization_id=self._demo_organization_id(),
            )
            self._db.add(course)
            self._db.flush()
        else:
            course.description = description
            course.syllabus = f"Syllabus SSA101 · version {SSA101_SYLLABUS_VERSION}"
        return course

    def _ensure_official_sources(self, course: models.Course) -> int:
        """Ingest the 72 official SSA101 chunks, keeping canonical chunk ids.

        Runs on every student/instructor read (see ensure_class's
        docstring) so returning users pick up fixture edits without a
        manual re-seed — cheap because ingest_official_chunks() skips the
        per-row sync once the id set already matches.
        """
        return ingest_official_chunks(
            self._db,
            course=course,
            subject_code=SSA101_CODE,
            document_id=SSA101_DOC_ID,
            title=SSA101_DOC_TITLE,
            version=SSA101_SYLLABUS_VERSION,
            chunks=load_ssa101_chunks(),
        )

    # ── people ───────────────────────────────────────────────────────
    def _ensure_instructor(self) -> str:
        """The ONE canonical demo instructor account (decided 22/08, after a
        real incident): `DEMO_INSTRUCTOR_EMAIL` is the single source of
        truth, always. This used to fall back to "any INSTRUCTOR/ADMIN row,
        `.first()`" when that exact email wasn't found, and separately, the
        very-last-resort creation branch made a NEW row under a *different*
        email (`huong.demo@cursusdemo.local`) than the one being searched
        for -- so a second call still wouldn't match `DEMO_INSTRUCTOR_EMAIL`
        and would instead re-find whatever `.first()` on
        INSTRUCTOR/ADMIN happened to return that time, with no guarantee
        it's the same row as last time. `ensure_class()` (below) then
        unconditionally re-assigns the SSA101 section to whatever this
        function returns on every process restart (`_CLASS_CACHE` is
        in-memory, reset each restart) -- so an unrelated test/demo account
        could silently become "the" SSA101 instructor, with zero visible
        error (API still 200, just classSize=0 for whoever used to think
        they owned the class). No fallback to an arbitrary account, ever:
        if the canonical email is missing, create exactly that account
        under exactly that email, so every future call -- including after
        any later restart -- finds this SAME row instead of drifting."""
        instructor = (
            self._db.query(models.User).filter_by(email=DEMO_INSTRUCTOR_EMAIL).first()
        )
        if instructor:
            return instructor.id

        instructor = models.User(
            id="user_gate2_instructor",
            email=DEMO_INSTRUCTOR_EMAIL,
            password_hash="unused",
            full_name="Cô Hương",
            role=models.UserRole.INSTRUCTOR.value,
            is_email_verified=True,
            is_active=True,
            created_at=datetime.now(),
            organization_id=self._demo_organization_id(),
        )
        self._db.add(instructor)
        self._db.flush()
        return instructor.id

    def _rename_persona(self, student_id: str) -> None:
        """Give the demo accounts their Blueprint §7 names (display only)."""
        for email, name in PERSONA_NAMES.items():
            user = self._db.query(models.User).filter_by(email=email).first()
            if user and user.full_name != name:
                user.full_name = name
        user = self._db.query(models.User).filter_by(id=student_id).first()
        if user and user.email == DEMO_STUDENT_EMAIL:
            user.full_name = PERSONA_NAMES[DEMO_STUDENT_EMAIL]
        self._db.flush()

    def _ensure_minh(self) -> models.User:
        minh = self._db.query(models.User).filter_by(id=MINH_USER_ID).first()
        if minh:
            return minh
        template = (
            self._db.query(models.User).filter_by(email=DEMO_STUDENT_EMAIL).first()
        )
        minh = models.User(
            id=MINH_USER_ID,
            email=MINH_EMAIL,
            # Never a usable credential — Minh exists only as alert evidence.
            password_hash="!demo-no-login",
            full_name=MINH_NAME,
            role=models.UserRole.STUDENT.value,
            organization_id=(
                template.organization_id if template else self._demo_organization_id()
            ),
            is_email_verified=True,
            is_active=True,
            created_at=datetime.now(),
        )
        self._db.add(minh)
        self._db.flush()
        return minh

    # ── class section / enrollment ───────────────────────────────────
    def _ensure_class_section(
        self, course: models.Course, instructor_id: str
    ) -> models.CourseSection:
        section = (
            self._db.query(models.CourseSection).filter_by(id=CLASS_SECTION_ID).first()
        )
        if not section:
            section = models.CourseSection(
                id=CLASS_SECTION_ID,
                course_id=course.id,
                instructor_id=instructor_id,
                term=CLASS_TERM,
                section_code=CLASS_SECTION_CODE,
            )
            self._db.add(section)
            self._db.flush()
        else:
            section.course_id = course.id
            # Deliberately NOT `section.instructor_id = instructor_id` here
            # (fixed 22/08): `instructor_id` is now stable and deterministic
            # from `_ensure_instructor()`, but this is the second half of
            # the same fix -- a section that already exists keeps its
            # already-assigned instructor rather than trusting a fresh
            # resolve on every call. Belt-and-suspenders: if
            # `_ensure_instructor()` ever regresses, this section's
            # ownership still can't silently flip across a restart.
        return section

    def _enroll(self, student_id: str) -> None:
        existing = (
            self._db.query(models.Enrollment)
            .filter_by(student_id=student_id, section_id=CLASS_SECTION_ID)
            .first()
        )
        if existing:
            return
        self._db.add(
            models.Enrollment(
                id=f"enr_gate2_{uuid.uuid4().hex[:10]}",
                student_id=student_id,
                section_id=CLASS_SECTION_ID,
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=datetime.now(),
            )
        )
        self._db.flush()

    # ── assignment ───────────────────────────────────────────────────
    def _ensure_part1_assignment(
        self, section: models.CourseSection, week_start: date
    ) -> models.Assignment:
        due = sunday_2359(week_start)
        assignment = (
            self._db.query(models.Assignment).filter_by(id=PART1_ASSIGNMENT_ID).first()
        )
        if not assignment:
            assignment = models.Assignment(
                id=PART1_ASSIGNMENT_ID,
                section_id=section.id,
                title=PART1_TITLE,
                description=PART1_DESCRIPTION,
                due_date=due,
                max_points=10.0,
                assessment_type=models.AssessmentType.PROJECT_MILESTONE.value,
            )
            self._db.add(assignment)
            self._db.flush()
        else:
            assignment.section_id = section.id
            assignment.title = PART1_TITLE
            assignment.description = PART1_DESCRIPTION
            assignment.due_date = due
        return assignment

    # ── plan state ───────────────────────────────────────────────────
    def _clear_student_plan_state(self, student_id: str) -> None:
        """Delete this student's plans/tasks/events/reflections/risk rows."""
        plans = (
            self._db.query(models.WeeklyPlan).filter_by(student_id=student_id).all()
        )
        plan_ids = [plan.id for plan in plans]
        if plan_ids:
            daily = (
                self._db.query(models.DailyPlan)
                .filter(models.DailyPlan.weekly_plan_id.in_(plan_ids))
                .all()
            )
            daily_ids = [item.id for item in daily]
            block_ids: list[str] = []
            if daily_ids:
                blocks = (
                    self._db.query(models.ScheduleBlock)
                    .filter(models.ScheduleBlock.daily_plan_id.in_(daily_ids))
                    .all()
                )
                block_ids = [block.id for block in blocks]
            task_ids: list[str] = []
            if block_ids:
                tasks = (
                    self._db.query(models.StudyTask)
                    .filter(models.StudyTask.schedule_block_id.in_(block_ids))
                    .all()
                )
                task_ids = [task.id for task in tasks]
            if task_ids:
                (
                    self._db.query(models.ProgressEvent)
                    .filter(models.ProgressEvent.task_id.in_(task_ids))
                    .delete(synchronize_session=False)
                )
                (
                    self._db.query(models.StudyTask)
                    .filter(models.StudyTask.id.in_(task_ids))
                    .delete(synchronize_session=False)
                )
            if block_ids:
                (
                    self._db.query(models.ScheduleBlock)
                    .filter(models.ScheduleBlock.id.in_(block_ids))
                    .delete(synchronize_session=False)
                )
            if daily_ids:
                (
                    self._db.query(models.DailyPlan)
                    .filter(models.DailyPlan.id.in_(daily_ids))
                    .delete(synchronize_session=False)
                )
            (
                self._db.query(models.WeeklyPlan)
                .filter(models.WeeklyPlan.id.in_(plan_ids))
                .delete(synchronize_session=False)
            )

        (
            self._db.query(models.ProgressEvent)
            .filter_by(student_id=student_id)
            .delete(synchronize_session=False)
        )
        (
            self._db.query(models.WeeklyReflection)
            .filter_by(student_id=student_id)
            .delete(synchronize_session=False)
        )
        risk_ids = [
            row[0]
            for row in self._db.query(models.RiskSignal.id)
            .filter_by(student_id=student_id)
            .all()
        ]
        if risk_ids:
            (
                self._db.query(models.InstructorIntervention)
                .filter(models.InstructorIntervention.risk_signal_id.in_(risk_ids))
                .delete(synchronize_session=False)
            )
            (
                self._db.query(models.RiskSignal)
                .filter(models.RiskSignal.id.in_(risk_ids))
                .delete(synchronize_session=False)
            )
        self._db.flush()

    def _seed_minh_week(self, week_start: date) -> None:
        """Minh's behavioural record: 1 of 4 done, 3 overdue, nothing started."""
        plan_id = f"plan_{MINH_USER_ID}_{week_start.isoformat()}"
        plan = models.WeeklyPlan(
            id=plan_id,
            student_id=MINH_USER_ID,
            week_number=week_start.isocalendar().week,
            goals={
                "statement": f"Hoàn thành {PART1_TITLE}",
                "status": "APPROVED",
                "week_start": week_start.isoformat(),
                "assignment_id": PART1_ASSIGNMENT_ID,
                "capacity_minutes": 480,
                "fixture_version": FIXTURE_VERSION,
                "provenance": prov.simulated(f"{FIXTURE_VERSION}:minh_plan"),
                "task_meta": {},
            },
            study_hours_allocated=8.0,
        )
        self._db.add(plan)
        self._db.flush()

        now = datetime.now()

        # Blueprint §7 pins Minh's deadline at ~36 hours out. The shared
        # Part-1 due date is Sunday 23:59, which is only 36h away on Friday —
        # so pin it per-student with an override, keeping the fixture
        # reproducible on any day of the week without touching Đăng's date.
        override_id = f"asgo_minh_{PART1_ASSIGNMENT_ID}"
        override = (
            self._db.query(models.AssignmentOverride).filter_by(id=override_id).first()
        )
        due_override = now + timedelta(hours=36)
        if override is None:
            self._db.add(
                models.AssignmentOverride(
                    id=override_id,
                    assignment_id=PART1_ASSIGNMENT_ID,
                    student_id=MINH_USER_ID,
                    due_date_override=due_override,
                )
            )
        else:
            override.due_date_override = due_override
        self._db.flush()

        task_meta: dict[str, dict] = {}
        for index, (title, minutes, day_offset, status) in enumerate(
            MINH_TASK_TEMPLATES
        ):
            scheduled = datetime.combine(
                (now + timedelta(days=day_offset)).date(), time(19, 0)
            )
            daily_id = f"dp_minh_{index}_{week_start.isoformat()}"
            block_id = f"sb_minh_{index}_{week_start.isoformat()}"
            task_id = f"task_minh_{index}_{week_start.isoformat()}"
            self._db.add(
                models.DailyPlan(
                    id=daily_id,
                    weekly_plan_id=plan_id,
                    date=scheduled,
                    status="TODO",
                )
            )
            self._db.add(
                models.ScheduleBlock(
                    id=block_id,
                    daily_plan_id=daily_id,
                    start_time=scheduled,
                    end_time=scheduled + timedelta(minutes=minutes),
                    activity_description="Khung giờ: evening",
                )
            )
            self._db.add(
                models.StudyTask(
                    id=task_id,
                    schedule_block_id=block_id,
                    assignment_id=PART1_ASSIGNMENT_ID,
                    title=title,
                    planned_minutes=minutes,
                    actual_minutes=minutes if status == "COMPLETED" else None,
                    priority="HIGH" if index < 2 else "MEDIUM",
                    status=status,
                    difficulty="MEDIUM",
                    rescheduled_count=0,
                )
            )
            # ProgressEvent only stores the task foreign key; there is no ORM
            # relationship for SQLAlchemy to infer insert ordering from. Flush
            # the daily plan, schedule block, and task before adding its event.
            self._db.flush()
            task_meta[task_id] = {
                "scheduled_date": scheduled.date().isoformat(),
                "provenance": prov.ai_suggested(),
                "source_refs": list(PART1_SOURCE_REFS[:1]),
            }
            if status == "COMPLETED":
                self._db.add(
                    models.ProgressEvent(
                        id=f"evt_minh_{index}_done",
                        student_id=MINH_USER_ID,
                        task_id=task_id,
                        event_type="TASK_COMPLETED",
                        payload={"actual_minutes": minutes},
                        occurred_at=now - timedelta(days=abs(day_offset)),
                    )
                )

        goals = dict(plan.goals)
        goals["task_meta"] = task_meta
        plan.goals = goals
        self._db.flush()
