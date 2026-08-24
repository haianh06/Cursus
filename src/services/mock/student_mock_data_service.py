"""Provision a complete mock semester for Student Weekly Planner demos.

Each student gets:
- 4 courses: SSA101, PRF192, CEA201, CSI106
- personal sections + enrollments
- lecture timetable with fixed FPT-style slots
- 1 fixed rest day (Mon-Fri)
- upcoming assignments
- syllabus/lecture documents + text chunks
- a sample self-study block in a free evening slot
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from src.db import models
from src.services.academic.timetable_service import monday_of
from src.services.mock.gate2_demo import (
    CLASS_SECTION_CODE as GATE2_CLASS_SECTION_CODE,
)
from src.services.mock.gate2_demo import (
    CLASS_SECTION_ID as GATE2_CLASS_SECTION_ID,
)
from src.services.mock.gate2_demo import (
    Gate2DemoService,
)
from src.services.mock.gate2_demo import (
    SSA101_CODE as GATE2_CLASS_COURSE_CODE,
)
from src.services.mock.gate2_demo import ingest_official_chunks, load_official_chunks

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
DOCS_ROOT = ROOT / "mock_data" / "documents"

# Fixed campus slots
SLOTS: dict[int, tuple[time, time]] = {
    1: (time(7, 30), time(9, 50)),
    2: (time(10, 0), time(12, 20)),
    3: (time(12, 50), time(15, 10)),
    4: (time(15, 20), time(17, 40)),
}

# Pair A / Pair B alternate across study days.
COURSE_PAIR_A = ("SSA101", "PRF192")
COURSE_PAIR_B = ("CEA201", "CSI106")

DEMO_COURSES = (
    {
        # Content of record for SSA101 comes from the official syllabus chunks
        # ingested by `gate2_demo`; keep this entry aligned with it.
        "code": "SSA101",
        "name": "Kỹ năng học thuật / Academic Skills",
        "description": (
            "Kỹ năng học thuật (Academic Skills) — 3 tín chỉ. Học phần rèn "
            "thói quen học tập, tư duy phản biện, giao tiếp học thuật và sử "
            "dụng AI có trách nhiệm."
        ),
        "room": "A101",
    },
    {
        "code": "PRF192",
        "name": "Programming Fundamentals with C",
        "description": (
            "Lập trình C (C11): kiểu dữ liệu, toán tử, hệ đếm, if/switch, "
            "vòng lặp, hàm, mảng 1D/2D, string; workshop + lab + PE."
        ),
        "room": "Lab A102",
    },
    {
        "code": "CEA201",
        "name": "Computer Organization and Architecture",
        "description": (
            "Tổ chức máy tính (Stallings-style): CPU, bus, memory/cache, "
            "I/O, instruction set, addressing, pipelining và hỗ trợ OS."
        ),
        "room": "B201",
    },
    {
        "code": "CSI106",
        "name": "Introduction to Computer Science",
        "description": (
            "Nhập môn CS (Forouzan lineage / CSI104–106): von Neumann, "
            "biểu diễn dữ liệu, thuật toán, ngôn ngữ lập trình, mạng TCP/IP."
        ),
        "room": "B202",
    },
)

# SSA101 no longer gets its own generic assignments here. The one SSA101
# assignment that matters for Gate 2 — "SSA101 Group Project — Part 1" — is
# owned by `gate2_demo.Gate2DemoService` so the demo story has exactly one
# canonical definition instead of two competing ones.
DEMO_ASSIGNMENTS = (
    {
        "course_code": "PRF192",
        "id_suffix": "lab02",
        "title": "PRF192 — Lab 02: Loops & Arrays",
        "description": (
            "Implement bằng C11: sum/max/reverse mảng 1D; nested loop cho mảng 2D; "
            "nộp file .c + screenshot chạy trên Dev-C++/VS Code."
        ),
        "days_until_due": 6,
        "max_points": 10.0,
        "assessment_type": "LAB",
    },
    {
        "course_code": "PRF192",
        "id_suffix": "workshop_functions",
        "title": "PRF192 — Workshop: Functions & Scope",
        "description": (
            "Viết hàm tính giai thừa, kiểm tra số nguyên tố, và swap bằng pointer; "
            "giải thích pass-by-value vs pass-by-address."
        ),
        "days_until_due": 12,
        "max_points": 10.0,
        "assessment_type": "ASSIGNMENT",
    },
    {
        "course_code": "CEA201",
        "id_suffix": "worksheet_cpu",
        "title": "CEA201 — Worksheet: CPU Datapath & Control",
        "description": (
            "Vẽ/truy vết datapath cho 1 lệnh R-type và 1 lệnh load/store; "
            "điền control signals (RegWrite, MemRead, ALUOp, PCSrc)."
        ),
        "days_until_due": 8,
        "max_points": 10.0,
        "assessment_type": "ASSIGNMENT",
    },
    {
        "course_code": "CEA201",
        "id_suffix": "cache_quiz",
        "title": "CEA201 — Practice Quiz: Cache & Memory Hierarchy",
        "description": (
            "Tính hit/miss ratio, address mapping (direct-mapped), "
            "và so sánh cache L1/L2 với main memory latency."
        ),
        "days_until_due": 14,
        "max_points": 5.0,
        "assessment_type": "QUIZ",
    },
    {
        "course_code": "CSI106",
        "id_suffix": "quiz_data_rep",
        "title": "CSI106 — Quiz Prep: Data Representation",
        "description": (
            "Ôn binary/hex/ASCII/Unicode, signed integers (2's complement), "
            "và chuyển đổi giữa các hệ đếm; làm đề ôn từ FAQ."
        ),
        "days_until_due": 7,
        "max_points": 5.0,
        "assessment_type": "QUIZ",
    },
    {
        "course_code": "CSI106",
        "id_suffix": "algo_worksheet",
        "title": "CSI106 — Algorithm Worksheet",
        "description": (
            "Viết pseudocode + flowchart cho tìm max trong mảng và binary search; "
            "ước lượng độ phức tạp O-notation mức intro."
        ),
        "days_until_due": 13,
        "max_points": 10.0,
        "assessment_type": "ASSIGNMENT",
    },
)

COURSE_DOCUMENTS: dict[str, tuple[dict[str, str], ...]] = {
    # None of the 4 DEMO_COURSES get fabricated markdown here anymore as of
    # Phase 2 (21/08): SSA101 (gate2_demo, from the start), CSI106 (Phase 1),
    # and now PRF192/CEA201 (Phase 2 — real syllabi parsed from
    # data/clean/courses/*.docx, see docs/planning/v2/scripts/
    # parse_all_courses.py) all have real, parsed syllabus content via
    # REAL_CONTENT_COURSES below instead. This dict is kept as the mechanism
    # for any FUTURE demo course that genuinely has no real syllabus source
    # yet — do not add an entry here for a course that already has a
    # chunks_<CODE>.json file; that would silently reintroduce the mock-vs-
    # real conflation Phase 1 fixed (see mục 16.1 in PROJECT_CONTEXT.md).
}

# Courses whose retrieval corpus is real, parsed syllabus content
# (docs/planning/v2/data/chunks_<CODE>.json) rather than the COURSE_DOCUMENTS
# fixture above. Add a course here once its chunk file exists — see
# docs/PROJECT_CONTEXT.md §16.1 for what's been parsed so far.
REAL_CONTENT_COURSES: tuple[tuple[str, str, str, str], ...] = (
    # (subject_code, document_id, title, syllabus_version)
    (
        "CSI106",
        "doc_csi106_syllabus_11585",
        "Syllabus CSI106 — Introduction to Computer Science",
        "11585-2024-07-29",
    ),
    # PRF192/CEA201 added Phase 2 (21/08) — document_id matches what
    # docs/planning/v2/scripts/parse_all_courses.py's batch ingest already
    # wrote (src/services/mock/real_curriculum_service.py), so this just
    # keeps that same Document/chunks fresh on every demo read instead of
    # creating a second, duplicate Document row for the same course.
    (
        "PRF192",
        "doc_real_prf192_syllabus",
        "Syllabus PRF192 — Programming Fundamentals with C",
        "12223-2024-11-22",
    ),
    (
        "CEA201",
        "doc_real_cea201_syllabus",
        "Syllabus CEA201 — Computer Organization and Architecture",
        "13245-2025-08-22",
    ),
)


def _section_heading(text: str) -> str:
    """Extract the first markdown heading from a chunk, if any."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return ""


class StudentMockDataService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def ensure_for_student(self, student_id: str) -> dict:
        user = self._db.query(models.User).filter_by(id=student_id).first()
        if not user:
            raise LookupError("Student not found")

        role = user.role if isinstance(user.role, str) else user.role.value
        if role != models.UserRole.STUDENT.value:
            return {"provisioned": False, "reason": "not_student"}

        organization_id = user.organization_id
        instructor_id = self._ensure_demo_instructor(organization_id)
        courses = self._ensure_courses(organization_id)
        documents = self._ensure_documents(courses)
        self._ensure_real_content(courses)
        sections = self._ensure_student_sections(
            student_id=student_id,
            instructor_id=instructor_id,
            courses=courses,
        )
        self._cleanup_stale_mock_enrollments(
            student_id=student_id,
            keep_section_ids={section.id for section in sections},
        )
        enrolled = self._ensure_enrollments(student_id=student_id, sections=sections)
        assignments = self._ensure_assignments(sections=sections)
        rest_day = self.rest_day_for_student(student_id)
        lectures = self._rebuild_week_lectures(
            student_id=student_id,
            sections=sections,
            rest_weekday=rest_day,
            week_start=monday_of(date.today()),
        )
        self_study = self._ensure_sample_self_study(
            student_id=student_id,
            rest_weekday=rest_day,
            week_start=monday_of(date.today()),
        )
        self._db.commit()

        logger.info(
            "Provisioned 4-course mock semester user=%s rest_day=%s enroll=%s asg=%s lec=%s docs=%s",
            student_id,
            rest_day,
            enrolled,
            assignments,
            lectures,
            documents,
        )
        return {
            "provisioned": True,
            "restWeekday": rest_day,
            "enrollments": enrolled,
            "assignments": assignments,
            "lectures": lectures,
            "documents": documents,
            "selfStudyBlocks": self_study,
            "courses": [course.code for course in courses],
        }

    def ensure_if_missing(self, student_id: str) -> dict | None:
        """Ensure the 4-course mock semester exists and content stays current.

        Returning students still get syllabus/assignment/lecture refresh so
        mock content updates propagate without re-registering.
        """
        expected_codes = {item["code"] for item in DEMO_COURSES}
        enrolled_courses = (
            self._db.query(models.Course)
            .join(models.CourseSection)
            .join(models.Enrollment)
            .filter(models.Enrollment.student_id == student_id)
            .all()
        )
        enrolled_codes = {course.code for course in enrolled_courses}
        if expected_codes.issubset(enrolled_codes):
            # Real-content courses (currently CSI106) still need their
            # syllabus chunks refreshed on every read — same reasoning as
            # Gate2DemoService.ensure_student() for SSA101 — even though the
            # rest of the mock semester is already provisioned and skipped.
            if self._ensure_real_content(enrolled_courses):
                self._db.commit()
            return {"provisioned": True, "refreshed": False}

        result = self.ensure_for_student(student_id)
        return result

    @staticmethod
    def rest_day_for_student(student_id: str) -> int:
        """Deterministic rest weekday in Mon-Fri (0=Mon ... 4=Fri)."""
        digest = hashlib.sha256(student_id.encode("utf-8")).hexdigest()
        return int(digest[:8], 16) % 5

    def _ensure_demo_instructor(self, organization_id: str | None) -> str:
        # Always resolve through Gate2DemoService's own idempotent
        # _ensure_instructor() -- the single source of truth for who owns
        # GATE2_CLASS_SECTION_ID (below). This used to fall back to "any
        # existing INSTRUCTOR row" when the canonical demo.instructor@
        # cursusdemo.local account hadn't been created yet (e.g. a brand new
        # test/demo student registers before Gate2DemoService.ensure_class()
        # has ever run). Because _ensure_student_sections() reuses that exact
        # GATE2_CLASS_SECTION_ID for every student's SSA101 section, and
        # CourseSection ownership is never reassigned once a section exists,
        # whichever instructor happened to win that race permanently "owned"
        # the shared Gate-2 class for the rest of the process/test session --
        # silently orphaning it from demo.instructor@cursusdemo.local with no
        # visible error (API still 200, just an empty roster/risk queue for
        # whoever expected to teach it). See Gate2DemoService._ensure_
        # instructor()'s own docstring for the prior incident this exact
        # pattern caused.
        return Gate2DemoService(self._db)._ensure_instructor()

    def _ensure_courses(self, organization_id: str | None) -> list[models.Course]:
        courses: list[models.Course] = []
        for course_def in DEMO_COURSES:
            course = (
                self._db.query(models.Course).filter_by(code=course_def["code"]).first()
            )
            if not course:
                course = models.Course(
                    id=f"course_mock_{course_def['code'].lower()}",
                    code=course_def["code"],
                    name=course_def["name"],
                    description=course_def["description"],
                    syllabus=f"Mock syllabus for {course_def['code']}",
                    organization_id=organization_id,
                )
                self._db.add(course)
                self._db.flush()
            else:
                course.name = course_def["name"]
                course.description = course_def["description"]
            courses.append(course)
        return courses

    def _ensure_student_sections(
        self,
        *,
        student_id: str,
        instructor_id: str,
        courses: list[models.Course],
    ) -> list[models.CourseSection]:
        suffix = hashlib.sha256(student_id.encode("utf-8")).hexdigest()[:8]
        sections: list[models.CourseSection] = []
        for index, course in enumerate(courses):
            # SSA101 is the one Gate-2 class every demo student shares, so the
            # lecturer dashboard has a real roster instead of one section per
            # student. The other three courses stay per-student.
            if course.code == GATE2_CLASS_COURSE_CODE:
                # But don't clobber a student who already has a *different*,
                # deliberately-set-up SSA101 enrollment (e.g. tests/support/
                # api_demo_dataset.py's fixed sec_ssa101_demo section, owned
                # by a specific instructor for that test's own scenario).
                # Forcing GATE2_CLASS_SECTION_ID here unconditionally used to
                # make _cleanup_stale_mock_enrollments() below delete that
                # enrollment as "stale" the moment this student's dashboard
                # was read for any other reason (e.g. missing one of the
                # other 3 mock courses) -- silently moving them to a
                # different section/instructor mid-test-suite.
                existing_ssa101_enrollment = (
                    self._db.query(models.CourseSection)
                    .join(models.Enrollment, models.Enrollment.section_id == models.CourseSection.id)
                    .filter(
                        models.Enrollment.student_id == student_id,
                        models.CourseSection.course_id == course.id,
                    )
                    .first()
                )
                section_id = (
                    existing_ssa101_enrollment.id if existing_ssa101_enrollment else GATE2_CLASS_SECTION_ID
                )
            else:
                section_id = f"section_mock_{course.code.lower()}_{suffix}"
            section = self._db.query(models.CourseSection).filter_by(id=section_id).first()
            if not section:
                section = models.CourseSection(
                    id=section_id,
                    course_id=course.id,
                    instructor_id=instructor_id,
                    term="Fall2026",
                    section_code=(
                        GATE2_CLASS_SECTION_CODE
                        if section_id == GATE2_CLASS_SECTION_ID
                        else f"SE{1801 + index}"
                    ),
                )
                self._db.add(section)
                self._db.flush()
            sections.append(section)
        return sections

    def _cleanup_stale_mock_enrollments(
        self,
        *,
        student_id: str,
        keep_section_ids: set[str],
    ) -> None:
        """Drop older mock enrollments for the 4 demo courses so TKB stays clean."""
        mock_codes = {item["code"] for item in DEMO_COURSES}
        stale = (
            self._db.query(models.Enrollment)
            .join(models.CourseSection)
            .join(models.Course)
            .filter(
                models.Enrollment.student_id == student_id,
                models.Course.code.in_(mock_codes),
                ~models.Enrollment.section_id.in_(keep_section_ids),
            )
            .all()
        )
        for enrollment in stale:
            self._db.delete(enrollment)
        if stale:
            self._db.flush()

    def _ensure_enrollments(
        self,
        *,
        student_id: str,
        sections: list[models.CourseSection],
    ) -> int:
        created = 0
        for section in sections:
            existing = (
                self._db.query(models.Enrollment)
                .filter_by(student_id=student_id, section_id=section.id)
                .first()
            )
            if existing:
                continue
            self._db.add(
                models.Enrollment(
                    id=f"enroll_mock_{uuid.uuid4().hex[:10]}",
                    student_id=student_id,
                    section_id=section.id,
                    status=models.EnrollmentStatus.ENROLLED.value,
                    enrolled_at=datetime.now(),
                )
            )
            created += 1
        self._db.flush()
        return created

    def _ensure_assignments(self, *, sections: list[models.CourseSection]) -> int:
        section_by_code: dict[str, models.CourseSection] = {}
        for section in sections:
            course = self._db.query(models.Course).filter_by(id=section.course_id).first()
            if course:
                section_by_code[course.code] = section

        created = 0
        now = datetime.now()
        for item in DEMO_ASSIGNMENTS:
            section = section_by_code.get(item["course_code"])
            if not section:
                continue
            assignment_id = f"asg_mock_{section.id}_{item['id_suffix']}"
            existing = (
                self._db.query(models.Assignment).filter_by(id=assignment_id).first()
            )
            due = now + timedelta(days=item["days_until_due"])
            if existing:
                existing.due_date = due
                existing.title = item["title"]
                existing.description = item["description"]
                continue
            self._db.add(
                models.Assignment(
                    id=assignment_id,
                    section_id=section.id,
                    title=item["title"],
                    description=item["description"],
                    due_date=due,
                    max_points=item["max_points"],
                    assessment_type=item["assessment_type"],
                )
            )
            created += 1
        self._db.flush()
        return created

    def _ensure_documents(self, courses: list[models.Course]) -> int:
        created = 0
        course_by_code = {course.code: course for course in courses}
        for code, docs in COURSE_DOCUMENTS.items():
            course = course_by_code.get(code)
            if not course:
                continue
            course_dir = DOCS_ROOT / code
            course_dir.mkdir(parents=True, exist_ok=True)
            for doc_def in docs:
                document_id = f"doc_mock_{code.lower()}_{doc_def['filename']}"
                document = (
                    self._db.query(models.Document).filter_by(id=document_id).first()
                )
                paragraphs = [
                    part.strip()
                    for part in doc_def["text"].split("\n\n")
                    if part.strip()
                ]

                # `COURSE_DOCUMENTS` is a static in-code fixture — its content
                # cannot change between requests. This ensure runs on every
                # student page load (see ensure_if_missing's docstring), so
                # re-writing the markdown file to disk and doing a DELETE +
                # per-paragraph INSERT round trip to the DB every single time,
                # even when the chunk count already matches what this doc_def
                # would produce, was adding real per-request latency for a
                # no-op. Skip the disk write + chunk rebuild once it's known
                # to already match; `document`'s row is still refreshed below
                # so metadata edits to `doc_def` still propagate cheaply.
                existing_chunk_count = (
                    self._db.query(models.DocumentChunk)
                    .filter_by(document_id=document_id)
                    .count()
                    if document
                    else 0
                )
                needs_chunk_rebuild = existing_chunk_count != len(paragraphs[:6])

                file_path = course_dir / doc_def["filename"]
                if not document or needs_chunk_rebuild:
                    file_path.write_text(doc_def["text"], encoding="utf-8")

                relative_path = str(file_path.relative_to(ROOT)).replace("\\", "/")
                if not document:
                    document = models.Document(
                        id=document_id,
                        course_id=course.id,
                        title=doc_def["title"],
                        file_path=relative_path,
                        doc_type=doc_def["doc_type"],
                        version="1.0",
                        metadata_info={"source": "mock", "course_code": code},
                    )
                    self._db.add(document)
                    self._db.flush()
                    created += 1
                else:
                    document.file_path = relative_path
                    document.title = doc_def["title"]
                    document.doc_type = doc_def["doc_type"]

                if not needs_chunk_rebuild:
                    continue

                # Refresh searchable chunks for future RAG wiring.
                (
                    self._db.query(models.DocumentChunk)
                    .filter_by(document_id=document.id)
                    .delete(synchronize_session=False)
                )
                for index, paragraph in enumerate(paragraphs[:6]):
                    section = _section_heading(paragraph)
                    source_label = (
                        f"{doc_def['title']} — {section}"
                        if section
                        else doc_def["title"]
                    )
                    self._db.add(
                        models.DocumentChunk(
                            id=f"chunk_mock_{document.id}_{index}",
                            document_id=document.id,
                            chunk_index=index,
                            text=paragraph,
                            token_count=max(1, len(paragraph.split())),
                            metadata_info={
                                "course_code": code,
                                "doc_type": doc_def["doc_type"],
                                "doc_title": doc_def["title"],
                                "section": section or None,
                                "source_label": source_label,
                            },
                        )
                    )
        self._db.flush()
        return created

    def _ensure_real_content(self, courses: list[models.Course]) -> int:
        """Real syllabus content for courses in REAL_CONTENT_COURSES,
        replacing the generic COURSE_DOCUMENTS fixture for them (Data
        Contract §16 — official_document, not simulated). Mirrors how
        gate2_demo.py handles SSA101; cheap no-op once ingested (see
        ingest_official_chunks)."""
        course_by_code = {course.code: course for course in courses}
        total = 0
        for code, document_id, title, version in REAL_CONTENT_COURSES:
            course = course_by_code.get(code)
            if not course:
                continue
            chunks = load_official_chunks(code, fallback_title=title)
            total += ingest_official_chunks(
                self._db,
                course=course,
                subject_code=code,
                document_id=document_id,
                title=title,
                version=version,
                chunks=chunks,
            )
        return total

    def _rebuild_week_lectures(
        self,
        *,
        student_id: str,
        sections: list[models.CourseSection],
        rest_weekday: int,
        week_start: date,
    ) -> int:
        section_ids = [section.id for section in sections]
        week_end = week_start + timedelta(days=7)

        # Remove previous mock lectures in this week for the student's sections.
        old_events = (
            self._db.query(models.CalendarEvent)
            .filter(
                models.CalendarEvent.section_id.in_(section_ids),
                models.CalendarEvent.event_type == "LECTURE",
                models.CalendarEvent.start_time >= datetime.combine(week_start, time.min),
                models.CalendarEvent.start_time < datetime.combine(week_end, time.min),
            )
            .all()
        )
        for event in old_events:
            self._db.delete(event)
        self._db.flush()

        section_by_code: dict[str, models.CourseSection] = {}
        room_by_code = {item["code"]: item["room"] for item in DEMO_COURSES}
        for section in sections:
            course = self._db.query(models.Course).filter_by(id=section.course_id).first()
            if course:
                section_by_code[course.code] = section

        study_days = [day for day in range(5) if day != rest_weekday]
        created = 0
        for index, weekday in enumerate(study_days):
            use_pair_a = index % 2 == 0
            pair = COURSE_PAIR_A if use_pair_a else COURSE_PAIR_B
            # Alternate morning/afternoon blocks by study-day index.
            slot_ids = (1, 2) if index % 2 == 0 else (3, 4)
            day = week_start + timedelta(days=weekday)
            for course_code, slot_id in zip(pair, slot_ids, strict=True):
                section = section_by_code.get(course_code)
                if not section:
                    continue
                start_clock, end_clock = SLOTS[slot_id]
                start = datetime.combine(day, start_clock)
                end = datetime.combine(day, end_clock)
                room = room_by_code.get(course_code, "A100")
                self._db.add(
                    models.CalendarEvent(
                        id=f"cal_mock_{uuid.uuid4().hex[:12]}",
                        section_id=section.id,
                        title=f"{course_code} Lecture (Slot {slot_id})",
                        description=(
                            f"{course_code} · Room {room} · "
                            f"Rest day={rest_weekday} · student={student_id[:8]}"
                        ),
                        start_time=start,
                        end_time=end,
                        event_type="LECTURE",
                    )
                )
                created += 1
        self._db.flush()
        return created

    def _ensure_sample_self_study(
        self,
        *,
        student_id: str,
        rest_weekday: int,
        week_start: date,
    ) -> int:
        # Prefer Tuesday evening; if Tuesday is rest day, use Thursday evening.
        evening_weekday = 1 if rest_weekday != 1 else 3
        start = datetime.combine(
            week_start + timedelta(days=evening_weekday),
            time(19, 0),
        )
        end = start + timedelta(hours=1, minutes=30)

        existing = (
            self._db.query(models.ScheduleBlock)
            .join(models.DailyPlan)
            .join(models.WeeklyPlan)
            .filter(
                models.WeeklyPlan.student_id == student_id,
                models.ScheduleBlock.start_time == start,
            )
            .first()
        )
        if existing:
            return 0

        from src.services.academic.timetable_service import TimetableService

        TimetableService(self._db).create_self_study_block(
            student_id=student_id,
            title="Self-study: SSA101 Group Project Part 1 + PRF192 Lab 02",
            start=start,
            end=end,
        )
        return 1
