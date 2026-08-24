# Progress Log — Nguyễn Anh Bình (Giảng viên: F4 Dashboard · F5 Risk + HITL)

> **Cách dùng:** tick `[x]` khi việc **đã test thật, chạy được** — không tick khi "code xong nhưng chưa chắc chạy". Commit file này mỗi khi tick thêm. Danh sách việc lấy đúng từ [`../roles/BINH_instructor.md`](../roles/BINH_instructor.md) mục 6-7 — không tự thêm/bớt scope ở đây.

## Sprint 0 — 11/08 (T3)
- [ ] Đã đọc `docs/archive/planning-v2/roles/BINH_instructor.md` và `docs/frontend/00_AI_CONTEXT_PACK.md`
- [ ] Polish UI hiện tại theo `docs/frontend/08_SCREEN_CONSISTENCY_CHECKLIST.md`
- [ ] Phác thảo wireframe/JSX rỗng cho Risk Case Detail (chưa cần API)

## Sprint 0 — 12/08 (T4)
- [ ] Viết `frontend/src/lib/api.js` phần Instructor (dashboard/risks/intervention)
- [ ] Bắt đầu build UI Risk Case Detail (Drawer, 400px desktop)

## 🎯 Milestone — 13/08 (T5): "1 flow hoàn chỉnh"
- [ ] F4 nối xong: `GET /instructor/dashboard` thật thay `DASH_DATA` hardcode
- [ ] F5 nối xong: `GET /instructor/risks` hiển thị đúng danh sách SV nguy cơ
- [ ] F5/HITL nối xong: `POST /instructor/risks/{id}/intervention`
- [ ] Test thật: xác nhận bấm "Can thiệp" KHÔNG gửi bất kỳ request/notification nào khác tới SV

## Sprint 1 — Gate 2 (14/08, T6)
- [ ] Sáng: chỉ sửa lỗi chặn demo, không thêm tính năng mới
- [ ] Xác nhận luồng GV chạy ổn định trên bản deploy thật

## Sprint 2 — Mốc 3 (15-22/08)
- [ ] Risk Case Detail hoàn chỉnh: lịch sử hoàn thành + lý do + ô ghi chú can thiệp
- [ ] (Nếu còn giờ) Phối hợp Hải Anh + Đăng xây endpoint Appeal (`roles/BINH_instructor.md` mục 5.3)
- [ ] Quyết định cùng Đăng: giữ hay bỏ hàng chờ Appeal ở Gate 2 nếu backend chưa kịp

## Final — 23/08
- [ ] Freeze code, không sửa gì ngoài lỗi chặn demo
- [ ] Đã rượt thử toàn bộ luồng GV trong kịch bản demo chính

## Definition of Done (gate chất lượng cuối, tick khi chắc chắn — không phải đoán)
- [ ] `DASH_DATA` hardcode đã bị xoá, dữ liệu 100% từ API
- [ ] Nút "Đánh dấu đã can thiệp" xác nhận không gửi gì tới SV (test thực nghiệm, không chỉ đọc code)
- [ ] Dashboard không hiện tên/nội dung chat riêng SV ở màn tổng quan
- [ ] Risk Case Detail hiển thị được ít nhất: lịch sử hoàn thành, lý do cụ thể, ô ghi chú can thiệp
- [ ] Test thật: từ tài khoản demo GV, thấy đúng SV Huy/Mai theo seed data
