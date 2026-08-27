"""Unit tests for the authorization policy engine (role + permission matrix).

These tests exercise `src.security.policy.is_allowed` directly, independent
of FastAPI/HTTP, to validate RBAC and permission decisions for every
supported role: Student, Instructor, Admin, Service Account.
"""

from src.db.models import UserRole
from src.security.permissions import Permission, Resource
from src.security.policy import is_allowed


def test_student_can_read_and_write_own_plan_resource():
    assert is_allowed(UserRole.STUDENT, Resource.PLAN, Permission.READ) is True
    assert is_allowed(UserRole.STUDENT, Resource.PLAN, Permission.WRITE) is True


def test_student_cannot_delete_plan_or_approve_risk():
    assert is_allowed(UserRole.STUDENT, Resource.PLAN, Permission.DELETE) is False
    assert is_allowed(UserRole.STUDENT, Resource.RISK, Permission.APPROVE) is False


def test_student_has_no_access_to_audit_or_intervention():
    assert is_allowed(UserRole.STUDENT, Resource.AUDIT, Permission.READ) is False
    assert is_allowed(UserRole.STUDENT, Resource.INTERVENTION, Permission.WRITE) is False


def test_instructor_can_approve_risk_and_write_intervention():
    assert is_allowed(UserRole.INSTRUCTOR, Resource.RISK, Permission.APPROVE) is True
    assert is_allowed(UserRole.INSTRUCTOR, Resource.INTERVENTION, Permission.WRITE) is True


def test_instructor_cannot_write_plan_or_manage_users():
    assert is_allowed(UserRole.INSTRUCTOR, Resource.PLAN, Permission.WRITE) is False
    assert is_allowed(UserRole.INSTRUCTOR, Resource.USER, Permission.MANAGE) is False


def test_admin_manage_implies_full_control_over_resource():
    for permission in (
        Permission.READ,
        Permission.WRITE,
        Permission.DELETE,
        Permission.APPROVE,
    ):
        assert is_allowed(UserRole.ADMIN, Resource.PLAN, permission) is True
        assert is_allowed(UserRole.ADMIN, Resource.RISK, permission) is True


def test_admin_can_manage_users_and_read_audit():
    assert is_allowed(UserRole.ADMIN, Resource.USER, Permission.MANAGE) is True
    assert is_allowed(UserRole.ADMIN, Resource.AUDIT, Permission.READ) is True


def test_service_account_can_only_manage_integration_and_write_sync_resources():
    assert is_allowed(UserRole.SERVICE_ACCOUNT, Resource.INTEGRATION, Permission.MANAGE) is True
    assert is_allowed(UserRole.SERVICE_ACCOUNT, Resource.COURSE, Permission.WRITE) is True
    assert is_allowed(UserRole.SERVICE_ACCOUNT, Resource.ASSIGNMENT, Permission.WRITE) is True


def test_service_account_cannot_read_plans_or_chats():
    assert is_allowed(UserRole.SERVICE_ACCOUNT, Resource.PLAN, Permission.READ) is False
    assert is_allowed(UserRole.SERVICE_ACCOUNT, Resource.CHAT, Permission.READ) is False
    assert is_allowed(UserRole.SERVICE_ACCOUNT, Resource.USER, Permission.MANAGE) is False


def test_is_allowed_accepts_role_as_plain_string():
    assert is_allowed("STUDENT", Resource.PLAN, Permission.READ) is True
    assert is_allowed("STUDENT", Resource.RISK, Permission.APPROVE) is False


def test_admin_has_read_sensitive_on_student_360_raw_data_resources():
    for resource in (
        Resource.PLAN,
        Resource.CHAT,
        Resource.SUBMISSION,
        Resource.REFLECTION,
        Resource.STUDENT_DOCUMENT,
        Resource.RISK_CASE,
        Resource.INTERVENTION,
        Resource.SESSION,
    ):
        assert is_allowed(UserRole.ADMIN, resource, Permission.READ_SENSITIVE) is True


def test_student_and_instructor_have_no_read_sensitive_anywhere():
    for role in (UserRole.STUDENT, UserRole.INSTRUCTOR, UserRole.SERVICE_ACCOUNT):
        assert is_allowed(role, Resource.SUBMISSION, Permission.READ_SENSITIVE) is False
        assert is_allowed(role, Resource.RISK_CASE, Permission.READ_SENSITIVE) is False


def test_admin_read_sensitive_does_not_leak_onto_resources_without_manage():
    # KPI is the one admin resource granted plain READ only (no MANAGE, so
    # the MANAGE-implies-everything shortcut in is_allowed() can't mask
    # this) -- confirms READ_SENSITIVE wasn't accidentally granted broadly.
    assert is_allowed(UserRole.ADMIN, Resource.KPI, Permission.READ_SENSITIVE) is False
