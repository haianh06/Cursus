from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


def get_correlation_id() -> str | None:
    return correlation_id_var.get()

# Ai đang gọi, dùng cho việc quy chi phí AI về tổ chức/người dùng
# (`AIUsageCallback`, src/services/core/ai_usage_recorder.py). Đặt tại một chốt
# chặn duy nhất — `AuthService.get_current_user` — thay vì luồn qua chữ ký của
# 11 hàm helper gọi LLM, vì không hàm nào trong số đó cầm `user` trong tay.
#
# Không rò giữa các request: mỗi request chạy trong task riêng và task chỉ
# COPY context của cha lúc tạo, giá trị đặt bên trong không truyền ngược ra.
actor_org_id_var: ContextVar[str | None] = ContextVar("actor_org_id", default=None)
actor_user_id_var: ContextVar[str | None] = ContextVar("actor_user_id", default=None)
