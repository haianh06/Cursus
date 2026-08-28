"""B5 — chọn lớp ngay khi mời giảng viên.

Trước task này, mời một giảng viên mới là việc hai bước rời nhau: admin gửi lời
mời, chờ người kia đăng ký xong, rồi mới quay lại màn Lớp học gán tay. Khoảng
giữa hai bước đó là lúc lớp nằm không có ai phụ trách.
"""

import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from tests.support.invite_helpers import create_test_invite
from tests.support.semester_practice_fixtures import (
    PASSWORD,
    auth_headers,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


def _make_section(*, course_id: str, instructor_id: str | None = None) -> str:
    section_id = f"sec_inv_{uuid.uuid4().hex[:10]}"
    db = SessionLocal()
    try:
        db.add(
            models.CourseSection(
                id=section_id,
                course_id=course_id,
                instructor_id=instructor_id,
                term="Fall2026",
                section_code=f"SE-{section_id[-4:]}",
            )
        )
        db.commit()
    finally:
        db.close()
    return section_id


@pytest.fixture
def invite_org():
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"inv-sec-{suffix}", name="Invite Section Org")
    admin_email = f"admin.inv.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    course_id = ensure_course(code=f"ZZINV{suffix[:3].upper()}", org_id=org_id)
    return {
        "suffix": suffix,
        "org_id": org_id,
        "admin_email": admin_email,
        "course_id": course_id,
    }


@pytest.mark.asyncio
async def test_admin_attaches_a_section_to_an_instructor_invite(client, invite_org):
    section_id = _make_section(course_id=invite_org["course_id"])
    token = await login(client, invite_org["admin_email"])

    created = await client.post(
        "/api/v1/admin/invites",
        headers=auth_headers(token),
        json={
            "email": f"inst.inv.{invite_org['suffix']}@test.local",
            "full_name": "Invited Instructor",
            "role": "INSTRUCTOR",
            "section_id": section_id,
        },
    )

    assert created.status_code == 201, created.text
    assert created.json()["section_id"] == section_id

    db = SessionLocal()
    try:
        invite = db.get(models.OrgInvite, created.json()["id"])
        assert invite.section_id == section_id
    finally:
        db.close()


@pytest.mark.asyncio
async def test_the_invited_instructor_owns_the_section_once_they_register(
    client, invite_org
):
    section_id = _make_section(course_id=invite_org["course_id"])
    email = f"inst.reg.{invite_org['suffix']}@test.local"
    invite_token = create_test_invite(
        email,
        role="INSTRUCTOR",
        full_name="Registering Instructor",
        org_slug=f"inv-sec-{invite_org['suffix']}",
        section_id=section_id,
    )

    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Registering Instructor",
            "invite_token": invite_token,
        },
    )

    assert registered.status_code == 201, registered.text

    db = SessionLocal()
    try:
        user = db.query(models.User).filter_by(email=email).one()
        section = db.get(models.CourseSection, section_id)
        assert section.instructor_id == user.id
    finally:
        db.close()


@pytest.mark.asyncio
async def test_registration_never_steals_a_section_that_already_has_an_instructor(
    client, invite_org
):
    """Giữa lúc gửi lời mời và lúc người kia đăng ký, admin vẫn có thể gán lớp
    cho người khác ở màn Lớp học. Bản gán sau cùng đó phải thắng — lời mời cũ
    không được âm thầm cướp lại lớp."""
    sitting_instructor = ensure_user(
        email=f"inst.sitting.{invite_org['suffix']}@test.local",
        org_id=invite_org["org_id"],
        role=models.UserRole.INSTRUCTOR,
    )
    section_id = _make_section(
        course_id=invite_org["course_id"], instructor_id=sitting_instructor
    )
    email = f"inst.late.{invite_org['suffix']}@test.local"
    invite_token = create_test_invite(
        email,
        role="INSTRUCTOR",
        full_name="Late Instructor",
        org_slug=f"inv-sec-{invite_org['suffix']}",
        section_id=section_id,
    )

    registered = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Late Instructor",
            "invite_token": invite_token,
        },
    )

    assert registered.status_code == 201, registered.text

    db = SessionLocal()
    try:
        section = db.get(models.CourseSection, section_id)
        assert section.instructor_id == sitting_instructor
    finally:
        db.close()


@pytest.mark.asyncio
async def test_a_section_from_another_organization_is_not_found(client, invite_org):
    other_org = ensure_org(
        slug=f"inv-other-{invite_org['suffix']}", name="Other Invite Org"
    )
    other_course = ensure_course(
        code=f"ZZOTH{invite_org['suffix'][:3].upper()}", org_id=other_org
    )
    foreign_section = _make_section(course_id=other_course)
    token = await login(client, invite_org["admin_email"])

    response = await client.post(
        "/api/v1/admin/invites",
        headers=auth_headers(token),
        json={
            "email": f"inst.foreign.{invite_org['suffix']}@test.local",
            "full_name": "Foreign Section",
            "role": "INSTRUCTOR",
            "section_id": foreign_section,
        },
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_a_student_invite_may_not_carry_a_section(client, invite_org):
    """`section_id` gán người được mời làm GV phụ trách lớp. Với vai trò khác
    thì trường này không có nghĩa gì — từ chối thẳng thay vì lặng lẽ bỏ qua."""
    section_id = _make_section(course_id=invite_org["course_id"])
    token = await login(client, invite_org["admin_email"])

    response = await client.post(
        "/api/v1/admin/invites",
        headers=auth_headers(token),
        json={
            "email": f"stu.inv.{invite_org['suffix']}@test.local",
            "full_name": "Student With Section",
            "role": "STUDENT",
            "section_id": section_id,
        },
    )

    assert response.status_code == 400, response.text
