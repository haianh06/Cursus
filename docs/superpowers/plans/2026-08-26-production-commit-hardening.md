# Production Commit Hardening Plan

**Goal:** Đưa nhánh `haidang2425` về trạng thái có thể kiểm chứng, commit theo phạm vi production và push an toàn lên GitHub.

## Phạm vi thực hiện

- [ ] Loại các tệp curriculum minh hoạ khỏi tập dữ liệu syllabus thật bằng kiểm tra hợp đồng dữ liệu.
- [ ] Chuyển E2E sang luồng sandbox chính thức thay cho tài khoản seed mật khẩu cũ.
- [ ] Loại file tạm, báo cáo test và bản sao `.env` khỏi phạm vi Git.
- [ ] Rà dependency, lint, build, backend tests và toàn bộ Playwright E2E.
- [ ] Rà staged diff và bí mật trước từng commit production.
- [ ] Push `haidang2425` lên `origin` và ghi nhận commit/kiểm thử còn lại.

## Tiêu chí hoàn tất

- Backend test suite không còn lỗi curriculum.
- Frontend lint/build và Playwright E2E đạt.
- Không có secret hoặc artifact tạm trong commit.
- Remote `origin/haidang2425` trỏ tới commit cuối đã kiểm chứng.
