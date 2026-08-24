# Progress Log — Trịnh Hải Đăng (Nhóm trưởng: Hạ tầng · Auth · Khung frontend · Data · Canvas ảo)

> **Cách dùng:** tick `[x]` khi việc **đã test thật, chạy được** — không tick khi "code xong nhưng chưa chắc chạy". Commit file này mỗi khi tick thêm. Danh sách việc lấy đúng từ [`../roles/DANG_infra-auth-frontend.md`](../roles/DANG_infra-auth-frontend.md) mục 6-7 — không tự thêm/bớt scope ở đây. **Việc mục "Sprint 0 — 11/08" và "12/08" (Job #0) chặn cả 3 người còn lại — ưu tiên tuyệt đối.**

## Sprint 0 — 11/08 (T3)
- [x] `src/` đã có sẵn trên nhánh hiện tại (merge trước đó, commit `fb6ea0b`) — không cần copy lại từ `origin/chung`
- [x] Cấu hình `.env`: `DATABASE_URL` Postgres thật (Supabase, qua Session Pooler vì host direct bị IPv6-only) — verify bằng cách ghi/đọc dữ liệu thật 11/08
- [ ] `REDIS_URL` — chưa cấu hình (chưa cần gấp, `redis_url` mặc định `None` vẫn chạy được)
- [ ] `GOOGLE_API_KEY` (Gemini) — chưa verify trong phiên làm việc này, kiểm tra lại trước Gate 2

## Sprint 0 — 12/08 (T4)
- [x] Chạy migration (`alembic upgrade head`) — verify thật lên Supabase Postgres 11/08
- [x] `uvicorn src.main:app` chạy được, `/docs` liệt kê đủ 7 router — verify bằng `openapi.json` 11/08
- [x] `POST /auth/login` trả JWT thật — verify bằng curl thật (register→login→me→refresh→logout, cả happy path lẫn lỗi: trùng email 409, sai mật khẩu 401, mật khẩu yếu bị chặn) — **Job #0 coi như xong**
- [x] `frontend/src/lib/api.js` đã có sẵn, đúng pattern cookie + CSRF
- [x] 6 màn Auth đã nối API thật từ trước — phát hiện + sửa 3 bug chặn luồng thật khi test 11/08: (1) link xác thực email sai port/path, (2) route `/onboarding` chặn nhầm user Google lần đầu, (3) race condition đọc session Supabase quá sớm sau redirect Google

## 🎯 Milestone — 13/08 (T5): "1 flow hoàn chỉnh"
- [x] Auth thật hoạt động đầu-cuối bằng email/password — verify bằng curl 11/08 (đăng ký → đăng nhập → `/auth/me` → refresh → logout, đều đúng). **Cập nhật 12/08:** luồng "đăng ký" ở đây đã đổi — không còn tự đăng ký mở, `/auth/register` nay bắt buộc `invite_token` (`ADR-007`). Đã verify lại end-to-end bằng script thật sau khi đổi: đăng ký không token → 422, demo-session 3 role → đúng org sandbox, admin FPT thật tạo/xem/thu hồi invite → đúng (xem `10-Cursus-Auth-Onboarding-Sandbox-Spec.md`).
- [ ] Auth thật qua Google — **đổi 12/08:** Google chỉ xác thực tài khoản đã được mời (không tự tạo tài khoản mới nữa, đóng lỗ hổng tự đăng ký ẩn). Vẫn **chờ Đăng tự test trên trình duyệt (cửa sổ InPrivate) để xác nhận cuối cùng**
- [ ] Hỗ trợ sửa lỗi tích hợp phát sinh cho Hải Anh/Chung/Bình trong ngày
- [ ] Deploy thử lên Railway (backend) + Vercel (frontend) — **chưa làm**

## Sprint 1 — Gate 2 (14/08, T6)
- [ ] Sáng: freeze code, chỉ sửa lỗi chặn demo
- [ ] Có URL deploy truy cập được từ máy khác (không phải "chạy trên máy tôi")
- [ ] Đã review ít nhất 1 PR của mỗi người trong 3 người còn lại

## Sprint 2 — Mốc 3 (15-22/08)
- [ ] Bật MFA/email-verify thật (đã có sẵn từ Job #0, chỉ cần bật UI)
- [ ] Ingest mở rộng ~10 môn ưu tiên năm 1-2
- [ ] Kiến trúc chịu tải: API key rotation, rate-limit, cache, circuit breaker (`02-SRS.md` mục 4.2)
- [ ] Xác nhận với team có cần load test k6 hay không, nếu cần thì thực hiện

## Final — 23/08
- [ ] Freeze code, rượt kịch bản demo (chính + lỗi) lần cuối cùng cả team
- [ ] Xác nhận `.env`/secret không lọt vào git trước khi nộp bài

## Definition of Done (gate chất lượng cuối, tick khi chắc chắn — không phải đoán)
- [ ] `uvicorn src.main:app` chạy được từ nhánh tích hợp chính, `/docs` liệt kê đủ 7 router
- [ ] `POST /auth/login` trả JWT thật, `GET /auth/me` trả đúng role
- [ ] Cả 6 màn auth nối API thật, không còn màn nào dùng demo-login cứng
- [ ] Có URL deploy truy cập được từ máy khác
- [ ] `.env`/secret không lọt vào git (kiểm tra `git status` trước mỗi commit)
