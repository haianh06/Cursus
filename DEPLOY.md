# Deploy Cursus — production

> **Cập nhật 23/08/2026 — viết lại toàn bộ.** Bản trước mô tả VPS + Docker Compose
> (`docker-compose.prod.yml`, `.env.production.example`) — 2 file đó **đã bị xoá khỏi repo**
> khi phương án deploy thật được chốt lại (xem `docs/decisions/ADR.md` ADR-001/ADR-003/
> ADR-014). File này giờ khớp đúng phương án đang dùng thật: **Vercel (frontend) + Railway
> (backend) + Supabase (Postgres/Auth/Storage)**, deploy thủ công qua CLI, không auto-deploy
> qua GitHub App (lý do: repo chỉ có 1 remote do BTC cấp, xem ADR-003).

## Kiến trúc deploy thật

```
Browser → HTTPS → Vercel (frontend static build, React/Vite)
                      │  REST, cookie cross-site (SameSite=None; Secure)
                      ▼
                   Railway (backend container, FastAPI, Dockerfile multi-stage)
                      │  connection pooler
                      ▼
                   Supabase (Postgres + pgvector extension, Auth chỉ dùng hosting DB —
                             app tự viết JWT+cookie, không dùng Supabase Auth service)
```

`docker-compose.yml` ở gốc repo **chỉ dùng cho dev local** (profile `local-db` cho Postgres/
Redis khi không có Supabase credentials) — không phản ánh kiến trúc production.

## Checklist trước khi deploy thật (thứ tự khuyến nghị)

1. **Đối chiếu `alembic_version` trên Supabase trước** — migration chain hiện đang lệch
   (xem `docs/PROJECT_CONTEXT.md` mục 20 ý 8). Chưa xử lý xong việc này thì `alembic upgrade
   head` từ máy deploy sẽ báo lỗi ngay. Đây là việc cần người có quyền Supabase Dashboard tự
   tay đối chiếu, không tự động hoá được.
2. Nâng Supabase lên gói trả phí (Pro) hoặc có lịch ping định kỳ — free tier tự pause
   project sau 7 ngày không ai truy cập.
3. `DATABASE_URL` dùng đúng **Transaction pooler** (`aws-0-<region>.pooler.supabase.com:5432`),
   **không dùng Direct connection** (`db.<project>.supabase.co`) — direct connection từng
   gây lỗi DNS ngắt quãng lúc dev.
4. Cookie cross-site: set `ACCESS_TOKEN_COOKIE_SAMESITE=none` + `Secure=true` trên Railway —
   mặc định code là `Lax`/`Strict` (đúng cho dev cùng domain), sai domain thật sẽ làm login
   "thành công" nhưng cookie không được gửi lại (bug trông ngẫu nhiên).
5. `CORS_ORIGINS` trỏ đúng domain Vercel thật.
6. `frontend/vercel.json` phải có mặt trên đúng nhánh đang deploy.
7. `VITE_API_URL` bị nhúng cứng vào bundle lúc build — đổi backend URL sau này phải
   rebuild + redeploy frontend, không chỉ đổi biến môi trường runtime.
8. Mock LMS (nếu deploy) cần 1 lượt deploy CLI riêng (domain/service khác Cursus), env
   riêng cho `MOCK_LMS_ADMIN_USER`/`MOCK_LMS_ADMIN_PASSWORD_HASH` và OAuth signing key.

Danh sách đầy đủ + giải thích từng rủi ro: `docs/PROJECT_CONTEXT.md` mục 20.

## 1. Biến môi trường bắt buộc (Railway — backend)

| Biến | Ví dụ / ghi chú |
|---|---|
| `DATABASE_URL` | Connection string Supabase, **pooler** (mục checklist #3) |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | Domain Vercel thật, vd `https://cursus.vercel.app` |
| `ACCESS_TOKEN_COOKIE_SAMESITE` | `none` |
| `ACCESS_TOKEN_COOKIE_SECURE` | `true` |
| `GOOGLE_API_KEY` | Key Gemini thật — xem `docs/PENDING_DECISIONS.md` #3 trước khi deploy (rà tên model đã khai tử) |
| `EMAIL_PROVIDER` | `smtp` nếu cần gửi email thật, `none` nếu demo không cần |

## 2. Deploy backend (Railway)

```bash
railway login
railway link          # chọn đúng project Railway đã tạo trước
railway up            # build + deploy từ Dockerfile hiện có, không cần sửa gì thêm
```

Railway tự chạy `Dockerfile` đa giai đoạn có sẵn ở gốc repo — không cần file compose riêng
cho production.

## 3. Deploy frontend (Vercel)

```bash
cd frontend
vercel --prod
```

Đảm bảo `VITE_API_URL` trỏ đúng domain Railway thật **trước khi build** (biến này bake cứng
vào bundle, xem checklist #7).

## 4. Deploy Mock LMS (nếu cần demo tích hợp hệ thống ngoài)

Mock LMS (`mock-lms/`) là 1 app FastAPI hoàn toàn tách biệt, tự deploy riêng (không chung
Dockerfile/service với Cursus):

```bash
cd mock-lms
railway up   # hoặc platform tương đương — chưa có script CLI riêng, làm thủ công lần đầu
```

Xem `mock-lms/README.md` cho biến môi trường riêng (`MOCK_LMS_ADMIN_USER`, `MOCK_LMS_ADMIN_PASSWORD_HASH`).

## 5. Smoke test sau khi deploy

- Đăng nhập cả 3 role qua domain thật (không phải localhost).
- Gọi `GET /api/v1/health` (hoặc endpoint tương đương) qua domain Railway.
- Thử 1 câu hỏi Cursus Assistant thật — xác nhận trích dẫn nguồn hiện đúng.
- Nếu deploy cả Mock LMS: sửa 1 deadline, xác nhận Cursus đọc đúng qua source precedence.

## Không dùng cách nào khác

Đã cân nhắc và loại các phương án sau, xem ADR-014 (`docs/decisions/ADR.md`) cho lý do đầy đủ:
Cloudflare Workers (Python/FastAPI support còn giới hạn), Render (chi phí thật cao hơn quảng
cáo), Fly.io, Hostinger VPS, Firebase (không hỗ trợ pgvector), Netlify (chỉ đáng cân nhắc nếu
ngân sách là ưu tiên, Vercel vẫn ổn cho quy mô hiện tại).
