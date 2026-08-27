"""Container entrypoint: wait for DB → Alembic upgrade → optional seed → uvicorn."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docker-entrypoint")

_SEEDABLE_ENVS = frozenset({"development", "test"})


def _run(cmd: list[str], *, check: bool = True) -> int:
    logger.info("running: %s", " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    if check and completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(cmd)}")
    return completed.returncode


def _wait_for_database(*, attempts: int = 60, delay_s: float = 2.0) -> None:
    """Block until SQLAlchemy can connect (Postgres may still be starting)."""
    from sqlalchemy import text

    from src.config import get_settings
    from src.db.connection import engine

    get_settings.cache_clear()
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("database_ready attempt=%s", attempt)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            # Avoid logging full DSN (may include password).
            logger.warning(
                "database_not_ready attempt=%s/%s error_type=%s",
                attempt,
                attempts,
                type(exc).__name__,
            )
            time.sleep(delay_s)
    raise RuntimeError(
        f"Database not ready after {attempts} attempts: {type(last_error).__name__}"
    )


def _alembic_upgrade() -> None:
    _run([sys.executable, "-m", "alembic", "upgrade", "head"])


def _users_exist() -> bool:
    from sqlalchemy import text

    from src.db.connection import engine

    with engine.connect() as connection:
        result = connection.execute(text("SELECT COUNT(*) FROM users"))
        count = int(result.scalar_one())
    return count > 0


def _seed_demo_dataset() -> None:
    """Seed the real sandbox flow used by the public role picker."""
    from src.db.connection import SessionLocal
    from src.db.models import User
    from src.services.mock.gate2_demo import DEMO_STUDENT_EMAIL, Gate2DemoService

    db = SessionLocal()
    try:
        student = db.query(User).filter_by(email=DEMO_STUDENT_EMAIL).first()
        if student is None:
            raise RuntimeError("Demo sandbox student was not provisioned")
        Gate2DemoService(db).reset(student_id=student.id)
    finally:
        db.close()


def _seed_if_needed() -> None:
    flag = os.getenv("SEED_ON_START", "false").strip().lower()
    if flag in {"0", "false", "no", ""}:
        logger.info("seed_on_start_disabled")
        return

    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in _SEEDABLE_ENVS:
        logger.warning("seed_blocked_non_dev_env app_env=%s", app_env)
        return

    dataset = os.getenv("SEED_DATASET", "demo").strip().lower()
    if dataset == "demo":
        logger.info("seeding_demo_dataset app_env=%s", app_env)
        _seed_demo_dataset()
        return

    try:
        if _users_exist():
            logger.info("seed_skipped_users_present")
            return
    except Exception as exc:  # noqa: BLE001
        logger.warning("seed_user_check_failed error_type=%s", type(exc).__name__)
        return

    logger.info("seeding_full_dataset app_env=%s", app_env)
    _run([sys.executable, "seed.py"], check=True)
    # Demo seed accounts are for local/dev only; mark verified so login works
    # without a real mailbox when EMAIL_PROVIDER=none.
    _run(
        [
            sys.executable,
            "-c",
            (
                "from src.db.connection import SessionLocal; "
                "from src.db.models import User; "
                "db=SessionLocal(); "
                "n=db.query(User).update({User.is_email_verified: True}); "
                "db.commit(); "
                "print('verified_users', n); "
                "db.close()"
            ),
        ],
        check=False,
    )


def _ensure_demo_sandbox() -> None:
    """Provision the three accounts used by `/auth/demo-session`.

    The generic API demo fixture uses different emails, so seeding it alone
    leaves the public role picker returning HTTP 503. The provisioning script
    is idempotent and keeps these accounts inside an isolated sandbox org.
    """
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env not in _SEEDABLE_ENVS:
        return
    _run(
        [
            sys.executable,
            "provision_organization.py",
            "cursus-demo",
            "Cursus Demo University",
            "sandbox",
            "--admin-email",
            "demo.admin@cursusdemo.local",
            "--admin-name",
            "Demo Admin",
        ]
    )


def _provision(email: str) -> None:
    script = Path("/app/scripts/provision_student_mock.py")
    if not script.exists():
        script = Path("scripts/provision_student_mock.py")
    if not script.exists():
        return
    try:
        subprocess.run(
            [sys.executable, str(script), "--email", email],
            check=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Failed provisioning mock data for %s", email)


def _seed_extra_users() -> None:
    from scripts.seed_extra_users import ensure_extra_users
    from src.db.connection import SessionLocal

    db = SessionLocal()
    try:
        ensure_extra_users(db)
    finally:
        db.close()


def _seed_curriculum() -> None:
    """Only fills in a placeholder `chunks_<CODE>.json` for catalog subjects
    that don't have one yet (mostly combo/elective slots with no real
    syllabus file) — `--files-only` so it never writes to the database.
    `seed_curriculum.py`'s own DB-writing path tags every chunk it inserts
    as `source=mock` unconditionally, including for subjects that DO have a
    real, rich chunk file — which would relabel real syllabus content as
    simulated. `_ingest_real_curriculum` below is the one place real content
    actually reaches the database, correctly tagged."""
    script = Path("/app/scripts/seed_curriculum.py")
    if not script.exists():
        script = Path("scripts/seed_curriculum.py")
    if not script.exists():
        logger.warning("seed_curriculum_script_missing")
        return
    logger.info("seeding_curriculum_chunk_files")
    _run([sys.executable, str(script), "--files-only"], check=False)


def _ingest_real_curriculum() -> None:
    """Load every course with a real, already-parsed syllabus
    (`docs/planning/v2/data/chunks_<CODE>.json`) into the database as
    `official_document`/`curriculum`-sourced content — see
    `src/services/mock/real_curriculum_service.py`. Safe to call on every
    boot: each course's chunks are fully replaced from the same source file,
    so this is idempotent, not additive."""
    from src.db.connection import SessionLocal
    from src.services.mock.real_curriculum_service import ingest_all_real_courses

    from src.services.mock.real_curriculum_service import purge_superseded_mock_catalog_docs

    db = SessionLocal()
    try:
        results = ingest_all_real_courses(db)
        logger.info(
            "real_curriculum_ingested courses=%s total_chunks=%s",
            len(results),
            sum(results.values()),
        )
        purged = purge_superseded_mock_catalog_docs(db)
        if purged:
            logger.info("purged_superseded_mock_catalog_docs count=%s", len(purged))
    except Exception:  # noqa: BLE001
        logger.exception("real_curriculum_ingest_failed")
    finally:
        db.close()


def _ensure_academic_term() -> None:
    """Demo/dev: publish Fall 2026 so students can open semester setup."""
    from datetime import UTC, date, datetime

    from src.db.connection import SessionLocal
    from src.db.models import AcademicTerm, Organization

    db = SessionLocal()
    try:
        if db.query(AcademicTerm).filter_by(is_active=True).first() is not None:
            return
        organization = db.query(Organization).filter_by(slug="cursus-demo").first()
        if organization is None:
            raise RuntimeError("Demo sandbox organization was not provisioned")
        db.add(
            AcademicTerm(
                id="term_fall2026",
                organization_id=organization.id,
                name="Fall 2026",
                start_date=date(2026, 9, 7),
                study_weeks=10,
                exam_weeks=2,
                is_active=True,
                created_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
        logger.info("academic_term_default_created")
    except Exception:
        db.rollback()
        logger.exception("academic_term_default_failed")
    finally:
        db.close()


def main() -> None:
    Path("/app/data").mkdir(parents=True, exist_ok=True)
    Path("/app/data/uploads").mkdir(parents=True, exist_ok=True)

    _wait_for_database()
    _alembic_upgrade()
    _ensure_demo_sandbox()
    _ensure_academic_term()
    _seed_if_needed()
    _seed_curriculum()
    _ingest_real_curriculum()
    _seed_extra_users()
    _provision("student.demo@example.test")

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "src.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    if os.getenv("APP_ENV", "development").strip().lower() == "development":
        # ./src is bind-mounted in docker-compose.yml for live editing; scope the
        # watch to it so unrelated mounts (data/, uploads) don't trigger restarts.
        cmd += ["--reload", "--reload-dir", "/app/src"]

    raise SystemExit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
