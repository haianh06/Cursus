from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
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


class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    client_id: Mapped[str] = mapped_column(String, primary_key=True)
    client_secret_hash: Mapped[str] = mapped_column(String)
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
