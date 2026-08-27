"""Quản trị lớp học cho Admin — phần "cấp phát" mà trước đây không role nào có.

Trước dịch vụ này, `CourseSection`/`Enrollment` chỉ được tạo bởi wizard học kỳ
của sinh viên và các script seed, nên Admin không có cách nào sửa việc gán sai
giảng viên. Mọi truy vấn ở đây đều fail-closed theo `organization_id` của admin
đang gọi.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.db import models


class SectionNotFoundError(LookupError):
    """Lớp không tồn tại, hoặc thuộc tổ chức khác — trả 404 cho cả 2 để không
    lộ sự tồn tại của dữ liệu tổ chức khác."""


class SectionInUseError(RuntimeError):
    """Lớp còn sinh viên đang học."""


def _course_belongs_to(course: models.Course, organization_id: str | None) -> bool:
    """Catalog môn học đang dùng chung giữa các tổ chức (`Course.organization_id`
    có thể NULL) — quy tắc duy nhất cho cả đọc lẫn ghi, đặt ở một chỗ để
    `list_sections` và `_require_course` không bao giờ lệch nhau."""
    return course.organization_id is None or course.organization_id == organization_id


def _require_course(db: Session, course_id: str, organization_id: str | None) -> models.Course:
    course = db.get(models.Course, course_id)
    if course is None or not _course_belongs_to(course, organization_id):
        raise SectionNotFoundError("course_not_found")
    return course


def _require_instructor(
    db: Session, instructor_id: str | None, organization_id: str | None
) -> models.User | None:
    if instructor_id is None:
        return None
    user = db.get(models.User, instructor_id)
    if user is None or user.organization_id != organization_id:
        raise SectionNotFoundError("instructor_not_found")
    if str(user.role) not in {
        models.UserRole.INSTRUCTOR.value,
        models.UserRole.INSTRUCTOR,
    }:
        raise SectionNotFoundError("instructor_not_found")
    return user


def _enrolled_count(db: Session, section_id: str) -> int:
    return (
        db.query(models.Enrollment)
        .filter_by(section_id=section_id, status=models.EnrollmentStatus.ENROLLED.value)
        .count()
    )


def serialize(db: Session, section: models.CourseSection) -> dict:
    course = db.get(models.Course, section.course_id)
    instructor = db.get(models.User, section.instructor_id) if section.instructor_id else None
    return {
        "id": section.id,
        "course_code": course.code if course else "",
        "course_name": course.name if course else "",
        "section_code": section.section_code or "",
        "term": section.term or "",
        "instructor_id": section.instructor_id,
        "instructor_name": instructor.full_name if instructor else None,
        "enrolled_count": _enrolled_count(db, section.id),
    }


def list_sections(db: Session, *, organization_id: str | None) -> list[dict]:
    rows = (
        db.query(models.CourseSection, models.Course)
        .join(models.Course, models.Course.id == models.CourseSection.course_id)
        .order_by(models.Course.code, models.CourseSection.section_code)
        .all()
    )
    return [
        serialize(db, section)
        for section, course in rows
        if _course_belongs_to(course, organization_id)
    ]


def create_section(
    db: Session,
    *,
    organization_id: str | None,
    course_id: str,
    section_code: str,
    term: str,
    instructor_id: str | None,
) -> dict:
    _require_course(db, course_id, organization_id)
    _require_instructor(db, instructor_id, organization_id)
    section = models.CourseSection(
        id=f"sec_adm_{uuid.uuid4().hex[:12]}",
        course_id=course_id,
        instructor_id=instructor_id,
        term=term[:32],
        section_code=section_code[:32],
    )
    db.add(section)
    db.flush()
    return serialize(db, section)


def _require_section(
    db: Session, section_id: str, organization_id: str | None
) -> models.CourseSection:
    section = db.get(models.CourseSection, section_id)
    if section is None:
        raise SectionNotFoundError("section_not_found")
    _require_course(db, section.course_id, organization_id)
    return section


def update_section(
    db: Session,
    *,
    organization_id: str | None,
    section_id: str,
    section_code: str | None,
    term: str | None,
    instructor_id: str | None,
    instructor_field_present: bool,
) -> dict:
    section = _require_section(db, section_id, organization_id)
    if section_code is not None:
        section.section_code = section_code[:32]
    if term is not None:
        section.term = term[:32]
    if instructor_field_present:
        _require_instructor(db, instructor_id, organization_id)
        section.instructor_id = instructor_id
    db.flush()
    return serialize(db, section)


def delete_section(db: Session, *, organization_id: str | None, section_id: str) -> None:
    section = _require_section(db, section_id, organization_id)
    if _enrolled_count(db, section.id) > 0:
        raise SectionInUseError("section_has_enrolled_students")
    db.delete(section)
    db.flush()


def list_roster(db: Session, *, organization_id: str | None, section_id: str) -> list[dict]:
    _require_section(db, section_id, organization_id)
    rows = (
        db.query(models.Enrollment, models.User)
        .join(models.User, models.User.id == models.Enrollment.student_id)
        .filter(
            models.Enrollment.section_id == section_id,
            models.Enrollment.status == models.EnrollmentStatus.ENROLLED.value,
        )
        .order_by(models.User.full_name)
        .all()
    )
    return [
        {
            "studentId": user.id,
            "fullName": user.full_name,
            "email": user.email,
            "status": enrollment.status,
        }
        for enrollment, user in rows
    ]


def add_to_roster(
    db: Session, *, organization_id: str | None, section_id: str, student_id: str
) -> None:
    _require_section(db, section_id, organization_id)
    student = db.get(models.User, student_id)
    if student is None or student.organization_id != organization_id:
        raise SectionNotFoundError("student_not_found")
    if str(student.role) not in {models.UserRole.STUDENT.value, models.UserRole.STUDENT}:
        raise SectionNotFoundError("student_not_found")
    existing = (
        db.query(models.Enrollment)
        .filter_by(student_id=student_id, section_id=section_id)
        .first()
    )
    if existing is not None:
        # Idempotent: bấm 2 lần không tạo 2 dòng, và cũng không báo lỗi —
        # Admin thao tác hàng loạt, một cú double-click không nên thành 409.
        existing.status = models.EnrollmentStatus.ENROLLED.value
        db.flush()
        return
    db.add(
        models.Enrollment(
            id=f"enr_adm_{uuid.uuid4().hex[:12]}",
            student_id=student_id,
            section_id=section_id,
            status=models.EnrollmentStatus.ENROLLED.value,
        )
    )
    db.flush()


def remove_from_roster(
    db: Session, *, organization_id: str | None, section_id: str, student_id: str
) -> None:
    _require_section(db, section_id, organization_id)
    enrollment = (
        db.query(models.Enrollment)
        .filter_by(student_id=student_id, section_id=section_id)
        .first()
    )
    if enrollment is None:
        raise SectionNotFoundError("enrollment_not_found")
    # Soft-delete: mark as DROPPED instead of hard-deleting the row.
    # This preserves enrolled_at, grade, and other metadata while preventing
    # access and preventing the student from appearing in list_roster().
    enrollment.status = models.EnrollmentStatus.DROPPED.value
    db.flush()
