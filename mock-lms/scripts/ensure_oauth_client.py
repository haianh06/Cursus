"""Ensure the configured Cursus OAuth client exists in the local LMS DB.

The Docker entrypoint calls this on every start. Re-hashing the same configured
secret is intentional: a persistent volume can be moved between containers,
while the environment remains the single source of truth for local demo auth.
"""
from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import ENGINE, Base, SessionLocal  # noqa: E402
from app.models import OAuthClient  # noqa: E402
from app.security import hash_secret  # noqa: E402


def main() -> None:
    client_id = os.environ.get("MOCK_LMS_CLIENT_ID")
    client_secret = os.environ.get("MOCK_LMS_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("OAuth bootstrap skipped: MOCK_LMS_CLIENT_ID/SECRET not configured.")
        return

    Base.metadata.create_all(bind=ENGINE)
    db = SessionLocal()
    try:
        client = db.get(OAuthClient, client_id)
        if client is None:
            client = OAuthClient(
                client_id=client_id,
                name="Cursus (Tool)",
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
            db.add(client)
        client.client_secret_hash = hash_secret(client_secret)
        db.commit()
    finally:
        db.close()
    print(f"Ensured OAuth client {client_id!r}.")


if __name__ == "__main__":
    main()
