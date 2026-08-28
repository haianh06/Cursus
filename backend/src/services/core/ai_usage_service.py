"""Tổng hợp bảng `ai_usage` thành báo cáo cho màn "Chi phí AI" của Admin.

Đây là vế cuối cùng của "giám sát cơ bản: độ trễ / lỗi / chi phí" (PLO 5).
Hai vế đầu đã có; dữ liệu vế chi phí do `AIUsageCallback` ghi từ 26/08 — file
này chỉ là đường đọc.

Gom theo `(feature, model)` ở tầng SQL rồi mới gập về từng `feature` ở Python,
vì đơn giá phụ thuộc model: một feature có thể chạy trên model chính lẫn model
fallback trong cùng một kỳ, và cộng token của hai model rồi nhân một đơn giá
sẽ ra số sai.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from src.db import models
from src.services.core.ai_pricing import (
    PRICING_AS_OF,
    PRICING_SOURCE,
    estimate_cost_usd,
    priced_models,
)

# Giới hạn cửa sổ thời gian người gọi chọn được. Không nhận số tuỳ ý để một
# `days=100000` không biến thành quét toàn bảng.
ALLOWED_DAYS = (7, 30, 90)
DEFAULT_DAYS = 30


def _rate(numerator: int, denominator: int) -> float | None:
    """Tỷ lệ, hoặc `None` khi mẫu số bằng 0.

    Cùng nguyên tắc với `admin_overview_service._metric()`: không có mẫu số thì
    không có tỷ lệ. Trả `0.0` ở đây sẽ hiện "tỷ lệ lỗi 0%" cho một hệ thống
    chưa từng gọi LLM lần nào — một lời khẳng định không có gì chống lưng.
    """
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def build_ai_usage_report(
    db: Session,
    *,
    organization_id: str | None,
    days: int = DEFAULT_DAYS,
) -> dict:
    if days not in ALLOWED_DAYS:
        days = DEFAULT_DAYS
    # `AIUsage.created_at` lưu naive UTC (`default=datetime.utcnow`), nên mốc
    # so sánh cũng phải naive — lệch tzinfo là so sánh sai kỳ, không phải lỗi
    # cú pháp nên sẽ không ai thấy.
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

    failures = func.sum(case((models.AIUsage.success.is_(False), 1), else_=0))
    rows = (
        db.query(
            models.AIUsage.feature,
            models.AIUsage.model,
            func.count(models.AIUsage.id).label("calls"),
            func.coalesce(func.sum(models.AIUsage.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(models.AIUsage.output_tokens), 0).label("output_tokens"),
            func.coalesce(func.sum(models.AIUsage.latency_ms), 0).label("latency_ms_total"),
            func.coalesce(failures, 0).label("failures"),
        )
        .filter(
            models.AIUsage.created_at >= since,
            models.AIUsage.organization_id == organization_id,
        )
        .group_by(models.AIUsage.feature, models.AIUsage.model)
        .all()
    )

    by_feature: dict[str, dict] = {}
    for row in rows:
        bucket = by_feature.setdefault(
            row.feature,
            {
                "feature": row.feature,
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms_total": 0,
                "failures": 0,
                "est_cost_usd": None,
                "calls_without_price": 0,
                "models": [],
            },
        )
        bucket["calls"] += row.calls
        bucket["input_tokens"] += row.input_tokens
        bucket["output_tokens"] += row.output_tokens
        bucket["latency_ms_total"] += row.latency_ms_total
        bucket["failures"] += row.failures
        bucket["models"].append(row.model)

        cost = estimate_cost_usd(row.model, row.input_tokens, row.output_tokens)
        if cost is None:
            bucket["calls_without_price"] += row.calls
        else:
            bucket["est_cost_usd"] = (bucket["est_cost_usd"] or 0.0) + cost

    features = []
    for bucket in by_feature.values():
        calls = bucket["calls"]
        features.append(
            {
                "feature": bucket["feature"],
                "calls": calls,
                "input_tokens": bucket["input_tokens"],
                "output_tokens": bucket["output_tokens"],
                "avg_latency_ms": round(bucket["latency_ms_total"] / calls) if calls else None,
                "error_rate": _rate(bucket["failures"], calls),
                "est_cost_usd": (
                    round(bucket["est_cost_usd"], 6) if bucket["est_cost_usd"] is not None else None
                ),
                "calls_without_price": bucket["calls_without_price"],
                "models": sorted(set(bucket["models"])),
            }
        )
    # Tốn nhất lên đầu. Feature chưa có đơn giá xếp sau nhóm đã tính được, vì
    # không biết chúng đứng ở đâu trong thứ tự đó.
    features.sort(key=lambda item: (item["est_cost_usd"] is None, -(item["est_cost_usd"] or 0)))

    total_calls = sum(item["calls"] for item in features)
    total_failures = sum(bucket["failures"] for bucket in by_feature.values())
    total_latency = sum(bucket["latency_ms_total"] for bucket in by_feature.values())
    priced_costs = [item["est_cost_usd"] for item in features if item["est_cost_usd"] is not None]
    calls_without_price = sum(item["calls_without_price"] for item in features)

    # Lần gọi không gắn tổ chức (`qa_answer_service` không giữ session người
    # dùng nên ghi organization_id = NULL). Không gộp vào bảng trên — làm vậy
    # là rò dữ liệu chéo tổ chức — nhưng phải đếm ra, nếu không tổng chi phí
    # thiếu đi một mảng mà không có dấu hiệu gì.
    unattributed_calls = (
        db.query(func.count(models.AIUsage.id))
        .filter(
            models.AIUsage.created_at >= since,
            models.AIUsage.organization_id.is_(None),
        )
        .scalar()
    ) or 0

    return {
        "days": days,
        "generated_at": datetime.now(UTC).isoformat(),
        "by_day": _build_daily_series(db, organization_id=organization_id, since=since, days=days),
        "totals": {
            "calls": total_calls,
            "input_tokens": sum(item["input_tokens"] for item in features),
            "output_tokens": sum(item["output_tokens"] for item in features),
            "avg_latency_ms": round(total_latency / total_calls) if total_calls else None,
            "error_rate": _rate(total_failures, total_calls),
            "est_cost_usd": round(sum(priced_costs), 6) if priced_costs else None,
            "calls_without_price": calls_without_price,
        },
        "by_feature": features,
        "unattributed_calls": unattributed_calls,
        "pricing": {
            "as_of": PRICING_AS_OF,
            "source": PRICING_SOURCE,
            "models_priced": priced_models(),
        },
        "method_note": _method_note(total_calls, calls_without_price, unattributed_calls),
    }


def _build_daily_series(
    db: Session,
    *,
    organization_id: str | None,
    since: datetime,
    days: int,
) -> list[dict]:
    """Chi phí và số lần gọi theo từng ngày, dùng cho biểu đồ cột.

    Trả về **đủ mọi ngày trong kỳ**, kể cả ngày không có lần gọi nào (calls=0).
    Nếu chỉ trả về ngày có dữ liệu, biểu đồ sẽ bóp các cột sát nhau và một
    khoảng lặng ba ngày trông y hệt ba ngày liên tiếp đều đặn — sai lệch thị
    giác, không phải sai số liệu, nhưng người xem vẫn đọc ra kết luận sai.

    Vẫn gom theo `(ngày, model)` vì đơn giá theo model, giống lý do ở
    `build_ai_usage_report`.
    """
    rows = (
        db.query(
            func.date(models.AIUsage.created_at).label("day"),
            models.AIUsage.model,
            func.count(models.AIUsage.id).label("calls"),
            func.coalesce(func.sum(models.AIUsage.input_tokens), 0).label("input_tokens"),
            func.coalesce(func.sum(models.AIUsage.output_tokens), 0).label("output_tokens"),
        )
        .filter(
            models.AIUsage.created_at >= since,
            models.AIUsage.organization_id == organization_id,
        )
        .group_by("day", models.AIUsage.model)
        .all()
    )

    buckets: dict[str, dict] = {}
    for row in rows:
        # SQLite trả chuỗi cho `date()`, Postgres trả `datetime.date`.
        key = row.day if isinstance(row.day, str) else row.day.isoformat()
        bucket = buckets.setdefault(key, {"calls": 0, "est_cost_usd": None})
        bucket["calls"] += row.calls
        cost = estimate_cost_usd(row.model, row.input_tokens, row.output_tokens)
        if cost is not None:
            bucket["est_cost_usd"] = (bucket["est_cost_usd"] or 0.0) + cost

    today = datetime.now(UTC).replace(tzinfo=None).date()
    series = []
    for offset in range(days - 1, -1, -1):
        key = (today - timedelta(days=offset)).isoformat()
        bucket = buckets.get(key, {"calls": 0, "est_cost_usd": None})
        series.append(
            {
                "date": key,
                "calls": bucket["calls"],
                "est_cost_usd": (
                    round(bucket["est_cost_usd"], 6)
                    if bucket["est_cost_usd"] is not None
                    else None
                ),
            }
        )
    return series


def _method_note(total_calls: int, calls_without_price: int, unattributed_calls: int) -> str:
    """Dòng giải thích cách đo, bắt buộc hiện cạnh mọi số liệu ở Admin Console
    (`CHUNG_admin.md` mục 2, ý 1). Nội dung đổi theo tình trạng dữ liệu thật
    chứ không phải một câu cố định — một câu cố định sẽ nói sai ngay khi bảng
    giá còn trống."""
    parts = [
        "Chi phí là ƯỚC TÍNH, tính bằng số token đã ghi nhân đơn giá niêm yết "
        "theo model, không phải số tiền lấy từ hoá đơn nhà cung cấp."
    ]
    if total_calls == 0:
        parts.append("Chưa có lần gọi LLM nào trong kỳ này.")
    # Chỉ nói "một phần lần gọi thiếu đơn giá" khi bảng giá đã có ít nhất một
    # model. Lúc bảng giá còn trống hoàn toàn thì câu này thừa — UI đã có một
    # câu riêng nói thẳng là chưa khai báo đơn giá cho model nào.
    if calls_without_price and priced_models():
        parts.append(
            f"{calls_without_price} lần gọi dùng model chưa khai báo đơn giá nên "
            "không được tính vào chi phí — xem src/services/core/ai_pricing.py."
        )
    if unattributed_calls:
        parts.append(
            f"{unattributed_calls} lần gọi không gắn tổ chức (không có ngữ cảnh "
            "người dùng lúc gọi) nằm ngoài bảng này."
        )
    return " ".join(parts)
