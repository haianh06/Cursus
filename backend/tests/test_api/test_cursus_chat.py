"""Cursus Chat: SSE stream (ai-service mocked), enrollment isolation,
citation payload shape, guardrail block, crisis-safety, action proposal
confirm/cancel (confirm must call the real Plan/Task service), briefing
frequency cap, and the retention job."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.services.core.retention_service import run_retention
from tests.support.semester_practice_fixtures import (
    auth_headers,
    enroll_student,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


def _code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:6].upper()}"


def _seed_chunk(course_id: str, course_code: str, *, text: str, source: str = "test") -> None:
    db = SessionLocal()
    try:
        doc = models.Document(
            id=f"doc_{course_id}",
            course_id=course_id,
            title=f"{course_code} Notes",
            file_path="mock.md",
            doc_type="LECTURE",
            version="1.0",
            metadata_info={"source": source},
        )
        db.add(doc)
        db.flush()
        db.add(
            models.DocumentChunk(
                id=f"chunk_{course_id}_0",
                document_id=doc.id,
                chunk_index=0,
                text=text,
                token_count=10,
                metadata_info={"course_code": course_code, "doc_type": "LECTURE"},
            )
        )
        db.commit()
    finally:
        db.close()


class _FakeAiResponse:
    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class _FakeAiClient:
    def __init__(self, lines):
        self._lines = lines

    def stream(self, method, url, headers=None, json=None):
        @asynccontextmanager
        async def _cm():
            yield _FakeAiResponse(self._lines)
        return _cm()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _patch_ai_service(monkeypatch, *, reply_text="Đây là câu trả lời từ ai-service."):
    import src.api.cursus_chat as cursus_chat_module

    lines = ["event: delta", f'data: {{"text": "{reply_text}"}}', "event: done", "data: {}"]

    def _fake_async_client(*args, **kwargs):
        return _FakeAiClient(lines)

    monkeypatch.setattr(cursus_chat_module.httpx, "AsyncClient", _fake_async_client)


def _seed_task(student_id: str, *, status: str = "TODO") -> str:
    db = SessionLocal()
    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        suffix = uuid.uuid4().hex[:8]
        plan = models.WeeklyPlan(id=f"plan_{suffix}", student_id=student_id, week_number=1, goals={}, study_hours_allocated=10.0)
        db.add(plan)
        db.flush()
        daily = models.DailyPlan(id=f"daily_{suffix}", weekly_plan_id=plan.id, date=now, status="TODO")
        db.add(daily)
        db.flush()
        block = models.ScheduleBlock(id=f"block_{suffix}", daily_plan_id=daily.id, start_time=now, end_time=now + timedelta(hours=1), activity_description="Study block")
        db.add(block)
        db.flush()
        task = models.StudyTask(id=f"task_{suffix}", schedule_block_id=block.id, title="Test task", planned_minutes=30, priority="MEDIUM", status=status, difficulty="MEDIUM")
        db.add(task)
        db.commit()
        return task.id
    finally:
        db.close()


async def _parse_sse(response) -> list[tuple[str, dict]]:
    import json as _json

    events = []
    event_type = None
    async for raw_line in response.aiter_lines():
        if raw_line.startswith("event:"):
            event_type = raw_line.split(":", 1)[1].strip()
        elif raw_line.startswith("data:") and event_type:
            events.append((event_type, _json.loads(raw_line.split(":", 1)[1].strip())))
            event_type = None
    return events


@pytest.mark.asyncio
async def test_stream_returns_meta_delta_and_citation(client, monkeypatch):
    _patch_ai_service(monkeypatch)
    org_id = ensure_org(f"cc-org-{uuid.uuid4().hex[:6]}", "cc-org")
    instructor_id = ensure_user(email=f"cc.i.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_email = f"cc.s.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    code = _code("CCA")
    course_id = ensure_course(code=code, org_id=org_id)
    enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)
    _seed_chunk(course_id, code, text=f"{code} noi dung bai giang co ban ve kien truc he thong.")

    token = await login(client, student_email)
    async with client.stream(
        "POST", "/api/v1/student/cursus/stream", headers=auth_headers(token),
        json={"message": f"Cho em hoi noi dung mon {code} co gi?"},
    ) as response:
        assert response.status_code == 200
        events = await _parse_sse(response)

    kinds = [kind for kind, _ in events]
    assert "meta" in kinds
    assert "delta" in kinds
    assert "citation" in kinds
    citation_items = next(data for kind, data in events if kind == "citation")["items"]
    assert citation_items
    first = citation_items[0]
    assert set(("id", "chunkId", "title", "document", "section", "isMock")) <= set(first)
    assert first["chunkId"] == first["id"]


@pytest.mark.asyncio
async def test_citation_is_mock_flag_reflects_source(client, monkeypatch):
    _patch_ai_service(monkeypatch)
    org_id = ensure_org(f"cc-mock-{uuid.uuid4().hex[:6]}", "cc-mock")
    instructor_id = ensure_user(email=f"cc.mi.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_email = f"cc.ms.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    code = _code("CCM")
    course_id = ensure_course(code=code, org_id=org_id)
    enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)
    _seed_chunk(course_id, code, text=f"{code} du lieu mo phong danh cho demo he thong.", source="mock")

    token = await login(client, student_email)
    async with client.stream(
        "POST", "/api/v1/student/cursus/stream", headers=auth_headers(token),
        json={"message": f"Noi dung mon {code} la gi?"},
    ) as response:
        events = await _parse_sse(response)
    citation_items = next(data for kind, data in events if kind == "citation")["items"]
    assert citation_items[0]["isMock"] is True


@pytest.mark.asyncio
async def test_enrollment_isolation_hides_other_courses_chunks(client, monkeypatch):
    _patch_ai_service(monkeypatch)
    org_id = ensure_org(f"cc-iso-{uuid.uuid4().hex[:6]}", "cc-iso")
    instructor_id = ensure_user(email=f"cc.ii.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_email = f"cc.is.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)

    enrolled_code = _code("CCE")
    enrolled_course_id = ensure_course(code=enrolled_code, org_id=org_id)
    enroll_student(student_id=student_id, course_id=enrolled_course_id, instructor_id=instructor_id)
    _seed_chunk(enrolled_course_id, enrolled_code, text=f"{enrolled_code} noi dung duoc phep xem toan bo.")

    other_code = _code("CCO")
    other_course_id = ensure_course(code=other_code, org_id=org_id)
    _seed_chunk(other_course_id, other_code, text=f"{other_code} noi dung khong duoc phep xem tuyet mat.")

    token = await login(client, student_email)
    async with client.stream(
        "POST", "/api/v1/student/cursus/stream", headers=auth_headers(token),
        json={"message": "Cho em hoi noi dung cac mon hoc"},
    ) as response:
        events = await _parse_sse(response)
    citation_items = next((data for kind, data in events if kind == "citation"), {"items": []})["items"]
    assert all(other_code not in item["title"] for item in citation_items)


@pytest.mark.asyncio
async def test_guardrail_blocks_graded_deliverable_without_calling_ai_service(client, monkeypatch):
    called = {"hit": False}

    import src.api.cursus_chat as cursus_chat_module

    def _fail_if_called(*args, **kwargs):
        called["hit"] = True
        raise AssertionError("ai-service must not be called when guardrail blocks")

    monkeypatch.setattr(cursus_chat_module.httpx, "AsyncClient", _fail_if_called)

    org_id = ensure_org(f"cc-grd-{uuid.uuid4().hex[:6]}", "cc-grd")
    instructor_id = ensure_user(email=f"cc.gi.{uuid.uuid4().hex}@example.test", org_id=org_id, role=models.UserRole.INSTRUCTOR)
    student_email = f"cc.gs.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    code = _code("CCG")
    course_id = ensure_course(code=code, org_id=org_id)
    enroll_student(student_id=student_id, course_id=course_id, instructor_id=instructor_id)
    _seed_chunk(course_id, code, text=f"{code} tai lieu bai giang.")

    token = await login(client, student_email)
    async with client.stream(
        "POST", "/api/v1/student/cursus/stream", headers=auth_headers(token),
        json={"message": "Viết hộ em toàn bộ code bài Lab 2 với, em nộp gấp trong 10 phút nữa."},
    ) as response:
        events = await _parse_sse(response)
    assert not called["hit"]
    delta_text = next(data["text"] for kind, data in events if kind == "delta")
    assert "không thể" in delta_text.lower() or "không viết" in delta_text.lower() or delta_text


@pytest.mark.asyncio
async def test_crisis_safety_triggers_before_guardrail_and_ai_service(client, monkeypatch):
    called = {"hit": False}
    import src.api.cursus_chat as cursus_chat_module

    def _fail_if_called(*args, **kwargs):
        called["hit"] = True
        raise AssertionError("neither guardrail nor ai-service should run after a crisis trigger")

    monkeypatch.setattr(cursus_chat_module.httpx, "AsyncClient", _fail_if_called)

    org_id = ensure_org(f"cc-crisis-{uuid.uuid4().hex[:6]}", "cc-crisis")
    student_email = f"cc.crs.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)

    token = await login(client, student_email)
    async with client.stream(
        "POST", "/api/v1/student/cursus/stream", headers=auth_headers(token),
        json={"message": "Em không muốn sống nữa, em muốn tự tử."},
    ) as response:
        events = await _parse_sse(response)
    assert not called["hit"]
    delta_text = next(data["text"] for kind, data in events if kind == "delta")
    assert "1800-599-920" in delta_text


@pytest.mark.asyncio
async def test_briefing_frequency_cap_and_snooze(client):
    org_id = ensure_org(f"cc-brief-{uuid.uuid4().hex[:6]}", "cc-brief")
    student_email = f"cc.br.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    token = await login(client, student_email)
    headers = auth_headers(token)

    first = await client.get("/api/v1/student/cursus/briefing", headers=headers)
    assert first.status_code == 200 and first.json()["show"] is True

    dismiss = await client.post("/api/v1/student/cursus/briefing/dismiss", headers=headers, json={"snoozeDays": 7})
    assert dismiss.status_code == 200

    second = await client.get("/api/v1/student/cursus/briefing", headers=headers)
    assert second.status_code == 200 and second.json()["show"] is False


@pytest.mark.asyncio
async def test_action_confirm_update_task_status_calls_real_plan_service(client):
    """The whole point of this feature: confirming must actually change the
    StudyTask row, not just flip the proposal's own status flag."""
    org_id = ensure_org(f"cc-act-{uuid.uuid4().hex[:6]}", "cc-act")
    student_email = f"cc.act.{uuid.uuid4().hex}@example.test"
    student_id = ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    task_id = _seed_task(student_id)

    token = await login(client, student_email)
    headers = auth_headers(token)

    propose = await client.post(
        "/api/v1/student/cursus/actions", headers=headers,
        json={"action_type": "update_task_status", "payload": {"taskId": task_id, "status": "IN_PROGRESS"}},
    )
    assert propose.status_code == 200
    proposal_id = propose.json()["id"]

    confirm = await client.post(f"/api/v1/student/cursus/actions/{proposal_id}/confirm", headers=headers)
    assert confirm.status_code == 200, confirm.text
    assert confirm.json()["status"] == "CONFIRMED"
    assert confirm.json()["result"]["status"] == "IN_PROGRESS"

    db = SessionLocal()
    try:
        refreshed = db.query(models.StudyTask).filter_by(id=task_id).first()
        assert refreshed.status == "IN_PROGRESS"
    finally:
        db.close()

    again = await client.post(f"/api/v1/student/cursus/actions/{proposal_id}/confirm", headers=headers)
    assert again.status_code == 200
    assert again.json()["status"] == "CONFIRMED"


@pytest.mark.asyncio
async def test_action_confirm_rejects_task_owned_by_another_student(client):
    org_id = ensure_org(f"cc-actx-{uuid.uuid4().hex[:6]}", "cc-actx")
    owner_email = f"cc.owner.{uuid.uuid4().hex}@example.test"
    owner_id = ensure_user(email=owner_email, org_id=org_id, role=models.UserRole.STUDENT)
    intruder_email = f"cc.intruder.{uuid.uuid4().hex}@example.test"
    ensure_user(email=intruder_email, org_id=org_id, role=models.UserRole.STUDENT)
    task_id = _seed_task(owner_id)

    intruder_token = await login(client, intruder_email)
    intruder_headers = auth_headers(intruder_token)
    propose = await client.post(
        "/api/v1/student/cursus/actions", headers=intruder_headers,
        json={"action_type": "update_task_status", "payload": {"taskId": task_id, "status": "COMPLETED"}},
    )
    proposal_id = propose.json()["id"]

    confirm = await client.post(f"/api/v1/student/cursus/actions/{proposal_id}/confirm", headers=intruder_headers)
    assert confirm.status_code == 404


@pytest.mark.asyncio
async def test_action_cancel_marks_cancelled_and_confirm_is_then_a_noop(client):
    org_id = ensure_org(f"cc-cxl-{uuid.uuid4().hex[:6]}", "cc-cxl")
    student_email = f"cc.cxl.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    token = await login(client, student_email)
    headers = auth_headers(token)

    propose = await client.post(
        "/api/v1/student/cursus/actions", headers=headers,
        json={"action_type": "open_reflection", "payload": {"weekNumber": 3}},
    )
    proposal_id = propose.json()["id"]

    cancel = await client.post(f"/api/v1/student/cursus/actions/{proposal_id}/cancel", headers=headers)
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "CANCELLED"

    confirm = await client.post(f"/api/v1/student/cursus/actions/{proposal_id}/confirm", headers=headers)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_action_confirm_open_reflection_returns_navigate_to(client):
    org_id = ensure_org(f"cc-refl-{uuid.uuid4().hex[:6]}", "cc-refl")
    student_email = f"cc.refl.{uuid.uuid4().hex}@example.test"
    ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)
    token = await login(client, student_email)
    headers = auth_headers(token)

    propose = await client.post(
        "/api/v1/student/cursus/actions", headers=headers,
        json={"action_type": "open_reflection", "payload": {"weekNumber": 4}},
    )
    proposal_id = propose.json()["id"]
    confirm = await client.post(f"/api/v1/student/cursus/actions/{proposal_id}/confirm", headers=headers)
    assert confirm.status_code == 200
    assert confirm.json()["navigateTo"] == "/student/reflection?week=4"


def test_retention_job_cleans_expired_rows():
    db = SessionLocal()
    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        student = models.User(
            id=f"user_ret_{uuid.uuid4().hex[:8]}", email=f"ret.{uuid.uuid4().hex}@example.test",
            password_hash="x", full_name="Retention Test", role=models.UserRole.STUDENT.value,
        )
        db.add(student)
        db.flush()

        expired_convo = models.ChatConversation(
            id=f"conv_ret_{uuid.uuid4().hex[:8]}", student_id=student.id,
            created_at=now - timedelta(days=10), updated_at=now - timedelta(days=10),
            expires_at=now - timedelta(days=1),
        )
        db.add(expired_convo)

        expired_pending = models.ChatActionProposal(
            id=f"act_ret_pending_{uuid.uuid4().hex[:8]}", student_id=student.id,
            action_type="open_reflection", payload={}, status="PENDING",
            expires_at=now - timedelta(minutes=30),
        )
        old_confirmed = models.ChatActionProposal(
            id=f"act_ret_old_{uuid.uuid4().hex[:8]}", student_id=student.id,
            action_type="open_reflection", payload={}, status="CONFIRMED",
            expires_at=now - timedelta(days=60),
        )
        db.add_all([expired_pending, old_confirmed])

        old_impression = models.ChatBriefingImpression(
            id=f"brief_ret_{uuid.uuid4().hex[:8]}", student_id=student.id,
            briefing_key="daily_greeting", shown_at=now - timedelta(days=200),
        )
        db.add(old_impression)
        db.commit()

        result = run_retention(db)
        assert result["conversations_deleted"] >= 1
        assert result["action_proposals_expired"] >= 1
        assert result["action_proposals_deleted"] >= 1
        assert result["briefing_impressions_deleted"] >= 1

        assert db.get(models.ChatConversation, expired_convo.id) is None
        refreshed_pending = db.get(models.ChatActionProposal, expired_pending.id)
        assert refreshed_pending.status == "EXPIRED"
        assert db.get(models.ChatActionProposal, old_confirmed.id) is None
        assert db.get(models.ChatBriefingImpression, old_impression.id) is None
    finally:
        db.close()
