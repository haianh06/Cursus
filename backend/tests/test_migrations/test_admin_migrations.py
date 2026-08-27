import os
from importlib import import_module
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from src.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def upgrade_sqlite_to_head(database_path: Path) -> set[str]:
    database_path = database_path.resolve()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    database_url = f"sqlite:///{database_path.as_posix()}"
    previous_database_url = os.environ.get("DATABASE_URL")

    try:
        os.environ["DATABASE_URL"] = database_url
        get_settings.cache_clear()
        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
        command.upgrade(config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url
        get_settings.cache_clear()

    engine = create_engine(database_url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_baseline_owns_existing_schema_but_not_future_admin_tables():
    revision = import_module("migrations.versions.20260808_baseline_schema")

    assert {"users", "courses", "audit_logs"} <= revision._BASELINE_TABLE_NAMES
    assert {
        "guardrail_rules",
        "admin_course_overrides",
        "course_ingest_jobs",
    }.isdisjoint(revision._BASELINE_TABLE_NAMES)


def test_empty_database_upgrades_to_head(tmp_path):
    tables = upgrade_sqlite_to_head(tmp_path / "fresh.db")

    assert "alembic_version" in tables
    assert "users" in tables
    assert "audit_logs" in tables
    assert "guardrail_rules" in tables
    assert "admin_course_overrides" in tables
    assert "course_ingest_jobs" in tables
