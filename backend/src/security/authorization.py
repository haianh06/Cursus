"""RBAC and permission-based FastAPI dependency guards.

- `require_roles` implements coarse-grained RBAC (which roles may reach a
  router/route at all).
- `require_permission` implements fine-grained permission checks via the
  policy engine (`src.security.policy.is_allowed`), for actions gated on a
  specific (resource, permission) pair rather than role alone.

Both guards depend on `get_current_user_from_token`, so an unauthenticated
request is rejected with 401 before role/permission checks (403) run.
"""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status

from src.api.auth import get_current_user_from_token
from src.db.models import User, UserRole
from src.security.permissions import Permission, Resource
from src.security.policy import is_allowed


def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    allowed_role_values = {role.value for role in allowed_roles}

    async def guard(
        current_user: User = Depends(get_current_user_from_token),
    ) -> User:
        role = _role_to_string(current_user.role)
        if role not in allowed_role_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role",
            )
        return current_user

    return guard


def require_permission(resource: Resource, permission: Permission) -> Callable[..., User]:
    async def guard(
        current_user: User = Depends(get_current_user_from_token),
    ) -> User:
        if not is_allowed(current_user.role, resource, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permission",
            )
        return current_user

    return guard


def _role_to_string(role: str | UserRole) -> str:
    if isinstance(role, UserRole):
        return role.value
    return role
