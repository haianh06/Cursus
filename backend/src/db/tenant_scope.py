"""FastAPI dependency that makes Postgres Row Level Security the real
enforcement boundary, instead of the inert defense-in-depth policies added
in migrations/versions/20260812_organizations_and_tenancy.py.

Why this exists (context for whoever wires it in): those RLS policies use
``USING (organization_id = current_setting('app.current_org_id', true))``.
That session variable is never set anywhere in the app today (verified via
``grep -rn "current_org_id" src/`` — zero hits before this file), so even
after removing ``BYPASSRLS`` from the connection role, RLS would evaluate
``organization_id = NULL`` on every query and block **all** rows for
**everyone** — a self-inflicted outage, not a security fix. This dependency
is the missing piece that sets the session variable from the authenticated
user's ``organization_id`` before a scoped query runs.

Status as of 2026-08-22: written and unit-testable, but **not yet wired
into any route** — every endpoint still depends on the plain ``get_db``
from ``src.db.connection``. Swapping ``Depends(get_db)`` for
``Depends(get_scoped_db)`` across ~40+ endpoints is the next step, done
deliberately (reviewed per-router, tested against a real Postgres) rather
than blindly here — see docs/decisions/rls-migration-plan.md step 6.
"""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db.connection import get_db
from src.db.models import User


def get_scoped_db(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
) -> Generator[Session, None, None]:
    """Drop-in replacement for ``Depends(get_db)`` on routes that must be
    subject to Postgres RLS. Sets ``app.current_org_id`` for the lifetime of
    the current transaction (``set_config(..., is_local=true)`` — resets
    automatically on commit/rollback, never leaks across pooled connections
    the way a bare ``SET`` without LOCAL would).

    No-op on SQLite (used by the fast local/CI test suite — see
    ``tests/conftest.py``): SQLite has no RLS concept and no
    ``current_setting`` function, so calling this would just error there for
    no safety benefit.

    Fails closed, not open: a user with no ``organization_id`` gets the
    session variable set to an empty string, which matches no real
    organization's id — RLS then hides every row rather than showing
    everything (the opposite of what an unset/NULL setting would do).
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(
            text("SELECT set_config('app.current_org_id', :org_id, true)"),
            {"org_id": current_user.organization_id or ""},
        )
    try:
        yield db
    finally:
        pass  # closing the session is get_db's job, not ours — same object.
