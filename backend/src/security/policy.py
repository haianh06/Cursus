"""Authorization policy engine.

Pure decision function over (role, resource, permission). Kept free of
FastAPI/DB concerns so it is trivially unit-testable; `src.security.authorization`
wraps it as a request dependency.
"""

from __future__ import annotations

from src.db.models import UserRole
from src.security.permissions import PERMISSION_MATRIX, Permission, Resource


def is_allowed(role: UserRole | str, resource: Resource, permission: Permission) -> bool:
    """Return True if `role` may perform `permission` on `resource`.

    MANAGE is treated as a superset: a role granted MANAGE on a resource is
    implicitly allowed READ, WRITE, DELETE, and APPROVE on that resource too.
    """
    role_enum = _to_role(role)
    granted = PERMISSION_MATRIX.get(role_enum, {}).get(resource, frozenset())
    if Permission.MANAGE in granted:
        return True
    return permission in granted


def _to_role(role: UserRole | str) -> UserRole:
    if isinstance(role, UserRole):
        return role
    return UserRole(role)
