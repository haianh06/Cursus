"""`system_status` must reflect only the caller's own organization.

`failed_jobs` counted every failed row in `course_ingest_jobs` with no
organization filter at all, so one school's broken ingest turned every
other school's Overview banner to DEGRADED.
"""

import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


def _fail_a_job(course_code: str) -> None:
    db = SessionLocal()
    try:
        db.add(
            models.CourseIngestJob(
                id=f"job_{uuid.uuid4().hex}",
                # `admin_course_repository.start_job` always upper-cases what
                # it stores, so mirror that here rather than the raw code.
                course_code=course_code.strip().upper(),
                document_id=None,
                operation="INGEST",
                status="failed",
                error="boom",
            )
        )
        db.commit()
    finally:
        db.close()


@pytest.mark.asyncio
async def test_another_orgs_failed_ingest_does_not_degrade_my_status(client):
    suffix = uuid.uuid4().hex[:6]
    mine = ensure_org(slug=f"ovw-a-{suffix}", name="Org A")
    theirs = ensure_org(slug=f"ovw-b-{suffix}", name="Org B")
    admin_email = f"admin.ovw.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=mine, role=models.UserRole.ADMIN)
    ensure_course(code=f"ZZOVWA{suffix[:3].upper()}", org_id=mine)
    their_code = f"ZZOVWB{suffix[:3].upper()}"
    ensure_course(code=their_code, org_id=theirs)

    _fail_a_job(their_code)

    token = await login(client, admin_email)
    response = await client.get("/api/v1/admin/overview", headers=auth_headers(token))

    assert response.status_code == 200, response.text
    assert response.json()["system_status"] == "HEALTHY"


@pytest.mark.asyncio
async def test_my_own_failed_ingest_does_degrade_my_status(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"ovw-c-{suffix}", name="Org C")
    admin_email = f"admin.ovwc.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    # Lower-case tail on purpose: the real catalog has codes like "ENW493c"
    # while `start_job` stores them upper-cased, so a plain `Course.code ==
    # course_code` join would silently miss this org's own failures.
    my_code = f"ZZOVWc{suffix[:3]}"
    ensure_course(code=my_code, org_id=org_id)

    _fail_a_job(my_code)

    token = await login(client, admin_email)
    response = await client.get("/api/v1/admin/overview", headers=auth_headers(token))

    assert response.status_code == 200, response.text
    assert response.json()["system_status"] == "DEGRADED"
