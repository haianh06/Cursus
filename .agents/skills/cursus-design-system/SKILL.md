---
name: cursus-design-system
description: Dùng skill này khi user yêu cầu thiết kế, code, hoặc chỉnh sửa bất kỳ màn hình UI nào của sản phẩm Cursus — bao gồm Student Home, Reflection, Instructor Home, Admin Console, hoặc bất kỳ component nào (button, card, chart, chat message, form). Kích hoạt khi thấy từ khoá: "thiết kế", "UI", "màn hình", "giao diện", "component", "Cursus".
---

# Cursus Design System — "Ink & Citrine"

> Nguồn chính thức: `docs/archive/planning-v2/08-Cursus-UI-UX-Master-Spec.md`. Nếu nội dung skill này và file `08` lệch nhau, `08` luôn thắng — chạy `/sync-docs` để đồng bộ lại. KHÔNG dùng lại bảng màu tím/indigo/mascot robot của bản nháp cũ (`ui-ux-brief.md`) — đã bị chính team đánh giá là "giống công thức phối màu AI-mặc-định" và thay thế chính thức bằng bảng dưới đây.

## Bối cảnh & định vị (đọc trước khi thiết kế bất kỳ gì)

Cursus là AI academic companion cho SV Software Engineering (FPT University), theo chu trình Plan → Do → Reflect. 3 vai trò: `student` (Đăng), `instructor` (Cô Hương), `admin` (Thầy Nam). Đối thủ (Canvas IgniteAI, Shovel, ChatGPT Study Mode, Gemini Guided Learning, AI Hay) đa phần là **chat-first, một lượt hỏi-đáp**. Cursus phải "cảm" được qua UI là **1 công cụ quản trị workflow học tập có cấu trúc**, KHÔNG phải một chatbot khác — vì vậy KHÔNG dùng bong bóng chat chiếm toàn màn hình, ưu tiên card/bảng/citation tường minh.

## Bảng màu chính xác (dùng đúng hex, không tự đổi sắc độ)

```
--ink: #15181C            /* chữ chính, đen ấm */
--ink-secondary: #5B5647  /* chữ phụ */
--ink-tertiary: #948E7C   /* chữ mờ, placeholder */
--paper: #FAF8F3          /* nền toàn trang, trắng ngà ấm */
--surface: #FFFFFF        /* nền card */
--border: #E6E2D8
--border-strong: #D6D1C2
--accent: #B7791F         /* Citrine — accent DUY NHẤT: CTA, citation chip, link, focus ring */
--accent-hover: #9C6414
--accent-soft: #F7ECD6
--success: #2F6B3A
--success-soft: #E6EFE2
--warning: #B7791F        /* CỐ Ý trùng accent — code thành var(--accent), không hardcode lại hex */
--warning-soft: #F7ECD6
--danger: #9B3B34         /* brick đỏ trầm, KHÔNG phải đỏ tươi */
--danger-soft: #F6E6E4
```

Chỉ dùng 3 màu trạng thái (success/warning/danger) đúng ngữ nghĩa, không trang trí.

## Typography

- Heading: **Source Serif 4** (fallback Georgia), weight 500-600 — cảm giác "tài liệu/xuất bản đáng tin".
- Body/UI: **Inter**, weight 400/500/600/700.
- **Số liệu + citation + mã môn (chữ ký thị giác sản phẩm, nhất quán tuyệt đối):** **IBM Plex Mono** — dùng cho MỌI citation label, `chunk_id`, % định lượng, mã môn (`SSA101`). Ẩn dụ: "số đo được, không phải ước lượng."

## Hình khối & chuyển động

- Bo góc: 6px (badge/input nhỏ), 8px (card/nút). KHÔNG bo tròn kiểu "AI mềm mại" (không 16px+, không pill-shape cho card).
- Viền (`border`) là ngôn ngữ phân tách chính, shadow rất nhẹ chỉ tách lớp nổi, không dùng shadow đậm.
- Tôn trọng `prefers-reduced-motion`.
- Focus ring: `outline: 2px solid var(--accent)` khi Tab, dùng `:focus-visible` — KHÔNG hiện khi click chuột.

## Icon

Bộ icon line-style nhất quán (ví dụ **Lucide**) — không dùng emoji làm icon chức năng. Emoji CHỈ dùng trong copy văn bản khi ngữ cảnh cho phép (ví dụ empty state vui: "Không có SV nào cần chú ý tuần này 🎉").
> Lưu ý: repo này đã chốt stack React (xem AGENTS.md mục 1) nên khi code thật, dùng package `lucide-react` cụ thể — nhưng khi mô tả design system ở cấp ý định (như skill này), giữ tên chung "Lucide" để không tự khoá framework ngoài ý muốn.

## Component states cụ thể

- **Task card sắp tới hạn (<48h):** border trái tông `warning`.
- **Tin nhắn Q&A bị guardrail chặn:** viền + icon tông `danger`, khác hẳn tin nhắn thường, kèm nút "Yêu cầu xem xét lại".
- **Nút "Đánh dấu đã can thiệp" (Instructor, khoảnh khắc HITL):** trạng thái sau khi bấm phải khác RÕ RỆT so với trước khi bấm — không chỉ đổi chữ nhỏ.
- **Curriculum table (Admin):** đã nạp → badge tông `accent` kèm số chunk; chưa nạp → badge tông neutral/xám.
- **KPI card (Admin):** `method_note` LUÔN hiện cùng lúc với 2 số lớn, không được tách rời hay ẩn.
- **Instructor Home:** KHÔNG hiển thị nội dung phản tư cá nhân nguyên văn của SV (privacy/FERPA-mindset).

## Data shape & mock layer

Xem đầy đủ envelope API ở mục 6 file `08` (`docs/archive/planning-v2/08-...md`) — đây là hợp đồng UI-consumption; nếu `02-SRS.md`/`06-hạ tầng` mô tả khác, coi `02`/`06` là nguồn backend thật, `08` chỉ phản ánh góc nhìn UI. Build mock data layer khớp đúng shape này để khi backend sẵn sàng chỉ cần đổi 1 chỗ cấu hình, không viết lại UI. Dữ liệu mẫu: môn `SSA101`, sĩ số 12, `class_avg_completion_by_week: [0.9, 0.79, 0.73, 0.7]`, KPI `78%` vs `45%`.

## Trạng thái Loading/Empty/Success/Error

Dùng ĐÚNG copy đã định nghĩa ở mục 5 file `08` cho từng khối (Task list, Q&A, Reflection, Dashboard chart, Alert list, hàng đợi xem xét, Curriculum table, KPI card) — không tự đặt lại câu khác.
