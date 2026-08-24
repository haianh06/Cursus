from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import get_settings

settings = get_settings()

_connect_args: dict = {}
_engine_kwargs: dict = {
    "pool_pre_ping": True,
}

if settings.database_url.startswith("sqlite"):
    _connect_args = {"check_same_thread": False}
    # SQLite does not use the same pool settings as Postgres.
    _engine_kwargs = {"connect_args": _connect_args}
else:
    _engine_kwargs = {
        "pool_pre_ping": True,
        "pool_size": 5,
        "max_overflow": 10,
    }

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
