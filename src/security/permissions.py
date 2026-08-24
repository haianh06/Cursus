"""Permission and Resource vocabulary for the authorization policy layer.

This module defines *what actions exist* (Permission) and *what they apply to*
(Resource), plus the static role -> resource -> permission matrix. It contains
no request/DB concerns; see `src.security.policy` for the decision function
and `src.security.authorization` / `src.security.ownership` for the FastAPI
dependency guards that use it.
"""

from __future__ import annotations

from enum import StrEnum

from src.db.models import UserRole


class Permission(StrEnum):
    """Generic action verbs supported by the authorization model."""

    READ = "READ"
    # A student's own raw records (not aggregate/summary data): distinct from
    # READ so a route can require this specifically and never be satisfied by
    # a role that only has ordinary READ. Every route gated on this permission
    # also runs the fail-closed audit-before-release pattern in
    # src/api/admin_student360.py -- the permission check and the audit write
    # are two independent layers, deliberately redundant with each other.
    READ_SENSITIVE = "READ_SENSITIVE"
    WRITE = "WRITE"
    DELETE = "DELETE"
    APPROVE = "APPROVE"
    MANAGE = "MANAGE"


class Resource(StrEnum):
    """Domain resource types protected by the authorization model."""

    PLAN = "PLAN"
    CHAT = "CHAT"
    ASSIGNMENT = "ASSIGNMENT"
    SUBMISSION = "SUBMISSION"
    REFLECTION = "REFLECTION"
    STUDENT_DOCUMENT = "STUDENT_DOCUMENT"
    COURSE = "COURSE"
    KPI = "KPI"
    RISK = "RISK"
    RISK_CASE = "RISK_CASE"
    INTERVENTION = "INTERVENTION"
    GUARDRAIL = "GUARDRAIL"
    SESSION = "SESSION"
    AUDIT = "AUDIT"
    USER = "USER"
    SETTING = "SETTING"
    INTEGRATION = "INTEGRATION"


# Static Role -> Resource -> Permission matrix.
#
# MANAGE on a resource implies full control (read/write/delete/approve) for
# that resource; this is expanded by `src.security.policy.is_allowed`, so it
# does not need to be spelled out permission-by-permission below.
PERMISSION_MATRIX: dict[UserRole, dict[Resource, frozenset[Permission]]] = {
    UserRole.STUDENT: {
        Resource.PLAN: frozenset({Permission.READ, Permission.WRITE}),
        Resource.CHAT: frozenset({Permission.READ, Permission.WRITE}),
        Resource.ASSIGNMENT: frozenset({Permission.READ}),
        Resource.COURSE: frozenset({Permission.READ}),
        Resource.SESSION: frozenset({Permission.READ, Permission.DELETE}),
    },
    UserRole.INSTRUCTOR: {
        Resource.COURSE: frozenset({Permission.READ}),
        Resource.ASSIGNMENT: frozenset({Permission.READ}),
        Resource.RISK: frozenset({Permission.READ, Permission.APPROVE}),
        Resource.INTERVENTION: frozenset({Permission.WRITE, Permission.APPROVE}),
        Resource.GUARDRAIL: frozenset({Permission.READ, Permission.APPROVE}),
        Resource.SESSION: frozenset({Permission.READ, Permission.DELETE}),
    },
    UserRole.ADMIN: {
        # MANAGE already implies READ (src.security.policy.is_allowed), so
        # READ_SENSITIVE below is additive, not a narrowing -- it exists so
        # the 13 raw-data routes in admin_student360.py can declare exactly
        # which capability they need instead of relying on the same broad
        # MANAGE grant these resources also carry for unrelated admin config
        # actions (e.g. CHAT here also gates guardrail-rule config, RISK
        # also gates risk-policy config -- neither of those reads a specific
        # student's own records).
        Resource.PLAN: frozenset({Permission.MANAGE, Permission.READ_SENSITIVE}),
        Resource.CHAT: frozenset({Permission.MANAGE, Permission.READ_SENSITIVE}),
        Resource.ASSIGNMENT: frozenset({Permission.MANAGE}),
        Resource.SUBMISSION: frozenset({Permission.READ_SENSITIVE}),
        Resource.REFLECTION: frozenset({Permission.READ_SENSITIVE}),
        Resource.STUDENT_DOCUMENT: frozenset({Permission.READ_SENSITIVE}),
        Resource.COURSE: frozenset({Permission.MANAGE}),
        Resource.KPI: frozenset({Permission.READ}),
        Resource.RISK: frozenset({Permission.MANAGE}),
        Resource.RISK_CASE: frozenset({Permission.READ_SENSITIVE}),
        Resource.INTERVENTION: frozenset({Permission.MANAGE, Permission.READ_SENSITIVE}),
        Resource.GUARDRAIL: frozenset({Permission.MANAGE}),
        Resource.SESSION: frozenset({Permission.MANAGE, Permission.READ_SENSITIVE}),
        Resource.AUDIT: frozenset({Permission.READ, Permission.MANAGE}),
        Resource.USER: frozenset({Permission.MANAGE}),
        Resource.SETTING: frozenset({Permission.MANAGE}),
    },
    UserRole.SERVICE_ACCOUNT: {
        Resource.INTEGRATION: frozenset({Permission.MANAGE}),
        Resource.COURSE: frozenset({Permission.WRITE}),
        Resource.ASSIGNMENT: frozenset({Permission.WRITE}),
    },
}
