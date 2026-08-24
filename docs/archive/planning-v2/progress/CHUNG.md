# Progress Log — Nguyễn Đức Chung (Admin: F6 Curriculum · F7 KPI)

> **Cách dùng:** tick `[x]` khi việc **đã test thật, chạy được** — không tick khi "code xong nhưng chưa chắc chạy". Commit file này mỗi khi tick thêm. Danh sách việc lấy đúng từ [`../roles/CHUNG_admin.md`](../roles/CHUNG_admin.md) mục 6-7 — không tự thêm/bớt scope ở đây. **Lưu ý:** role của bạn có thêm việc "tự viết backend" mà 2 role kia không có — sprint của bạn không phụ thuộc Job #0 để bắt đầu, chỉ phụ thuộc để chạy thử.

## Sprint 0 — 11/08 (T3)
- [ ] Đã đọc `docs/archive/planning-v2/roles/CHUNG_admin.md` và `docs/frontend/00_AI_CONTEXT_PACK.md`
- [ ] Thiết kế schema request/response cho `src/api/admin.py` (viết docstring/spec, chưa cần chạy được)

## Sprint 0 — 12/08 (T4)
- [ ] Viết code thật `GET /admin/courses` trong `src/api/admin.py`
- [ ] Viết code thật `GET /admin/kpi` (đọc từ `seed_students_SSA101.json`, bắt buộc có `method_note`)
- [ ] Viết `POST /admin/courses`, `DELETE /admin/courses/{code}`
- [ ] Test độc lập bằng backend local (không cần chờ Job #0 merge xong 100%)

## 🎯 Milestone — 13/08 (T5): "1 flow hoàn chỉnh"
- [ ] `AdminConsole.jsx` nối API thật — bảng curriculum không còn hardcode
- [ ] `AdminConsole.jsx` nối API thật — KPI section không còn hardcode, `method_note` luôn hiện
- [ ] `src/api/admin.py` đã đăng ký vào `main.py` (`app.include_router(admin_router, ...)`)

## Sprint 1 — Gate 2 (14/08, T6)
- [ ] Sáng: chỉ sửa lỗi chặn demo, không thêm tính năng mới
- [ ] Xác nhận luồng Admin chạy ổn định trên bản deploy thật

## Sprint 2 — Mốc 3 (15-22/08)
- [ ] Audit Log UI (`GET /audit/events` — API có sẵn, chỉ thiếu UI) hiển thị được ≥5 sự kiện thật
- [ ] Đã thống nhất với Đăng scope Rule Engine (read-only hay thật) — xem `roles/CHUNG_admin.md` mục 5.3
- [ ] Nếu chọn scope "thật": xây `GET`/`PATCH /admin/guardrail-rules`
- [ ] CRUD ingest đầy đủ qua UI (upload tài liệu → `document_ingest_service`)

## Final — 23/08
- [ ] Freeze code, không sửa gì ngoài lỗi chặn demo
- [ ] Đã rượt thử toàn bộ luồng Admin trong kịch bản demo chính

## Definition of Done (gate chất lượng cuối, tick khi chắc chắn — không phải đoán)
- [ ] `src/api/admin.py` tồn tại, có ≥4 endpoint, đăng ký đúng vào `main.py`
- [ ] `KPI` hardcode trong `AdminConsole.jsx` đã bị xoá, `method_note` luôn hiện trong response thật
- [ ] Bảng curriculum phản ánh đúng trạng thái ingest thật, không phải màu ngẫu nhiên
- [ ] Audit log hiện được ≥5 sự kiện thật khi demo
- [ ] Rule Engine ở đúng scope đã thống nhất với Đăng, không hứa UI vượt quá backend
