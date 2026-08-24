# Progress Log — Nguyễn Hải Anh (Sinh viên: F2 Plan · F3 Q&A · Reflect)

> **Cách dùng:** tick `[x]` khi việc **đã test thật, chạy được** — không tick khi "code xong nhưng chưa chắc chạy". Commit file này mỗi khi tick thêm (không cần PR riêng, gộp chung commit code). Đây là bằng chứng tiến độ thay cho báo cáo miệng — nhóm trưởng chạy `python scripts/progress_report.py` bất kỳ lúc nào để xem % mà không cần hỏi bạn.
>
> Danh sách việc lấy đúng từ [`../roles/HAIANH_student.md`](../roles/HAIANH_student.md) mục 6-7 — không tự thêm/bớt scope ở đây, chỉ tick tiến độ. Nếu việc thực tế phát sinh khác, sửa cả 2 file cho khớp.

## Sprint 0 — 11/08 (T3)
- [ ] Đã đọc `docs/archive/planning-v2/roles/HAIANH_student.md` và `docs/frontend/00_AI_CONTEXT_PACK.md`
- [ ] Thêm trạng thái Error còn thiếu ở khối Plan (`StudentHome.jsx`)
- [ ] Kiểm tra lại UI hiện tại theo `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md`
- [ ] Xác nhận i18n đủ 2 ngôn ngữ cho mọi chuỗi hiện có

## Sprint 0 — 12/08 (T4)
- [ ] Viết `frontend/src/lib/api.js` phần Student (endpoint plans/qa/student) — chưa cần chạy được nếu Job #0 chưa xong
- [ ] Test thử qua Swagger UI (`/docs`) ngay khi Đăng báo backend chạy

## 🎯 Milestone — 13/08 (T5): "1 flow hoàn chỉnh"
- [ ] F2 nối xong: `POST /plans/generate` thật thay cho `setTimeout` giả lập
- [ ] F2: `POST /plans/accept` khi SV xác nhận kế hoạch
- [ ] F2: `PATCH /plans/tasks/{id}` cho toggle/xoá task
- [ ] F3 nối xong: `POST /qa` thật, xoá đoạn regex guardrail tự chế ở frontend
- [ ] Test thật câu "giải hộ em bài này" trên UI đã nối API → thấy bubble đỏ đúng từ backend

## Sprint 1 — Gate 2 (14/08, T6)
- [ ] Sáng: chỉ sửa lỗi chặn demo, không thêm tính năng mới
- [ ] Xác nhận luồng SV chạy ổn định trên bản deploy thật (không chỉ local)

## Sprint 2 — Mốc 3 (15-22/08)
- [ ] Reflect nối API thật: `GET /student/reflections`, `POST /student/reflections/generate`
- [ ] Rà lại toàn bộ theo `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md`
- [ ] (Nếu còn giờ) Phối hợp Bình + Đăng xây endpoint Appeal (`roles/HAIANH_student.md` mục 5.3)
- [ ] (Nếu còn giờ) Đổi accent màu Reflection sang `var(--reflect)` theo gợi ý nâng cấp

## Final — 23/08
- [ ] Freeze code, không sửa gì ngoài lỗi chặn demo
- [ ] Đã rượt thử toàn bộ luồng SV trong kịch bản demo chính

## Definition of Done (gate chất lượng cuối, tick khi chắc chắn — không phải đoán)
- [ ] Không còn `await new Promise(setTimeout(...))` giả lập nào trong `StudentHome.jsx`/`StudentReflection.jsx`
- [ ] Đoạn regex guardrail tự chế ở frontend đã bị xoá hoàn toàn
- [ ] Task/câu trả lời không có `source_label` hiển thị đúng cảnh báo, không bịa nội dung
- [ ] Đủ 4 trạng thái Loading/Empty/Success/Error cho cả khối Plan và khối QA
- [ ] Mọi chuỗi mới có trong `locales/en.js` và `vi.js`
