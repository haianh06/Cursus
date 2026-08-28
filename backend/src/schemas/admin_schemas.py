from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

InvitableRole = Literal["STUDENT", "INSTRUCTOR", "ADMIN"]


class CreateInviteRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: InvitableRole
    # Lớp người được mời sẽ phụ trách ngay khi đăng ký xong. Chỉ có nghĩa với
    # role INSTRUCTOR; route từ chối 400 nếu gửi kèm role khác thay vì lặng lẽ
    # bỏ qua, vì "bỏ qua âm thầm" là kiểu lỗi admin không bao giờ phát hiện ra.
    section_id: str | None = Field(default=None, max_length=64)


class InviteResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    expires_at: str
    used_at: str | None
    revoked_at: str | None
    section_id: str | None = None
    delivery_status: Literal["pending", "sent", "failed"]
    resend_count: int = Field(ge=0)
    last_sent_at: str | None
    created_at: str


class AdminUserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class UpdateUserStatusRequest(BaseModel):
    is_active: bool
    reason: str | None = None


class AccessRequestResponse(BaseModel):
    id: str
    institution_name: str
    contact_name: str
    email: str
    role_interested: str | None
    message: str | None
    created_at: str


class AdminCourse(BaseModel):
    subject_code: str
    subject_name: str
    semester: str
    # "mock_only" = mục 16 data contract: this course only has fabricated
    # (student_mock_data_service.COURSE_DOCUMENTS) content, no official
    # syllabus chunks — must render distinctly from "ingested", never the
    # same badge.
    ingest_status: Literal["ingested", "not_ingested", "mock_only", "processing", "failed"]
    ingest_error: str | None = None
    chunk_count: int = Field(ge=0)
    mock_chunk_count: int = Field(ge=0, default=0)
    is_added: bool = False


class AdminCoursesData(BaseModel):
    subject_count: int = Field(ge=0)
    courses: list[AdminCourse]


class AdminCoursesResponse(BaseModel):
    success: Literal[True]
    data: AdminCoursesData


class CurriculumClo(BaseModel):
    code: str
    text: str


class CurriculumSession(BaseModel):
    number: int | None
    topic: str
    # None (not "") when the source syllabus genuinely omits this session's
    # materials/task -- e.g. exam/review sessions -- so the frontend can
    # render an honest "—" instead of an empty-looking cell.
    materials: str | None = None
    task: str | None = None


class CurriculumDetailData(BaseModel):
    # Raw key-value pairs straight from the syllabus source (course name,
    # credits, description, prerequisite, tools, scoring scale, grading
    # policy, pass mark, decision no/approved date...) -- deliberately not
    # typed field-by-field since the exact key set is the source file's own
    # shape, not a Cursus-defined contract.
    meta: dict[str, str]
    clo_count: int = Field(ge=0)
    session_count: int = Field(ge=0)
    clos: list[CurriculumClo]
    sessions: list[CurriculumSession]


class CurriculumDetailResponse(BaseModel):
    success: Literal[True]
    data: CurriculumDetailData


class AdminKpiData(BaseModel):
    with_cursus_overall: float = Field(ge=0, le=1)
    baseline_overall: float = Field(ge=0, le=1)
    method_note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AdminKpiResponse(BaseModel):
    success: Literal[True]
    data: AdminKpiData


class AdminWeeklyRiskPoint(BaseModel):
    week: int
    count: int = Field(ge=0)


class AdminAnalyticsData(BaseModel):
    total_documents: int = Field(ge=0)
    at_risk_student_count: int = Field(ge=0)
    weekly_risk_trend: list[AdminWeeklyRiskPoint]


class AdminAnalyticsResponse(BaseModel):
    success: Literal[True]
    data: AdminAnalyticsData


class AdminAnalyticsSummaryData(BaseModel):
    at_risk_students: int = Field(ge=0)
    ingested_courses: int = Field(ge=0)
    total_courses: int = Field(ge=0)
    total_documents: int = Field(ge=0)
    total_chunks: int = Field(ge=0)
    measurement_status: Literal["not_measured"]
    method_note: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AdminAnalyticsSummaryResponse(BaseModel):
    success: Literal[True]
    data: AdminAnalyticsSummaryData


class AdminGuardrailRule(BaseModel):
    code: str
    name: str
    description: str
    enabled: bool
    core_locked: bool
    current_version: str | None = None
    pattern_count: int = Field(ge=1)
    updated_at: str
    updated_by: str | None = None


class AdminGuardrailRulesData(BaseModel):
    rules: list[AdminGuardrailRule]
    any_disabled: bool


class AdminGuardrailRulesResponse(BaseModel):
    success: Literal[True]
    data: AdminGuardrailRulesData


class AdminGuardrailRuleUpdateRequest(BaseModel):
    enabled: bool
    reason: str | None = None


class AdminGuardrailRuleUpdateData(BaseModel):
    rule: AdminGuardrailRule
    any_disabled: bool


class AdminGuardrailRuleUpdateResponse(BaseModel):
    success: Literal[True]
    data: AdminGuardrailRuleUpdateData


class AdminGuardrailRulePreviewRequest(BaseModel):
    enabled: bool
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)]


class AdminGuardrailRulePreviewData(BaseModel):
    code: str
    current_enabled: bool
    proposed_enabled: bool
    core_locked: bool
    changed_codes: list[str]
    any_disabled: bool
    reason: str


class AdminGuardrailRulePreviewResponse(BaseModel):
    success: Literal[True]
    data: AdminGuardrailRulePreviewData


class AdminGuardrailPolicyVersion(BaseModel):
    version: str
    rules_snapshot: dict[str, bool]
    source_version: str | None = None
    change_reason: str | None = None
    rolled_back_from: str | None = None
    is_active: bool
    created_by: str | None = None
    created_at: str


class AdminGuardrailHistoryData(BaseModel):
    versions: list[AdminGuardrailPolicyVersion]


class AdminGuardrailHistoryResponse(BaseModel):
    success: Literal[True]
    data: AdminGuardrailHistoryData


class AdminGuardrailRollbackRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=2000)]


class AdminGuardrailRollbackData(BaseModel):
    version: str
    rolled_back_from: str
    rules: dict[str, bool]
    any_disabled: bool


class AdminGuardrailRollbackResponse(BaseModel):
    success: Literal[True]
    data: AdminGuardrailRollbackData


class AdminGuardrailRestoreRequest(BaseModel):
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=0, max_length=2000)] = ""


class AdminCourseCreateRequest(BaseModel):
    subject_code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=32)]
    subject_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    semester: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]


class AdminDocument(BaseModel):
    id: str
    course_code: str | None = None
    title: str
    filename: str | None = None
    doc_type: str
    version: str
    chunk_count: int = Field(ge=0)
    content_flagged: bool
    publication_status: str
    version_group: str
    previous_version_id: str | None = None
    validated_at: str | None = None
    published_at: str | None = None
    archived_at: str | None = None
    change_reason: str | None = None


class AdminDocumentsData(BaseModel):
    documents: list[AdminDocument]


class AdminDocumentsResponse(BaseModel):
    success: Literal[True]
    data: AdminDocumentsData


class AdminDocumentContentData(BaseModel):
    id: str
    filename: str | None = None
    title: str
    version: str
    content: str
    truncated: bool


class AdminDocumentContentResponse(BaseModel):
    success: Literal[True]
    data: AdminDocumentContentData


class AdminDocumentVersionsData(BaseModel):
    versions: list[AdminDocument]


class AdminDocumentVersionsResponse(BaseModel):
    success: Literal[True]
    data: AdminDocumentVersionsData


class AdminDocumentMutationData(BaseModel):
    document: AdminDocument


class AdminDocumentMutationResponse(BaseModel):
    success: Literal[True]
    data: AdminDocumentMutationData


class AdminIngestJobData(BaseModel):
    job_id: str
    status: Literal["processing"]


class AdminIngestJobResponse(BaseModel):
    success: Literal[True]
    data: AdminIngestJobData


# ── Academic term / course exam / class activity (camelCase fields, matches
# src/schemas/qa.py's convention for the frontend's JSON shape) ────────────
# ruff: noqa: N815


class AcademicTermUpsertRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    startDate: str
    studyWeeks: int = Field(default=10, ge=1, le=20)
    examWeeks: int = Field(default=2, ge=1, le=6)

    @property
    def start_date(self):
        from datetime import date

        return date.fromisoformat(self.startDate)


class AcademicTermOut(BaseModel):
    id: str
    name: str
    start_date: str
    end_date: str
    study_weeks: int
    exam_weeks: int
    exam_start: str | None = None
    exam_end: str | None = None
    is_active: bool


class ExamSessionIn(BaseModel):
    examDate: str
    slotId: int = Field(ge=1, le=6)
    label: str = Field(default="", max_length=40)

    @property
    def exam_date(self):
        from datetime import date

        return date.fromisoformat(self.examDate)


class CourseExamUpsertRequest(BaseModel):
    courseId: str = Field(..., min_length=1)
    kind: Literal["MIDTERM", "FINAL", "PROGRESS_TEST"]
    sessions: list[ExamSessionIn] = Field(min_length=1)


class ExamSessionOut(BaseModel):
    id: str
    exam_date: str
    slot_id: int
    label: str


class CourseExamOut(BaseModel):
    id: str
    course_id: str
    course_code: str | None = None
    course_name: str | None = None
    kind: str
    sessions: list[ExamSessionOut]


class ClassActivityRequest(BaseModel):
    courseId: str = Field(..., min_length=1)
    activityDate: str
    kind: Literal["LECTURE_HELD", "CANCELLED", "MAKEUP", "NOTE"]
    title: str = Field(default="", max_length=200)


class ClassActivityOut(BaseModel):
    id: str
    course_id: str
    course_code: str | None = None
    activity_date: str
    kind: str
    title: str
    created_by: str
    created_at: str


# ── Risk policy versioning (mục 14.1) ────────────────────────────────────

SeverityBand = tuple[int, Literal["normal", "watch", "needs_support"], Literal["LOW", "MEDIUM", "HIGH"]]


class RiskPolicyOut(BaseModel):
    policyVersion: int | None
    effectiveFrom: str | None
    signalWeights: dict[str, float]
    signalThresholds: dict[str, float]
    severityBands: list[SeverityBand]
    reason: str
    rolledBackFrom: int | None
    createdBy: str | None
    createdAt: str | None


class RiskPolicyDraft(BaseModel):
    """Shared body shape for both preview and publish — same proposed
    policy, publish just additionally requires `reason`."""

    signalWeights: dict[str, float]
    signalThresholds: dict[str, float]
    severityBands: list[SeverityBand]


class RiskPolicyPublishRequest(RiskPolicyDraft):
    reason: str = Field(..., min_length=1, max_length=2000)


class RiskPolicyPreviewChange(BaseModel):
    studentId: str
    sectionId: str
    beforeSeverity: str
    afterSeverity: str
    beforeScore: int
    afterScore: int


class RiskPolicyPreviewResponse(BaseModel):
    totalEvaluated: int
    changedCount: int
    changes: list[RiskPolicyPreviewChange]


class RiskPolicyRollbackRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


# ── Mock LMS sync (mục 6.6) ────────────────────────────────────────────────

class MockLmsSyncChange(BaseModel):
    courseCode: str
    assignmentId: str
    assignmentName: str
    field: str
    before: str | None
    after: str
    winningTier: str
    winningTierLabel: str


class MockLmsSyncPreviewResponse(BaseModel):
    totalEvaluated: int
    changedCount: int
    changes: list[MockLmsSyncChange]


class MockLmsSyncPublishRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class MockLmsSyncRollbackRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


class MockLmsSyncVersionOut(BaseModel):
    syncVersion: int
    payload: list[MockLmsSyncChange]
    reason: str
    rolledBackFrom: int | None
    createdBy: str | None
    createdAt: str


# ── Admin settings (mục 6.5) ──────────────────────────────────────────────

class AdminSettingsOut(BaseModel):
    demoModeEnabled: bool
    autoRiskAlertsEnabled: bool
    defaultSemester: str
    updatedAt: str
    updatedBy: str | None


class AdminSettingsUpdateRequest(BaseModel):
    demoModeEnabled: bool | None = None
    autoRiskAlertsEnabled: bool | None = None
    defaultSemester: Annotated[str, StringConstraints(min_length=1, max_length=50)] | None = None


# ── Admin sections (Task 6 — CourseSection CRUD + instructor assignment) ──


class SectionCreateRequest(BaseModel):
    course_id: str = Field(alias="courseId")
    section_code: str = Field(alias="sectionCode", min_length=1, max_length=32)
    term: str = Field(min_length=1, max_length=32)
    instructor_id: str | None = Field(default=None, alias="instructorId")

    model_config = ConfigDict(populate_by_name=True)


class SectionUpdateRequest(BaseModel):
    section_code: str | None = Field(default=None, alias="sectionCode", max_length=32)
    term: str | None = Field(default=None, max_length=32)
    instructor_id: str | None = Field(default=None, alias="instructorId")

    model_config = ConfigDict(populate_by_name=True)


class SectionOut(BaseModel):
    id: str
    course_code: str = Field(serialization_alias="courseCode")
    course_name: str = Field(serialization_alias="courseName")
    section_code: str = Field(serialization_alias="sectionCode")
    term: str
    instructor_id: str | None = Field(serialization_alias="instructorId")
    instructor_name: str | None = Field(serialization_alias="instructorName")
    enrolled_count: int = Field(serialization_alias="enrolledCount")

    model_config = ConfigDict(populate_by_name=True)


class RosterAddRequest(BaseModel):
    student_id: str = Field(alias="studentId")

    model_config = ConfigDict(populate_by_name=True)
