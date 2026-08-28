"""Đơn giá LLM dùng để ước tính chi phí cho màn "Chi phí AI" (PLO 5).

Tách thành module riêng thay vì nhét vào `config.py` là có chủ đích. ADR-002
đã ghi thẳng bài học của dự án này: *"không hardcode tên/giá model version cụ
thể quá lâu mà không có kế hoạch re-verify"* — dòng `gemini-1.5-*` và
`text-embedding-004` trong bản docs đầu tiên đã ngừng hoạt động thật chỉ vài
tháng sau. Một file riêng, có `PRICING_AS_OF` và `PRICING_SOURCE` ngay đầu
file, là chỗ duy nhất phải sửa khi giá đổi — và tự nó nói cho người đọc biết
số liệu cũ tới mức nào.

**Quy tắc quan trọng nhất ở đây: model không có trong bảng thì KHÔNG đoán giá.**
`estimate_cost_usd()` trả `None`, và tầng trên đếm riêng số lần gọi đó để UI
nói rõ "N lần gọi chưa có đơn giá". Điền một con số phỏng đoán rồi để nó hiện
lên màn hình quản trị chính là kiểu lỗi mà ràng buộc "không tự bịa số liệu"
(`docs/archive/planning-v2/roles/CHUNG_admin.md` mục 2, ý 2) nhắm tới — số sai
mà trông như số thật còn tệ hơn không có số.
"""

from __future__ import annotations

# Ngày đối chiếu bảng giá bên dưới với trang giá chính thức. Đổi giá thì đổi
# luôn ngày này — UI hiện nó ra trong `method_note` để người xem tự đánh giá
# số liệu đã cũ chưa. `None` = chưa đối chiếu lần nào, UI nói thẳng điều đó
# thay vì hiện một ngày trống rỗng.
PRICING_AS_OF: str | None = "28/08/2026"
PRICING_SOURCE = "https://ai.google.dev/gemini-api/docs/pricing"

# model -> (USD mỗi 1 triệu input token, USD mỗi 1 triệu output token)
#
# Giá bậc TRẢ PHÍ (paid tier) đối chiếu ngày 27/08/2026 tại PRICING_SOURCE.
# Hai lưu ý khi đọc con số ra:
#
#  1. Nếu project đang chạy trên free tier thì hoá đơn thật là 0 đồng — con
#     số ở đây là "nếu tính theo giá niêm yết thì tốn bằng này", đúng như
#     `method_note` nói. Đây là thước đo mức tiêu thụ, không phải hoá đơn.
#  2. Google niêm yết hai bậc cho dòng 3.x: bậc hiện tại (tới 31/12/2026) và
#     bậc cao hơn từ 01/01/2027. Ở đây lấy bậc HIỆN TẠI. Qua năm phải sửa —
#     đó chính là lý do `PRICING_AS_OF` tồn tại.
#
# `gemini-1.5-flash` và `gemini-2.0-flash-lite` (hai fallback khai trong
# `config.py`) KHÔNG còn trên trang giá — khớp với ghi chú sẵn có ở
# `config.py` rằng chúng không còn khả dụng. Cố ý không điền: gọi trúng chúng
# thì báo "chưa có đơn giá" thay vì gán một con số bịa.
PRICES_USD_PER_MILLION: dict[str, tuple[float, float]] = {
    # ── Gemini ──────────────────────────────────────────────────────────
    # Giữ lại dù `ai_engine` đã chuyển sang OpenAI: bảng `ai_usage` khoá theo
    # tên model, nên các hàng ghi trước lúc chuyển vẫn tính đúng giá của
    # chúng. Xoá đi là làm lịch sử chi phí mất một mảng mà không báo gì.
    "gemini-3.6-flash": (0.75, 3.75),
    "gemini-embedding-001": (0.15, 0.0),
    # ── OpenAI (đường đang chạy sau khi gộp develop) ─────────────────────
    # Giá niêm yết đối chiếu 28/08/2026 tại developers.openai.com/api/docs/pricing.
    # Đây là hai model `ai_engine` định tuyến tới (`ai_engine/routing.py`):
    # terra cho việc nặng, luna cho việc nhẹ.
    "gpt-5.6-terra": (2.00, 12.00),
    "gpt-5.6-luna": (0.20, 1.20),
    # Bậc rẻ hơn, dùng cho route LIGHT lúc dev/test.
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-4o-mini": (0.15, 0.60),
    # Cùng hai model đó khi gọi qua gateway tương thích OpenAI — tiền tố
    # "pro/" là do gateway đặt, không phải model khác. **Giá ở đây là giả
    # định gateway thu đúng giá niêm yết của OpenAI**; gateway hoàn toàn có
    # thể tính thêm phí. Ai chạy qua gateway phải hỏi bên vận hành rồi sửa
    # lại hai dòng này — để nguyên là chấp nhận một giả định chưa kiểm.
    "pro/gpt-5.6-terra": (2.00, 12.00),
    "pro/gpt-5.6-luna": (0.20, 1.20),
}


def normalize_model(model: str) -> str:
    """`AIUsageCallback` lấy tên model từ `llm_output` của provider, nơi có thể
    trả về "models/gemini-3.6-flash" hoặc "gemini-3.6-flash" tuỳ đường gọi.
    Chuẩn hoá để hai dạng đó không thành hai dòng khác nhau trong báo cáo."""
    return model.strip().removeprefix("models/").lower()


def price_for(model: str) -> tuple[float, float] | None:
    """Đơn giá của model, hoặc `None` nếu chưa khai báo — không phỏng đoán."""
    return PRICES_USD_PER_MILLION.get(normalize_model(model))


def estimate_cost_usd(model: str, input_tokens: int, output_tokens: int) -> float | None:
    """Chi phí ước tính USD, hoặc `None` khi model chưa có đơn giá.

    `None` khác hẳn `0.0`: `0.0` nghĩa là "đã tính, ra 0 đồng", còn `None`
    nghĩa là "không đủ dữ kiện để tính". Trộn hai thứ này lại sẽ làm tổng chi
    phí thấp hơn thực tế mà không có dấu hiệu gì.
    """
    price = price_for(model)
    if price is None:
        return None
    input_usd, output_usd = price
    return (input_tokens / 1_000_000) * input_usd + (output_tokens / 1_000_000) * output_usd


def priced_models() -> list[str]:
    """Danh sách model đã có đơn giá — UI hiện ra để người xem biết phần chi
    phí đang tính dựa trên những model nào."""
    return sorted(PRICES_USD_PER_MILLION)
