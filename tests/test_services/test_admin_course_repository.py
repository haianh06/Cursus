import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.db.models import Base, Course


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_added_course_has_real_course_row_and_duplicate_is_rejected(db_session):
    from src.repositories.admin_course_repository import AdminCourseRepository

    repo = AdminCourseRepository(db_session, catalog_codes={"SSA101"})
    override = repo.add_course("NEW101", "New course", "9", "admin_demo")

    assert override.is_added is True
    assert db_session.query(Course).filter_by(code="NEW101").one().name == "New course"
    with pytest.raises(ValueError):
        repo.add_course("NEW101", "Duplicate", "9", "admin_demo")
    with pytest.raises(ValueError):
        repo.add_course("SSA101", "Catalog duplicate", "1", "admin_demo")


def test_catalog_hide_and_restore_remove_only_the_overlay(db_session):
    from src.repositories.admin_course_repository import AdminCourseRepository

    repo = AdminCourseRepository(db_session, catalog_codes={"SSA101"})
    repo.hide_course("SSA101", "admin_demo")
    assert repo.list_overrides()[0].hidden is True

    repo.restore_course("SSA101", "admin_demo")
    assert repo.list_overrides() == []


def test_added_course_hide_and_restore_preserve_real_course(db_session):
    from src.repositories.admin_course_repository import AdminCourseRepository

    repo = AdminCourseRepository(db_session, catalog_codes={"SSA101"})
    repo.add_course("NEW101", "New course", "9", "admin_demo")
    repo.hide_course("NEW101", "admin_demo")
    repo.restore_course("NEW101", "admin_demo")

    assert repo.list_overrides()[0].hidden is False
    assert db_session.query(Course).filter_by(code="NEW101").one() is not None


def test_latest_jobs_returns_newest_job_per_course(db_session):
    from src.repositories.admin_course_repository import AdminCourseRepository

    repo = AdminCourseRepository(db_session, catalog_codes={"SSA101"})
    first = repo.start_job("SSA101", operation="upload")
    second = repo.start_job("SSA101", operation="replace")
    other = repo.start_job("NEW101", operation="upload")
    repo.finish_job(first.id, status="failed", error="old")

    latest = repo.latest_jobs()
    assert {job.id for job in latest} == {second.id, other.id}


def test_stale_processing_jobs_are_marked_failed(db_session):
    from datetime import timedelta

    from src.repositories.admin_course_repository import AdminCourseRepository, utc_now_naive

    repo = AdminCourseRepository(db_session, catalog_codes={"SSA101"})
    job = repo.start_job("SSA101", operation="upload")
    job.created_at = utc_now_naive() - timedelta(hours=2)
    repo.fail_stale_jobs(max_age_seconds=300)

    assert job.status == "failed"
    assert job.error == "Ingest job timed out"
