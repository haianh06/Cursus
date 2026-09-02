"""D1+D2 — đo chi phí/độ trễ mỗi lần gọi LLM (ràng buộc BTC #6, PLO 5).

Không test nào ở đây gọi mạng thật. Callback của LangChain được gọi tay với
đúng hình dạng `LLMResult` mà `ChatGoogleGenerativeAI` trả về, vì chính chỗ
bóc số token ra khỏi `LLMResult` mới là chỗ dễ sai — xem
`test_the_callback_still_reads_tokens_when_the_caller_used_structured_output`.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from src.db import models
from src.db.connection import SessionLocal
from src.services.core.ai_usage_recorder import (
    AIUsageCallback,
    record_llm_call,
    record_usage,
    tokens_from_openai_usage,
)


def _llm_result(*, input_tokens: int, output_tokens: int) -> LLMResult:
    message = AIMessage(
        content="ok",
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        },
    )
    return LLMResult(generations=[[ChatGeneration(message=message)]])


def _row_for(org_id: str) -> models.AIUsage:
    db = SessionLocal()
    try:
        return db.query(models.AIUsage).filter_by(organization_id=org_id).one()
    finally:
        db.close()


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

        row = db.query(models.AIUsage).filter_by(organization_id=f"org_{org_suffix}").one()
        assert row.input_tokens == 120
        assert row.output_tokens == 45
        assert row.latency_ms == 830
        assert row.success is True
        # Cột thời gian là điểm khiến `LLMUsageEvent` cũ không dùng được —
        # không có nó thì không chia được chi phí theo kỳ (ADR-017).
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
            latency_ms=1500,
            success=False,
        )
        db.commit()

        row = db.query(models.AIUsage).filter_by(organization_id=f"org_{org_suffix}").one()
        assert row.success is False
        assert row.latency_ms == 1500
    finally:
        db.rollback()
        db.close()


def test_the_callback_records_tokens_and_latency_for_a_chat_model_run():
    org_id = f"org_cb_{uuid.uuid4().hex[:8]}"
    handler = AIUsageCallback(
        feature="weekly_plan", organization_id=org_id, user_id="user_cb"
    )
    run_id = uuid.uuid4()

    handler.on_chat_model_start({}, [[]], run_id=run_id)
    handler.on_llm_end(_llm_result(input_tokens=310, output_tokens=88), run_id=run_id)

    row = _row_for(org_id)
    assert row.feature == "weekly_plan"
    assert row.input_tokens == 310
    assert row.output_tokens == 88
    assert row.success is True
    assert row.latency_ms >= 0


def test_the_callback_still_reads_tokens_when_the_caller_used_structured_output():
    """8/11 chỗ gọi LLM dùng `.with_structured_output(...)`, cách gọi này trả
    về object đã bóc sẵn nên `response.usage_metadata` phía người gọi là mất.

    Callback thì nhận `LLMResult` thô ở tầng dưới, trước khi parser chạy — nên
    số token vẫn còn. Test này ghim đúng tính chất đó: handler không hề chạm
    tới giá trị mà người gọi nhận được.
    """
    org_id = f"org_so_{uuid.uuid4().hex[:8]}"
    handler = AIUsageCallback(feature="qa_answer", organization_id=org_id, user_id=None)
    run_id = uuid.uuid4()

    handler.on_chat_model_start({}, [[]], run_id=run_id)
    handler.on_llm_end(_llm_result(input_tokens=1024, output_tokens=7), run_id=run_id)

    row = _row_for(org_id)
    assert row.input_tokens == 1024
    assert row.output_tokens == 7


def test_the_callback_falls_back_to_llm_output_token_usage():
    """Không phải bản nào của provider cũng gắn `usage_metadata` lên message;
    một số trả ở `llm_output["token_usage"]`. Ghi 0 token trong khi thật ra có
    tốn tiền là kiểu sai tệ nhất — im lặng và trông vẫn hợp lý."""
    org_id = f"org_fb_{uuid.uuid4().hex[:8]}"
    handler = AIUsageCallback(feature="reflection", organization_id=org_id, user_id=None)
    run_id = uuid.uuid4()
    result = LLMResult(
        generations=[[ChatGeneration(message=AIMessage(content="ok"))]],
        llm_output={"token_usage": {"prompt_tokens": 40, "completion_tokens": 9}},
    )

    handler.on_chat_model_start({}, [[]], run_id=run_id)
    handler.on_llm_end(result, run_id=run_id)

    row = _row_for(org_id)
    assert row.input_tokens == 40
    assert row.output_tokens == 9


def test_the_callback_records_a_failed_run_with_success_false():
    org_id = f"org_err_{uuid.uuid4().hex[:8]}"
    handler = AIUsageCallback(feature="quiz_generator", organization_id=org_id, user_id=None)
    run_id = uuid.uuid4()

    handler.on_chat_model_start({}, [[]], run_id=run_id)
    handler.on_llm_error(RuntimeError("quota exceeded"), run_id=run_id)

    row = _row_for(org_id)
    assert row.success is False
    assert row.input_tokens == 0


def test_a_broken_recorder_never_breaks_the_llm_call(monkeypatch):
    """Đo đạc là việc phụ. Nếu ghi số liệu hỏng thì sinh viên vẫn phải nhận
    được câu trả lời — callback nuốt lỗi thay vì ném ngược lên người gọi."""
    from src.services.core import ai_usage_recorder

    def _boom(*args, **kwargs):
        raise RuntimeError("database is down")

    monkeypatch.setattr(ai_usage_recorder, "record_usage", _boom)
    handler = AIUsageCallback(feature="qa_answer", organization_id="org_x", user_id=None)
    run_id = uuid.uuid4()

    handler.on_chat_model_start({}, [[]], run_id=run_id)
    handler.on_llm_end(_llm_result(input_tokens=1, output_tokens=1), run_id=run_id)


def test_ai_engine_structured_records_a_row_for_every_call():
    """`get_llm()` đã bị gỡ khi `ai_engine` thay LangChain bằng SDK openai.
    Chỗ nối mới nằm ở `structured.py` — bộ ghi có tồn tại mà không được gọi
    thì bảng vẫn rỗng, đúng số phận của `RAGTrace`/`LLMUsageEvent`."""
    source = Path("src/services/core/ai_engine/structured.py").read_text(encoding="utf-8")

    assert "record_llm_call" in source
    # Cả nhánh hỏng lẫn nhánh thành công đều phải ghi: một lần gọi hỏng vẫn
    # tốn thời gian và vẫn là một lần gọi.
    assert source.count("record_llm_call(") == 2
    assert "success=False" in source and "success=True" in source


def test_ai_engine_chat_stream_asks_the_gateway_for_usage():
    """Luồng stream không trả `usage` trừ khi hỏi. Thiếu `stream_options` thì
    mọi lần chat đều ghi 0 token mà không có dấu hiệu gì."""
    source = Path("src/services/core/ai_engine/chat_stream.py").read_text(encoding="utf-8")

    assert 'stream_options={"include_usage": True}' in source
    # 2 in the main streaming function (success + failure) + 2 in
    # generate_followup_suggestions (success + failure) -- see that
    # function's docstring for why the follow-up-chip call is recorded too.
    assert source.count("record_llm_call(") == 4


def test_record_llm_call_writes_a_row_and_commits_it():
    org_id = f"org_engine_{uuid.uuid4().hex[:8]}"
    record_llm_call(
        feature="course_complex",
        model="pro/gpt-5.6-terra",
        input_tokens=120,
        output_tokens=340,
        latency_ms=1500,
        success=True,
        organization_id=org_id,
    )

    db = SessionLocal()
    try:
        row = db.query(models.AIUsage).filter_by(organization_id=org_id).one()
        assert row.feature == "course_complex"
        assert (row.input_tokens, row.output_tokens) == (120, 340)
        assert row.latency_ms == 1500
        assert row.success is True
    finally:
        db.query(models.AIUsage).filter_by(organization_id=org_id).delete()
        db.commit()
        db.close()


def test_tokens_from_openai_usage_returns_zeros_when_the_gateway_sent_none():
    """Gateway không hỗ trợ `include_usage` thì `usage` là None. Số lần gọi và
    độ trễ vẫn đúng; riêng token thiếu — ghi 0 chứ không được nổ."""
    assert tokens_from_openai_usage(None) == (0, 0)


@pytest.mark.parametrize("tokens", [(0, 0), (5, 0)])
def test_zero_token_runs_are_still_recorded(tokens):
    """Một lần gọi trả về rỗng vẫn tốn thời gian và vẫn là một lần gọi. Bỏ qua
    nó là làm sai chính con số "gọi bao nhiêu lần" mà báo cáo cần."""
    org_id = f"org_z_{uuid.uuid4().hex[:8]}"
    handler = AIUsageCallback(feature="planner", organization_id=org_id, user_id=None)
    run_id = uuid.uuid4()

    handler.on_chat_model_start({}, [[]], run_id=run_id)
    handler.on_llm_end(
        _llm_result(input_tokens=tokens[0], output_tokens=tokens[1]), run_id=run_id
    )

    row = _row_for(org_id)
    assert row.input_tokens == tokens[0]
    assert row.output_tokens == tokens[1]


def test_every_llm_call_site_names_its_feature():
    """Cột `feature` là trục nhóm của báo cáo "tính năng nào tốn nhất". Một
    chỗ gọi quên gắn nhãn không làm hỏng gì thấy được — nó chỉ lặng lẽ đổ vào
    ô "unattributed" và làm báo cáo sai. Kiểm tĩnh ở đây để chỗ gọi mới thêm
    sau này cũng bị chặn, chứ không chỉ 11 chỗ hiện có.

    Dùng `ast` chứ không grep: nhiều docstring trong `src/` nhắc tới `get_llm()`
    như văn xuôi, grep sẽ báo nhầm chúng thành lỗi.
    """
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "src"
    offenders: list[str] = []
    for path in src.rglob("*.py"):
        if path.name == "llm.py":
            continue  # nơi định nghĩa chính hàm này
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name != "get_llm":
                continue
            if not any(kw.arg == "feature" for kw in node.keywords):
                offenders.append(f"{path.relative_to(src)}:{node.lineno}")

    assert offenders == [], "get_llm() gọi mà không nêu feature: " + ", ".join(offenders)


def test_the_callback_falls_back_to_the_actor_of_the_current_request():
    """Cả 11 chỗ gọi LLM đều nằm trong hàm helper không cầm `user` trong tay
    (`_from_llm`, `_generate_with_llm`, ...). Luồn org/user qua 11 chữ ký hàm
    chỉ để đo đạc là cái giá quá đắt — lấy từ ngữ cảnh request thay vào đó.

    Không có bước này thì `organization_id` sẽ luôn NULL, và bảng mới lặp lại
    đúng số phận của `LLMUsageEvent`: có cột, không ai điền.
    """
    from src.security.request_context import actor_org_id_var, actor_user_id_var

    org_id = f"org_ctx_{uuid.uuid4().hex[:8]}"
    org_token = actor_org_id_var.set(org_id)
    user_token = actor_user_id_var.set("user_ctx")
    try:
        handler = AIUsageCallback(feature="qa_answer")
        run_id = uuid.uuid4()
        handler.on_chat_model_start({}, [[]], run_id=run_id)
        handler.on_llm_end(_llm_result(input_tokens=3, output_tokens=4), run_id=run_id)
    finally:
        actor_org_id_var.reset(org_token)
        actor_user_id_var.reset(user_token)

    row = _row_for(org_id)
    assert row.user_id == "user_ctx"


def test_an_explicit_actor_still_wins_over_the_request_context():
    from src.security.request_context import actor_org_id_var

    org_token = actor_org_id_var.set("org_from_context")
    explicit = f"org_exp_{uuid.uuid4().hex[:8]}"
    try:
        handler = AIUsageCallback(feature="qa_answer", organization_id=explicit)
        run_id = uuid.uuid4()
        handler.on_chat_model_start({}, [[]], run_id=run_id)
        handler.on_llm_end(_llm_result(input_tokens=1, output_tokens=1), run_id=run_id)
    finally:
        actor_org_id_var.reset(org_token)

    row = _row_for(explicit)
    assert row.organization_id == explicit


@pytest.mark.asyncio
async def test_resolving_the_current_user_publishes_them_as_the_ai_usage_actor(client):
    """Chốt chặn duy nhất mọi route đi qua là `AuthService.get_current_user`.
    Đặt ngữ cảnh ở đó thì không route nào phải nhớ làm việc này."""
    from src.api.auth import get_auth_service, get_org_invite_service
    from src.config import get_settings
    from src.db.models import UserRole
    from src.security.request_context import actor_org_id_var, actor_user_id_var
    from src.services.core.notification_service import NotificationService
    from tests.support.semester_practice_fixtures import ensure_org, ensure_user, login

    suffix = uuid.uuid4().hex[:6]
    org_id = ensure_org(slug=f"ctx-org-{suffix}", name="Context Org")
    email = f"ctx.{suffix}@test.local"
    user_id = ensure_user(email=email, org_id=org_id, role=UserRole.ADMIN)
    token = await login(client, email)

    actor_org_id_var.set(None)
    actor_user_id_var.set(None)

    db = SessionLocal()
    try:
        settings = get_settings()
        invites = get_org_invite_service(db, settings, NotificationService(settings))
        auth_service = get_auth_service(db, settings, invites)
        await auth_service.get_current_user(token)
    finally:
        db.close()

    assert actor_org_id_var.get() == org_id
    assert actor_user_id_var.get() == user_id


def test_constructor_callbacks_survive_with_structured_output(monkeypatch):
    """Toàn bộ thiết kế D1 đặt cược vào một giả định: callback gắn lúc tạo
    client vẫn bắn khi người gọi bọc thêm `.with_structured_output(...)`.

    Nếu giả định sai thì 8/11 chỗ gọi im lặng không ghi gì — bảng gần rỗng mà
    không có lỗi nào. Chứng minh bằng model giả của chính langchain-core: cơ
    chế callback nằm ở `BaseChatModel`, dùng chung với `ChatGoogleGenerativeAI`.
    """
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage as _AIMessage

    # Đây là test duy nhất chạy model thật qua runtime LangChain. `.env` của
    # dự án bật `LANGCHAIN_TRACING_V2=true` với key giả, nên nếu không tắt ở
    # đây thì mỗi lần chạy suite sẽ POST hụt sang api.smith.langchain.com và
    # in một trang traceback 403 — test phải không phụ thuộc mạng.
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    monkeypatch.setenv("LANGSMITH_TRACING", "false")

    org_id = f"org_wso_{uuid.uuid4().hex[:8]}"
    handler = AIUsageCallback(feature="qa_answer", organization_id=org_id)
    reply = _AIMessage(
        content='{"answer": "ok"}',
        usage_metadata={"input_tokens": 77, "output_tokens": 11, "total_tokens": 88},
    )
    model = GenericFakeChatModel(messages=iter([reply]), callbacks=[handler])

    model.invoke("bất kỳ câu hỏi nào")

    row = _row_for(org_id)
    assert row.input_tokens == 77
    assert row.output_tokens == 11
