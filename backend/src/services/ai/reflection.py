"""Sinh nội dung phản tư cuối tuần (FR-6.1, FR-6.3).

Đầu vào gồm số liệu tiến độ tuần và (tuỳ chọn) câu trả lời sinh viên tự nhập
trong luồng đối thoại 3 bước. Đầu ra là một đoạn phản tư ngắn.

FR-6.3 cấm đưa ra nhận định/chẩn đoán tâm lý — ràng buộc này được ghi thẳng vào
system prompt và bản fallback cũng tuân thủ: chỉ mô tả số liệu và gợi ý hành vi
học tập, không suy đoán trạng thái tinh thần.
"""

from __future__ import annotations

import logging
from typing import TypedDict

from src.config import Settings, get_settings
from src.services.core.llm import get_llm

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là trợ giảng học thuật, viết đoạn phản tư cuối tuần cho sinh viên.

QUY TẮC BẮT BUỘC:
1. TUYỆT ĐỐI KHÔNG đưa ra nhận định hay chẩn đoán tâm lý (không nói sinh viên căng thẳng,
   lo âu, mất động lực, kiệt sức...). Chỉ nói về hành vi học tập quan sát được qua số liệu.
2. Bám vào SỐ LIỆU được cung cấp, không bịa thêm con số nào khác.
3. Viết 3-5 câu tiếng Việt, giọng điềm đạm, khích lệ nhưng không sáo rỗng.
4. Kết bằng đúng một gợi ý hành động cụ thể cho tuần tới.
5. Trả về văn bản thuần, không markdown, không tiêu đề."""


class ReflectionInput(TypedDict, total=False):
    """Số liệu tuần + câu trả lời tự nhập của sinh viên (nếu có)."""

    week_number: int
    completed_tasks: int
    total_tasks: int
    hours_actual: float
    hours_planned: float
    rating: str | None
    blockers: str | None
    next_plan: str | None


def compose(payload: ReflectionInput) -> str:
    """Trả đoạn phản tư cho tuần đang xét.

    Có API key thì dùng LLM; không thì dựng bằng mẫu tất định. Cả hai nhánh đều
    chỉ dựa trên số liệu thật, nên nội dung luôn kiểm chứng được.
    """
    if not _has_real_api_key(get_settings()):
        logger.info("reflection_using_deterministic_fallback")
        return _fallback_text(payload)

    try:
        response = get_llm().invoke([("system", SYSTEM_PROMPT), ("human", _build_prompt(payload))])
        text = str(response.content).strip()
        return text or _fallback_text(payload)
    except Exception as exc:  # noqa: BLE001 - lỗi mạng/SDK không được làm hỏng luồng
        logger.error("reflection_llm_call_failed", extra={"error": str(exc)})
        return _fallback_text(payload)


def completion_rate(payload: ReflectionInput) -> float:
    """Tỷ lệ hoàn thành task theo phần trăm, làm tròn 1 chữ số."""
    total = payload.get("total_tasks") or 0
    if total <= 0:
        return 0.0
    return round(payload.get("completed_tasks", 0) / total * 100, 1)


def _build_prompt(payload: ReflectionInput) -> str:
    lines = [
        f"Tuần: {payload.get('week_number', '?')}",
        f"Task hoàn thành: {payload.get('completed_tasks', 0)}/{payload.get('total_tasks', 0)}"
        f" ({completion_rate(payload)}%)",
        f"Giờ tự học thực tế: {payload.get('hours_actual', 0)}h / kế hoạch {payload.get('hours_planned', 0)}h",
    ]
    lines.extend(_answer_lines(payload))
    return "SỐ LIỆU TUẦN:\n" + "\n".join(lines)


def _answer_lines(payload: ReflectionInput) -> list[str]:
    """Các câu sinh viên tự nhập, bỏ qua ô để trống."""
    fields = (
        ("Sinh viên tự đánh giá", payload.get("rating")),
        ("Khó khăn gặp phải", payload.get("blockers")),
        ("Dự định tuần tới", payload.get("next_plan")),
    )
    return [f"{label}: {value}" for label, value in fields if value]


def _fallback_text(payload: ReflectionInput) -> str:
    """Bản tất định — chỉ mô tả số liệu, tuyệt đối không suy đoán tâm lý (FR-6.3)."""
    rate = completion_rate(payload)
    parts = [
        f"Tuần {payload.get('week_number', '?')} bạn hoàn thành "
        f"{payload.get('completed_tasks', 0)}/{payload.get('total_tasks', 0)} nhiệm vụ đã đề ra ({rate}%).",
        f"Thời gian tự học thực tế là {payload.get('hours_actual', 0)} giờ "
        f"trên {payload.get('hours_planned', 0)} giờ đã lên kế hoạch.",
    ]
    if payload.get("blockers"):
        parts.append(f"Khó khăn bạn ghi nhận: {payload['blockers']}.")
    parts.append(_next_step_hint(rate))
    return " ".join(parts)


def _next_step_hint(rate: float) -> str:
    if rate >= 80:
        return "Tuần tới hãy giữ nguyên nhịp này và thử nâng độ khó của một nhiệm vụ trọng tâm."
    if rate >= 50:
        return "Tuần tới hãy chia nhỏ nhiệm vụ dài nhất thành 2-3 phần để dễ hoàn thành đúng hạn hơn."
    return "Tuần tới hãy chọn ra đúng ba nhiệm vụ quan trọng nhất và hoàn thành trọn vẹn trước khi mở thêm việc mới."


def _has_real_api_key(settings: Settings) -> bool:
    key = settings.openai_api_key or ""
    return bool(key) and not key.startswith("sk-your")
