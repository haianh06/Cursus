"""Register an OAuth client_credentials client. Prints the plaintext secret ONCE --
only the argon2 hash is stored, same discipline as password storage elsewhere in the
main project.

Usage:
    python scripts/create_oauth_client.py --client-id cursus-tool --name "Cursus (Tool)"
"""
from __future__ import annotations

import argparse
import secrets
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.db import Base, ENGINE, SessionLocal  # noqa: E402
from app.models import OAuthClient  # noqa: E402
from app.security import hash_secret  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--client-id", required=True)
    parser.add_argument("--name", default="")
    args = parser.parse_args()

    raw_secret = secrets.token_urlsafe(32)

    Base.metadata.create_all(bind=ENGINE)
    db = SessionLocal()
    try:
        existing = db.get(OAuthClient, args.client_id)
        if existing:
            print(f"client_id {args.client_id!r} already exists -- rotating its secret.")
            existing.client_secret_hash = hash_secret(raw_secret)
        else:
            db.add(
                OAuthClient(
                    client_id=args.client_id,
                    client_secret_hash=hash_secret(raw_secret),
                    name=args.name or args.client_id,
                    created_at=datetime.utcnow(),
                )
            )
        db.commit()
    finally:
        db.close()

    print()
    print(f"client_id     = {args.client_id}")
    print(f"client_secret = {raw_secret}")
    print()
    print("Save this secret now -- it is not stored anywhere in plaintext and cannot be recovered.")


if __name__ == "__main__":
    main()
