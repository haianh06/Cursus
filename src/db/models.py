import enum
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

# Helper association table for course prerequisites
course_prerequisites = Table(
    "course_prerequisites",
    Base.metadata,
    Column("course_id", String, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
    Column("prerequisite_id", String, ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True),
)

# Helper association table for study task dependencies
task_dependencies = Table(
    "task_dependencies",
    Base.metadata,
    Column("parent_task_id", String, ForeignKey("study_tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("child_task_id", String, ForeignKey("study_tasks.id", ondelete="CASCADE"), primary_key=True),
)

class UserRole(enum.Enum):
    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"
    ADMIN = "ADMIN"
    SERVICE_ACCOUNT = "SERVICE_ACCOUNT"

class OrganizationKind(enum.Enum):
    PRODUCTION = "production"
    SANDBOX = "sandbox"


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    kind: Mapped[str] = mapped_column(String, default=OrganizationKind.PRODUCTION.value)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrganizationMembership(Base):
    """Explicit membership record — the audit/authorization-adjacent trail of
    who belongs to which org. `users.role` (not this row) is what
    `require_roles` actually checks today; this table mirrors it at
    creation time and is where a future multi-org-per-user model would
    live without changing existing authorization call sites."""

    __tablename__ = "organization_memberships"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OrgInvite(Base):
    """Replaces open self-registration. Role and organization are fixed at
    invite-creation time by a trusted admin — never client-supplied at
    registration."""

    __tablename__ = "org_invites"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(
        String, ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String, index=True)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    invited_by_user_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccessRequest(Base):
    """Public lead-gen form submission ('Yêu cầu quyền truy cập cho tổ chức').
    No auth required to submit; admins review out of band."""

    __tablename__ = "access_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    institution_name: Mapped[str] = mapped_column(String)
    contact_name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, index=True)
    role_interested: Mapped[str | None] = mapped_column(String, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(String)
    share_reflection_summary: Mapped[bool] = mapped_column(Boolean, default=False)
    # Nullable in this ORM declaration only to match the migration's own
    # multi-step rollout (add nullable -> backfill -> set NOT NULL); the
    # live DB schema is NOT NULL (see migrations/versions/20260812_...).
    # Every code path that creates a User (register, provisioning scripts,
    # seed scripts) always sets this — never leave it unset.
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=True, index=True
    )
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    major: Mapped[str | None] = mapped_column(String, nullable=True)
    student_code: Mapped[str | None] = mapped_column(String, nullable=True)
    # Per-account UI preferences (theme/language/showMascot) synced from the
    # Settings screen — replaces what used to be localStorage-only state.
    preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="student")
    weekly_plans: Mapped[list["WeeklyPlan"]] = relationship(back_populates="student")
    weekly_reflections: Mapped[list["WeeklyReflection"]] = relationship(back_populates="student")
    risk_signals: Mapped[list["RiskSignal"]] = relationship(back_populates="student", foreign_keys="RiskSignal.student_id")
    organization: Mapped["Organization | None"] = relationship(foreign_keys=[organization_id])

class AuthSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    token_family_id: Mapped[str] = mapped_column(String, index=True)
    device_label: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    remember_me: Mapped[bool] = mapped_column(Boolean, default=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    absolute_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class VerificationToken(Base):
    __tablename__ = "verification_tokens"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MfaTotpCredential(Base):
    __tablename__ = "mfa_totp_credentials"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    secret_encrypted: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    last_used_counter: Mapped[int | None] = mapped_column(Integer, nullable=True)
    failed_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class MfaRecoveryCode(Base):
    __tablename__ = "mfa_recovery_codes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    code_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MfaTrustedDevice(Base):
    __tablename__ = "mfa_trusted_devices"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    device_token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    device_label: Mapped[str | None] = mapped_column(String, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    actor_user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # mục 9 ý2 / docs/PENDING_DECISIONS.md #2: added 22/08 -- this table had
    # no organization column at all, so any ADMIN could read every other
    # organization's audit log. Nullable because historical rows (backfilled
    # from the actor's *current* org, best-effort) and system-level events
    # with no actor can't always have one; AuditRepository.list_events()
    # filters by exact match, so a NULL row is excluded for every viewer
    # rather than shown to everyone -- fail closed, same choice already made
    # for the admin analytics/user-status org-scoping fix earlier tonight.
    organization_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String, index=True)
    resource_type: Mapped[str | None] = mapped_column(String, nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str] = mapped_column(String)
    ip_address: Mapped[str | None] = mapped_column(String, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    metadata_info: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )

class CurriculumVersion(Base):
    __tablename__ = "curriculum_versions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str] = mapped_column(String, unique=True)
    effective_date: Mapped[datetime] = mapped_column(DateTime)
    # Nullable here only — live DB is NOT NULL. See the comment on
    # User.organization_id above; same reasoning (test fixtures on SQLite).
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=True, index=True
    )

class Program(Base):
    __tablename__ = "programs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    # Nullable here only — live DB is NOT NULL. See User.organization_id.
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=True, index=True
    )

class Course(Base):
    __tablename__ = "courses"
    id: Mapped[str] = mapped_column(String, primary_key=True) # e.g. PRF192
    code: Mapped[str] = mapped_column(String, unique=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    syllabus: Mapped[str | None] = mapped_column(Text, nullable=True)
    assessment_structure: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    curriculum_version_id: Mapped[str | None] = mapped_column(String, ForeignKey("curriculum_versions.id"), nullable=True)
    # Nullable here only — live DB is NOT NULL. See User.organization_id.
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=True, index=True
    )

    prerequisites = relationship(
        "Course",
        secondary=course_prerequisites,
        primaryjoin="Course.id==course_prerequisites.c.course_id",
        secondaryjoin="Course.id==course_prerequisites.c.prerequisite_id",
        backref="prerequisite_for"
    )

class CourseSection(Base):
    __tablename__ = "course_sections"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))
    instructor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    term: Mapped[str] = mapped_column(String) # e.g. Fall2026
    section_code: Mapped[str] = mapped_column(String) # e.g. SE1801

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="section")
    modules: Mapped[list["Module"]] = relationship(back_populates="section")

class EnrollmentStatus(enum.Enum):
    ENROLLED = "ENROLLED"
    COMPLETED = "COMPLETED"
    DROPPED = "DROPPED"

class Enrollment(Base):
    __tablename__ = "enrollments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    section_id: Mapped[str] = mapped_column(String, ForeignKey("course_sections.id", ondelete="CASCADE"))
    status: Mapped[EnrollmentStatus] = mapped_column(String, default="ENROLLED")
    grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped[User] = relationship(back_populates="enrollments")
    section: Mapped[CourseSection] = relationship(back_populates="enrollments")

class Module(Base):
    __tablename__ = "modules"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("course_sections.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    week_number: Mapped[int] = mapped_column(Integer)
    sequence_order: Mapped[int] = mapped_column(Integer)

    section: Mapped[CourseSection] = relationship(back_populates="modules")
    lessons: Mapped[list["Lesson"]] = relationship(back_populates="module")

class Lesson(Base):
    __tablename__ = "lessons"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    module_id: Mapped[str] = mapped_column(String, ForeignKey("modules.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    sequence_order: Mapped[int] = mapped_column(Integer)

    module: Mapped[Module] = relationship(back_populates="lessons")

class DocType(enum.Enum):
    SYLLABUS = "SYLLABUS"
    LECTURE = "LECTURE"
    FAQ = "FAQ"
    LAB = "LAB"
    NOTES = "NOTES"

class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    file_path: Mapped[str] = mapped_column(String)
    doc_type: Mapped[DocType] = mapped_column(String)
    version: Mapped[str] = mapped_column(String)
    metadata_info: Mapped[dict] = mapped_column(JSON)
    scope: Mapped[str] = mapped_column(String, default="OFFICIAL")
    publication_status: Mapped[str] = mapped_column(String, default="DRAFT") # DRAFT, READY_FOR_REVIEW, PUBLISHED, ARCHIVED
    version_group: Mapped[str | None] = mapped_column(String, nullable=True)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String, nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    validated_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer)
    metadata_info: Mapped[dict] = mapped_column(JSON)

class Announcement(Base):
    __tablename__ = "announcements"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("course_sections.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AdminAnnouncement(Base):
    """Thong bao rong tu Admin toi TAT CA giang vien — khac Announcement (gan
    1 section cu the, dung cho luong mock Canvas). Hien o dashboard GV."""
    __tablename__ = "admin_announcements"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("course_sections.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    event_type: Mapped[str] = mapped_column(String) # LECTURE, DEADLINE, EXAM
    semester_setup_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("semester_setups.id", ondelete="CASCADE"), nullable=True
    )

class AssessmentType(enum.Enum):
    LAB = "LAB"
    ASSIGNMENT = "ASSIGNMENT"
    PROJECT_MILESTONE = "PROJECT_MILESTONE"
    QUIZ = "QUIZ"

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("course_sections.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    due_date: Mapped[datetime] = mapped_column(DateTime)
    max_points: Mapped[float] = mapped_column(Float)
    assessment_type: Mapped[AssessmentType] = mapped_column(String)

class AssignmentOverride(Base):
    __tablename__ = "assignment_overrides"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    assignment_id: Mapped[str] = mapped_column(String, ForeignKey("assignments.id", ondelete="CASCADE"))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    due_date_override: Mapped[datetime] = mapped_column(DateTime)

class Quiz(Base):
    __tablename__ = "quizzes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    section_id: Mapped[str] = mapped_column(String, ForeignKey("course_sections.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    time_limit_minutes: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    max_points: Mapped[float] = mapped_column(Float)
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class QuizQuestion(Base):
    __tablename__ = "quiz_questions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    quiz_id: Mapped[str] = mapped_column(String, ForeignKey("quizzes.id", ondelete="CASCADE"))
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[str] = mapped_column(String) # MULTIPLE_CHOICE, CODE
    correct_answer: Mapped[str] = mapped_column(Text)
    options: Mapped[dict] = mapped_column(JSON)
    points: Mapped[float] = mapped_column(Float)
    order_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

class Rubric(Base):
    __tablename__ = "rubrics"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    assignment_id: Mapped[str] = mapped_column(String, ForeignKey("assignments.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)

class RubricCriterion(Base):
    __tablename__ = "rubric_criteria"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    rubric_id: Mapped[str] = mapped_column(String, ForeignKey("rubrics.id", ondelete="CASCADE"))
    criterion_name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    max_points: Mapped[float] = mapped_column(Float)

class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    assignment_id: Mapped[str | None] = mapped_column(String, ForeignKey("assignments.id", ondelete="CASCADE"), nullable=True)
    quiz_id: Mapped[str | None] = mapped_column(String, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    submitted_at: Mapped[datetime] = mapped_column(DateTime)
    content: Mapped[dict] = mapped_column(JSON)
    grading_status: Mapped[str] = mapped_column(String) # PENDING, GRADED
    grade: Mapped[float | None] = mapped_column(Float, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)

class LearningGoal(Base):
    __tablename__ = "learning_goals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    term: Mapped[str] = mapped_column(String)
    goal_statement: Mapped[str] = mapped_column(Text)
    target_gpa: Mapped[float] = mapped_column(Float)

class WeeklyPlan(Base):
    __tablename__ = "weekly_plans"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    week_number: Mapped[int] = mapped_column(Integer)
    goals: Mapped[dict] = mapped_column(JSON)
    study_hours_allocated: Mapped[float] = mapped_column(Float)

    student: Mapped[User] = relationship(back_populates="weekly_plans")
    daily_plans: Mapped[list["DailyPlan"]] = relationship(back_populates="weekly_plan")

class DailyPlan(Base):
    __tablename__ = "daily_plans"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    weekly_plan_id: Mapped[str] = mapped_column(String, ForeignKey("weekly_plans.id", ondelete="CASCADE"))
    date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String) # TODO, IN_PROGRESS, COMPLETED

    weekly_plan: Mapped[WeeklyPlan] = relationship(back_populates="daily_plans")
    schedule_blocks: Mapped[list["ScheduleBlock"]] = relationship(back_populates="daily_plan")

class ScheduleBlock(Base):
    __tablename__ = "schedule_blocks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    daily_plan_id: Mapped[str] = mapped_column(String, ForeignKey("daily_plans.id", ondelete="CASCADE"))
    start_time: Mapped[datetime] = mapped_column(DateTime)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    activity_description: Mapped[str] = mapped_column(String)
    # Shared by every occurrence created from one "repeat weekly until" self-study
    # block, so an edit/delete can be scoped to "this" one occurrence or "all" of
    # them. NULL for a plain (non-repeating) block.
    recurrence_series_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)

    daily_plan: Mapped[DailyPlan] = relationship(back_populates="schedule_blocks")
    study_tasks: Mapped[list["StudyTask"]] = relationship(back_populates="schedule_block")
    self_study_sessions: Mapped[list["SelfStudySession"]] = relationship(back_populates="schedule_block")

class StudyTask(Base):
    __tablename__ = "study_tasks"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    schedule_block_id: Mapped[str] = mapped_column(String, ForeignKey("schedule_blocks.id", ondelete="CASCADE"))
    assignment_id: Mapped[str | None] = mapped_column(String, ForeignKey("assignments.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    planned_minutes: Mapped[int] = mapped_column(Integer)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[str] = mapped_column(String) # HIGH, MEDIUM, LOW
    status: Mapped[str] = mapped_column(String) # TODO, IN_PROGRESS, COMPLETED, MISSED
    difficulty: Mapped[str] = mapped_column(String) # EASY, MEDIUM, HARD
    rescheduled_count: Mapped[int] = mapped_column(Integer, default=0)

    schedule_block: Mapped[ScheduleBlock] = relationship(back_populates="study_tasks")

    dependencies = relationship(
        "StudyTask",
        secondary=task_dependencies,
        primaryjoin="StudyTask.id==task_dependencies.c.child_task_id",
        secondaryjoin="StudyTask.id==task_dependencies.c.parent_task_id",
        backref="dependents"
    )

class SelfStudySession(Base):
    """One Pomodoro focus session per self-study timetable block. 1:1 with
    ScheduleBlock (unique constraint below) -- enforced at the DB level so a
    double-click "start" race can be resolved by catching the resulting
    IntegrityError and adopting the winning row rather than erroring."""
    __tablename__ = "self_study_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    schedule_block_id: Mapped[str] = mapped_column(
        String, ForeignKey("schedule_blocks.id", ondelete="CASCADE"), unique=True
    )
    title: Mapped[str] = mapped_column(String)
    planned_minutes: Mapped[int] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    actual_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pomodoros_completed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String) # IN_PROGRESS, COMPLETED, ABANDONED

    schedule_block: Mapped[ScheduleBlock] = relationship(back_populates="self_study_sessions")

class ReplanProposal(Base):
    __tablename__ = "replan_proposals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    original_plan_id: Mapped[str] = mapped_column(String, ForeignKey("weekly_plans.id"))
    proposed_changes: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String) # PROPOSED, ACCEPTED, REJECTED
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ProgressEvent(Base):
    __tablename__ = "progress_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[str | None] = mapped_column(String, ForeignKey("study_tasks.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String) # TASK_CREATED, TASK_STARTED, TASK_COMPLETED, RESOURCE_VIEWED...
    payload: Mapped[dict] = mapped_column(JSON)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    task_id: Mapped[str | None] = mapped_column(String, ForeignKey("study_tasks.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String) # IN_APP, EMAIL, PUSH
    scheduled_time: Mapped[datetime] = mapped_column(DateTime)

class ReminderDelivery(Base):
    __tablename__ = "reminder_deliveries"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    reminder_id: Mapped[str] = mapped_column(String, ForeignKey("reminders.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String) # SENT, OPENED, IGNORED
    delivered_at: Mapped[datetime] = mapped_column(DateTime)
    action_taken_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class ResourceAccessEvent(Base):
    __tablename__ = "resource_access_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    document_id: Mapped[str] = mapped_column(String, ForeignKey("documents.id", ondelete="CASCADE"))
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration_seconds: Mapped[int] = mapped_column(Integer)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    section_id: Mapped[str | None] = mapped_column(String, ForeignKey("course_sections.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String)
    subject_code: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    conversation_id: Mapped[str] = mapped_column(String, ForeignKey("conversations.id", ondelete="CASCADE"))
    sender: Mapped[str] = mapped_column(String) # USER, ASSISTANT
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metadata_info: Mapped[dict] = mapped_column(JSON)

class StudentMemoryConsent(Base):
    """Opt-in flag for cross-session chat memory -- Privacy-by-Design: default
    off. Withdrawing consent hard-deletes every entry (see StudentMemoryService),
    not just a future-writes gate."""
    __tablename__ = "student_memory_consent"
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class StudentMemoryEntry(Base):
    """Cross-session chat memory: long-term preferences + per-subject learning
    episodes, one unified table with a `kind` discriminator."""
    __tablename__ = "student_memory_entries"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # NULL for kind="preference" (subject-agnostic); set for weak_topic/strength_topic.
    subject_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    kind: Mapped[str] = mapped_column(String) # preference | weak_topic | strength_topic
    content: Mapped[str] = mapped_column(String)
    source_conversation_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True
    )
    reinforce_count: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_reinforced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class RAGTrace(Base):
    __tablename__ = "rag_traces"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    message_id: Mapped[str] = mapped_column(String, ForeignKey("messages.id", ondelete="CASCADE"))
    retrieved_chunks: Mapped[dict] = mapped_column(JSON)
    generation_metadata: Mapped[dict] = mapped_column(JSON)

class LLMUsageEvent(Base):
    __tablename__ = "llm_usage_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    message_id: Mapped[str] = mapped_column(String, ForeignKey("messages.id", ondelete="CASCADE"))
    model: Mapped[str] = mapped_column(String)
    prompt_tokens: Mapped[int] = mapped_column(Integer)
    completion_tokens: Mapped[int] = mapped_column(Integer)
    cost: Mapped[float] = mapped_column(Float)

class LLMQuotaEvent(Base):
    """One row per RESOURCE_EXHAUSTED (429) response from the LLM provider —
    Gemini's free tier gives no way to query remaining quota ahead of a call,
    so this is the only signal the app has: recorded reactively, right when
    a real call actually gets rejected. Admin's quota panel and the chat
    UI's inline "using fallback" badge both read from this table. Not tied
    to a Message (unlike LLMUsageEvent) since a quota failure can happen
    before any assistant Message would otherwise be written."""
    __tablename__ = "llm_quota_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    model: Mapped[str] = mapped_column(String)
    source: Mapped[str] = mapped_column(String)  # which service call site hit the 429

class GuardrailEvent(Base):
    __tablename__ = "guardrail_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    message_id: Mapped[str] = mapped_column(String, ForeignKey("messages.id", ondelete="CASCADE"))
    classification: Mapped[str] = mapped_column(String) # ALLOWED, LIMITED, BLOCKED
    safety_evaluation: Mapped[dict] = mapped_column(JSON)
    # Instructor review queue (F5 HITL for blocked Q&A)
    review_status: Mapped[str | None] = mapped_column(String, nullable=True) # PENDING, APPROVED, REJECTED
    block_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    blocked_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)

class GuardrailRule(Base):
    __tablename__ = "guardrail_rules"
    code: Mapped[str] = mapped_column(String, primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # core_locked rules (anti prompt-injection / data-leak) can't be disabled
    # through the Admin UI at all -- a safety net against a compromised or
    # careless Admin account turning off the system's own guardrails.
    core_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    current_version: Mapped[str | None] = mapped_column(String, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class GuardrailPolicyVersion(Base):
    """One snapshot of all guardrail rules' enabled state, published every
    time an Admin changes a rule. Gives the Admin Console a real audit trail
    ("what did the policy look like on date X") instead of only exposing
    the current enabled/disabled flags.
    """

    __tablename__ = "guardrail_policy_versions"
    version: Mapped[str] = mapped_column(String, primary_key=True)
    rules_snapshot: Mapped[dict] = mapped_column(JSON)
    source_version: Mapped[str | None] = mapped_column(String, nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AdminCourseOverride(Base):
    __tablename__ = "admin_course_overrides"
    subject_code: Mapped[str] = mapped_column(String, primary_key=True)
    subject_name: Mapped[str | None] = mapped_column(String, nullable=True)
    semester: Mapped[str | None] = mapped_column(String, nullable=True)
    is_added: Mapped[bool] = mapped_column(Boolean, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_by: Mapped[str | None] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

class CourseIngestJob(Base):
    __tablename__ = "course_ingest_jobs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_code: Mapped[str] = mapped_column(String, index=True)
    document_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    operation: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class WeeklyReflection(Base):
    __tablename__ = "weekly_reflections"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    week_number: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    metrics: Mapped[dict] = mapped_column(JSON)

    student: Mapped[User] = relationship(back_populates="weekly_reflections")

class RiskSignal(Base):
    __tablename__ = "risk_signals"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    section_id: Mapped[str] = mapped_column(String, ForeignKey("course_sections.id", ondelete="CASCADE"))
    assignment_id: Mapped[str | None] = mapped_column(String, ForeignKey("assignments.id", ondelete="SET NULL"), nullable=True)
    risk_type: Mapped[str] = mapped_column(String) # LATE_SUBMISSION, ABANDONMENT, OVERLOAD, ACADEMIC_DECLINE, WEEKLY_GOAL_FAILURE
    risk_level: Mapped[str] = mapped_column(String) # LOW, MEDIUM, HIGH
    triggered_rules: Mapped[dict] = mapped_column(JSON)
    evidence: Mapped[dict] = mapped_column(JSON)
    recommended_action: Mapped[str] = mapped_column(Text)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_type: Mapped[str | None] = mapped_column(String, nullable=True)
    policy_version: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("risk_policies.policy_version", ondelete="SET NULL"), nullable=True
    )
    instructor_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    student: Mapped[User] = relationship(back_populates="risk_signals", foreign_keys=[student_id])

class InstructorIntervention(Base):
    __tablename__ = "instructor_interventions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    risk_signal_id: Mapped[str] = mapped_column(String, ForeignKey("risk_signals.id", ondelete="CASCADE"))
    instructor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    action_taken: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String) # PENDING, ACTIVE, COMPLETED
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class InstructorStudentNote(Base):
    """So ghi chu rieng cua GV ve 1 SV (khong gan voi risk case nao) - chi
    tac gia moi doc/xoa duoc, khong chia se cho GV khac cung day SV do."""
    __tablename__ = "instructor_student_notes"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    instructor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class RAGEvaluationCase(Base):
    __tablename__ = "rag_evaluation_cases"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))
    question: Mapped[str] = mapped_column(Text)
    reference_answer: Mapped[str] = mapped_column(Text)
    target_chunks: Mapped[dict] = mapped_column(JSON)

class RAGEvaluationResult(Base):
    __tablename__ = "rag_evaluation_results"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    evaluation_case_id: Mapped[str] = mapped_column(String, ForeignKey("rag_evaluation_cases.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(String)
    generated_answer: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column(Float)
    evaluation_metadata: Mapped[dict] = mapped_column(JSON)

class GuardrailEvaluationCase(Base):
    __tablename__ = "guardrail_evaluation_cases"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    prompt: Mapped[str] = mapped_column(Text)
    policy_context: Mapped[str] = mapped_column(Text)
    expected_classification: Mapped[str] = mapped_column(String) # ALLOWED, LIMITED, BLOCKED
    expected_action: Mapped[str] = mapped_column(Text)
    reference_response: Mapped[str] = mapped_column(Text)

class GuardrailEvaluationResult(Base):
    __tablename__ = "guardrail_evaluation_results"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    evaluation_case_id: Mapped[str] = mapped_column(String, ForeignKey("guardrail_evaluation_cases.id", ondelete="CASCADE"))
    run_id: Mapped[str] = mapped_column(String)
    generated_classification: Mapped[str] = mapped_column(String)
    generated_response: Mapped[str] = mapped_column(Text)
    is_safe: Mapped[bool] = mapped_column(Boolean)
    evaluation_metadata: Mapped[dict] = mapped_column(JSON)


# ── Semester setup (migrations/versions/20260821_semester_practice.py) ──────
# Tenant scoping is transitive via student_id -> User.organization_id, same
# pattern as StudyTask/DailyPlan reaching org scope through assignment/section.

class SemesterSetup(Base):
    __tablename__ = "semester_setups"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SemesterCourse(Base):
    __tablename__ = "semester_courses"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    semester_id: Mapped[str] = mapped_column(String, ForeignKey("semester_setups.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))

class SemesterWeekSlot(Base):
    __tablename__ = "semester_week_slots"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    semester_id: Mapped[str] = mapped_column(String, ForeignKey("semester_setups.id", ondelete="CASCADE"))
    weekday: Mapped[int] = mapped_column(Integer)
    slot_id: Mapped[int] = mapped_column(Integer)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))

class SemesterException(Base):
    __tablename__ = "semester_exceptions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    semester_id: Mapped[str] = mapped_column(String, ForeignKey("semester_setups.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    label: Mapped[str] = mapped_column(String, default="")


# ── Academic terms + exams (org-scoped directly — see migration docstring) ──

class AcademicTerm(Base):
    __tablename__ = "academic_terms"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    organization_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id"))
    name: Mapped[str] = mapped_column(String)
    start_date: Mapped[date] = mapped_column(Date)
    study_weeks: Mapped[int] = mapped_column(Integer, default=10)
    exam_weeks: Mapped[int] = mapped_column(Integer, default=2)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CourseExam(Base):
    __tablename__ = "course_exams"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    term_id: Mapped[str] = mapped_column(String, ForeignKey("academic_terms.id", ondelete="CASCADE"))
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String) # MIDTERM, FINAL, PROGRESS_TEST

class CourseExamSession(Base):
    __tablename__ = "course_exam_sessions"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    exam_id: Mapped[str] = mapped_column(String, ForeignKey("course_exams.id", ondelete="CASCADE"))
    exam_date: Mapped[date] = mapped_column(Date)
    slot_id: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String, default="Ca 1")

class CourseExamSessionStudent(Base):
    __tablename__ = "course_exam_session_students"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, ForeignKey("course_exam_sessions.id", ondelete="CASCADE"))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))

class ClassActivity(Base):
    __tablename__ = "class_activities"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))
    activity_date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String) # LECTURE_HELD, CANCELLED, MAKEUP, NOTE
    title: Mapped[str] = mapped_column(String, default="")
    created_by: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ── Practice sets (course-scoped — org reached via course_id) ───────────────

class PracticeSet(Base):
    __tablename__ = "practice_sets"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id", ondelete="CASCADE"))
    course_code: Mapped[str] = mapped_column(String)
    slide_key: Mapped[str] = mapped_column(String)
    week_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String) # DRAFT, PENDING_REVIEW, PUBLISHED, REJECTED
    language: Mapped[str] = mapped_column(String, default="vi")
    requested_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PracticeItem(Base):
    __tablename__ = "practice_items"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    set_id: Mapped[str] = mapped_column(String, ForeignKey("practice_sets.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String) # MCQ, FLASHCARD
    sort_order: Mapped[int] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    correct_key: Mapped[str | None] = mapped_column(String, nullable=True)
    answer: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[str] = mapped_column(Text, default="")
    source_label: Mapped[str] = mapped_column(String, default="")


# ── Risk policy versioning (migrations/versions/20260823_risk_policy_and_admin_settings.py) ──
# mục 14.1 PROJECT_CONTEXT.md: mỗi bộ ngưỡng/trọng số là 1 version bất biến —
# publish tạo version mới, không sửa/ghi đè version cũ. `RiskSignal.policy_version`
# ở trên ghim lại version đã dùng lúc tính điểm cho đúng alert đó.

class RiskPolicy(Base):
    __tablename__ = "risk_policies"
    policy_version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    signal_weights: Mapped[dict] = mapped_column(JSON)
    signal_thresholds: Mapped[dict] = mapped_column(JSON)
    severity_bands: Mapped[list] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    rolled_back_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MockLmsSyncVersion(Base):
    """Mock LMS sync history (mục 6.6) — same immutable-append pattern as
    RiskPolicy: no `is_active` flag, "current" = MAX(sync_version), every
    publish/rollback inserts a new row so history stays linear and auditable."""

    __tablename__ = "mock_lms_sync_versions"
    sync_version: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # List of {course_code, assignment_id, field, before, after, winning_tier}.
    payload: Mapped[list] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    rolled_back_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ── Admin settings (migrations/versions/20260823_risk_policy_and_admin_settings.py) ──
# Một hàng / tổ chức (mục 6.5: demo mode, tự động cảnh báo, học kỳ mặc định).

class AdminSettings(Base):
    __tablename__ = "admin_settings"
    organization_id: Mapped[str] = mapped_column(String, ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True)
    demo_mode_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_risk_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    default_semester: Mapped[str] = mapped_column(String, default="Fall2026")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

class DataRequest(Base):
    __tablename__ = "data_requests"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    requester_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    # Nullable + fail-closed (excluded from list/detail queries when NULL),
    # same pattern as audit_logs.organization_id — see
    # migrations/versions/20260825_audit_log_org_scoping.py. Without this an
    # admin from org A could see/process org B's DSAR requests.
    organization_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("organizations.id"), nullable=True, index=True
    )
    request_type: Mapped[str] = mapped_column(String) # ACCESS, EXPORT, RECTIFY, DELETE
    status: Mapped[str] = mapped_column(String) # PENDING, IN_PROGRESS, COMPLETED, REJECTED
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    preview_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    result_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    processed_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

