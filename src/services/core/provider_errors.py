"""Classify LLM / provider failures into stable error codes for the UI.

Ported from origin/develop verbatim — pure string classification, no
schema/DB dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderFailure:
    code: str
    message: str


def classify_provider_error(exc: BaseException) -> ProviderFailure:
    """Map SDK/HTTP exceptions to user-facing codes."""
    text = f"{type(exc).__name__}: {exc}".lower()
    status = _extract_status(text)

    if status == 429 or any(
        token in text
        for token in (
            "resource_exhausted",
            "quota",
            "rate limit",
            "rate_limit",
            "too many requests",
        )
    ):
        return ProviderFailure(
            code="LLM_QUOTA",
            message=(
                "Gemini đang hết hạn mức (quota) hoặc bị giới hạn tốc độ. "
                "Hệ thống trả lời tạm từ học liệu môn — chi tiết có thể kém hơn."
            ),
        )

    if status in {401, 403} or any(
        token in text for token in ("api key", "unauthorized", "permission denied", "invalid api")
    ):
        return ProviderFailure(
            code="LLM_AUTH",
            message=(
                "Không xác thực được với Gemini (API key sai/thiếu quyền). "
                "Đang trả lời tạm từ học liệu môn."
            ),
        )

    if status == 404 or "not found" in text or "is not found" in text:
        return ProviderFailure(
            code="LLM_MODEL_UNAVAILABLE",
            message=(
                "Model Gemini hiện không khả dụng với tài khoản này. "
                "Đang trả lời tạm từ học liệu môn."
            ),
        )

    if status in {500, 502, 503, 504} or any(
        token in text for token in ("unavailable", "timed out", "timeout", "connection")
    ):
        return ProviderFailure(
            code="LLM_UNAVAILABLE",
            message=(
                "Dịch vụ Gemini tạm thời không phản hồi. "
                "Đang trả lời tạm từ học liệu môn."
            ),
        )

    return ProviderFailure(
        code="LLM_ERROR",
        message=(
            "Gemini gặp lỗi khi tạo câu trả lời. "
            "Đang trả lời tạm từ học liệu môn."
        ),
    )


def _extract_status(text: str) -> int | None:
    match = re.search(r"\b([45]\d\d)\b", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None
