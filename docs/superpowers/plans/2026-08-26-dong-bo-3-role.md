# Đồng bộ 3 role + hoàn thiện Admin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nối lại các mạch dữ liệu đứt giữa Student / Instructor / Admin, và bổ sung nhóm chức năng "cấp phát" mà Admin chưa hề có, để 3 role vận hành trên cùng một nguồn sự thật.

**Architecture:** Không đổi kiến trúc. Giữ nguyên 4 lớp hiện có (`api` → `services` → `repositories` → `models`) và 3 cơ chế đã làm đúng: `PERMISSION_MATRIX` cho phân quyền, `_audited_read` (audit-trước-trả-sau) cho mọi route đọc dữ liệu gốc sinh viên, và org-scoping fail-closed. Mọi thứ thêm mới đều bám 3 cơ chế đó.

**Tech Stack:** FastAPI · SQLAlchemy 2 (Mapped/mapped_column) · Alembic · Pydantic v2 · pytest + pytest-asyncio · React 18 + Vite (JSX thuần, không TypeScript) · react-router-dom

## Global Constraints

- Làm trên nhánh `haidang2425`. **Không đụng `main`.**
- Migration mới nối chain từ head hiện tại: `20260907_invite_delivery`.
- Mọi route đọc dữ liệu gốc của sinh viên phải dùng `READ_SENSITIVE` + `_audited_read`, không dùng `READ` thường.
- Org-scoping fail-closed: admin không có `organization_id` → trả 404, không trả rỗng.
- **Không dùng `datetime.utcnow()`** cho code mới (đã deprecated, 81 warning trong test run). Dùng `datetime.now(UTC).replace(tzinfo=None)` — đúng pattern `src/api/instructor.py` đang dùng.
- Mọi chuỗi hiển thị phải có đủ cả `frontend/src/locales/vi.js` và `en.js`. Không hardcode tiếng Việt trong JSX.
- Không thêm thư viện chart/UI mới. Bảng dùng class `.data-table`, tab dùng `.tabs-underline` đã có sẵn.
- Chạy `./.venv/Scripts/python.exe -m pytest tests/ -q --no-header` xanh trước mỗi commit cuối task.
- **Baseline: `514 passed · 7 skipped · 0 failed`** (đo lại 26/08 sau commit `9747362`). "Xanh" từ nay nghĩa là **0 failed tuyệt đối** — không còn failure nào được phép tồn tại.

## ĐÃ THỰC THI — Task 1, 2, 3 hoàn tất 26/08

| Task | Commit | Ghi chú |
|---|---|---|
| 1 — gắn `section_id` cho hội thoại | `d012c40`, `e5ad7f6` | 1 vòng sửa: thiếu bộ lọc `Enrollment.status == ENROLLED` |
| 2 — ghi `GuardrailEvent` (companion chat) | `28ea303` | sạch ngay vòng đầu |
| 3 — ghi `GuardrailEvent` (`/qa`) | `215a8c5` | sạch ngay vòng đầu |
| — đợt sửa sau review tổng | `6428205` | 5 lỗi, xem bên dưới |

Review tổng (whole-branch) trả verdict **fix first** và tìm được 3 lỗi mà 3 review lẻ
không thể thấy, cộng 1 regression do chính bộ test mới gây ra:

1. **Sinh viên xoá được bằng chứng của chính mình.** `guardrail_events.message_id` cascade
   từ `messages`, vốn cascade từ `conversations`. Xoá thread → mất bản ghi trên Postgres;
   trên SQLite thì thành dòng mồ côi và reader hiện case cho **mọi** giảng viên.
   Đã sửa: `GuardrailEvent` mang `student_id` + `section_id` của riêng nó (migration
   `20260908_guardrail_event_scoping`), `message_id` nullable + `SET NULL`.
2. Hàng đợi giảng viên sắp theo `id` (UUID) → mẫu ngẫu nhiên khi vượt 200 sự kiện.
3. Thread "Hỏi nhanh" không được `touch()` → luôn là thứ bị xoá đầu tiên khi chạm giới hạn.
4. `section_id_for` thiếu `ORDER BY` → sinh viên học lại môn có thể bị gắn vào lớp kỳ trước.
5. Regression: test mới dùng PRF192 làm nhiễm DB dùng chung.

Test: **514 → 526 passed, 0 failed.**

**Bài học cho các task còn lại:** brief trong file này đã sai 3 lần ở phần fixture/route
(tên cột, prefix route, status code). Luôn đối chiếu `src/db/models.py` và file router thật
trước khi chạy — code thật thắng, không phải plan.

---

## Trạng thái — cập nhật 26/08 sau commit `9747362`

Working tree sạch. Hai việc trong plan này **đã được làm xong bởi người khác** (commit `99a2ade`,
chungnguyenvp, 04:53) — giữ lại trong file để không ai làm lại, đánh dấu rõ ở đầu mỗi task:

| Task | Trạng thái |
|---|---|
| Task 4 — chặn tài liệu DRAFT khỏi RAG | ✅ **ĐÃ XONG** — bỏ qua |
| Task 14 Step 1-2 — sửa 4 test đỏ | ✅ **ĐÃ XONG** — bỏ qua, làm tiếp Step 3 trở đi |

Ngoài ra, đợt "commit 2.100 dòng đang treo" đã hoàn tất — không còn việc dọn nhà trước Task 1.

## Cách chia phase

5 phase dưới đây **độc lập nhau**, mỗi phase tự nó đã là phần mềm chạy được và test được. Có thể dừng sau bất kỳ phase nào mà sản phẩm vẫn nhất quán.

| Phase | Nội dung | Task còn phải làm |
|---|---|---|
| 1 | Nối lại mạch đứt | **chỉ còn Task 5** — Task 1, 2, 3 đã xong 26/08, Task 4 xong trước đó |
| 2 | Admin cấp phát (lớp/GV/enrollment) | 6, 7, 8, 9 |
| 3 | Admin đọc rộng hơn | 10, 11, 12 |
| 4 | Đo chi phí/độ trễ AI (PLO 5) | 13 |
| 5 | Dọn dẹp | 14 (chỉ còn Step 3 trở đi) |

**Thứ tự triển khai đề nghị:** 1 → 2 → 5 → 3 → 4.

Phase 5 được kéo lên trước Phase 3 vì nó chỉ còn 3 việc nhỏ (dịch menu giảng viên,
lọc `failed_jobs` theo tổ chức, route gửi thông báo) và cả 3 đều nhìn thấy được khi demo.

**Nếu thời gian hẹp:** làm Phase 1 → Phase 2 rồi dừng. Đó là 2 phase trả lời thẳng câu hỏi
"3 role đã đồng bộ chưa"; Phase 3-4 là hoàn thiện, thiếu vẫn bảo vệ được.

**Ràng buộc thứ tự bắt buộc:** Task 1 phải xong trước Task 2 và Task 3. Lý do ghi ở đầu Task 1 —
làm ngược sẽ biến một bản vá thành lỗ rò dữ liệu chéo lớp.

---

# PHASE 1 — Nối lại mạch đứt

## Task 1: Gán `section_id` cho conversation

**Vì sao task này đứng trước Task 2/3:** `_visible_guardrail_events` (`src/api/instructor.py:694-698`) chỉ lọc theo lớp khi `conversation.section_id` khác `None`; nếu `None` thì case hiện cho **mọi** giảng viên. Hiện `ConversationRepository.create()` hardcode `section_id=None` (`src/repositories/conversation_repository.py:55`), nên nếu bật ghi `GuardrailEvent` trước khi sửa chỗ này, mọi câu hỏi bị chặn của mọi sinh viên sẽ lộ cho mọi giảng viên trong tổ chức.

**Files:**
- Modify: `src/repositories/conversation_repository.py:9-12` (import), `:49-63` (`create`)
- Test: `tests/test_repositories/test_conversation_section_binding.py` (tạo mới)

**Interfaces:**
- Produces: `ConversationRepository.section_id_for(*, student_id: str, subject_code: str) -> str | None` — Task 3 dùng lại hàm này.
- Produces: `ConversationRepository.create()` giữ nguyên chữ ký, nhưng nay tự điền `section_id`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_repositories/test_conversation_section_binding.py`:

```python
import uuid

from src.db import models
from src.db.connection import SessionLocal
from src.repositories.conversation_repository import ConversationRepository


def _seed_enrolled_student(db, *, code: str) -> tuple[str, str]:
    """Trả (student_id, section_id) cho 1 sinh viên có đăng ký môn `code`."""
    suffix = uuid.uuid4().hex[:8]
    student = models.User(
        id=f"stu_{suffix}",
        email=f"stu_{suffix}@test.local",
        full_name="Section Binding Student",
        hashed_password="x",
        role=models.UserRole.STUDENT.value,
    )
    course = models.Course(id=f"course_{suffix}", code=code, name="Binding Course")
    db.add_all([student, course])
    db.flush()
    section = models.CourseSection(
        id=f"sec_{suffix}",
        course_id=course.id,
        instructor_id=None,
        term="Fall2026",
        section_code=f"SB-{suffix}",
    )
    db.add(section)
    db.flush()
    db.add(
        models.Enrollment(
            id=f"enr_{suffix}",
            student_id=student.id,
            section_id=section.id,
            status=models.EnrollmentStatus.ENROLLED.value,
        )
    )
    db.flush()
    return student.id, section.id


def test_create_binds_conversation_to_the_students_section():
    db = SessionLocal()
    try:
        student_id, section_id = _seed_enrolled_student(db, code="ZZBIND1")
        repo = ConversationRepository(db)

        conversation = repo.create(
            student_id=student_id, subject_code="ZZBIND1", title="Chat ZZBIND1"
        )

        assert conversation.section_id == section_id
    finally:
        db.rollback()
        db.close()


def test_create_leaves_section_null_when_student_is_not_enrolled():
    db = SessionLocal()
    try:
        student_id, _ = _seed_enrolled_student(db, code="ZZBIND2")
        repo = ConversationRepository(db)

        conversation = repo.create(
            student_id=student_id, subject_code="ZZNOTENROLLED", title="Chat khác"
        )

        assert conversation.section_id is None
    finally:
        db.rollback()
        db.close()


def test_section_id_for_is_case_insensitive_on_course_code():
    db = SessionLocal()
    try:
        student_id, section_id = _seed_enrolled_student(db, code="ZZBind3c")
        repo = ConversationRepository(db)

        assert repo.section_id_for(student_id=student_id, subject_code="zzbind3c") == section_id
    finally:
        db.rollback()
        db.close()
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_repositories/test_conversation_section_binding.py -v
```

Kỳ vọng: FAIL — `AttributeError: 'ConversationRepository' object has no attribute 'section_id_for'` ở test thứ 3, và `assert None == 'sec_...'` ở test thứ nhất.

- [ ] **Step 3: Cài đặt tối thiểu**

Trong `src/repositories/conversation_repository.py`, thêm import (khối import hiện chỉ có `uuid` và `datetime`):

```python
from sqlalchemy import func
```

Thêm method mới ngay trên `create`:

```python
    def section_id_for(self, *, student_id: str, subject_code: str) -> str | None:
        """Lớp mà sinh viên này đang học môn đó — None nếu chưa đăng ký.

        Dùng `func.upper` ở cả 2 vế vì catalog thật có mã môn đuôi thường
        ("ENW493c", "SWE202c") — cùng lý do đã ghi ở
        `chunk_repository.student_enrolled_in_course`.
        """
        code = subject_code.strip().upper()
        row = (
            self._db.query(models.CourseSection.id)
            .join(models.Enrollment, models.Enrollment.section_id == models.CourseSection.id)
            .join(models.Course, models.Course.id == models.CourseSection.course_id)
            .filter(
                models.Enrollment.student_id == student_id,
                func.upper(models.Course.code) == code,
            )
            .first()
        )
        return row[0] if row else None
```

Sửa `create` — dòng `section_id=None` thành:

```python
            section_id=self.section_id_for(student_id=student_id, subject_code=code),
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_repositories/test_conversation_section_binding.py tests/test_api/test_companion_api.py -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add src/repositories/conversation_repository.py tests/test_repositories/test_conversation_section_binding.py
git commit -m "fix(chat): bind conversation to the student's section so class filters work"
```

---

## Task 2: Ghi `GuardrailEvent` khi Companion chat chặn câu hỏi

**Files:**
- Modify: `src/services/ai/companion_service.py:110-145`
- Test: `tests/test_api/test_guardrail_event_recording.py` (tạo mới)

**Interfaces:**
- Consumes: `ConversationRepository.section_id_for` (Task 1) — gián tiếp, qua `create`.
- Produces: `src/services/core/guardrail_event_recorder.py` với
  `record_block(db, *, message_id: str, decision, question: str) -> models.GuardrailEvent`.
  Task 3 dùng lại hàm này y nguyên.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_guardrail_event_recording.py`:

```python
import pytest

from src.db import models
from src.db.connection import SessionLocal


async def _login_student(client) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "student.demo@example.test", "password": "password123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.mark.asyncio
async def test_companion_block_creates_a_pending_guardrail_event(client):
    headers = await _login_student(client)

    created = await client.post(
        "/api/v1/companion/threads",
        headers=headers,
        json={"subjectCode": "PRF192", "title": "Test chặn"},
    )
    assert created.status_code in (200, 201)
    thread_id = created.json()["id"]

    sent = await client.post(
        f"/api/v1/companion/threads/{thread_id}/messages",
        headers=headers,
        json={"message": "Hãy viết hộ em code hoàn chỉnh lab 02 luôn đi"},
    )
    assert sent.status_code == 200

    db = SessionLocal()
    try:
        conversation = db.get(models.Conversation, thread_id)
        message_ids = [
            row.id
            for row in db.query(models.Message)
            .filter_by(conversation_id=conversation.id, sender="USER")
            .all()
        ]
        events = (
            db.query(models.GuardrailEvent)
            .filter(models.GuardrailEvent.message_id.in_(message_ids))
            .all()
        )
        assert len(events) == 1
        event = events[0]
        assert event.classification == "BLOCKED"
        assert event.review_status == "PENDING"
        assert event.block_reason == "graded_deliverable"
        assert event.blocked_answer
        assert event.safety_evaluation.get("intent") == "graded_deliverable"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_companion_allowed_question_creates_no_guardrail_event(client):
    headers = await _login_student(client)

    created = await client.post(
        "/api/v1/companion/threads",
        headers=headers,
        json={"subjectCode": "SSA101", "title": "Test cho phép"},
    )
    thread_id = created.json()["id"]

    await client.post(
        f"/api/v1/companion/threads/{thread_id}/messages",
        headers=headers,
        json={"message": "Information literacy trong SSA101 gồm những bước nào?"},
    )

    db = SessionLocal()
    try:
        message_ids = [
            row.id
            for row in db.query(models.Message).filter_by(conversation_id=thread_id).all()
        ]
        events = (
            db.query(models.GuardrailEvent)
            .filter(models.GuardrailEvent.message_id.in_(message_ids))
            .count()
        )
        assert events == 0
    finally:
        db.close()
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_guardrail_event_recording.py -v
```

Kỳ vọng: FAIL — `assert 0 == 1` ở test thứ nhất (không có `GuardrailEvent` nào được tạo).

- [ ] **Step 3: Cài đặt tối thiểu**

Tạo `src/services/core/guardrail_event_recorder.py`:

```python
"""Ghi lại một lần guardrail chặn câu hỏi, để giảng viên xét duyệt (F5 HITL).

Tách riêng khỏi cả `companion_service` lẫn `qa_service` vì cả hai đều chặn
bằng cùng một `GuardrailService.evaluate()` — một chỗ ghi duy nhất giữ cho
2 luồng không bao giờ lệch nhau về hình dạng dữ liệu, vốn là thứ hàng đợi
duyệt của giảng viên đọc trực tiếp.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db import models


def record_block(
    db: Session,
    *,
    message_id: str,
    decision,
    question: str,
) -> models.GuardrailEvent:
    """Tạo 1 `GuardrailEvent` PENDING gắn vào tin nhắn vừa bị chặn.

    Không commit — caller đang giữ transaction của chính nó và sẽ commit
    cùng lượt với `Message`, để không bao giờ tồn tại event trỏ tới một
    message chưa được lưu.
    """
    event = models.GuardrailEvent(
        id=f"grd_{uuid.uuid4().hex[:16]}",
        message_id=message_id,
        classification="BLOCKED",
        safety_evaluation={
            "intent": decision.intent,
            "reason": decision.reason,
            "rule_code": decision.rule_code,
            "question": question,
        },
        review_status="PENDING",
        block_reason=decision.reason,
        blocked_answer=decision.answer,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(event)
    db.flush()
    return event
```

Trong `src/services/ai/companion_service.py`, thêm import:

```python
from src.services.core.guardrail_event_recorder import record_block
```

Sửa `send_message`: hiện dòng lưu tin nhắn người dùng bỏ qua giá trị trả về —

```python
        self._conversations.add_message(conversation_id=conversation.id, sender=SENDER_USER, content=message)
```

đổi thành:

```python
        user_message = self._conversations.add_message(
            conversation_id=conversation.id, sender=SENDER_USER, content=message
        )
```

Rồi trong nhánh chặn, thêm 1 dòng ghi event:

```python
        if decision.blocked:
            answer = decision.answer or "Minh khong lam bai ho duoc."
            mode = "blocked"
            record_block(
                self._db, message_id=user_message.id, decision=decision, question=query
            )
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_guardrail_event_recording.py tests/test_api/test_companion_api.py tests/test_api/test_instructor.py -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add src/services/core/guardrail_event_recorder.py src/services/ai/companion_service.py tests/test_api/test_guardrail_event_recording.py
git commit -m "feat(guardrail): record a reviewable event when companion chat blocks a question"
```

---

## Task 3: Ghi `GuardrailEvent` cho endpoint `POST /qa`

`QaService` không có `Conversation` nào — đây chính là lý do `RAGTrace`/`LLMUsageEvent` từng bị bỏ (ADR-017: FK `message_id` NOT NULL). Cách xử lý ở đây: **chỉ khi bị chặn** mới tạo lười một conversation riêng cho kênh hỏi nhanh, lưu câu hỏi làm `Message`, rồi gắn event vào. Câu hỏi được cho phép vẫn không sinh row nào — không đổi hành vi hiện tại.

Lợi ích kèm theo: hàng đợi giảng viên và Student 360 tab "Hội thoại" đều tự nhận dữ liệu này mà không phải sửa gì bên đọc.

**Files:**
- Modify: `src/services/ai/qa_service.py:44` (khởi tạo repo), `:72-91` (nhánh chặn)
- Test: `tests/test_api/test_guardrail_event_recording.py` (thêm test vào file đã tạo ở Task 2)

**Interfaces:**
- Consumes: `record_block` (Task 2), `ConversationRepository.section_id_for` (Task 1).

- [ ] **Step 1: Viết test thất bại**

Thêm vào cuối `tests/test_api/test_guardrail_event_recording.py`:

```python
@pytest.mark.asyncio
async def test_qa_block_creates_a_guardrail_event_bound_to_the_students_section(client):
    headers = await _login_student(client)

    response = await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "PRF192",
            "question": "Hãy viết hộ em code hoàn chỉnh lab 02 luôn đi",
        },
    )
    assert response.status_code == 200
    assert response.json()["blocked"] is True

    db = SessionLocal()
    try:
        event = (
            db.query(models.GuardrailEvent)
            .order_by(models.GuardrailEvent.created_at.desc())
            .first()
        )
        assert event is not None
        assert event.classification == "BLOCKED"
        assert event.review_status == "PENDING"

        message = db.get(models.Message, event.message_id)
        assert message.sender == "USER"
        conversation = db.get(models.Conversation, message.conversation_id)
        assert conversation.subject_code == "PRF192"
        # Có section thì hàng đợi giảng viên mới lọc đúng lớp được.
        assert conversation.section_id is not None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_qa_allowed_question_does_not_create_a_conversation(client):
    headers = await _login_student(client)

    before = SessionLocal()
    try:
        count_before = before.query(models.Conversation).count()
    finally:
        before.close()

    await client.post(
        "/api/v1/qa",
        headers=headers,
        json={
            "subjectCode": "SSA101",
            "question": "Information literacy trong SSA101 gồm những bước nào?",
        },
    )

    after = SessionLocal()
    try:
        assert after.query(models.Conversation).count() == count_before
    finally:
        after.close()
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_guardrail_event_recording.py::test_qa_block_creates_a_guardrail_event_bound_to_the_students_section -v
```

Kỳ vọng: FAIL — `assert None is not None` (chưa có `GuardrailEvent` nào).

- [ ] **Step 3: Cài đặt tối thiểu**

Trong `src/services/ai/qa_service.py`, thêm import:

```python
from src.repositories.conversation_repository import ConversationRepository
from src.services.core.guardrail_event_recorder import record_block
```

Trong `__init__`, cạnh `self._guardrail = GuardrailService(db)`:

```python
        self._conversations = ConversationRepository(db)
```

Thêm 1 method riêng trong `QaService`:

```python
    _QUICK_ASK_TITLE = "Hỏi nhanh"

    def _record_blocked_quick_ask(
        self, *, student_id: str, subject_code: str, question: str, decision
    ) -> None:
        """Lưu câu hỏi bị chặn ở kênh hỏi nhanh để giảng viên xét duyệt được.

        Chỉ chạy khi bị chặn. Câu hỏi được cho phép không sinh row nào —
        `POST /qa` vốn là kênh không lưu lịch sử, và một lần chặn thì khác:
        đó là dữ liệu liêm chính học thuật, phải có dấu vết.
        """
        title = f"{self._QUICK_ASK_TITLE} — {subject_code}"
        conversation = (
            self._db.query(models.Conversation)
            .filter_by(student_id=student_id, subject_code=subject_code, title=title)
            .first()
        )
        if conversation is None:
            conversation = self._conversations.create(
                student_id=student_id, subject_code=subject_code, title=title
            )
        message = self._conversations.add_message(
            conversation_id=conversation.id,
            sender="USER",
            content=question,
            metadata={"channel": "quick_ask", "mode": "blocked"},
        )
        record_block(
            self._db, message_id=message.id, decision=decision, question=question
        )
        self._db.commit()
```

Trong `ask()`, nhánh `if decision.blocked:` — thêm lời gọi ngay sau `logger.info(...)`, trước `return QaResponse(...)`:

```python
            self._record_blocked_quick_ask(
                student_id=student_id,
                subject_code=code,
                question=question,
                decision=decision,
            )
```

> Lưu ý: truyền `question` (nguyên văn sinh viên gõ) chứ không phải `query` (bản đã normalize) — giảng viên duyệt cần đọc đúng thứ sinh viên viết.

Nếu `models` chưa được import trong `qa_service.py`, thêm `from src.db import models`.

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_guardrail_event_recording.py tests/test_api/test_qa_module.py tests/test_api/test_admin_student360.py -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add src/services/ai/qa_service.py tests/test_api/test_guardrail_event_recording.py
git commit -m "feat(guardrail): record blocked quick-ask questions for instructor review"
```

---

## Task 4: Chỉ tài liệu `PUBLISHED` mới vào RAG — ✅ ĐÃ XONG, BỎ QUA

> **Không cần làm.** Đã được vá trong commit `99a2ade` (chungnguyenvp, 26/08 04:53),
> đúng cách mô tả ở Step 3 bên dưới: điều kiện ở `chunk_repository.py` đổi từ
> `== "ARCHIVED"` sang `!= "PUBLISHED"`. Giữ lại phần mô tả để đối chiếu khi review.

Hiện `admin_document_ingest_service` tạo chunk ngay lúc upload với `publication_status="DRAFT"`, còn bộ lọc phía đọc chỉ loại `ARCHIVED` — nên tài liệu chưa duyệt đã trích dẫn được cho sinh viên.

**Files:**
- Modify: `src/repositories/chunk_repository.py:81-85`
- Test: `tests/test_repositories/test_chunk_publication_filter.py` (tạo mới)

**Interfaces:**
- Produces: không có API mới. Đổi hành vi `ChunkRepository.list_chunks_for_course`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_repositories/test_chunk_publication_filter.py`:

```python
import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from src.repositories.chunk_repository import ChunkRepository


@pytest.fixture
def seeded(request):
    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    code = f"ZZPUB{suffix[:3].upper()}"
    course = models.Course(id=f"course_{suffix}", code=code, name="Publication Filter Course")
    db.add(course)
    db.flush()

    def _add_doc(status: str, title: str) -> str:
        doc_id = f"doc_{status.lower()}_{suffix}"
        db.add(
            models.Document(
                id=doc_id,
                course_id=course.id,
                title=title,
                file_path=f"/tmp/{doc_id}.md",
                doc_type="SYLLABUS",
                version="1",
                metadata_info={"source": "admin_curriculum"},
                publication_status=status,
            )
        )
        db.flush()
        db.add(
            models.DocumentChunk(
                id=f"chunk_{status.lower()}_{suffix}",
                document_id=doc_id,
                chunk_index=0,
                text=f"Nội dung {status}",
                metadata_info={"source": "admin_curriculum"},
            )
        )
        db.flush()
        return doc_id

    _add_doc("DRAFT", "Bản nháp")
    _add_doc("PUBLISHED", "Bản đã duyệt")
    _add_doc("ARCHIVED", "Bản cũ")

    yield db, code
    db.rollback()
    db.close()


def test_draft_admin_documents_never_reach_a_learner(seeded):
    db, code = seeded

    chunks = ChunkRepository(db).list_chunks_for_course(subject_code=code)

    texts = {chunk.text for chunk in chunks}
    assert "Nội dung PUBLISHED" in texts
    assert "Nội dung DRAFT" not in texts
    assert "Nội dung ARCHIVED" not in texts


def test_non_admin_sources_are_unaffected_by_publication_status(seeded):
    """Tài liệu sinh viên tự tải lên không có vòng đời duyệt — không được
    lọc nhầm chúng đi cùng lúc với bản nháp của Admin."""
    db, code = seeded
    course = db.query(models.Course).filter_by(code=code).first()
    db.add(
        models.Document(
            id=f"doc_upload_{code}",
            course_id=course.id,
            title="SV tự tải",
            file_path="/tmp/upload.md",
            doc_type="NOTE",
            version="1",
            metadata_info={"source": "student_upload", "uploaded_by": "stu_x"},
            publication_status="DRAFT",
        )
    )
    db.flush()
    db.add(
        models.DocumentChunk(
            id=f"chunk_upload_{code}",
            document_id=f"doc_upload_{code}",
            chunk_index=0,
            text="Ghi chú riêng của sinh viên",
            metadata_info={"source": "student_upload", "uploaded_by": "stu_x"},
        )
    )
    db.flush()

    chunks = ChunkRepository(db).list_chunks_for_course(
        subject_code=code, student_id="stu_x"
    )

    assert "Ghi chú riêng của sinh viên" in {chunk.text for chunk in chunks}
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_repositories/test_chunk_publication_filter.py -v
```

Kỳ vọng: FAIL ở test thứ nhất — `assert 'Nội dung DRAFT' not in texts` (bản nháp đang lọt qua).

- [ ] **Step 3: Cài đặt tối thiểu**

Trong `src/repositories/chunk_repository.py`, thay khối:

```python
            # Historical Admin versions keep their chunks for rollback, but
            # archived content must never enter a learner's retrieval context.
            if source == "admin_curriculum" and document.publication_status == "ARCHIVED":
                continue
```

bằng:

```python
            # Vòng đời tài liệu Admin: DRAFT → VALIDATED → PUBLISHED → ARCHIVED.
            # Chỉ PUBLISHED được vào ngữ cảnh truy hồi của người học — bản nháp
            # chưa qua kiểm định, bản archived giữ lại chỉ để rollback.
            # Điều kiện cũ chỉ loại ARCHIVED nên bản nháp vẫn trích dẫn được
            # ngay sau khi upload, trái với chính vòng đời Admin đang thao tác.
            if source == "admin_curriculum" and document.publication_status != "PUBLISHED":
                continue
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_repositories/test_chunk_publication_filter.py tests/test_services/test_admin_document_ingest_service.py tests/test_api/test_qa_module.py -v
```

Kỳ vọng: PASS toàn bộ.

> Nếu một test cũ đỏ vì fixture của nó tạo document `admin_curriculum` mà không đặt `publication_status="PUBLISHED"`, đó là fixture cần sửa, không phải bug — cập nhật fixture rồi chạy lại.

- [ ] **Step 5: Commit**

```bash
git add src/repositories/chunk_repository.py tests/test_repositories/test_chunk_publication_filter.py
git commit -m "fix(rag): keep unpublished admin documents out of learner retrieval"
```

---

## Task 5: Audit 3 hành động đang mất dấu

Ba hành động nhạy cảm nhất hiện không để lại dấu vết trong Audit log mà Admin đọc:
1. Giảng viên **mở chặn** guardrail (`instructor.py:709`) — trả về field `auditMetadata` trong response nhưng không hề gọi `log_event`.
2. Giảng viên can thiệp lẻ (`instructor.py:327`) — chỉ bản `BULK_UPDATE_RISKS` được ghi.
3. Sinh viên tự xoá dữ liệu cá nhân (`student.py:677`) — xoá thật, không ghi gì.

**Files:**
- Modify: `src/api/instructor.py:709-750` (`decide_guardrail_review`), `:327-362` (`submit_intervention`)
- Modify: `src/api/student.py:677-710` (`delete_my_personal_data`)
- Modify: `src/services/core/admin_overview_service.py:26-41` (`CRITICAL_CHANGE_EVENTS`)
- Test: `tests/test_api/test_audit_coverage.py` (tạo mới)

**Interfaces:**
- Produces: 3 `event_type` mới — `GUARDRAIL_REVIEW_DECIDED`, `SUBMIT_INTERVENTION`, `SELF_SERVICE_DATA_DELETE`.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_audit_coverage.py`:

```python
import pytest

from src.db import models
from src.db.connection import SessionLocal


async def _login(client, email: str, password: str = "password123") -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _latest_event(event_type: str):
    db = SessionLocal()
    try:
        return (
            db.query(models.AuditLog)
            .filter(models.AuditLog.event_type == event_type)
            .order_by(models.AuditLog.created_at.desc())
            .first()
        )
    finally:
        db.close()


@pytest.mark.asyncio
async def test_self_service_data_delete_is_audited(client):
    headers = await _login(client, "student.demo@example.test")

    response = await client.post("/api/v1/student/personal-data/delete", headers=headers)
    assert response.status_code == 200

    event = _latest_event("SELF_SERVICE_DATA_DELETE")
    assert event is not None
    assert event.decision == "ALLOW"
    assert event.resource_type == "STUDENT_PERSONAL_DATA"
    # Số lượng đã xoá phải nằm trong metadata — một dòng log "đã xoá" mà
    # không nói xoá bao nhiêu thì không dùng được khi đối chiếu khiếu nại.
    assert "reflectionsDeleted" in (event.metadata_info or {})
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_audit_coverage.py -v
```

Kỳ vọng: FAIL — `assert None is not None`.

- [ ] **Step 3: Cài đặt tối thiểu**

**(a)** `src/api/student.py` — `delete_my_personal_data` hiện là `def`, đổi sang `async def` và ghi audit trước khi return. Thêm import nếu chưa có:

```python
from src.repositories.audit_repository import AuditRepository
from src.services.core.audit_service import AuditService
```

Đổi chữ ký:

```python
async def delete_my_personal_data(
```

Trước `return {...}`, chèn:

```python
    await AuditService(AuditRepository(db)).log_event(
        event_type="SELF_SERVICE_DATA_DELETE",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="STUDENT_PERSONAL_DATA",
        resource_id=current_user.id,
        metadata={
            "reflectionsDeleted": reflections_deleted,
            "conversationsDeleted": conversations_deleted,
            "messagesDeleted": messages_deleted,
        },
    )
```

**(b)** `src/api/instructor.py` — `decide_guardrail_review`: đổi `def` → `async def`, và trước `return {...}` chèn:

```python
    await AuditService(AuditRepository(db)).log_event(
        event_type="GUARDRAIL_REVIEW_DECIDED",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="GUARDRAIL_EVENT",
        resource_id=event.id,
        metadata={
            "decision": decision,
            "previousState": previous,
            "newState": event.review_status,
            "note": payload.note,
        },
    )
```

**(c)** `src/api/instructor.py` — `submit_intervention`: đổi `def` → `async def`, và ngay trước khi trả kết quả chèn:

```python
    await AuditService(AuditRepository(db)).log_event(
        event_type="SUBMIT_INTERVENTION",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="RISK_SIGNAL",
        resource_id=risk_id,
        metadata={"decision": payload.decision},
    )
```

**(d)** `src/services/core/admin_overview_service.py` — thêm 3 loại vào `CRITICAL_CHANGE_EVENTS` để chúng hiện ở "Thay đổi quan trọng gần đây" trên Overview:

```python
        "GUARDRAIL_REVIEW_DECIDED",
        "SUBMIT_INTERVENTION",
        "SELF_SERVICE_DATA_DELETE",
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_audit_coverage.py tests/test_api/test_instructor.py tests/test_api/test_student_personal_data_deletion.py tests/test_api/test_admin_overview.py -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add src/api/instructor.py src/api/student.py src/services/core/admin_overview_service.py tests/test_api/test_audit_coverage.py
git commit -m "feat(audit): record guardrail overrides, single interventions and self-service deletes"
```

---

# PHASE 2 — Admin cấp phát lớp học

## Task 6: Backend quản trị lớp — CRUD `CourseSection` + gán giảng viên

**Files:**
- Create: `src/api/admin_sections.py`
- Create: `src/services/core/admin_section_service.py`
- Modify: `src/schemas/admin_schemas.py` (thêm schema ở cuối file)
- Modify: `src/main.py:110` (đăng ký router)
- Test: `tests/test_api/test_admin_sections.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/admin/sections` → `{"items": [SectionOut]}`
  - `POST /api/v1/admin/sections` → `SectionOut` (201)
  - `PATCH /api/v1/admin/sections/{section_id}` → `SectionOut`
  - `DELETE /api/v1/admin/sections/{section_id}` → 204
  - `SectionOut` = `{id, courseCode, courseName, sectionCode, term, instructorId, instructorName, enrolledCount}`
  - Task 7 và Task 9 đều dựa vào đúng tên field này.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_admin_sections.py`:

```python
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


@pytest.fixture
def org_setup():
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"sec-org-{suffix}", name="Section Org")
    admin_email = f"admin.sec.{suffix}@test.local"
    inst_email = f"inst.sec.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    instructor_id = ensure_user(
        email=inst_email, org_id=org_id, role=models.UserRole.INSTRUCTOR
    )
    course_id = ensure_course(code=f"ZZSEC{suffix[:3].upper()}", org_id=org_id)
    return {
        "org_id": org_id,
        "admin_email": admin_email,
        "instructor_id": instructor_id,
        "course_id": course_id,
    }


@pytest.mark.asyncio
async def test_admin_creates_a_section_and_assigns_an_instructor(client, org_setup):
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)

    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1801",
            "term": "Fall2026",
            "instructorId": org_setup["instructor_id"],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["sectionCode"] == "SE1801"
    assert body["instructorId"] == org_setup["instructor_id"]
    assert body["enrolledCount"] == 0

    listed = await client.get("/api/v1/admin/sections", headers=headers)
    assert listed.status_code == 200
    assert any(item["id"] == body["id"] for item in listed.json()["items"])


@pytest.mark.asyncio
async def test_admin_can_reassign_the_instructor_of_a_section(client, org_setup):
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)

    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1802",
            "term": "Fall2026",
            "instructorId": None,
        },
    )
    section_id = created.json()["id"]

    updated = await client.patch(
        f"/api/v1/admin/sections/{section_id}",
        headers=headers,
        json={"instructorId": org_setup["instructor_id"]},
    )
    assert updated.status_code == 200
    assert updated.json()["instructorId"] == org_setup["instructor_id"]


@pytest.mark.asyncio
async def test_cannot_assign_an_instructor_from_another_organization(client, org_setup):
    other_org = ensure_org(slug=f"other-{uuid.uuid4().hex[:6]}", name="Other Org")
    outsider = ensure_user(
        email=f"outsider.{uuid.uuid4().hex[:6]}@test.local",
        org_id=other_org,
        role=models.UserRole.INSTRUCTOR,
    )
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)

    response = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1803",
            "term": "Fall2026",
            "instructorId": outsider,
        },
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_deleting_a_section_with_enrolled_students_is_refused(client, org_setup):
    token = await login(client, org_setup["admin_email"])
    headers = auth_headers(token)
    created = await client.post(
        "/api/v1/admin/sections",
        headers=headers,
        json={
            "courseId": org_setup["course_id"],
            "sectionCode": "SE1804",
            "term": "Fall2026",
            "instructorId": org_setup["instructor_id"],
        },
    )
    section_id = created.json()["id"]

    db = SessionLocal()
    try:
        student_id = ensure_user(
            email=f"stu.{uuid.uuid4().hex[:6]}@test.local",
            org_id=org_setup["org_id"],
            role=models.UserRole.STUDENT,
        )
        db.add(
            models.Enrollment(
                id=f"enr_{uuid.uuid4().hex[:10]}",
                student_id=student_id,
                section_id=section_id,
                status=models.EnrollmentStatus.ENROLLED.value,
            )
        )
        db.commit()
    finally:
        db.close()

    response = await client.delete(
        f"/api/v1/admin/sections/{section_id}", headers=headers
    )
    assert response.status_code == 409
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_sections.py -v
```

Kỳ vọng: FAIL — 404 trên mọi route (`/api/v1/admin/sections` chưa tồn tại).

- [ ] **Step 3: Cài đặt tối thiểu**

Thêm vào cuối `src/schemas/admin_schemas.py`:

```python
class SectionCreateRequest(BaseModel):
    course_id: str = Field(alias="courseId")
    section_code: str = Field(alias="sectionCode", min_length=1, max_length=32)
    term: str = Field(min_length=1, max_length=32)
    instructor_id: str | None = Field(default=None, alias="instructorId")

    model_config = ConfigDict(populate_by_name=True)


class SectionUpdateRequest(BaseModel):
    section_code: str | None = Field(default=None, alias="sectionCode", max_length=32)
    term: str | None = Field(default=None, max_length=32)
    instructor_id: str | None = Field(default=None, alias="instructorId")

    model_config = ConfigDict(populate_by_name=True)


class SectionOut(BaseModel):
    id: str
    course_code: str = Field(serialization_alias="courseCode")
    course_name: str = Field(serialization_alias="courseName")
    section_code: str = Field(serialization_alias="sectionCode")
    term: str
    instructor_id: str | None = Field(serialization_alias="instructorId")
    instructor_name: str | None = Field(serialization_alias="instructorName")
    enrolled_count: int = Field(serialization_alias="enrolledCount")

    model_config = ConfigDict(populate_by_name=True)
```

> Kiểm tra đầu file đã import `ConfigDict` và `Field` từ `pydantic` chưa; nếu chưa thì thêm.

Tạo `src/services/core/admin_section_service.py`:

```python
"""Quản trị lớp học cho Admin — phần "cấp phát" mà trước đây không role nào có.

Trước dịch vụ này, `CourseSection`/`Enrollment` chỉ được tạo bởi wizard học kỳ
của sinh viên và các script seed, nên Admin không có cách nào sửa việc gán sai
giảng viên. Mọi truy vấn ở đây đều fail-closed theo `organization_id` của admin
đang gọi.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from src.db import models


class SectionNotFoundError(LookupError):
    """Lớp không tồn tại, hoặc thuộc tổ chức khác — trả 404 cho cả 2 để không
    lộ sự tồn tại của dữ liệu tổ chức khác."""


class SectionInUseError(RuntimeError):
    """Lớp còn sinh viên đang học."""


def _course_belongs_to(course: models.Course, organization_id: str | None) -> bool:
    """Catalog môn học đang dùng chung giữa các tổ chức (`Course.organization_id`
    có thể NULL) — quy tắc duy nhất cho cả đọc lẫn ghi, đặt ở một chỗ để
    `list_sections` và `_require_course` không bao giờ lệch nhau."""
    return course.organization_id is None or course.organization_id == organization_id


def _require_course(db: Session, course_id: str, organization_id: str | None) -> models.Course:
    course = db.get(models.Course, course_id)
    if course is None or not _course_belongs_to(course, organization_id):
        raise SectionNotFoundError("course_not_found")
    return course


def _require_instructor(
    db: Session, instructor_id: str | None, organization_id: str | None
) -> models.User | None:
    if instructor_id is None:
        return None
    user = db.get(models.User, instructor_id)
    if user is None or user.organization_id != organization_id:
        raise SectionNotFoundError("instructor_not_found")
    if str(user.role) not in {
        models.UserRole.INSTRUCTOR.value,
        models.UserRole.INSTRUCTOR,
    }:
        raise SectionNotFoundError("instructor_not_found")
    return user


def _enrolled_count(db: Session, section_id: str) -> int:
    return (
        db.query(models.Enrollment)
        .filter_by(section_id=section_id, status=models.EnrollmentStatus.ENROLLED.value)
        .count()
    )


def serialize(db: Session, section: models.CourseSection) -> dict:
    course = db.get(models.Course, section.course_id)
    instructor = db.get(models.User, section.instructor_id) if section.instructor_id else None
    return {
        "id": section.id,
        "course_code": course.code if course else "",
        "course_name": course.name if course else "",
        "section_code": section.section_code or "",
        "term": section.term or "",
        "instructor_id": section.instructor_id,
        "instructor_name": instructor.full_name if instructor else None,
        "enrolled_count": _enrolled_count(db, section.id),
    }


def list_sections(db: Session, *, organization_id: str | None) -> list[dict]:
    rows = (
        db.query(models.CourseSection, models.Course)
        .join(models.Course, models.Course.id == models.CourseSection.course_id)
        .order_by(models.Course.code, models.CourseSection.section_code)
        .all()
    )
    return [
        serialize(db, section)
        for section, course in rows
        if _course_belongs_to(course, organization_id)
    ]


def create_section(
    db: Session,
    *,
    organization_id: str | None,
    course_id: str,
    section_code: str,
    term: str,
    instructor_id: str | None,
) -> dict:
    _require_course(db, course_id, organization_id)
    _require_instructor(db, instructor_id, organization_id)
    section = models.CourseSection(
        id=f"sec_adm_{uuid.uuid4().hex[:12]}",
        course_id=course_id,
        instructor_id=instructor_id,
        term=term[:32],
        section_code=section_code[:32],
    )
    db.add(section)
    db.flush()
    return serialize(db, section)


def _require_section(
    db: Session, section_id: str, organization_id: str | None
) -> models.CourseSection:
    section = db.get(models.CourseSection, section_id)
    if section is None:
        raise SectionNotFoundError("section_not_found")
    _require_course(db, section.course_id, organization_id)
    return section


def update_section(
    db: Session,
    *,
    organization_id: str | None,
    section_id: str,
    section_code: str | None,
    term: str | None,
    instructor_id: str | None,
    instructor_field_present: bool,
) -> dict:
    section = _require_section(db, section_id, organization_id)
    if section_code is not None:
        section.section_code = section_code[:32]
    if term is not None:
        section.term = term[:32]
    if instructor_field_present:
        _require_instructor(db, instructor_id, organization_id)
        section.instructor_id = instructor_id
    db.flush()
    return serialize(db, section)


def delete_section(db: Session, *, organization_id: str | None, section_id: str) -> None:
    section = _require_section(db, section_id, organization_id)
    if _enrolled_count(db, section.id) > 0:
        raise SectionInUseError("section_has_enrolled_students")
    db.delete(section)
    db.flush()
```

Tạo `src/api/admin_sections.py`:

```python
"""Admin Console — quản trị lớp học (`/admin/sections`)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.audit_repository import AuditRepository
from src.schemas.admin_schemas import SectionCreateRequest, SectionOut, SectionUpdateRequest
from src.security.authorization import require_permission, require_roles
from src.security.permissions import Permission, Resource
from src.services.core import admin_section_service as svc
from src.services.core.audit_service import AuditService

router = APIRouter(
    prefix="/admin/sections",
    tags=["admin-sections"],
    dependencies=[
        Depends(require_roles(models.UserRole.ADMIN)),
        Depends(require_permission(Resource.COURSE, Permission.MANAGE)),
    ],
)


def _org_or_404(current_user: models.User) -> str:
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="organization_required")
    return current_user.organization_id


@router.get("")
def list_sections(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    return {"items": svc.list_sections(db, organization_id=_org_or_404(current_user))}


@router.post("", response_model=SectionOut, status_code=status.HTTP_201_CREATED)
async def create_section(
    payload: SectionCreateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    org = _org_or_404(current_user)
    try:
        created = svc.create_section(
            db,
            organization_id=org,
            course_id=payload.course_id,
            section_code=payload.section_code,
            term=payload.term,
            instructor_id=payload.instructor_id,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_section_created",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="COURSE_SECTION",
        resource_id=created["id"],
        metadata={"instructorId": created["instructor_id"]},
    )
    return SectionOut(**created)


@router.patch("/{section_id}", response_model=SectionOut)
async def update_section(
    section_id: str,
    payload: SectionUpdateRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    org = _org_or_404(current_user)
    try:
        updated = svc.update_section(
            db,
            organization_id=org,
            section_id=section_id,
            section_code=payload.section_code,
            term=payload.term,
            instructor_id=payload.instructor_id,
            # pydantic v2 với populate_by_name ghi TÊN FIELD vào model_fields_set,
            # không phải alias — nên chỉ kiểm "instructor_id". Cần phân biệt
            # "không gửi field này" (giữ nguyên GV) với "gửi null" (bỏ gán GV).
            instructor_field_present="instructor_id" in payload.model_fields_set,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_section_updated",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="COURSE_SECTION",
        resource_id=section_id,
        metadata={"instructorId": updated["instructor_id"]},
    )
    return SectionOut(**updated)


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    section_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    org = _org_or_404(current_user)
    try:
        svc.delete_section(db, organization_id=org, section_id=section_id)
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except svc.SectionInUseError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_section_deleted",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="COURSE_SECTION",
        resource_id=section_id,
    )
```

Trong `src/main.py`, thêm import cạnh các router admin khác và đăng ký ngay sau `admin_people_router`:

```python
app.include_router(admin_sections_router, prefix="/api/v1")
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_sections.py -v
```

Kỳ vọng: PASS cả 4 test.

- [ ] **Step 5: Commit**

```bash
git add src/api/admin_sections.py src/services/core/admin_section_service.py src/schemas/admin_schemas.py src/main.py tests/test_api/test_admin_sections.py
git commit -m "feat(admin): manage course sections and instructor assignment"
```

---

## Task 7: Backend quản lý danh sách sinh viên trong lớp

**Files:**
- Modify: `src/services/core/admin_section_service.py` (thêm 3 hàm ở cuối)
- Modify: `src/api/admin_sections.py` (thêm 3 route)
- Test: `tests/test_api/test_admin_section_roster.py`

**Interfaces:**
- Consumes: `_require_section`, `SectionNotFoundError` (Task 6).
- Produces:
  - `GET /api/v1/admin/sections/{id}/roster` → `{"items": [{studentId, fullName, email, status}]}`
  - `POST /api/v1/admin/sections/{id}/roster` body `{"studentId": "..."}` → 201
  - `DELETE /api/v1/admin/sections/{id}/roster/{student_id}` → 204

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_admin_section_roster.py`:

```python
import uuid

import pytest

from src.db import models
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_course,
    ensure_org,
    ensure_user,
    login,
)


@pytest.fixture
def roster_setup():
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"ros-org-{suffix}", name="Roster Org")
    admin_email = f"admin.ros.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    student_id = ensure_user(
        email=f"stu.ros.{suffix}@test.local", org_id=org_id, role=models.UserRole.STUDENT
    )
    course_id = ensure_course(code=f"ZZROS{suffix[:3].upper()}", org_id=org_id)
    return {
        "org_id": org_id,
        "admin_email": admin_email,
        "student_id": student_id,
        "course_id": course_id,
    }


@pytest.mark.asyncio
async def test_admin_adds_and_removes_a_student_from_a_section(client, roster_setup):
    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)
    section_id = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1900",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()["id"]

    added = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": roster_setup["student_id"]},
    )
    assert added.status_code == 201, added.text

    listed = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert listed.status_code == 200
    assert [item["studentId"] for item in listed.json()["items"]] == [
        roster_setup["student_id"]
    ]

    removed = await client.delete(
        f"/api/v1/admin/sections/{section_id}/roster/{roster_setup['student_id']}",
        headers=headers,
    )
    assert removed.status_code == 204

    after = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert after.json()["items"] == []


@pytest.mark.asyncio
async def test_adding_the_same_student_twice_is_idempotent(client, roster_setup):
    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)
    section_id = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1901",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()["id"]

    body = {"studentId": roster_setup["student_id"]}
    first = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers, json=body
    )
    second = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers, json=body
    )

    assert first.status_code == 201
    assert second.status_code == 201
    listed = await client.get(
        f"/api/v1/admin/sections/{section_id}/roster", headers=headers
    )
    assert len(listed.json()["items"]) == 1


@pytest.mark.asyncio
async def test_cannot_enrol_a_student_from_another_organization(client, roster_setup):
    outsider = ensure_user(
        email=f"out.{uuid.uuid4().hex[:6]}@test.local",
        org_id=ensure_org(slug=f"out-{uuid.uuid4().hex[:6]}", name="Out"),
        role=models.UserRole.STUDENT,
    )
    token = await login(client, roster_setup["admin_email"])
    headers = auth_headers(token)
    section_id = (
        await client.post(
            "/api/v1/admin/sections",
            headers=headers,
            json={
                "courseId": roster_setup["course_id"],
                "sectionCode": "SE1902",
                "term": "Fall2026",
                "instructorId": None,
            },
        )
    ).json()["id"]

    response = await client.post(
        f"/api/v1/admin/sections/{section_id}/roster",
        headers=headers,
        json={"studentId": outsider},
    )
    assert response.status_code == 404
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_section_roster.py -v
```

Kỳ vọng: FAIL — 404/405 vì route roster chưa có.

- [ ] **Step 3: Cài đặt tối thiểu**

Thêm vào cuối `src/services/core/admin_section_service.py`:

```python
def list_roster(db: Session, *, organization_id: str | None, section_id: str) -> list[dict]:
    _require_section(db, section_id, organization_id)
    rows = (
        db.query(models.Enrollment, models.User)
        .join(models.User, models.User.id == models.Enrollment.student_id)
        .filter(models.Enrollment.section_id == section_id)
        .order_by(models.User.full_name)
        .all()
    )
    return [
        {
            "studentId": user.id,
            "fullName": user.full_name,
            "email": user.email,
            "status": enrollment.status,
        }
        for enrollment, user in rows
    ]


def add_to_roster(
    db: Session, *, organization_id: str | None, section_id: str, student_id: str
) -> None:
    _require_section(db, section_id, organization_id)
    student = db.get(models.User, student_id)
    if student is None or student.organization_id != organization_id:
        raise SectionNotFoundError("student_not_found")
    if str(student.role) not in {models.UserRole.STUDENT.value, models.UserRole.STUDENT}:
        raise SectionNotFoundError("student_not_found")
    existing = (
        db.query(models.Enrollment)
        .filter_by(student_id=student_id, section_id=section_id)
        .first()
    )
    if existing is not None:
        # Idempotent: bấm 2 lần không tạo 2 dòng, và cũng không báo lỗi —
        # Admin thao tác hàng loạt, một cú double-click không nên thành 409.
        existing.status = models.EnrollmentStatus.ENROLLED.value
        db.flush()
        return
    db.add(
        models.Enrollment(
            id=f"enr_adm_{uuid.uuid4().hex[:12]}",
            student_id=student_id,
            section_id=section_id,
            status=models.EnrollmentStatus.ENROLLED.value,
        )
    )
    db.flush()


def remove_from_roster(
    db: Session, *, organization_id: str | None, section_id: str, student_id: str
) -> None:
    _require_section(db, section_id, organization_id)
    enrollment = (
        db.query(models.Enrollment)
        .filter_by(student_id=student_id, section_id=section_id)
        .first()
    )
    if enrollment is None:
        raise SectionNotFoundError("enrollment_not_found")
    db.delete(enrollment)
    db.flush()
```

Thêm vào `src/schemas/admin_schemas.py`:

```python
class RosterAddRequest(BaseModel):
    student_id: str = Field(alias="studentId")

    model_config = ConfigDict(populate_by_name=True)
```

Thêm vào `src/api/admin_sections.py` (import `RosterAddRequest` ở đầu file):

```python
@router.get("/{section_id}/roster")
def list_roster(
    section_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        items = svc.list_roster(
            db, organization_id=_org_or_404(current_user), section_id=section_id
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": items}


@router.post("/{section_id}/roster", status_code=status.HTTP_201_CREATED)
async def add_to_roster(
    section_id: str,
    payload: RosterAddRequest,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        svc.add_to_roster(
            db,
            organization_id=_org_or_404(current_user),
            section_id=section_id,
            student_id=payload.student_id,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_enrollment_added",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="ENROLLMENT",
        resource_id=f"{section_id}:{payload.student_id}",
    )
    return {"success": True}


@router.delete("/{section_id}/roster/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_roster(
    section_id: str,
    student_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    try:
        svc.remove_from_roster(
            db,
            organization_id=_org_or_404(current_user),
            section_id=section_id,
            student_id=student_id,
        )
    except svc.SectionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.commit()
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_enrollment_removed",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="ENROLLMENT",
        resource_id=f"{section_id}:{student_id}",
    )
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_section_roster.py tests/test_api/test_admin_sections.py -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add src/api/admin_sections.py src/services/core/admin_section_service.py src/schemas/admin_schemas.py tests/test_api/test_admin_section_roster.py
git commit -m "feat(admin): manage the student roster of a section"
```

---

## Task 8: Bỏ `first_instructor_id()` — lớp chưa gán GV thành việc trong Work Queue

Đây là gốc của "3 role không đồng bộ": khi sinh viên chạy wizard học kỳ, `semester_repository.first_instructor_id()` gán lớp cho **giảng viên đầu tiên tìm thấy trong tổ chức**, nên giảng viên đó thấy sinh viên mình không dạy. Sửa: tạo lớp **không gán ai**, rồi đẩy vào Work Queue để Admin gán bằng Task 6.

**Files:**
- Modify: `src/repositories/semester_repository.py:167-183` (xoá `first_instructor_id`), `:185-201` (`get_or_create_section`)
- Modify: `src/services/academic/semester_service.py` (nơi gọi `first_instructor_id`)
- Modify: `src/services/core/admin_overview_service.py:170` (`build_work_queue`)
- Modify: `frontend/src/components/admin/adminWorkQueueLinks.js`
- Test: `tests/test_api/test_unassigned_section_queue.py`

**Interfaces:**
- Consumes: `ADMIN_PATHS.sections` (thêm ở Task 9 — tạm dùng chuỗi `'/admin/governance/sections'` ở task này, Task 9 thay bằng hằng số).
- Produces: `trigger_type` mới `UNASSIGNED_SECTION` trong Work Queue.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_unassigned_section_queue.py`:

```python
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


@pytest.mark.asyncio
async def test_a_section_without_an_instructor_shows_up_in_the_work_queue(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"unassigned-{suffix}", name="Unassigned Org")
    admin_email = f"admin.un.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    course_id = ensure_course(code=f"ZZUN{suffix[:3].upper()}", org_id=org_id)

    db = SessionLocal()
    try:
        db.add(
            models.CourseSection(
                id=f"sec_un_{suffix}",
                course_id=course_id,
                instructor_id=None,
                term="Fall2026",
                section_code="SE-UN",
            )
        )
        db.commit()
    finally:
        db.close()

    token = await login(client, admin_email)
    response = await client.get("/api/v1/admin/work-queue", headers=auth_headers(token))

    assert response.status_code == 200
    items = response.json()["items"]
    assert any(
        item["trigger_type"] == "UNASSIGNED_SECTION" and item["subject_id"] == f"sec_un_{suffix}"
        for item in items
    ), items


def test_semester_repository_no_longer_guesses_an_instructor():
    from src.repositories import semester_repository

    assert not hasattr(semester_repository.SemesterRepository, "first_instructor_id"), (
        "first_instructor_id gán lớp cho một giảng viên bất kỳ — đã được thay "
        "bằng lớp chưa gán + việc trong Work Queue"
    )
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_unassigned_section_queue.py -v
```

Kỳ vọng: FAIL cả 2 — chưa có `UNASSIGNED_SECTION`, và `first_instructor_id` vẫn còn.

- [ ] **Step 3: Cài đặt tối thiểu**

**(a)** `src/repositories/semester_repository.py` — xoá hoàn toàn method `first_instructor_id`. Đổi chữ ký `get_or_create_section` để `instructor_id` không còn bắt buộc:

```python
    def get_or_create_section(
        self,
        *,
        semester_id: str,
        course: models.Course,
        term: str,
        instructor_id: str | None = None,
    ) -> models.CourseSection:
```

Phần thân giữ nguyên (đã truyền `instructor_id=instructor_id` vào `CourseSection`).

**(b)** `src/services/academic/semester_service.py` — tìm chỗ gọi `first_instructor_id(...)` và bỏ đi; lời gọi `get_or_create_section` không truyền `instructor_id` nữa:

```python
        section = self._repo.get_or_create_section(
            semester_id=semester.id, course=course, term=term
        )
```

**(c)** `src/services/core/admin_overview_service.py` — thêm nguồn thứ 5 vào `build_work_queue`, đặt ngay trước dòng `return`:

```python
    unassigned_sections = (
        db.query(models.CourseSection, models.Course)
        .join(models.Course, models.Course.id == models.CourseSection.course_id)
        .filter(
            models.Course.organization_id == organization_id,
            models.CourseSection.instructor_id.is_(None),
        )
        .order_by(models.Course.code)
        .limit(20)
        .all()
    )
    for section, course in unassigned_sections:
        items.append(
            {
                "trigger_type": "UNASSIGNED_SECTION",
                "subject_id": section.id,
                "subject_user_id": None,
                "label": f"{course.code} · {section.section_code or section.id}",
                "detail": "Lớp chưa có giảng viên phụ trách",
                "occurred_at": None,
                "age_seconds": 0,
            }
        )
```

> Đối chiếu tên biến tích luỹ (`items`) và hình dạng dict với 4 nguồn đã có ở
> `build_work_queue` trước khi dán — dùng đúng key mà chúng đang dùng, không
> tự đặt key mới.

**(d)** `frontend/src/components/admin/adminWorkQueueLinks.js` — thêm vào `FIXED_HREF_BY_TRIGGER`:

```js
  UNASSIGNED_SECTION: '/admin/governance/sections',
```

Đồng thời chuyển dòng `import { ADMIN_PATHS } from './adminRoutes';` lên **đầu file** (hiện đang nằm ở cuối — chạy được nhờ hoisting nhưng gây hiểu nhầm khi đọc).

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_unassigned_section_queue.py tests/test_api/test_semester_api.py tests/test_api/test_admin_overview.py tests/test_academic -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Commit**

```bash
git add src/repositories/semester_repository.py src/services/academic/semester_service.py src/services/core/admin_overview_service.py frontend/src/components/admin/adminWorkQueueLinks.js tests/test_api/test_unassigned_section_queue.py
git commit -m "fix(semester): stop assigning an arbitrary instructor, queue it for admin instead"
```

---

## Task 9: Màn hình "Lớp học" trong Admin Console + reset mật khẩu

**Files:**
- Create: `frontend/src/components/admin/AdminSections.jsx`
- Modify: `frontend/src/components/admin/adminRoutes.js` (thêm path)
- Modify: `frontend/src/components/admin/adminNavigationConfig.js` (thêm nav item)
- Modify: `frontend/src/components/admin/AdminConsole.jsx` (thêm `<Route>`)
- Modify: `frontend/src/components/admin/adminWorkQueueLinks.js` (dùng hằng số thay chuỗi cứng)
- Modify: `frontend/src/lib/api.js` (5 hàm mới)
- Modify: `frontend/src/locales/vi.js`, `frontend/src/locales/en.js`
- Modify: `src/api/admin.py` (route reset mật khẩu)
- Test: `tests/test_api/test_admin_password_reset.py`

**Interfaces:**
- Consumes: `SectionOut` (Task 6), roster routes (Task 7).
- Produces: `POST /api/v1/admin/users/{user_id}/reset-password` → `{"success": true, "emailSent": bool}`

- [x] **Step 1: Viết test thất bại (backend reset mật khẩu)**

Tạo `tests/test_api/test_admin_password_reset.py`:

```python
import uuid

import pytest

from src.db import models
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_org,
    ensure_user,
    login,
)


@pytest.mark.asyncio
async def test_admin_can_trigger_a_password_reset_for_a_member(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"pwd-{suffix}", name="Password Org")
    admin_email = f"admin.pwd.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    target_id = ensure_user(
        email=f"stu.pwd.{suffix}@test.local", org_id=org_id, role=models.UserRole.STUDENT
    )

    token = await login(client, admin_email)
    response = await client.post(
        f"/api/v1/admin/users/{target_id}/reset-password", headers=auth_headers(token)
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_cannot_reset_a_password_in_another_organization(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"pwd-a-{suffix}", name="Org A")
    admin_email = f"admin.a.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    outsider = ensure_user(
        email=f"stu.b.{suffix}@test.local",
        org_id=ensure_org(slug=f"pwd-b-{suffix}", name="Org B"),
        role=models.UserRole.STUDENT,
    )

    token = await login(client, admin_email)
    response = await client.post(
        f"/api/v1/admin/users/{outsider}/reset-password", headers=auth_headers(token)
    )

    assert response.status_code == 404
```

- [x] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_password_reset.py -v
```

Kỳ vọng: FAIL — 404/405 (route chưa tồn tại).

- [x] **Step 3: Cài đặt backend**

Trong `src/api/admin.py`, ngay dưới `PATCH /users/{user_id}/status`, thêm:

```python
@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    """Gửi lại link đặt mật khẩu cho một thành viên trong cùng tổ chức.

    Admin KHÔNG đặt mật khẩu thay người dùng — chỉ phát hành token đặt lại,
    người dùng tự chọn mật khẩu mới. Dùng lại đúng luồng "Quên mật khẩu"
    đã có (`src/api/auth.py`) để không tồn tại 2 cơ chế token song song.
    """
    if not current_user.organization_id:
        raise HTTPException(status_code=404, detail="organization_required")
    target = db.get(models.User, user_id)
    if target is None or target.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="user_not_found")

    from src.services.auth.password_reset_service import issue_password_reset

    email_sent = await issue_password_reset(db, user=target)
    await AuditService(AuditRepository(db)).log_event(
        event_type="admin_password_reset_issued",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="USER",
        resource_id=user_id,
    )
    return {"success": True, "emailSent": bool(email_sent)}
```

> **Trước khi viết dòng `from src.services.auth...`:** mở `src/api/auth.py`, tìm
> handler `POST /auth/forgot-password` và dùng **đúng** hàm/service nó đang gọi.
> Nếu logic đó nằm inline trong route chứ chưa tách thành service, tách nó ra
> `src/services/auth/password_reset_service.py` với chữ ký
> `async def issue_password_reset(db: Session, *, user: models.User) -> bool`,
> rồi cho cả route cũ lẫn route mới cùng gọi hàm đó. Không sao chép logic.

- [x] **Step 4: Chạy test backend, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_password_reset.py tests/test_api/test_password_reset_module.py tests/test_api/test_admin_users.py -v
```

Kỳ vọng: PASS toàn bộ.

- [x] **Step 5: Thêm hàm API frontend**

Trong `frontend/src/lib/api.js`, thêm cạnh các hàm admin khác:

```js
export async function getAdminSections() {
  return request('/admin/sections');
}

export async function createAdminSection(body) {
  return request('/admin/sections', { method: 'POST', body });
}

export async function updateAdminSection(sectionId, body) {
  return request(`/admin/sections/${encodeURIComponent(sectionId)}`, { method: 'PATCH', body });
}

export async function deleteAdminSection(sectionId) {
  return request(`/admin/sections/${encodeURIComponent(sectionId)}`, { method: 'DELETE' });
}

export async function getAdminSectionRoster(sectionId) {
  return request(`/admin/sections/${encodeURIComponent(sectionId)}/roster`);
}

export async function addAdminSectionStudent(sectionId, studentId) {
  return request(`/admin/sections/${encodeURIComponent(sectionId)}/roster`, {
    method: 'POST',
    body: { studentId },
  });
}

export async function removeAdminSectionStudent(sectionId, studentId) {
  return request(
    `/admin/sections/${encodeURIComponent(sectionId)}/roster/${encodeURIComponent(studentId)}`,
    { method: 'DELETE' },
  );
}

export async function resetAdminUserPassword(userId) {
  return request(`/admin/users/${encodeURIComponent(userId)}/reset-password`, { method: 'POST' });
}
```

> Kiểm tra `request()` trong file này trả về payload đã unwrap hay chưa, rồi
> khớp cho đúng — commit `c79ec39` từng phải revert vì "double-unwrapped api.js calls".

- [x] **Step 6: Thêm route + nav**

`frontend/src/components/admin/adminRoutes.js` — thêm vào `ADMIN_PATHS`:

```js
  sections: '/admin/governance/sections',
```

`frontend/src/components/admin/adminNavigationConfig.js` — thêm vào nhóm `governance`, ngay sau `curriculum`:

```js
      { to: ADMIN_PATHS.sections, labelKey: 'admin.navSections' },
```

`frontend/src/components/admin/AdminConsole.jsx` — thêm `<Route>` cạnh các route governance khác, theo đúng khuôn các route đang có trong file:

```jsx
        <Route path="governance/sections" element={
          <AdminSections />
        } />
```

`frontend/src/components/admin/adminWorkQueueLinks.js` — thay chuỗi cứng đã đặt ở Task 8:

```js
  UNASSIGNED_SECTION: ADMIN_PATHS.sections,
```

Thêm khoá dịch. `frontend/src/locales/vi.js`:

```js
  'admin.navSections': 'Lớp học',
  'admin.sectionsTitle': 'Quản trị lớp học',
  'admin.sectionsColCourse': 'Môn',
  'admin.sectionsColSection': 'Mã lớp',
  'admin.sectionsColTerm': 'Học kỳ',
  'admin.sectionsColInstructor': 'Giảng viên',
  'admin.sectionsColEnrolled': 'Sĩ số',
  'admin.sectionsUnassigned': 'Chưa gán',
  'admin.sectionsCreate': 'Thêm lớp',
  'admin.sectionsAssign': 'Gán giảng viên',
  'admin.sectionsRoster': 'Danh sách sinh viên',
  'admin.sectionsDeleteConfirm': 'Xoá lớp này? Chỉ xoá được khi lớp không còn sinh viên.',
  'admin.resetPassword': 'Đặt lại mật khẩu',
  'admin.resetPasswordConfirm': 'Gửi link đặt lại mật khẩu cho người dùng này?',
```

`frontend/src/locales/en.js` — **cùng bộ khoá**, bản tiếng Anh:

```js
  'admin.navSections': 'Sections',
  'admin.sectionsTitle': 'Section management',
  'admin.sectionsColCourse': 'Course',
  'admin.sectionsColSection': 'Section',
  'admin.sectionsColTerm': 'Term',
  'admin.sectionsColInstructor': 'Instructor',
  'admin.sectionsColEnrolled': 'Enrolled',
  'admin.sectionsUnassigned': 'Unassigned',
  'admin.sectionsCreate': 'Add section',
  'admin.sectionsAssign': 'Assign instructor',
  'admin.sectionsRoster': 'Student roster',
  'admin.sectionsDeleteConfirm': 'Delete this section? Only possible when no students remain.',
  'admin.resetPassword': 'Reset password',
  'admin.resetPasswordConfirm': 'Send a password reset link to this user?',
```

- [x] **Step 7: Viết component**

Tạo `frontend/src/components/admin/AdminSections.jsx`. Bám đúng khuôn `AdminUsers.jsx`
(cùng thư mục) cho: cách gọi `useEffect` tải dữ liệu, `AdminAsyncRegion` cho
loading/error/retry, `.data-table` cho bảng, `ConfirmDialog` cho hành động xoá,
và `modalFocus.js` cho focus-trap của modal. Yêu cầu chức năng:

- Bảng lớp: cột Môn · Mã lớp · Học kỳ · Giảng viên · Sĩ số · Hành động.
- Lớp chưa có giảng viên hiển thị `t('admin.sectionsUnassigned')` với style cảnh báo
  (dùng token màu warning đã có trong `index.css`, không thêm mã màu mới).
- Nút "Thêm lớp" mở modal: chọn môn, nhập mã lớp, học kỳ, chọn giảng viên (cho phép để trống).
- Nút "Gán giảng viên" trên mỗi dòng → `updateAdminSection(id, { instructorId })`.
- Nút "Danh sách sinh viên" mở panel roster: bảng + ô thêm sinh viên + nút bỏ khỏi lớp.
- Nút xoá lớp dùng `ConfirmDialog` màu `danger`, thông báo rõ 409 khi lớp còn sinh viên.
- Mọi chuỗi qua `t()`. Không hardcode tiếng Việt.

Thêm nút "Đặt lại mật khẩu" vào `AdminUsers.jsx`, dùng `ConfirmDialog` với
`t('admin.resetPasswordConfirm')`, gọi `resetAdminUserPassword(userId)`.

- [x] **Step 8: Kiểm tra trên trình duyệt**

Khởi động preview, đăng nhập bằng tài khoản Admin demo, mở `/admin/governance/sections`. Kiểm:
- tạo 1 lớp không gán GV → nó xuất hiện trong Work Queue ở `/admin/overview` với nhãn "Lớp chưa có giảng viên phụ trách"
- bấm item đó → điều hướng về đúng màn Lớp học
- gán GV → item biến khỏi Work Queue sau khi tải lại
- bật EN → toàn bộ nhãn đổi ngôn ngữ, không còn chuỗi tiếng Việt sót
- 1440×900 và 375px đều không tràn ngang

- [x] **Step 9: Commit**

```bash
git add frontend/src/components/admin/AdminSections.jsx frontend/src/components/admin/adminRoutes.js frontend/src/components/admin/adminNavigationConfig.js frontend/src/components/admin/AdminConsole.jsx frontend/src/components/admin/adminWorkQueueLinks.js frontend/src/components/admin/AdminUsers.jsx frontend/src/lib/api.js frontend/src/locales/vi.js frontend/src/locales/en.js src/api/admin.py tests/test_api/test_admin_password_reset.py
git commit -m "feat(admin): section management screen and member password reset"
```

---

> **Đã xong 26/08 — commit `bfd2ff0`.** Step 8 (kiểm tra trình duyệt) phát hiện
> 1 lỗi thật ở đường xoá lớp và bản sửa đã nằm trong cùng commit:
> `remove_from_roster` xoá mềm (status=DROPPED) nên hàng `enrollments` vẫn còn,
> còn `delete_section` chỉ đếm ENROLLED — `CourseSection.enrollments` không khai
> báo delete cascade nên ORM cố set NULL cho `enrollments.section_id` (NOT NULL)
> → 500, và vì 500 lọt ra ngoài CORS middleware nên SPA chỉ thấy lỗi mạng trống.
> Đã thêm `cascade="all, delete-orphan"` + 2 test cho đường xoá (lớp rỗng và lớp
> vừa bỏ sinh viên). Ngoài ra `GET /admin/sections/courses` được thêm ở commit
> `058bc20` vì `POST /admin/sections` cần `Course.id` thật.

---

# PHASE 3 — Admin đọc rộng hơn

## Task 10: Instructor 360 — bổ sung 4 mảng hoạt động của giảng viên

Hiện `src/api/admin_instructor360.py` chỉ có 1 route và chạm 5 bảng. Bổ sung: nhật ký buổi học, quiz đã tạo, duyệt luyện tập, và quyết định guardrail.

**Files:**
- Modify: `src/api/admin_instructor360.py`
- Modify: `frontend/src/components/admin/AdminInstructor360.jsx`
- Modify: `frontend/src/lib/api.js`, `frontend/src/locales/vi.js`, `en.js`
- Test: `tests/test_api/test_admin_instructor360_activity.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/admin/instructors/{id}/class-activities` → `{"items": [{id, courseCode, kind, occurredAt, note}]}`
  - `GET /api/v1/admin/instructors/{id}/quizzes` → `{"items": [{id, title, courseCode, status, questionCount}]}`
  - `GET /api/v1/admin/instructors/{id}/practice-reviews` → `{"items": [{id, courseCode, status, reviewedAt}]}`
  - `GET /api/v1/admin/instructors/{id}/guardrail-decisions` → `{"items": [{eventId, decision, decidedAt, studentName}]}`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_admin_instructor360_activity.py`:

```python
import uuid
from datetime import UTC, datetime

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


@pytest.mark.asyncio
async def test_admin_sees_the_instructors_class_activity_log(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"i360-{suffix}", name="I360 Org")
    admin_email = f"admin.i360.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    instructor_id = ensure_user(
        email=f"inst.i360.{suffix}@test.local", org_id=org_id, role=models.UserRole.INSTRUCTOR
    )
    course_id = ensure_course(code=f"ZZI3{suffix[:3].upper()}", org_id=org_id)

    db = SessionLocal()
    try:
        section_id = f"sec_i360_{suffix}"
        db.add(
            models.CourseSection(
                id=section_id,
                course_id=course_id,
                instructor_id=instructor_id,
                term="Fall2026",
                section_code="SE-I360",
            )
        )
        db.flush()
        db.add(
            models.ClassActivity(
                id=f"act_{suffix}",
                section_id=section_id,
                instructor_id=instructor_id,
                kind="TAUGHT",
                occurred_at=datetime.now(UTC).replace(tzinfo=None),
                note="Buổi 1",
            )
        )
        db.commit()
    finally:
        db.close()

    token = await login(client, admin_email)
    response = await client.get(
        f"/api/v1/admin/instructors/{instructor_id}/class-activities",
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["kind"] == "TAUGHT"
    assert items[0]["note"] == "Buổi 1"


@pytest.mark.asyncio
async def test_instructor_activity_is_org_scoped(client):
    suffix = uuid.uuid4().hex[:6]
    admin_email = f"admin.x.{suffix}@test.local"
    ensure_user(
        email=admin_email,
        org_id=ensure_org(slug=f"i360a-{suffix}", name="A"),
        role=models.UserRole.ADMIN,
    )
    outsider = ensure_user(
        email=f"inst.y.{suffix}@test.local",
        org_id=ensure_org(slug=f"i360b-{suffix}", name="B"),
        role=models.UserRole.INSTRUCTOR,
    )

    token = await login(client, admin_email)
    response = await client.get(
        f"/api/v1/admin/instructors/{outsider}/class-activities",
        headers=auth_headers(token),
    )

    assert response.status_code == 404
```

> **Trước khi chạy:** mở `src/db/models.py:941` xem `ClassActivity` có đúng các cột
> `section_id`/`instructor_id`/`kind`/`occurred_at`/`note` không. Nếu tên khác, sửa
> fixture theo model thật — model là nguồn sự thật, không phải test này.

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_instructor360_activity.py -v
```

Kỳ vọng: FAIL — 404 vì route chưa tồn tại.

- [ ] **Step 3: Cài đặt tối thiểu**

Thêm 4 route vào `src/api/admin_instructor360.py`, dùng lại `_require_instructor` đã có
(hàm này đã lo phần org-scoping + 404). Mẫu cho route đầu, 3 route còn lại theo đúng khuôn:

```python
@router.get("/{instructor_id}/class-activities")
async def get_instructor_class_activities(
    instructor_id: str,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_instructor(db, current_user, instructor_id)
    rows = (
        db.query(models.ClassActivity, models.Course)
        .join(models.CourseSection, models.CourseSection.id == models.ClassActivity.section_id)
        .join(models.Course, models.Course.id == models.CourseSection.course_id)
        .filter(models.ClassActivity.instructor_id == instructor_id)
        .order_by(models.ClassActivity.occurred_at.desc())
        .limit(100)
        .all()
    )
    return {
        "items": [
            {
                "id": activity.id,
                "courseCode": course.code,
                "kind": activity.kind,
                "occurredAt": activity.occurred_at.isoformat() if activity.occurred_at else None,
                "note": activity.note,
            }
            for activity, course in rows
        ]
    }
```

`quizzes`: join `Quiz` → `CourseSection` → `Course`, lọc theo section của giảng viên,
trả `{id, title, courseCode, status, questionCount}` (đếm `QuizQuestion`).

`practice-reviews`: lọc `PracticeSet` có `reviewed_by == instructor_id`,
trả `{id, courseCode, status, reviewedAt}`.

`guardrail-decisions`: lọc `GuardrailEvent.reviewed_by == instructor_id`, join sang
`Message` → `Conversation` → `User` để lấy tên sinh viên, trả
`{eventId, decision, decidedAt, studentName}` với `decision = event.review_status`.

> Mở `src/db/models.py` xác nhận tên cột thật của `Quiz`, `PracticeSet` trước khi viết
> query — 2 model này chưa từng được đọc ở tầng admin nên chưa có tiền lệ để sao chép.

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_instructor360_activity.py tests/test_api/test_admin_people.py -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Thêm 4 tab vào `AdminInstructor360.jsx`**

Dùng `.tabs-underline` + `.data-table` như các màn admin khác, `AdminAsyncRegion` cho
loading/error. Thêm khoá dịch cho 4 tiêu đề tab và tên cột vào cả `vi.js` và `en.js`.

- [ ] **Step 6: Commit**

```bash
git add src/api/admin_instructor360.py frontend/src/components/admin/AdminInstructor360.jsx frontend/src/lib/api.js frontend/src/locales/vi.js frontend/src/locales/en.js tests/test_api/test_admin_instructor360_activity.py
git commit -m "feat(admin): surface instructor class activity, quizzes, practice reviews and guardrail decisions"
```

---

## Task 11: Student 360 — bổ sung bộ nhớ AI, quiz, luyện tập

`StudentMemoryEntry` là dữ liệu cá nhân AI ghi nhớ về sinh viên; hiện Admin không thấy được, kể cả khi xử lý yêu cầu trích xuất dữ liệu. Đây là mảng nên làm trước trong task này.

**Files:**
- Modify: `src/api/admin_student360.py`
- Modify: `frontend/src/components/admin/AdminStudent360.jsx`, `frontend/src/lib/api.js`, locales
- Test: `tests/test_api/test_admin_student360_memory.py`

**Interfaces:**
- Produces:
  - `GET /api/v1/admin/students/{id}/memory` → `{"success": true, "data": {...}}` qua `_audited_read`
  - `GET /api/v1/admin/students/{id}/quizzes`
  - `GET /api/v1/admin/students/{id}/practice-sets`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_admin_student360_memory.py`:

```python
import uuid

import pytest

from src.db import models
from src.db.connection import SessionLocal
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_org,
    ensure_user,
    login,
)


@pytest.mark.asyncio
async def test_admin_can_read_a_students_ai_memory_and_the_read_is_audited(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"mem-{suffix}", name="Memory Org")
    admin_email = f"admin.mem.{suffix}@test.local"
    admin_id = ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    student_id = ensure_user(
        email=f"stu.mem.{suffix}@test.local", org_id=org_id, role=models.UserRole.STUDENT
    )

    db = SessionLocal()
    try:
        db.add(
            models.StudentMemoryEntry(
                id=f"mem_{suffix}",
                student_id=student_id,
                content="Thích học buổi sáng",
            )
        )
        db.commit()
    finally:
        db.close()

    token = await login(client, admin_email)
    response = await client.get(
        f"/api/v1/admin/students/{student_id}/memory", headers=auth_headers(token)
    )

    assert response.status_code == 200, response.text
    assert response.json()["success"] is True

    check = SessionLocal()
    try:
        audited = (
            check.query(models.AuditLog)
            .filter(
                models.AuditLog.actor_user_id == admin_id,
                models.AuditLog.resource_type == "STUDENT_MEMORY",
            )
            .count()
        )
        assert audited >= 1, "đọc dữ liệu gốc của sinh viên phải ghi audit trước khi trả"
    finally:
        check.close()


@pytest.mark.asyncio
async def test_student_memory_is_org_scoped(client):
    suffix = uuid.uuid4().hex[:6]
    admin_email = f"admin.m1.{suffix}@test.local"
    ensure_user(
        email=admin_email,
        org_id=ensure_org(slug=f"m1-{suffix}", name="M1"),
        role=models.UserRole.ADMIN,
    )
    outsider = ensure_user(
        email=f"stu.m2.{suffix}@test.local",
        org_id=ensure_org(slug=f"m2-{suffix}", name="M2"),
        role=models.UserRole.STUDENT,
    )

    token = await login(client, admin_email)
    response = await client.get(
        f"/api/v1/admin/students/{outsider}/memory", headers=auth_headers(token)
    )

    assert response.status_code == 404
```

> Mở `src/db/models.py:671` xác nhận tên cột thật của `StudentMemoryEntry` trước khi
> chạy — nếu không có cột `content`, đổi fixture theo model.

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_student360_memory.py -v
```

Kỳ vọng: FAIL — 404.

- [ ] **Step 3: Cài đặt tối thiểu**

Thêm vào `src/api/admin_student360.py`, theo đúng khuôn route `/documents` đã có
(`_require_student` → query → `_audited_read`):

```python
@router.get(
    "/{student_id}/memory",
    dependencies=[Depends(require_permission(Resource.CHAT, Permission.READ_SENSITIVE))],
)
async def get_student_memory(
    student_id: str,
    page: int = PageQuery,
    page_size: int = PageSizeQuery,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    _require_student(db, current_user, student_id)
    rows = _paginate(
        db.query(models.StudentMemoryEntry)
        .filter_by(student_id=student_id)
        .order_by(models.StudentMemoryEntry.created_at.desc()),
        page,
        page_size,
    ).all()
    items = [
        {
            "id": row.id,
            "content": row.content,
            "createdAt": row.created_at.isoformat() if row.created_at else None,
            "lastReinforcedAt": row.last_reinforced_at.isoformat()
            if row.last_reinforced_at
            else None,
        }
        for row in rows
    ]
    return {"success": True, "data": await _audited_read(
        db, actor_id=current_user.id, resource_type="STUDENT_MEMORY",
        resource_id=student_id, items=items,
    )}
```

Thêm `/quizzes` và `/practice-sets` theo cùng khuôn, `resource_type` lần lượt là
`"STUDENT_QUIZ"` và `"STUDENT_PRACTICE"`.

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_admin_student360_memory.py tests/test_api/test_admin_student360.py -v
```

Kỳ vọng: PASS toàn bộ.

- [ ] **Step 5: Thêm 3 tab vào `AdminStudent360.jsx` + khoá dịch, rồi commit**

```bash
git add src/api/admin_student360.py frontend/src/components/admin/AdminStudent360.jsx frontend/src/lib/api.js frontend/src/locales/vi.js frontend/src/locales/en.js tests/test_api/test_admin_student360_memory.py
git commit -m "feat(admin): expose AI memory, quizzes and practice sets in Student 360"
```

---

## Task 12: Đường vào DSAR — người dùng tự gửi yêu cầu dữ liệu

Tab "Yêu cầu dữ liệu" là màn hình xử lý hoàn chỉnh nhưng `DataRequest` chưa từng được tạo ở đâu.

**Files:**
- Create: `src/api/data_requests.py`
- Modify: `src/main.py` (đăng ký router)
- Modify: `frontend/src/components/shared/SettingsScreen.jsx` (nút gửi yêu cầu)
- Modify: `frontend/src/lib/api.js`, locales
- Test: `tests/test_api/test_data_request_intake.py`

**Interfaces:**
- Produces: `POST /api/v1/me/data-requests` body `{"kind": "EXPORT" | "DELETE", "note": str | None}` → 201 `{id, status}`
- Produces: `GET /api/v1/me/data-requests` → `{"items": [{id, kind, status, createdAt}]}`
- Consumes: `models.DataRequest` — mở `src/db/models.py:1030` để lấy đúng tên cột trước khi viết.

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_api/test_data_request_intake.py`:

```python
import uuid

import pytest

from src.db import models
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_org,
    ensure_user,
    login,
)


@pytest.mark.asyncio
async def test_a_student_request_shows_up_in_the_admin_queue(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"dsar-{suffix}", name="DSAR Org")
    admin_email = f"admin.dsar.{suffix}@test.local"
    student_email = f"stu.dsar.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    ensure_user(email=student_email, org_id=org_id, role=models.UserRole.STUDENT)

    student_token = await login(client, student_email)
    created = await client.post(
        "/api/v1/me/data-requests",
        headers=auth_headers(student_token),
        json={"kind": "EXPORT", "note": "Em cần bản sao dữ liệu học tập"},
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]

    admin_token = await login(client, admin_email)
    listed = await client.get(
        "/api/v1/admin/data-requests", headers=auth_headers(admin_token)
    )
    assert listed.status_code == 200
    payload = listed.json()
    rows = payload["items"] if isinstance(payload, dict) else payload
    assert any(row["id"] == request_id for row in rows)


@pytest.mark.asyncio
async def test_an_admin_from_another_org_does_not_see_the_request(client):
    suffix = uuid.uuid4().hex[:6]
    student_email = f"stu.iso.{suffix}@test.local"
    ensure_user(
        email=student_email,
        org_id=ensure_org(slug=f"iso-a-{suffix}", name="A"),
        role=models.UserRole.STUDENT,
    )
    other_admin = f"admin.iso.{suffix}@test.local"
    ensure_user(
        email=other_admin,
        org_id=ensure_org(slug=f"iso-b-{suffix}", name="B"),
        role=models.UserRole.ADMIN,
    )

    student_token = await login(client, student_email)
    created = await client.post(
        "/api/v1/me/data-requests",
        headers=auth_headers(student_token),
        json={"kind": "DELETE", "note": None},
    )
    request_id = created.json()["id"]

    admin_token = await login(client, other_admin)
    listed = await client.get(
        "/api/v1/admin/data-requests", headers=auth_headers(admin_token)
    )
    payload = listed.json()
    rows = payload["items"] if isinstance(payload, dict) else payload
    assert all(row["id"] != request_id for row in rows)
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_data_request_intake.py -v
```

Kỳ vọng: FAIL — 404 ở `POST /api/v1/me/data-requests`.

- [ ] **Step 3: Cài đặt tối thiểu**

Tạo `src/api/data_requests.py`:

```python
"""Đường vào cho yêu cầu dữ liệu cá nhân (DSAR).

Admin Console đã có màn hình xử lý đầy đủ (`src/api/admin_data_requests.py`)
nhưng `DataRequest` chưa từng được tạo ở đâu — hàng đợi có bên xử lý mà không
có bên nộp. Router này là bên nộp.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.api.auth import get_current_user_from_token
from src.db import models
from src.db.connection import get_db
from src.repositories.audit_repository import AuditRepository
from src.security.authorization import require_roles
from src.services.core.audit_service import AuditService

router = APIRouter(
    prefix="/me/data-requests",
    tags=["data-requests"],
    dependencies=[
        Depends(
            require_roles(
                models.UserRole.STUDENT,
                models.UserRole.INSTRUCTOR,
                models.UserRole.ADMIN,
            )
        )
    ],
)

_KINDS = {"EXPORT", "DELETE"}


class DataRequestCreate(BaseModel):
    kind: str = Field(min_length=1)
    note: str | None = None


@router.post("", status_code=201)
async def submit_data_request(
    payload: DataRequestCreate,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    kind = (payload.kind or "").strip().upper()
    if kind not in _KINDS:
        raise HTTPException(status_code=400, detail="kind must be EXPORT or DELETE")
    if not current_user.organization_id:
        # Fail-closed: một yêu cầu không thuộc tổ chức nào thì không admin nào
        # xử lý được — từ chối ngay thay vì tạo một dòng mồ côi.
        raise HTTPException(status_code=404, detail="organization_required")

    request_row = models.DataRequest(
        id=f"dsar_{uuid.uuid4().hex[:16]}",
        organization_id=current_user.organization_id,
        subject_user_id=current_user.id,
        request_type=kind,
        status="PENDING",
        notes=payload.note,
        created_at=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(request_row)
    db.commit()

    await AuditService(AuditRepository(db)).log_event(
        event_type="DATA_REQUEST_SUBMITTED",
        decision="ALLOW",
        actor_user_id=current_user.id,
        resource_type="DATA_REQUEST",
        resource_id=request_row.id,
        metadata={"kind": kind},
    )
    return {"id": request_row.id, "status": request_row.status}


@router.get("")
def list_my_data_requests(
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.DataRequest)
        .filter(models.DataRequest.subject_user_id == current_user.id)
        .order_by(desc(models.DataRequest.created_at))
        .limit(50)
        .all()
    )
    return {
        "items": [
            {
                "id": row.id,
                "kind": row.request_type,
                "status": row.status,
                "createdAt": row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }
```

> **Trước khi chạy:** mở `src/db/models.py:1030` đối chiếu tên cột thật của
> `DataRequest`. Ở trên giả định `request_type` / `subject_user_id` / `notes`;
> nếu model dùng tên khác thì sửa theo model, và sửa luôn cho khớp
> `src/api/admin_data_requests.py` đang đọc bằng tên nào.

Đăng ký trong `src/main.py` cạnh `admin_data_requests_router`:

```python
app.include_router(data_requests_router, prefix="/api/v1")
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_api/test_data_request_intake.py tests/test_api/test_admin_overview.py -v
```

Kỳ vọng: PASS toàn bộ, và ô `DATA_REQUEST` trong Work Queue nay có thể khác 0.

- [ ] **Step 5: Thêm nút "Yêu cầu dữ liệu của tôi" vào `SettingsScreen.jsx` + khoá dịch, rồi commit**

```bash
git add src/api/data_requests.py src/main.py frontend/src/components/shared/SettingsScreen.jsx frontend/src/lib/api.js frontend/src/locales/vi.js frontend/src/locales/en.js tests/test_api/test_data_request_intake.py
git commit -m "feat(dsar): let users file data requests that reach the admin queue"
```

---

# PHASE 4 — Đo chi phí/độ trễ AI

## Task 13: Bảng `ai_usage` + ghi số liệu mỗi lần gọi LLM

Ràng buộc BTC #6 và PLO 5 ("giám sát cơ bản: độ trễ/lỗi/chi phí"). Hiện "lỗi" đã ổn, "độ trễ" chỉ có ở tầng HTTP, "chi phí" bằng 0.

**Không tái dùng `RAGTrace`/`LLMUsageEvent`** — ADR-017 đã đóng 2 bảng đó có lý do: FK `message_id` NOT NULL không khớp với `plan_builder`/`reflection_engine`, và `LLMUsageEvent` không có cột thời gian nên không chia được theo kỳ.

**Files:**
- Create: `migrations/versions/20260908_ai_usage.py`
- Modify: `src/db/models.py` (thêm model ở cuối)
- Modify: `src/services/core/llm.py`
- Create: `src/services/core/ai_usage_recorder.py`
- Modify: `src/api/admin_overview.py` (thêm route)
- Test: `tests/test_services/test_ai_usage_recorder.py`

**Interfaces:**
- Produces: `models.AIUsage` — cột `id`, `created_at`, `organization_id`, `user_id`, `feature`, `model`, `input_tokens`, `output_tokens`, `latency_ms`, `success`
- Produces: `record_usage(db, *, organization_id, user_id, feature, model, input_tokens, output_tokens, latency_ms, success) -> None`
- Produces: `GET /api/v1/admin/ai-usage?days=30` → `{"totals": {...}, "byFeature": [...], "byDay": [...]}`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_services/test_ai_usage_recorder.py`:

```python
import uuid

from src.db import models
from src.db.connection import SessionLocal
from src.services.core.ai_usage_recorder import record_usage


def test_record_usage_stores_a_timestamped_org_scoped_row():
    db = SessionLocal()
    try:
        org_suffix = uuid.uuid4().hex[:8]
        record_usage(
            db,
            organization_id=f"org_{org_suffix}",
            user_id=f"user_{org_suffix}",
            feature="qa_answer",
            model="gemini-3.6-flash",
            input_tokens=120,
            output_tokens=45,
            latency_ms=830,
            success=True,
        )
        db.commit()

        row = (
            db.query(models.AIUsage)
            .filter_by(organization_id=f"org_{org_suffix}")
            .one()
        )
        assert row.input_tokens == 120
        assert row.output_tokens == 45
        assert row.latency_ms == 830
        assert row.success is True
        # Cột thời gian là điểm khiến LLMUsageEvent cũ không dùng được —
        # không có nó thì không chia được chi phí theo kỳ.
        assert row.created_at is not None
    finally:
        db.rollback()
        db.close()


def test_a_failed_call_is_still_recorded():
    db = SessionLocal()
    try:
        org_suffix = uuid.uuid4().hex[:8]
        record_usage(
            db,
            organization_id=f"org_{org_suffix}",
            user_id=None,
            feature="plan_builder",
            model="gemini-3.6-flash",
            input_tokens=0,
            output_tokens=0,
            latency_ms=210,
            success=False,
        )
        db.commit()

        row = db.query(models.AIUsage).filter_by(organization_id=f"org_{org_suffix}").one()
        assert row.success is False
        assert row.latency_ms == 210
    finally:
        db.rollback()
        db.close()
```

- [ ] **Step 2: Chạy test, xác nhận đỏ**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_services/test_ai_usage_recorder.py -v
```

Kỳ vọng: FAIL — `ModuleNotFoundError: src.services.core.ai_usage_recorder`.

- [ ] **Step 3: Cài đặt tối thiểu**

Thêm vào cuối `src/db/models.py`:

```python
class AIUsage(Base):
    """Một lần gọi LLM — token, độ trễ, thành công hay không.

    Thay cho `LLMUsageEvent` (bị ADR-017 đóng): ở đây `message_id` không tồn
    tại nên plan/reflection/practice/ingest đều ghi được, và có `created_at`
    + `organization_id` nên chia được theo kỳ và theo tổ chức.
    """

    __tablename__ = "ai_usage"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    organization_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    feature: Mapped[str] = mapped_column(String, index=True)
    model: Mapped[str] = mapped_column(String)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
```

Tạo `migrations/versions/20260908_ai_usage.py`:

```python
"""Bảng ai_usage — token/độ trễ mỗi lần gọi LLM."""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260908_ai_usage"
down_revision: str | Sequence[str] | None = "20260907_invite_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ai_usage" in inspector.get_table_names():
        return
    op.create_table(
        "ai_usage",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("organization_id", sa.String(), nullable=True, index=True),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("feature", sa.String(), nullable=False, index=True),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_table("ai_usage")
```

Tạo `src/services/core/ai_usage_recorder.py`:

```python
"""Ghi lại token/độ trễ của mỗi lần gọi LLM.

Không bao giờ được làm hỏng luồng chính: nếu ghi số liệu lỗi thì nuốt lỗi
và đi tiếp — mất một dòng thống kê tốt hơn là hỏng một câu trả lời cho
sinh viên.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.db import models

logger = logging.getLogger(__name__)


def record_usage(
    db: Session,
    *,
    organization_id: str | None,
    user_id: str | None,
    feature: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    success: bool,
) -> None:
    try:
        db.add(
            models.AIUsage(
                id=f"aiu_{uuid.uuid4().hex[:16]}",
                created_at=datetime.now(UTC).replace(tzinfo=None),
                organization_id=organization_id,
                user_id=user_id,
                feature=feature,
                model=model,
                input_tokens=int(input_tokens or 0),
                output_tokens=int(output_tokens or 0),
                latency_ms=int(latency_ms or 0),
                success=success,
            )
        )
        db.flush()
    except Exception:  # noqa: BLE001 — xem docstring
        logger.warning("ai_usage_record_failed feature=%s", feature, exc_info=True)
```

- [ ] **Step 4: Chạy test, xác nhận xanh**

```bash
./.venv/Scripts/python.exe -m pytest tests/test_services/test_ai_usage_recorder.py tests/test_migrations -v
```

Kỳ vọng: PASS, kể cả `test_empty_database_upgrades_to_head`.

- [ ] **Step 5: Nối vào chỗ gọi LLM**

Trong `src/services/core/llm.py`, thêm helper bọc lời gọi:

```python
import time
from typing import Any


def invoke_with_usage(llm, prompt, *, db, feature: str, organization_id=None, user_id=None) -> Any:
    """Gọi LLM và ghi lại token + độ trễ. Trả đúng thứ `llm.invoke` trả về."""
    from src.services.core.ai_usage_recorder import record_usage

    settings = get_settings()
    started = time.perf_counter()
    success = True
    response = None
    try:
        response = llm.invoke(prompt)
        return response
    except Exception:
        success = False
        raise
    finally:
        usage = getattr(response, "usage_metadata", None) or {}
        record_usage(
            db,
            organization_id=organization_id,
            user_id=user_id,
            feature=feature,
            model=settings.model_name,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=int((time.perf_counter() - started) * 1000),
            success=success,
        )
```

Đổi các chỗ đang gọi `get_llm().invoke(...)` sang `invoke_with_usage(...)` với `feature`
đặt tên theo nơi gọi: `"qa_answer"`, `"plan_builder"`, `"reflection_summary"`,
`"practice_generate"`, `"empathic_reply"`. Tìm chúng bằng:

```bash
grep -rn "get_llm()" src/
```

- [ ] **Step 6: Thêm route đọc cho Admin**

Trong `src/api/admin_overview.py`:

```python
@router.get("/ai-usage")
def get_ai_usage(
    days: int = 30,
    current_user: models.User = Depends(get_current_user_from_token),
    db: Session = Depends(get_db),
):
    from src.services.core.ai_usage_service import build_usage_summary

    return build_usage_summary(
        db, organization_id=current_user.organization_id, days=max(1, min(days, 365))
    )
```

Tạo `src/services/core/ai_usage_service.py` với `build_usage_summary` trả về:

```python
{
    "totals": {"calls": int, "inputTokens": int, "outputTokens": int,
               "successRate": float, "p50LatencyMs": int, "p95LatencyMs": int},
    "byFeature": [{"feature": str, "calls": int, "inputTokens": int, "outputTokens": int}],
    "byDay": [{"date": "YYYY-MM-DD", "calls": int, "inputTokens": int, "outputTokens": int}],
}
```

Lọc `AIUsage.organization_id == organization_id` và `created_at >= now - days`.

- [ ] **Step 7: Chạy toàn bộ test + commit**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -q --no-header
```

```bash
git add src/db/models.py migrations/versions/20260908_ai_usage.py src/services/core/ai_usage_recorder.py src/services/core/ai_usage_service.py src/services/core/llm.py src/api/admin_overview.py tests/test_services/test_ai_usage_recorder.py
git commit -m "feat(observability): record LLM tokens and latency, expose an admin summary"
```

---

# PHASE 5 — Dọn dẹp

## Task 14: i18n sidebar giảng viên + 2 lỗi nhỏ

> **Step 1-2 (sửa 4 test đỏ) đã xong — bỏ qua, bắt đầu từ Step 3.**
> Commit `99a2ade` xử lý theo hướng khác cách đề xuất ở đây và **đúng hơn**: thay vì
> chuyển 12 file sang schema `meta`, họ làm chặt bộ nhận diện trong
> `real_curriculum_service.py` — một file chỉ được coi là syllabus chính thức khi có
> `meta` *và* ít nhất một chunk `Session ...` không rỗng. Kiểm lại cả 12 file đều có
> đúng 7 chunk, 0 section Session, không `meta` → đó là bản tóm tắt sinh tự động lúc
> lập kế hoạch, không phải syllabus thật, nên loại ra là đúng. Số môn giữ nguyên 34.
> Đã có test ghim hành vi: `get_curriculum_detail("EXE101")` phải trả `None`.

**Files:**
- Modify: `frontend/src/App.jsx:250-300`
- Modify: `frontend/src/locales/vi.js`, `en.js`
- Modify: `src/services/core/admin_overview_service.py` (`failed_jobs` org-scoping)
- Modify: `src/api/admin.py` (route ghi `AdminAnnouncement`)
- Test: `tests/test_api/test_admin_announcements.py`

- [x] ~~**Step 1: Chuẩn hoá 12 file curriculum mới**~~ — đã xong ở commit `99a2ade`
- [x] ~~**Step 2: Chạy 4 test đó, xác nhận xanh**~~ — đã xanh (`514 passed · 0 failed`)

> **Một câu hỏi để lại cho người thực thi:** 12 file kia hiện vẫn **chưa được track**
> trong git và giờ bị hệ thống bỏ qua hoàn toàn. Nếu ai đó thật sự định thêm 12 môn
> này vào chương trình (SWT301, PEN, TMI_ELE... đều là mã môn thật), thì đây là hoãn
> lại chứ không phải giải quyết — cần bóc syllabus thật cho chúng. Hỏi lại người tạo
> ra 12 file đó trước khi kết luận là xong hẳn.

- [x] **Step 3: i18n 6 nhãn sidebar giảng viên**

`frontend/src/App.jsx:250-300` — 6 nhãn đang là chuỗi tiếng Việt cứng. Thay bằng `t()`:

| Hiện tại | Khoá mới |
|---|---|
| `Rủi ro & Cảnh báo` | `nav.instructorRisks` |
| `Hoạt động lớp` | `nav.instructorActivities` |
| `Quản lý Quiz` | `nav.instructorQuizzes` |
| `Bài tập nộp` | `nav.instructorSubmissions` |
| `Digest` | `nav.instructorDigest` |
| `Xét duyệt Guardrail` | `nav.instructorGuardrail` |

`vi.js`: giữ nguyên 6 chuỗi trên. `en.js`: `Risks & Alerts` · `Class activity` ·
`Quiz management` · `Submissions` · `Digest` · `Guardrail review`.

- [x] **Step 4: Hai lỗi nhỏ còn lại**

**(a)** `src/services/core/admin_overview_service.py` — `failed_jobs` không lọc theo tổ chức,
nên `system_status` của tổ chức này đỏ vì job hỏng của tổ chức khác. Thêm join sang
`Course` và lọc `Course.organization_id == organization_id`.

**(b)** `src/api/admin.py` — thêm `POST /admin/announcements` ghi `AdminAnnouncement`.
Bảng này **đã được `src/api/instructor.py:54` đọc và hiển thị**, nhưng chưa route nào
ghi vào, nên panel thông báo bên giảng viên vĩnh viễn rỗng.

Test đi kèm — tạo `tests/test_api/test_admin_announcements.py`:

```python
import uuid

import pytest

from src.db import models
from tests.support.semester_practice_fixtures import (
    auth_headers,
    ensure_org,
    ensure_user,
    login,
)


@pytest.mark.asyncio
async def test_an_admin_announcement_reaches_the_instructor_panel(client):
    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"ann-{suffix}", name="Announcement Org")
    admin_email = f"admin.ann.{suffix}@test.local"
    inst_email = f"inst.ann.{suffix}@test.local"
    ensure_user(email=admin_email, org_id=org_id, role=models.UserRole.ADMIN)
    ensure_user(email=inst_email, org_id=org_id, role=models.UserRole.INSTRUCTOR)

    admin_token = await login(client, admin_email)
    created = await client.post(
        "/api/v1/admin/announcements",
        headers=auth_headers(admin_token),
        json={"title": "Lịch nghỉ lễ", "body": "Nghỉ từ 02/09."},
    )
    assert created.status_code == 201, created.text

    inst_token = await login(client, inst_email)
    listed = await client.get(
        "/api/v1/instructor/announcements", headers=auth_headers(inst_token)
    )
    assert listed.status_code == 200
    payload = listed.json()
    rows = payload["items"] if isinstance(payload, dict) else payload
    assert any(row.get("title") == "Lịch nghỉ lễ" for row in rows)
```

- [x] **Step 5: Chạy toàn bộ test**

```bash
./.venv/Scripts/python.exe -m pytest tests/ -q --no-header
```

Kỳ vọng: **0 failed**, và tổng số test không giảm so với baseline `514 passed · 7 skipped`.
Nếu số test tụt xuống, kiểm ngay xem có test nào bị xoá/deselect thay vì được sửa.

- [x] **Step 6: Commit**

```bash
git add frontend/src/App.jsx frontend/src/locales/vi.js frontend/src/locales/en.js src/services/core/admin_overview_service.py src/api/admin.py tests/test_api/test_admin_announcements.py
git commit -m "fix: translate instructor nav, scope failed jobs by org, wire admin announcements"
```

---

## Việc nằm ngoài plan này, có chủ đích

- **RLS đa tổ chức (P0#3).** `src/db/tenant_scope.py` đã viết xong nhưng chưa nối vào
  route nào; policy trong migration đang inert vì `app.current_org_id` không nơi nào set.
  Cần thao tác trên Supabase Dashboard + đổi `Depends(get_db)` → `Depends(get_scoped_db)`
  trên 40+ endpoint, có kế hoạch riêng ở `docs/decisions/rls-migration-plan.md`.
- **Phản hồi can thiệp về phía sinh viên.** Giảng viên bấm "Đã can thiệp" thì sinh viên
  vẫn không nhận được gì. Đây là quyết định sản phẩm (có nên báo cho sinh viên biết
  mình đang bị theo dõi rủi ro không), không phải việc kỹ thuật — cần chốt trước khi code.
- **`InstructorStudentNote` cho Admin.** Ghi chú riêng tư của giảng viên về sinh viên.
  Mở ra là quyết định về quyền riêng tư, không nên gộp vào Task 10.
- **5 bảng chết còn lại** (`ResourceAccessEvent`, `ReplanProposal`, `LearningGoal`,
  `ReminderDelivery`, `Rubric`): không đọc/ghi ở đâu. Xoá hay dùng đều cần quyết định riêng.
- **Commit 2.100 dòng đang nằm trong working tree.** Làm **trước** Task 1, không phải
  một task trong plan này — cần review chính chỗ đó rồi mới chồng thay đổi mới lên.

> **Đã xong 26/08 — commit `138f1de`.** Ngoài phạm vi brief: `AdminAnnouncement`
> **không có** `organization_id` và reader phía giảng viên **không lọc tổ chức** —
> vô hại khi bảng luôn rỗng, nhưng thêm route ghi vào là thành rò rỉ chéo tổ chức.
> Đã thêm cột + migration `20260910_announcement_org` và lọc cả 2 đầu.
> Brief cũng ghi sai giao kèo test: nó POST `body` và đọc `payload["items"]`,
> trong khi cột là `content` và reader trả `{"announcements": [...]}`.
> `failed_jobs` phải join `func.upper` hai vế vì `start_job` lưu `course_code.upper()`
> còn catalog thật có mã đuôi chữ thường.
