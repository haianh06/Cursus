"""Own SQLite datastore -- deliberately not the Cursus Postgres DB.

Path is anchored to this file's directory so `uvicorn app.main:app` works the
same regardless of the caller's current working directory.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DB_PATH = Path(os.environ.get("MOCK_LMS_DB_PATH", Path(__file__).resolve().parent.parent / "mock_lms.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
ENGINE = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
