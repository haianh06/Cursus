"""Ghi chi phí + độ trễ của mỗi lần gọi LLM (D1, đi cùng bảng `AIUsage` ở D2).

Vì sao là callback chứ không phải đọc `response.usage_metadata` ở chỗ gọi:
8 trong 11 chỗ gọi LLM của hệ thống dùng `.with_structured_output(...)`, và
cách gọi đó trả về object đã parse — `usage_metadata` không đi kèm. Đọc ở
phía người gọi thì 8/11 chỗ sẽ ghi ra 0 token mà **không báo lỗi gì**, đúng
kiểu sai tệ nhất: bảng có dữ liệu, con số trông hợp lý, và sai.

Callback của LangChain thì nhận `LLMResult` thô ở tầng dưới, trước khi parser
chạy — nên nó thấy được token bất kể người gọi dùng kiểu nào.

Mọi lỗi ở đây đều bị nuốt: đo đạc là việc phụ, không được làm hỏng câu trả
lời của sinh viên.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from sqlalchemy.orm import Session

from src.db import models
from src.db.connection import SessionLocal
from src.security.request_context import actor_org_id_var, actor_user_id_var

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
) -> models.AIUsage:
    """Thêm một hàng `AIUsage` vào session. **Không** commit — người gọi
    quyết định ranh giới giao dịch (callback tự commit trên session riêng của
    nó; test thì commit rồi rollback)."""
    row = models.AIUsage(
        id=f"aiu_{uuid.uuid4().hex}",
        organization_id=organization_id,
        user_id=user_id,
        feature=feature,
        model=model,
        input_tokens=int(input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        latency_ms=int(latency_ms or 0),
        success=bool(success),
    )
    db.add(row)
    return row


def _tokens_from(response: LLMResult) -> tuple[int, int]:
    """Bóc (input, output) token khỏi `LLMResult`, thử theo thứ tự tin cậy.

    `usage_metadata` trên chính message là đường chuẩn của langchain-core và
    là thứ `ChatGoogleGenerativeAI` gắn. `llm_output["token_usage"]` là hình
    dạng cũ vài provider vẫn dùng — giữ làm đường lui, vì ghi 0 token trong
    khi thật ra có tốn tiền thì không ai phát hiện ra.
    """
    for generation_list in response.generations or []:
        for generation in generation_list:
            message = getattr(generation, "message", None)
            usage = getattr(message, "usage_metadata", None)
            if usage:
                return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))

    token_usage = (response.llm_output or {}).get("token_usage") or {}
    if token_usage:
        return (
            int(token_usage.get("prompt_tokens", 0)),
            int(token_usage.get("completion_tokens", 0)),
        )
    return 0, 0


def _model_from(response: LLMResult, fallback: str) -> str:
    return str((response.llm_output or {}).get("model_name") or fallback)


class AIUsageCallback(BaseCallbackHandler):
    """Gắn vào client trong `get_llm()`. Một instance cho mỗi client, nhưng
    vẫn khoá thời điểm bắt đầu theo `run_id` vì một client có thể được gọi
    nhiều lần (ví dụ `qa_answer_service` thử lại khi câu trả lời mất dấu)."""

    def __init__(
        self,
        *,
        feature: str,
        model: str = "",
        organization_id: str | None = None,
        user_id: str | None = None,
    ) -> None:
        self.feature = feature
        self.model = model
        self.organization_id = organization_id
        self.user_id = user_id
        self._started_at: dict[str, float] = {}

    # LangChain gọi `on_chat_model_start` cho chat model và `on_llm_start` cho
    # completion model. Nhận cả hai để không phụ thuộc vào việc provider được
    # xếp vào loại nào — bỏ sót một cái là bảng rỗng mà không có dấu hiệu gì.
    def on_chat_model_start(self, serialized: Any, messages: Any, **kwargs: Any) -> None:
        self._mark_start(kwargs.get("run_id"))

    def on_llm_start(self, serialized: Any, prompts: Any, **kwargs: Any) -> None:
        self._mark_start(kwargs.get("run_id"))

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        input_tokens, output_tokens = _tokens_from(response)
        self._write(
            run_id=kwargs.get("run_id"),
            model=_model_from(response, self.model),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            success=True,
        )

    def on_llm_error(self, error: BaseException, **kwargs: Any) -> None:
        # Một lần gọi hỏng vẫn tốn thời gian và vẫn là một lần gọi. Bỏ qua nó
        # là làm sai chính tỷ lệ lỗi mà PLO 5 hỏi tới.
        self._write(
            run_id=kwargs.get("run_id"),
            model=self.model,
            input_tokens=0,
            output_tokens=0,
            success=False,
        )

    def _mark_start(self, run_id: UUID | str | None) -> None:
        self._started_at[str(run_id)] = time.perf_counter()

    def _write(
        self,
        *,
        run_id: UUID | str | None,
        model: str,
        input_tokens: int,
        output_tokens: int,
        success: bool,
    ) -> None:
        started = self._started_at.pop(str(run_id), None)
        latency_ms = int((time.perf_counter() - started) * 1000) if started else 0
        # Giá trị truyền thẳng thắng ngữ cảnh: chỗ gọi biết rõ hơn thì tin nó.
        organization_id = self.organization_id or actor_org_id_var.get()
        user_id = self.user_id or actor_user_id_var.get()
        db = None
        try:
            db = SessionLocal()
            record_usage(
                db,
                organization_id=organization_id,
                user_id=user_id,
                feature=self.feature,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                success=success,
            )
            db.commit()
        except Exception:
            # Nuốt có chủ đích: đo đạc không được phép làm hỏng câu trả lời.
            # Vẫn log để một bảng rỗng không bị hiểu nhầm là "không ai gọi AI".
            logger.warning("ai_usage_record_failed", exc_info=True)
            if db is not None:
                db.rollback()
        finally:
            if db is not None:
                db.close()


def record_llm_call(
    *,
    feature: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    success: bool,
    organization_id: str | None = None,
    user_id: str | None = None,
) -> None:
    """Ghi một lần gọi LLM trên session riêng của chính nó, tự commit.

    Thay `AIUsageCallback` cho đường `ai_engine` (SDK `openai` gọi thẳng, không
    qua LangChain nên không có chỗ cắm callback). Đơn giản hơn hẳn bản callback:
    `chat.completions.create` trả `response.usage` ngay trong response, không
    cần bám theo `run_id` để ghép mốc thời gian.

    `AIUsageCallback` bên dưới vẫn giữ cho bất kỳ đường LangChain nào còn sót,
    và để các hàng `ai_usage` cũ vẫn giải thích được nguồn gốc.

    Nuốt mọi lỗi có chủ đích: đo đạc không được phép làm hỏng câu trả lời.
    """
    db = None
    try:
        db = SessionLocal()
        record_usage(
            db,
            # Chỗ gọi biết ngữ cảnh rõ hơn thì tin nó; không thì lấy từ biến
            # ngữ cảnh request, đúng như `AIUsageCallback._write` vẫn làm.
            organization_id=organization_id or actor_org_id_var.get(),
            user_id=user_id or actor_user_id_var.get(),
            feature=feature,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            success=success,
        )
        db.commit()
    except Exception:
        logger.exception("ai_usage_record_failed feature=%s model=%s", feature, model)
        if db is not None:
            db.rollback()
    finally:
        if db is not None:
            db.close()


def tokens_from_openai_usage(usage: object) -> tuple[int, int]:
    """(input, output) từ `response.usage` của SDK openai.

    Trả (0, 0) khi không có `usage` — xảy ra với đường stream nếu gateway
    không hỗ trợ `stream_options={"include_usage": True}`. Số lần gọi và độ
    trễ vẫn đúng trong trường hợp đó; chỉ riêng token là thiếu.
    """
    if usage is None:
        return 0, 0
    return (
        int(getattr(usage, "prompt_tokens", 0) or 0),
        int(getattr(usage, "completion_tokens", 0) or 0),
    )
