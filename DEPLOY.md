# Deploy Cursus — production

> **Cập nhật 24/08/2026.** Quyết định mới (yêu cầu trực tiếp, ghi đè ADR-014):
> backend deploy lên **Render** thay vì Railway. ADR-014 (`docs/decisions/ADR.md`) từng
> loại Render vì lo cold-start free tier (30-60s) và DB free tier hết hạn sau 30 ngày —
> hai rủi ro đó **vẫn còn nguyên** với phương án này, xem mục "Rủi ro Render free tier"
> bên dưới. `render.yaml` ở gốc repo mô tả service, `autoDeploy: false` giữ đúng tinh
> thần ADR-003 (deploy thủ công, không tự động deploy mỗi lần push).
>
> Ngoài ra: frontend dùng `@supabase/supabase-js` thật cho luồng OAuth onboarding
> (`frontend/src/lib/supabaseClient.js`, `OnboardingScreen.jsx`) — khác với ghi chú cũ
> "không dùng Supabase Auth service". Cần set `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY`
> thật trên Vercel, không chỉ `DATABASE_URL`.

## Kiến trúc deploy thật

```
Browser → HTTPS → Vercel (frontend static build, React/Vite)
                      │  REST, cookie cross-site (SameSite=None; Secure)
                      │  + Supabase Auth trực tiếp (OAuth onboarding)
                      ▼
                   Render (backend container, FastAPI, Dockerfile, autoDeploy: false)
                      │  connection pooler (runtime) / direct connection (migration)
                      ▼
                   Supabase (Postgres + pgvector, Auth cho OAuth onboarding, app vẫn
                             tự phát JWT+cookie cho session sau khi onboarding xong)
```

### Rủi ro Render free tier (chưa được giải quyết, chỉ được ghi nhận lại)

- **Cold start 30-60s**: instance free ngủ sau ~15 phút không có traffic, request đầu
  tiên sau đó chờ backend khởi động lại. Nếu demo có giám khảo/BTC truy cập bất ngờ,
  cân nhắc nâng plan trả phí trước buổi demo, hoặc ping định kỳ (cron ping `/health`).
- **Supabase free tier tự pause** sau 7 ngày không hoạt động (đã ghi ở checklist #2
  bên dưới) — độc lập với Render, vẫn áp dụng.

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

## 0. Tạo project Supabase (Postgres)

```bash
supabase login
supabase orgs list                      # lấy org-id
supabase projects create cursus-prod --org-id <ORG_ID> --db-password '<STRONG_PASSWORD>' --region ap-southeast-1
```

Từ dashboard Supabase (Project Settings → Database → Connection string) lấy 2 chuỗi:
- **Direct/session (port 5432)** — dùng để chạy `alembic upgrade head` (pooler transaction
  mode ở port 6543 hay lỗi với DDL/prepared statements — xem `migrations/env.py`, không có
  code nào tự xử lý khác biệt pooler/direct).
- **Transaction pooler (port 6543)** — dùng làm `DATABASE_URL` runtime trên Render.

Chạy migration từ máy local, trỏ về direct connection:

```bash
DATABASE_URL="postgresql://postgres:<PW>@db.<project-ref>.supabase.co:5432/postgres" alembic upgrade head
```

Từ Project Settings → API, lấy `Project URL` và `anon public key` cho frontend
(`VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` — dùng cho OAuth onboarding, xem
`frontend/src/lib/supabaseClient.js`).

## 1. Biến môi trường bắt buộc (Render — backend)

`render.yaml` ở gốc repo đã khai báo các biến này với `sync: false` (giá trị đặt tay
trong Render Dashboard → service → Environment, không commit vào repo):

| Biến | Ví dụ / ghi chú |
|---|---|
| `DATABASE_URL` | Connection string Supabase, **transaction pooler port 6543** (mục 0) |
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CORS_ORIGINS` | Domain Vercel thật, vd `https://cursus.vercel.app` |
| `GOOGLE_API_KEY` | Key Gemini thật — xem `docs/PENDING_DECISIONS.md` #3 trước khi deploy (rà tên model đã khai tử) |
| `EMAIL_PROVIDER` | `smtp` nếu cần gửi email thật, `none` nếu demo không cần |
| `EMAIL_VERIFICATION_URL_BASE` / `PASSWORD_RESET_URL_BASE` | Domain Vercel thật |

`ACCESS_TOKEN_COOKIE_SAMESITE=none` / `ACCESS_TOKEN_COOKIE_SECURE=true` (và cặp `REFRESH_TOKEN_*`
tương ứng) đã có sẵn giá trị cứng trong `render.yaml` — không cần đặt lại.

## 2. Deploy backend (Render)

Lần đầu (một lần, qua Dashboard — bước OAuth kết nối GitHub không tự động hoá được):

1. Render Dashboard → **New → Blueprint** → chọn repo GitHub hiện tại (`Cursus_demo`) →
   Render đọc `render.yaml` ở gốc repo và tạo service `cursus-backend` (Docker runtime,
   `autoDeploy: false` — không tự deploy mỗi lần push, giữ đúng tinh thần ADR-003).
2. Điền các biến `sync: false` ở mục 1 vào Environment của service.
3. Bấm **Manual Deploy → Deploy latest commit** cho lần deploy đầu tiên.

Từ lần sau, deploy thủ công qua CLI (không cần vào lại dashboard):

```bash
render login
render services list                 # lấy service id của cursus-backend
render deploys create <SERVICE_ID>   # trigger deploy thủ công
```

## 3. Deploy frontend (Vercel)

```bash
cd frontend
vercel login
vercel link
vercel env add VITE_API_URL production        # domain Render thật, vd https://cursus-backend.onrender.com/api/v1
vercel env add VITE_SUPABASE_URL production
vercel env add VITE_SUPABASE_ANON_KEY production
vercel --prod
```

Đảm bảo `VITE_API_URL` trỏ đúng domain Render thật **trước khi build** (biến này bake cứng
vào bundle, xem checklist #7). `frontend/vercel.json` đã có rewrite SPA fallback
(`/(.*) → /index.html`) cho client-side routing của `react-router-dom`.

## 4. Deploy Mock LMS (nếu cần demo tích hợp hệ thống ngoài)

Mock LMS (`mock-lms/`) là 1 app FastAPI hoàn toàn tách biệt, tự deploy riêng (không chung
Dockerfile/service với Cursus):

```bash
cd mock-lms
render login
# Dashboard → New → Web Service → connect repo, root directory `mock-lms/`, Docker/Python
# runtime tương ứng — service + domain riêng, tách khỏi cursus-backend.
```

Xem `mock-lms/README.md` cho biến môi trường riêng (`MOCK_LMS_ADMIN_USER`, `MOCK_LMS_ADMIN_PASSWORD_HASH`).

## 5. Smoke test sau khi deploy

- Đăng nhập cả 3 role qua domain thật (không phải localhost).
- Gọi `GET /health` qua domain Render thật (sau khi cold start free tier, có thể mất 30-60s).
- Thử 1 câu hỏi Cursus Assistant thật — xác nhận trích dẫn nguồn hiện đúng.
- Nếu deploy cả Mock LMS: sửa 1 deadline, xác nhận Cursus đọc đúng qua source precedence.

## Lịch sử: các phương án đã cân nhắc và loại

ADR-014 (`docs/decisions/ADR.md`) từng loại các phương án sau cho **backend**: Railway được
chọn thay Render (Render free tier cold-start 30-60s + DB hết hạn), Cloudflare Workers
(Python/FastAPI support còn giới hạn), Fly.io, Hostinger VPS. Quyết định 24/08/2026 ở đầu file
này **đổi lại sang Render**, chấp nhận rủi ro cold-start/DB-expiry mà ADR-014 đã cảnh báo (xem
"Rủi ro Render free tier" ở trên) — ADR-014 giữ nguyên làm hồ sơ quyết định gốc, không sửa lại.

Cho **frontend**: Firebase (không hỗ trợ pgvector), Netlify (chỉ đáng cân nhắc nếu ngân sách
là ưu tiên, Vercel vẫn ổn cho quy mô hiện tại) — vẫn giữ nguyên, không đổi.
