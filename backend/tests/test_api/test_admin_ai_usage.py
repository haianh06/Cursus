"""Màn "Chi phí AI" (PLO 5, vế chi phí) — đường đọc bảng `ai_usage`."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from src.db.connection import SessionLocal
from src.db.models import AIUsage, User
from src.services.core import ai_pricing
from tests.test_api.test_admin import _ensure_admin_user


def _admin_org_id() -> str:
    db = SessionLocal()
    try:
        return db.query(User).filter_by(email="admin.demo@example.test").first().organization_id
    finally:
        db.close()


def _add_usage(**overrides) -> None:
    db = SessionLocal()
    try:
        row = {
            "id": f"aiu_{uuid.uuid4().hex[:12]}",
            "created_at": datetime.now(UTC).replace(tzinfo=None),
            "organization_id": _admin_org_id(),
            "user_id": "admin_demo",
            "feature": "qa_answer",
            "model": "gemini-3.6-flash",
            "input_tokens": 1000,
            "output_tokens": 500,
            "latency_ms": 800,
            "success": True,
        }
        row.update(overrides)
        db.add(AIUsage(**row))
        db.commit()
    finally:
        db.close()


async def _admin_headers(client) -> dict[str, str]:
    _ensure_admin_user()
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin.demo@example.test", "password": "AdminPassword123"},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['token']}"}


@pytest.mark.asyncio
async def test_ai_usage_requires_admin_role(client):
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "instructor.demo@example.test", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    resp = await client.get("/api/v1/admin/ai-usage", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_ai_usage_empty_table_returns_zeros_not_an_error(client):
    """Bảng `ai_usage` hiện 0 dòng trên máy dev. Màn hình phải mở được và nói
    rõ là chưa có dữ liệu, chứ không phải lỗi 500 hay bảng trắng."""
    headers = await _admin_headers(client)

    resp = await client.get("/api/v1/admin/ai-usage?days=7", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["days"] == 7
    assert data["totals"]["calls"] == 0
    assert data["by_feature"] == []
    # Không có mẫu số thì không có tỷ lệ — `0.0` ở đây là một khẳng định
    # không có gì chống lưng (cùng nguyên tắc với admin_overview_service).
    assert data["totals"]["error_rate"] is None
    assert data["totals"]["avg_latency_ms"] is None
    assert "Chưa có lần gọi LLM nào" in data["method_note"]


@pytest.mark.asyncio
async def test_ai_usage_groups_by_feature_and_counts_errors(client):
    headers = await _admin_headers(client)
    feature = f"test_feature_{uuid.uuid4().hex[:6]}"
    _add_usage(feature=feature, latency_ms=1000)
    _add_usage(feature=feature, latency_ms=2000, success=False)

    resp = await client.get("/api/v1/admin/ai-usage?days=30", headers=headers)
    assert resp.status_code == 200, resp.text
    row = next(item for item in resp.json()["by_feature"] if item["feature"] == feature)

    assert row["calls"] == 2
    assert row["input_tokens"] == 2000
    assert row["output_tokens"] == 1000
    assert row["avg_latency_ms"] == 1500
    assert row["error_rate"] == 0.5


@pytest.mark.asyncio
async def test_model_without_a_declared_price_reports_null_cost_not_zero(client):
    """`None` = "không đủ dữ kiện để tính", `0.0` = "đã tính, ra 0 đồng". Trộn
    hai thứ này làm tổng chi phí thấp hơn thực tế mà không có dấu hiệu gì."""
    headers = await _admin_headers(client)
    feature = f"test_unpriced_{uuid.uuid4().hex[:6]}"
    _add_usage(feature=feature, model="model-khong-co-trong-bang-gia")

    resp = await client.get("/api/v1/admin/ai-usage?days=30", headers=headers)
    row = next(item for item in resp.json()["by_feature"] if item["feature"] == feature)

    assert row["est_cost_usd"] is None
    assert row["calls_without_price"] == 1


@pytest.mark.asyncio
async def test_cost_is_computed_when_the_model_has_a_price(client, monkeypatch):
    headers = await _admin_headers(client)
    feature = f"test_priced_{uuid.uuid4().hex[:6]}"
    model = f"model-co-gia-{uuid.uuid4().hex[:6]}"
    monkeypatch.setitem(ai_pricing.PRICES_USD_PER_MILLION, model, (10.0, 30.0))
    _add_usage(feature=feature, model=model, input_tokens=1_000_000, output_tokens=1_000_000)

    resp = await client.get("/api/v1/admin/ai-usage?days=30", headers=headers)
    row = next(item for item in resp.json()["by_feature"] if item["feature"] == feature)

    assert row["est_cost_usd"] == 40.0
    assert row["calls_without_price"] == 0


@pytest.mark.asyncio
async def test_rows_outside_the_window_are_excluded(client):
    headers = await _admin_headers(client)
    feature = f"test_old_{uuid.uuid4().hex[:6]}"
    _add_usage(
        feature=feature,
        created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=45),
    )

    within = await client.get("/api/v1/admin/ai-usage?days=7", headers=headers)
    assert all(item["feature"] != feature for item in within.json()["by_feature"])

    wider = await client.get("/api/v1/admin/ai-usage?days=90", headers=headers)
    assert any(item["feature"] == feature for item in wider.json()["by_feature"])


@pytest.mark.asyncio
async def test_calls_without_an_organization_are_counted_separately(client):
    """`qa_answer_service` không giữ session người dùng nên ghi
    `organization_id = NULL`. Gộp chúng vào bảng của một tổ chức là rò dữ liệu
    chéo; bỏ hẳn thì tổng chi phí thiếu mà không ai biết."""
    headers = await _admin_headers(client)
    feature = f"test_orphan_{uuid.uuid4().hex[:6]}"
    _add_usage(feature=feature, organization_id=None)

    data = (await client.get("/api/v1/admin/ai-usage?days=30", headers=headers)).json()

    assert all(item["feature"] != feature for item in data["by_feature"])
    assert data["unattributed_calls"] >= 1
    assert "không gắn tổ chức" in data["method_note"]


@pytest.mark.asyncio
async def test_invalid_days_falls_back_to_the_default_window(client):
    headers = await _admin_headers(client)
    resp = await client.get("/api/v1/admin/ai-usage?days=100000", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["days"] == 30


@pytest.mark.asyncio
async def test_daily_series_covers_every_day_including_empty_ones(client):
    """Bỏ ngày rỗng khỏi chuỗi sẽ làm biểu đồ bóp các cột sát nhau: một khoảng
    lặng ba ngày trông y hệt ba ngày liên tiếp có dữ liệu."""
    headers = await _admin_headers(client)
    _add_usage(feature=f"test_daily_{uuid.uuid4().hex[:6]}")

    data = (await client.get("/api/v1/admin/ai-usage?days=7", headers=headers)).json()
    series = data["by_day"]

    assert len(series) == 7
    assert [row["date"] for row in series] == sorted(row["date"] for row in series)
    assert sum(row["calls"] for row in series) >= 1
    # Ngày rỗng vẫn có mặt, với calls = 0 chứ không phải bị lược đi.
    assert any(row["calls"] == 0 for row in series)


@pytest.mark.asyncio
async def test_daily_series_prices_each_day_when_the_model_has_a_price(client, monkeypatch):
    headers = await _admin_headers(client)
    model = f"model-daily-{uuid.uuid4().hex[:6]}"
    monkeypatch.setitem(ai_pricing.PRICES_USD_PER_MILLION, model, (10.0, 30.0))
    _add_usage(
        feature=f"test_daily_cost_{uuid.uuid4().hex[:6]}",
        model=model,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )

    series = (await client.get("/api/v1/admin/ai-usage?days=7", headers=headers)).json()["by_day"]
    today = series[-1]

    assert today["est_cost_usd"] is not None
    assert today["est_cost_usd"] >= 40.0
