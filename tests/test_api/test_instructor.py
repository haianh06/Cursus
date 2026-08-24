from datetime import UTC, datetime, timedelta

import pytest

from src.db import models
from src.db.connection import SessionLocal


def _seed_blocked_guardrail_event() -> str:
    """Guardrail_service khong persist gi ca (xem ghi chu trong instructor.py)
    nen phai tu dung Conversation/Message/GuardrailEvent de test duoc endpoint
    doc/duyet. Idempotent: goi lai nhieu lan van an toan."""
    db = SessionLocal()
    try:
        existing = db.query(models.GuardrailEvent).filter_by(id="grail_test_ethan").first()
        if existing:
            return existing.id

        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            models.Conversation(
                id="conv_test_ethan",
                student_id="student_ethan",
                section_id="sec_ssa101_demo",
                title="Test conversation",
                created_at=now,
            )
        )
        db.add(
            models.Message(
                id="msg_test_ethan_blocked",
                conversation_id="conv_test_ethan",
                sender="USER",
                content="Giải hộ em bài tập Programming Assignment 2",
                created_at=now,
                metadata_info={},
            )
        )
        db.add(
            models.GuardrailEvent(
                id="grail_test_ethan",
                message_id="msg_test_ethan_blocked",
                classification="BLOCKED",
                safety_evaluation={
                    "reason": "academic_integrity",
                    "answer": "Mình không làm bài hộ được, nhưng có thể gợi ý hướng tiếp cận.",
                },
                created_at=now,
            )
        )
        db.commit()
        return "grail_test_ethan"
    finally:
        db.close()


def _seed_high_completion_weeks(student_id: str, week_numbers: list[int]) -> None:
    """Tao WeeklyPlan voi 100% task COMPLETED cho tung tuan trong danh sach —
    dung de kich hoat F8 Kudos trong test. Idempotent theo id `kudos_{student}_w{n}`."""
    db = SessionLocal()
    try:
        now = datetime.now(UTC).replace(tzinfo=None)
        for week in week_numbers:
            plan_id = f"kudos_{student_id}_w{week}"
            if db.query(models.WeeklyPlan).filter_by(id=plan_id).first():
                continue
            db.add(
                models.WeeklyPlan(
                    id=plan_id,
                    student_id=student_id,
                    week_number=week,
                    goals={"statement": "Kudos test plan"},
                    study_hours_allocated=5.0,
                )
            )
            daily_id = f"dp_{plan_id}"
            db.add(models.DailyPlan(id=daily_id, weekly_plan_id=plan_id, date=now, status="DONE"))

            block_id = f"sb_{plan_id}"
            db.add(
                models.ScheduleBlock(
                    id=block_id,
                    daily_plan_id=daily_id,
                    start_time=now,
                    end_time=now,
                    activity_description="Kudos test block",
                )
            )
            db.add(
                models.StudyTask(
                    id=f"task_{plan_id}",
                    schedule_block_id=block_id,
                    assignment_id=None,
                    title="Kudos test task",
                    planned_minutes=30,
                    actual_minutes=30,
                    priority="MEDIUM",
                    status="COMPLETED",
                    difficulty="MEDIUM",
                )
            )
        db.commit()
    finally:
        db.close()


def _seed_second_enrollment_for_ethan_under_inst_demo() -> None:
    """Ethan hoc them 1 lop khac cung do inst_demo day — tai hien bug that tim
    thay khi test tren du lieu seed 600 SV qua docker compose: mot SV hoc
    nhieu lop cua cung 1 GV bi liet ke trung trong Kudos vi endpoint duyet
    tung Enrollment thay vi tung SV duy nhat."""
    db = SessionLocal()
    try:
        if db.query(models.CourseSection).filter_by(id="sec_kudos_dedup_demo2").first():
            return
        # ZZKUDOS999 — ma mon chi dung rieng cho test nay, tranh dam vao
        # "PRF192" (da la ma that trong mock_data/ va nhieu test khac dung).
        db.add(
            models.Course(
                id="ZZKUDOS999",
                code="ZZKUDOS999",
                name="Kudos Dedup Regression Course",
                description="Test course for kudos dedup regression.",
            )
        )
        db.add(
            models.CourseSection(
                id="sec_kudos_dedup_demo2",
                course_id="ZZKUDOS999",
                instructor_id="inst_demo",
                term="Fall2026",
                section_code="SE1802",
            )
        )
        db.add(
            models.Enrollment(
                id="enr_ethan_kudos_dedup",
                student_id="student_ethan",
                section_id="sec_kudos_dedup_demo2",
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()


def _seed_weekly_rate(student_id: str, week_number: int, completed: int, total: int) -> None:
    """Tao 1 WeeklyPlan voi dung `completed`/`total` task COMPLETED cho 1 tuan
    cu the — dung de dung len (hoac tranh dung) A2 (canh bao xu huong giam).
    Idempotent theo id `rate_{student}_w{week}`."""
    db = SessionLocal()
    try:
        plan_id = f"rate_{student_id}_w{week_number}"
        if db.query(models.WeeklyPlan).filter_by(id=plan_id).first():
            return
        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            models.WeeklyPlan(
                id=plan_id,
                student_id=student_id,
                week_number=week_number,
                goals={"statement": "Trend test plan"},
                study_hours_allocated=5.0,
            )
        )
        daily_id = f"dp_{plan_id}"
        db.add(models.DailyPlan(id=daily_id, weekly_plan_id=plan_id, date=now, status="TODO"))
        block_id = f"sb_{plan_id}"
        db.add(
            models.ScheduleBlock(
                id=block_id,
                daily_plan_id=daily_id,
                start_time=now,
                end_time=now,
                activity_description="Trend test block",
            )
        )
        for i in range(total):
            db.add(
                models.StudyTask(
                    id=f"task_{plan_id}_{i}",
                    schedule_block_id=block_id,
                    assignment_id=None,
                    title=f"Trend test task {i}",
                    planned_minutes=30,
                    actual_minutes=30 if i < completed else None,
                    priority="MEDIUM",
                    status="COMPLETED" if i < completed else "TODO",
                    difficulty="MEDIUM",
                )
            )
        db.commit()
    finally:
        db.close()


def _seed_trend_student_under_inst_demo() -> str:
    """SV + lop rieng chi de test A2, tach khoi Ethan de khong dam vao du
    lieu cac test Kudos/F5 khac dang dung chung Ethan."""
    db = SessionLocal()
    try:
        student_id = "student_trend_demo"
        if db.query(models.User).filter_by(id=student_id).first():
            return student_id
        now = datetime.now(UTC).replace(tzinfo=None)
        db.add(
            models.User(
                id=student_id,
                email="student.trend@example.test",
                password_hash="x",
                full_name="Trend Demo Student",
                role=models.UserRole.STUDENT.value,
                is_email_verified=True,
                is_active=True,
                created_at=now,
            )
        )
        db.add(
            models.Course(
                id="ZZTREND999",
                code="ZZTREND999",
                name="Trend Regression Course",
                description="Test course for A2 declining-trend detection.",
            )
        )
        db.add(
            models.CourseSection(
                id="sec_trend_demo",
                course_id="ZZTREND999",
                instructor_id="inst_demo",
                term="Fall2026",
                section_code="SE1803",
            )
        )
        db.add(
            models.Enrollment(
                id="enr_trend_demo",
                student_id=student_id,
                section_id="sec_trend_demo",
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=now,
            )
        )
        db.commit()
        return student_id
    finally:
        db.close()


def _seed_ethan_second_instructor_enrollment() -> None:
    """Ethan hoc them 1 lop do inst_other day — de test ghi chu rieng (A3)
    that su rieng tu GIUA HAI GV cung day 1 SV, khong chi la chua test duoc."""
    db = SessionLocal()
    try:
        if db.query(models.CourseSection).filter_by(id="sec_note_privacy_demo").first():
            return
        db.add(
            models.Course(
                id="ZZNOTES999",
                code="ZZNOTES999",
                name="Note Privacy Regression Course",
                description="Test course for A3 note-privacy regression.",
            )
        )
        db.add(
            models.CourseSection(
                id="sec_note_privacy_demo",
                course_id="ZZNOTES999",
                instructor_id="inst_other",
                term="Fall2026",
                section_code="SE1804",
            )
        )
        db.add(
            models.Enrollment(
                id="enr_ethan_note_privacy",
                student_id="student_ethan",
                section_id="sec_note_privacy_demo",
                status=models.EnrollmentStatus.ENROLLED.value,
                enrolled_at=datetime.now(UTC).replace(tzinfo=None),
            )
        )
        db.commit()
    finally:
        db.close()


def _seed_submission(assignment_id: str, student_id: str, *, is_late: bool) -> None:
    db = SessionLocal()
    try:
        sub_id = f"sub_{assignment_id}_{student_id}"
        if db.query(models.Submission).filter_by(id=sub_id).first():
            return
        db.add(
            models.Submission(
                id=sub_id,
                assignment_id=assignment_id,
                student_id=student_id,
                submitted_at=datetime.now(UTC).replace(tzinfo=None),
                content={"text": "demo submission"},
                grading_status="PENDING",
                is_late=is_late,
            )
        )
        db.commit()
    finally:
        db.close()


async def _login_instructor(client):
    payload = {
        "email": "instructor.demo@example.test",
        "password": "password123"
    }
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    token = resp.json()["token"]
    # /auth/login cung set 1 httponly cookie, va _extract_access_token uu
    # tien cookie hon header Authorization — neu khong xoa, dang nhap them
    # 1 nguoi khac tren CUNG client se lam moi request sau do (ke ca dung
    # Bearer token cua nguoi dau) bi tinh nham danh tinh theo cookie moi nhat.
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_instructor_lifecycle_endpoints(client):
    # 1. Login as instructor
    payload = {
        "email": "instructor.demo@example.test",
        "password": "password123"
    }
    resp = await client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get instructor dashboard
    resp = await client.get("/api/v1/instructor/dashboard", headers=headers)
    assert resp.status_code == 200
    dash = resp.json()
    assert "totalActiveWarnings" in dash
    assert "courses" in dash

    # 3. Get instructor risks
    resp = await client.get("/api/v1/instructor/risks", headers=headers)
    assert resp.status_code == 200
    risks = resp.json()
    assert len(risks) > 0
    risk_id = risks[0]["id"]

    # 4. Get specific risk details
    resp = await client.get(f"/api/v1/instructor/risks/{risk_id}", headers=headers)
    assert resp.status_code == 200
    risk_detail = resp.json()
    assert risk_detail["id"] == risk_id

    # 5. Submit intervention decision
    decision_payload = {
        "decision": "APPROVE",
        "editedIntervention": "Gửi email hỗ trợ SV và nhắc nhở làm bài nhóm."
    }
    resp = await client.post(
        f"/api/v1/instructor/risks/{risk_id}/intervention",
        json=decision_payload,
        headers=headers
    )
    assert resp.status_code == 200
    res = resp.json()
    assert res["decision"] == "APPROVE"
    assert res["status"] == "INTERVENTION_APPROVED"


@pytest.mark.asyncio
async def test_instructor_dashboard_has_real_class_metrics(client):
    """F4: classSize va classAvgCompletionByWeek phai la so/du lieu that tu
    DB (Enrollment + WeeklyPlan), khong con la truong bi thieu buoc frontend
    phai tu bu bang du lieu mau."""
    headers = await _login_instructor(client)

    resp = await client.get("/api/v1/instructor/dashboard", headers=headers)
    assert resp.status_code == 200
    dash = resp.json()

    assert "classSize" in dash
    assert isinstance(dash["classSize"], int)
    assert dash["classSize"] >= 1  # student_ethan dang ENROLLED o sec_ssa101_demo

    assert "classAvgCompletionByWeek" in dash
    assert isinstance(dash["classAvgCompletionByWeek"], list)
    for rate in dash["classAvgCompletionByWeek"]:
        assert 0.0 <= rate <= 1.0


@pytest.mark.asyncio
async def test_instructor_dashboard_course_filter(client):
    """F9: loc theo course_id phai thu hep so lieu, nhung danh sach `courses`
    (nguon cho dropdown) luon giu nguyen toan bo cac lop GV dang day."""
    headers = await _login_instructor(client)

    resp = await client.get(
        "/api/v1/instructor/dashboard?course_id=SSA101", headers=headers
    )
    assert resp.status_code == 200
    matched = resp.json()
    assert matched["classSize"] >= 1
    assert any(c["id"] == "SSA101" for c in matched["courses"])

    resp = await client.get(
        "/api/v1/instructor/dashboard?course_id=DOES_NOT_EXIST", headers=headers
    )
    assert resp.status_code == 200
    empty = resp.json()
    assert empty["classSize"] == 0
    assert empty["totalActiveWarnings"] == 0
    # Danh sach mon cho dropdown khong duoc bi loc theo - phai van thay SSA101.
    assert any(c["id"] == "SSA101" for c in empty["courses"])


@pytest.mark.asyncio
async def test_instructor_intervention_note_persists(client):
    """F5 Risk Case Detail: ghi chu can thiep GV tu nhap phai duoc luu va
    doc lai dung tu ca GET risks (danh sach) lan GET risks/{id} (chi tiet)."""
    headers = await _login_instructor(client)
    risk_id = "risk_ethan_demo"

    resp = await client.post(
        f"/api/v1/instructor/risks/{risk_id}/intervention",
        json={"decision": "APPROVE", "note": "Đã gọi điện trao đổi, hẹn gặp thứ Năm."},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/instructor/risks/{risk_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["instructorNote"] == "Đã gọi điện trao đổi, hẹn gặp thứ Năm."

    resp = await client.get("/api/v1/instructor/risks", headers=headers)
    assert resp.status_code == 200
    listed = next(r for r in resp.json() if r["id"] == risk_id)
    assert listed["instructorNote"] == "Đã gọi điện trao đổi, hẹn gặp thứ Năm."


@pytest.mark.asyncio
async def test_guardrail_review_queue_lifecycle(client):
    """Appeal queue: GV thay dung case bi chan trong lop minh, duyet bo chan,
    va doc lai dung trang thai — khong lien quan gi toi case cua lop khac."""
    event_id = _seed_blocked_guardrail_event()
    headers = await _login_instructor(client)

    resp = await client.get("/api/v1/instructor/guardrail-reviews", headers=headers)
    assert resp.status_code == 200
    reviews = resp.json()
    case = next(item for item in reviews if item["id"] == event_id)
    assert case["studentAlias"] == "Ethan Nguyen"
    assert case["blockReason"] == "academic_integrity"
    assert case["question"] == "Giải hộ em bài tập Programming Assignment 2"
    assert case["reviewStatus"] == "PENDING"

    resp = await client.post(
        f"/api/v1/instructor/guardrail-reviews/{event_id}",
        json={"decision": "UNBLOCK", "note": "Gợi ý hướng làm, không cho đáp án."},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["reviewStatus"] == "UNBLOCKED"

    resp = await client.get("/api/v1/instructor/guardrail-reviews", headers=headers)
    updated = next(item for item in resp.json() if item["id"] == event_id)
    assert updated["reviewStatus"] == "UNBLOCKED"


@pytest.mark.asyncio
async def test_guardrail_review_queue_scoped_to_own_class(client):
    """GV cua lop khac (inst_other) khong duoc thay case cua sec_ssa101_demo,
    va khong duyet duoc case do qua endpoint POST (404, khong phai 200)."""
    event_id = _seed_blocked_guardrail_event()

    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.other@example.test", "password": "password123"},
    )
    assert resp.status_code == 200
    other_headers = {"Authorization": f"Bearer {resp.json()['token']}"}

    resp = await client.get("/api/v1/instructor/guardrail-reviews", headers=other_headers)
    assert resp.status_code == 200
    assert all(item["id"] != event_id for item in resp.json())

    resp = await client.post(
        f"/api/v1/instructor/guardrail-reviews/{event_id}",
        json={"decision": "KEEP"},
        headers=other_headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_instructor_kudos_flags_sustained_high_completion(client):
    """F8: SV dat >=90% hoan thanh 2 tuan gan nhat lien tuc (co du lieu) thi
    xuat hien trong /instructor/kudos, sap xep tuan moi nhat truoc."""
    _seed_high_completion_weeks("student_ethan", [99, 100])
    _seed_second_enrollment_for_ethan_under_inst_demo()
    headers = await _login_instructor(client)

    resp = await client.get("/api/v1/instructor/kudos", headers=headers)
    assert resp.status_code == 200
    kudos = resp.json()["kudos"]
    matches = [item for item in kudos if item["studentId"] == "student_ethan"]
    # Regression: Ethan hoc 2 lop cua cung inst_demo (SSA101 + PRF192) nhung
    # phai chi xuat hien 1 dong Kudos duy nhat, khong phai 1 dong / lop.
    assert len(matches) == 1
    entry = matches[0]
    assert entry["weeks"] == [100, 99]
    assert entry["courseId"] == "SSA101"

    resp = await client.get(
        "/api/v1/instructor/kudos?course_id=DOES_NOT_EXIST", headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["kudos"] == []


@pytest.mark.asyncio
async def test_intervention_history_accumulates_every_decision(client):
    """F10: moi lan bam quyet dinh phai them 1 dong lich su moi, khong ghi
    de len dong truoc — RiskSignal chi giu duoc trang thai MOI NHAT nen day
    la nguon duy nhat de xem lai toan bo qua trinh can thiep."""
    headers = await _login_instructor(client)
    risk_id = "risk_ethan_demo"

    resp = await client.post(
        f"/api/v1/instructor/risks/{risk_id}/intervention",
        json={"decision": "APPROVE", "note": "Lần 1: đã gọi điện."},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.post(
        f"/api/v1/instructor/risks/{risk_id}/intervention",
        json={"decision": "REJECT"},
        headers=headers,
    )
    assert resp.status_code == 200

    resp = await client.get(
        f"/api/v1/instructor/risks/{risk_id}/interventions", headers=headers
    )
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) >= 2
    assert history[0]["decision"] == "REJECT"
    assert history[0]["note"] == "Đã bỏ qua cảnh báo."
    assert history[0]["instructorName"] == "Demo Instructor"
    assert any(item["note"] == "Lần 1: đã gọi điện." for item in history)


@pytest.mark.asyncio
async def test_dashboard_export_returns_csv_matching_dashboard_numbers(client):
    """F12: file CSV xuat ra phai khop dung so voi /instructor/dashboard —
    khong duoc tinh rieng mot lan nua roi lech nhau."""
    headers = await _login_instructor(client)

    resp = await client.get("/api/v1/instructor/dashboard", headers=headers)
    dashboard = resp.json()

    resp = await client.get("/api/v1/instructor/dashboard/export", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    csv_text = resp.text
    assert f"Sĩ số,{dashboard['classSize']}" in csv_text
    assert f"Số rủi ro mức cao,{dashboard['highRiskCount']}" in csv_text


@pytest.mark.asyncio
async def test_declining_completion_trend_creates_academic_decline_risk(client):
    """A2: ty le hoan thanh giam LIEN TUC 3 tuan gan nhat (90% -> 50% -> 10%)
    phai tu dong sinh 1 RiskSignal that (risk_type=ACADEMIC_DECLINE) va khong
    duoc tao them ban sao khi GV tai lai danh sach nhieu lan."""
    student_id = _seed_trend_student_under_inst_demo()
    _seed_weekly_rate(student_id, 30, completed=9, total=10)
    _seed_weekly_rate(student_id, 31, completed=5, total=10)
    _seed_weekly_rate(student_id, 32, completed=1, total=10)

    headers = await _login_instructor(client)

    resp = await client.get("/api/v1/instructor/risks", headers=headers)
    assert resp.status_code == 200
    matches = [
        r for r in resp.json()
        if r["studentId"] == student_id and r["riskType"] == "ACADEMIC_DECLINE"
    ]
    assert len(matches) == 1
    assert matches[0]["riskLevel"] in {"MEDIUM", "HIGH"}
    assert matches[0]["evidence"]["completionRates"] == [90.0, 50.0, 10.0]

    # Tai lai lan 2 khong duoc sinh them case moi cho cung SV.
    resp = await client.get("/api/v1/instructor/risks", headers=headers)
    matches_again = [
        r for r in resp.json()
        if r["studentId"] == student_id and r["riskType"] == "ACADEMIC_DECLINE"
    ]
    assert len(matches_again) == 1
    assert matches_again[0]["id"] == matches[0]["id"]


@pytest.mark.asyncio
async def test_stable_completion_does_not_create_academic_decline_risk(client):
    """A2: ty le on dinh/tang thi khong duoc bao xu huong giam — Kudos test da
    seed Ethan hoan thanh 100% o tuan 10-11, dung lai du lieu do de kiem tra
    khong co canh bao gia."""
    headers = await _login_instructor(client)
    resp = await client.get("/api/v1/instructor/risks", headers=headers)
    assert resp.status_code == 200
    matches = [
        r for r in resp.json()
        if r["studentId"] == "student_ethan" and r["riskType"] == "ACADEMIC_DECLINE"
    ]
    assert matches == []


@pytest.mark.asyncio
async def test_student_profile_scopes_history_to_owned_sections(client):
    """A1: ho so SV phai gom dung lop/case cua GV dang xem, va GV khong day SV
    do thi khong xem duoc ho so (404, giong quy tac cua /instructor/risks).
    (Truong hop 2 GV CUNG day 1 SV nhung chi thay lop cua rieng minh da co
    test_student_notes_are_private_per_instructor bao phu qua kiem tra ghi chu.)"""
    headers = await _login_instructor(client)

    resp = await client.get("/api/v1/instructor/students/student_ethan/profile", headers=headers)
    assert resp.status_code == 200
    profile = resp.json()
    assert profile["displayName"] == "Ethan Nguyen"
    assert any(c["code"] == "SSA101" for c in profile["courses"])
    assert any(r["id"] == "risk_ethan_demo" for r in profile["riskHistory"])

    # inst_other KHONG day Ethan (chua goi _seed_ethan_second_instructor_enrollment)
    # nen phai bi tu choi giong het quy tac cua /instructor/risks.
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.other@example.test", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    resp = await client.get(
        "/api/v1/instructor/students/student_ethan/profile", headers=other_headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_student_notes_are_private_per_instructor(client):
    """A3: ghi chu la CUA RIENG tung GV — 2 GV cung day 1 SV khong thay ghi
    chu cua nhau, du ca hai deu co quyen xem ho so SV do."""
    _seed_ethan_second_instructor_enrollment()
    headers = await _login_instructor(client)

    resp = await client.post(
        "/api/v1/instructor/students/student_ethan/notes",
        json={"content": "Đã gọi điện trao đổi, hẹn gặp thứ Năm."},
        headers=headers,
    )
    assert resp.status_code == 201
    note = resp.json()
    assert note["content"] == "Đã gọi điện trao đổi, hẹn gặp thứ Năm."

    resp = await client.get("/api/v1/instructor/students/student_ethan/notes", headers=headers)
    assert resp.status_code == 200
    assert any(n["id"] == note["id"] for n in resp.json()["notes"])

    # Xoa TRUOC khi dang nhap sang GV khac: /auth/login set httponly cookie
    # va _extract_access_token uu tien cookie hon header Authorization, nen
    # dang nhap lan 2 tren CUNG client se lam moi request sau do (ke ca khi
    # van truyen dung Bearer token cua GV dau) bi tinh nham thanh GV thu 2.
    resp = await client.delete(
        f"/api/v1/instructor/students/student_ethan/notes/{note['id']}", headers=headers
    )
    assert resp.status_code == 204
    resp = await client.get("/api/v1/instructor/students/student_ethan/notes", headers=headers)
    assert all(n["id"] != note["id"] for n in resp.json()["notes"])

    resp = await client.post(
        "/api/v1/instructor/students/student_ethan/notes",
        json={"content": "Ghi chú thứ hai — chỉ mình inst_demo được thấy."},
        headers=headers,
    )
    assert resp.status_code == 201
    note2 = resp.json()

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.other@example.test", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    # inst_other cung day Ethan (qua sec_note_privacy_demo) nen xem duoc ho so,
    # nhung KHONG duoc thay ghi chu rieng cua inst_demo.
    resp = await client.get("/api/v1/instructor/students/student_ethan/notes", headers=other_headers)
    assert resp.status_code == 200
    assert resp.json()["notes"] == []
    assert all(n["id"] != note2["id"] for n in resp.json()["notes"])


@pytest.mark.asyncio
async def test_assignment_submission_roster_flags_missing_and_late(client):
    """A4: danh sach nop bai phai hien ca SV CHUA nop (khong duoc am tham bo
    qua) va phan biet duoc nop tre."""
    headers = await _login_instructor(client)
    assignment_id = "asg_ssa101_demo"

    resp = await client.get(
        f"/api/v1/instructor/assignments/{assignment_id}/submissions", headers=headers
    )
    assert resp.status_code == 200
    roster = resp.json()["submissions"]
    ethan_row = next(row for row in roster if row["studentId"] == "student_ethan")
    assert ethan_row["submitted"] is False

    _seed_submission(assignment_id, "student_ethan", is_late=True)

    resp = await client.get(
        f"/api/v1/instructor/assignments/{assignment_id}/submissions", headers=headers
    )
    roster = resp.json()["submissions"]
    ethan_row = next(row for row in roster if row["studentId"] == "student_ethan")
    assert ethan_row["submitted"] is True
    assert ethan_row["isLate"] is True

    # GV khac khong duoc xem danh sach nop bai cua lop minh khong day.
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.other@example.test", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {login.json()['token']}"}
    resp = await client.get(
        f"/api/v1/instructor/assignments/{assignment_id}/submissions", headers=other_headers
    )
    assert resp.status_code == 404


def _seed_bulk_target_risk(risk_id: str, *, student_id: str = "student_ethan") -> str:
    """1 case rui ro rieng, doc lap voi risk_ethan_demo — dung de test B1 ma
    khong lam hong trang thai resolved_at cua case goc (nhieu test khac dua
    vao risk_ethan_demo con o trang thai PENDING)."""
    db = SessionLocal()
    try:
        if db.query(models.RiskSignal).filter_by(id=risk_id).first():
            return risk_id
        db.add(
            models.RiskSignal(
                id=risk_id,
                student_id=student_id,
                section_id="sec_ssa101_demo",
                assignment_id=None,
                risk_type="WEEKLY_GOAL_FAILURE",
                risk_level="MEDIUM",
                triggered_rules={"rule": "bulk_test"},
                evidence={"note": "bulk intervention test"},
                recommended_action="Reach out",
                generated_at=datetime.now(UTC),
                resolved_at=None,
                resolution_type=None,
                policy_version="v1",
            )
        )
        db.commit()
        return risk_id
    finally:
        db.close()


def _seed_overdue_risk(risk_id: str, *, days_old: int) -> str:
    db = SessionLocal()
    try:
        if db.query(models.RiskSignal).filter_by(id=risk_id).first():
            return risk_id
        db.add(
            models.RiskSignal(
                id=risk_id,
                student_id="student_ethan",
                section_id="sec_ssa101_demo",
                assignment_id=None,
                risk_type="ABANDONMENT",
                risk_level="HIGH",
                triggered_rules={"rule": "overdue_test"},
                evidence={"note": "overdue sla test"},
                recommended_action="Escalate",
                generated_at=datetime.now(UTC) - timedelta(days=days_old),
                resolved_at=None,
                resolution_type=None,
                policy_version="v1",
            )
        )
        db.commit()
        return risk_id
    finally:
        db.close()


def _seed_weekly_reflection(student_id: str, week_number: int, *, challenge: str) -> None:
    """Metrics that phai giu nguyen dinh dang cua src/api/student.py de test
    dung dung field ma _serialize_reflection_summary (C2) doc."""
    db = SessionLocal()
    try:
        ref_id = f"ref_{student_id}_w{week_number}"
        if db.query(models.WeeklyReflection).filter_by(id=ref_id).first():
            return
        db.add(
            models.WeeklyReflection(
                id=ref_id,
                student_id=student_id,
                week_number=week_number,
                content="AI-composed narrative — never exposed to instructors.",
                generated_at=datetime.now(UTC).replace(tzinfo=None),
                metrics={
                    "hoursPlanned": 10.0,
                    "hoursActual": 6.0,
                    "completionRate": 60.0,
                    "completionBand": "ON_TRACK",
                    "adjustments": ["request_help"],
                    "studentInput": {
                        "rating": 3,
                        "challenge": challenge,
                        "plan": "Sẽ cố gắng hơn tuần sau.",
                    },
                },
            )
        )
        db.commit()
    finally:
        db.close()


async def _login_student(client, email="student.demo@example.test"):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": "password123"}
    )
    assert resp.status_code == 200
    client.cookies.clear()  # xem ghi chu trong _login_instructor
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.mark.asyncio
async def test_bulk_intervention_applies_to_owned_cases_and_skips_others(client):
    """B1: 1 lan bam ap dung cho nhieu case cung luc, nhung case cua GV khac
    phai bi tu choi rieng (khong lam hong ca request)."""
    _seed_bulk_target_risk("risk_bulk_1")
    _seed_bulk_target_risk("risk_bulk_2")
    headers = await _login_instructor(client)

    resp = await client.post(
        "/api/v1/instructor/risks/bulk-intervention",
        json={
            "riskIds": ["risk_bulk_1", "risk_bulk_2", "risk_other_instructor", "does-not-exist"],
            "decision": "APPROVE",
            "note": "Nhắc hàng loạt: hoàn thành dưới 50% tuần này.",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["appliedCount"] == 2
    assert body["failedCount"] == 2
    by_id = {row["riskId"]: row for row in body["results"]}
    assert by_id["risk_bulk_1"]["ok"] is True
    assert by_id["risk_bulk_2"]["ok"] is True
    assert by_id["risk_other_instructor"]["ok"] is False
    assert by_id["does-not-exist"]["ok"] is False

    resp = await client.get("/api/v1/instructor/risks/risk_bulk_1", headers=headers)
    assert resp.json()["status"] == "INTERVENTION_APPROVED"
    assert resp.json()["instructorNote"] == "Nhắc hàng loạt: hoàn thành dưới 50% tuần này."

    # Case cua GV khac phai KHONG bi dong o boi bulk (van con nguyen PENDING).
    other_headers = await _login_instructor_other(client)
    resp = await client.get(
        "/api/v1/instructor/risks/risk_other_instructor", headers=other_headers
    )
    assert resp.json()["status"] == "INTERVENTION_PENDING"


async def _login_instructor_other(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.other@example.test", "password": "password123"},
    )
    assert resp.status_code == 200
    client.cookies.clear()  # xem ghi chu trong _login_instructor
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.mark.asyncio
async def test_risk_sla_overdue_flag(client):
    """B2: case mo qua RISK_SLA_DAYS (3 ngay) ma chua co quyet dinh phai
    duoc gan isOverdue=true; case moi thi khong."""
    _seed_overdue_risk("risk_overdue_test", days_old=5)
    headers = await _login_instructor(client)

    resp = await client.get("/api/v1/instructor/risks/risk_overdue_test", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["isOverdue"] is True
    assert body["daysOpen"] >= 5

    resp = await client.get("/api/v1/instructor/risks/risk_ethan_demo", headers=headers)
    body2 = resp.json()
    # risk_ethan_demo sinh ra 2 ngay truoc (xem api_demo_dataset.py) — chua qua han.
    assert body2["isOverdue"] is False


@pytest.mark.asyncio
async def test_class_comparison_lists_courses_with_metrics(client):
    """B3: so sanh nhieu lop phai gom SSA101 (lop co du lieu that) voi dung
    si so/so canh bao — khong assert toan bo danh sach vi cac test khac co
    the da them course rieng (ZZKUDOS999, ZZTREND999, ...) cho inst_demo."""
    headers = await _login_instructor(client)
    resp = await client.get("/api/v1/instructor/classes/compare", headers=headers)
    assert resp.status_code == 200
    classes = resp.json()["classes"]
    ssa = next((c for c in classes if c["code"] == "SSA101"), None)
    assert ssa is not None
    assert ssa["classSize"] >= 1
    assert isinstance(ssa["highRiskCount"], int)
    assert isinstance(ssa["overdueCount"], int)


@pytest.mark.asyncio
async def test_instructor_digest_lists_recent_cases_and_can_email(client):
    """C1: digest phai gom case rui ro moi phat sinh trong khoang ngay yeu
    cau, va endpoint gui email khong duoc loi ke ca khi EMAIL_PROVIDER=none
    (NullEmailService trong moi truong test)."""
    headers = await _login_instructor(client)
    resp = await client.get("/api/v1/instructor/digest?days=30", headers=headers)
    assert resp.status_code == 200
    digest = resp.json()
    assert digest["summary"]["newRiskCount"] >= 1
    assert any(r["id"] == "risk_ethan_demo" for r in digest["newRiskCases"])

    resp = await client.post("/api/v1/instructor/digest/email?days=30", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["sent"] is True
    assert resp.json()["to"] == "instructor.demo@example.test"


@pytest.mark.asyncio
async def test_reflection_summary_hidden_until_student_consents(client):
    """C2: mac dinh KHONG duoc tra ban tom tat phan tu; chi sau khi SV tu bat
    consent thi moi hien — va CHI hien chi so, khong bao gio lo van ban goc
    (content/challenge/plan) SV da viet."""
    secret_challenge = "Em đang gặp khó khăn riêng về tài chính gia đình."
    _seed_weekly_reflection("student_ethan", 40, challenge=secret_challenge)
    instructor_headers = await _login_instructor(client)

    resp = await client.get(
        "/api/v1/instructor/students/student_ethan/profile", headers=instructor_headers
    )
    profile = resp.json()
    assert profile["reflectionSharingEnabled"] is False
    assert profile["reflectionSummary"] == []

    student_headers = await _login_student(client)
    resp = await client.patch(
        "/api/v1/student/privacy-settings",
        json={"share_reflection_summary": True},
        headers=student_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["shareReflectionSummary"] is True

    resp = await client.get(
        "/api/v1/instructor/students/student_ethan/profile", headers=instructor_headers
    )
    profile = resp.json()
    assert profile["reflectionSharingEnabled"] is True
    entry = next(e for e in profile["reflectionSummary"] if e["weekNumber"] == 40)
    assert entry["completionRate"] == 60.0
    assert entry["requestedHelp"] is True
    # Van ban goc SV go khong duoc xuat hien o BAT KY dau trong response.
    assert "content" not in entry
    assert "challenge" not in entry
    assert secret_challenge not in resp.text

    # SV tu tat lai — profile phai tro ve rong ngay.
    resp = await client.patch(
        "/api/v1/student/privacy-settings",
        json={"share_reflection_summary": False},
        headers=student_headers,
    )
    assert resp.json()["shareReflectionSummary"] is False
    resp = await client.get(
        "/api/v1/instructor/students/student_ethan/profile", headers=instructor_headers
    )
    assert resp.json()["reflectionSummary"] == []
