"""Input DTOs for the Authentication service.

The service layer depends on these plain dataclasses instead of the FastAPI
request models in `src.api.auth_schemas`, so `AuthService` never imports from
the API layer (Clean Architecture dependency rule: inner layers must not
depend on outer layers). The router is responsible for mapping its Pydantic
request models onto these DTOs before calling the service.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterInput:
    """Registration is invite-only — there is no client-supplied role or
    organization here. Both are resolved server-side from the invite token."""

    email: str
    password: str
    full_name: str
    invite_token: str


@dataclass(frozen=True)
class LoginInput:
    email: str
    password: str
    remember_me: bool = False
