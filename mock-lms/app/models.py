from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class PlatformCourse(Base):
    __tablename__ = "platform_courses"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    semester: Mapped[str] = mapped_column(String)
    credit: Mapped[int] = mapped_column(Integer, default=0)

    assignments: Mapped[list["PlatformAssignment"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )


class PlatformAssignment(Base):
    __tablename__ = "platform_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    course_id: Mapped[str] = mapped_column(ForeignKey("platform_courses.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    due_at: Mapped[datetime] = mapped_column(DateTime)
    points_possible: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    course: Mapped[PlatformCourse] = relationship(back_populates="assignments")


class Syllabus(Base):
    """One subject's full detail (materials/CLOs/session plan/question bank/
    assessment structure) -- ported from the FLM Learning Materials Portal
    prototype's mock data into real seeded rows (scripts/seed_curriculum.py),
    not client-side hardcoding. Only subjects with genuine detailed content
    get a row here; PlatformCourse (the Canvas-style catalog) covers every
    course, this is the richer subset.

    materials/clos/sessions/questions/assessments are stored as JSON rather
    than fully normalized tables: this is read-mostly reference content
    (a syllabus doesn't get queried by "find all sessions where..." the way
    assignments/due-dates do), and each row's shape exactly mirrors the
    frontend's FLMSyllabus type -- see mock-lms/frontend/src/types.ts.
    """

    __tablename__ = "syllabi"

    subject_code: Mapped[str] = mapped_column(String, primary_key=True)
    syllabus_id: Mapped[int] = mapped_column(Integer)
    syllabus_name: Mapped[str] = mapped_column(String)
    course_name_english: Mapped[str] = mapped_column(String)
    learning_teaching_method: Mapped[str] = mapped_column(String)
    no_credit: Mapped[int] = mapped_column(Integer)
    degree_level: Mapped[str] = mapped_column(String)
    time_allocation: Mapped[str] = mapped_column(String)
    pre_requisite: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    student_tasks: Mapped[str] = mapped_column(Text, default="")
    tools: Mapped[str] = mapped_column(String, default="")
    scoring_scale: Mapped[int] = mapped_column(Integer, default=10)
    decision_no: Mapped[str] = mapped_column(String, default="")
    approved_date: Mapped[str] = mapped_column(String, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=True)

    materials: Mapped[list] = mapped_column(JSON, default=list)
    clos: Mapped[list] = mapped_column(JSON, default=list)
    sessions: Mapped[list] = mapped_column(JSON, default=list)
    questions: Mapped[list] = mapped_column(JSON, default=list)
    assessments: Mapped[list] = mapped_column(JSON, default=list)


class CurriculumProgram(Base):
    """A degree program's full semester-by-semester subject plan (the
    "Khung Chương Trình Đào Tạo" view)."""

    __tablename__ = "curriculum_programs"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    faculty: Mapped[str] = mapped_column(String)
    decision_no: Mapped[str] = mapped_column(String)
    effective_year: Mapped[str] = mapped_column(String)
    total_credits: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text, default="")
    # [{ semesterNo, title, subjects: [{code, name, credits, semester,
    #    category, prerequisite, syllabusId, isActive}] }]
    semesters: Mapped[list] = mapped_column(JSON, default=list)


class PrerequisiteNode(Base):
    """One subject's position in the prerequisite dependency graph."""

    __tablename__ = "prerequisite_nodes"

    code: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    semester: Mapped[int] = mapped_column(Integer)
    credits: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = mapped_column(String)
    prerequisites: Mapped[list] = mapped_column(JSON, default=list)
    is_prerequisite_of: Mapped[list] = mapped_column(JSON, default=list)


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    client_id: Mapped[str] = mapped_column(String, primary_key=True)
    client_secret_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
