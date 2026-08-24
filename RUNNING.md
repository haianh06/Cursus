# Hướng dẫn chạy dự án (local)

Dự án gồm **backend** (FastAPI, `src/`) và **frontend** (Vite + React, `frontend/src/`).

Deploy production / VPS: xem [DEPLOY.md](DEPLOY.md) — lưu ý tài liệu đó mô tả hạ tầng
(`docker-compose.prod.yml`, `frontend/Dockerfile`, entrypoint tự `alembic upgrade head`)
**chưa có trong repo hiện tại**, chỉ dùng được sau khi các file đó được thêm vào.

## 1. Yêu cầu

- Python 3.11+ (repo dùng `.venv`)
- Node.js 18+ và npm (frontend)
- Một database Postgres có thể kết nối được — dự án dùng Supabase (xem ADR-001), không
  cần cài Postgres local. Repo **không** có sẵn Postgres/Redis trong Docker Compose (xem mục 4).

## 2. Chạy Backend (FastAPI)

### 2.1. Virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

```bash
source .venv/Scripts/activate
```

Nếu chưa có `.venv`:

```bash
python -m venv .venv
# activate rồi:
pip install -r requirements.txt
```

### 2.2. Biến môi trường

```bash
cp .env.example .env
```

**Bắt buộc** (backend crash ngay lúc start nếu thiếu — không có giá trị mặc định trong `src/config.py`):

- `JWT_SECRET_KEY` — chuỗi ngẫu nhiên tối thiểu 32 ký tự. Tạo nhanh:
  `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- `DATABASE_URL` — connection string Postgres (vd. connection string pooler của Supabase).
  SQLite (`sqlite:///./data/app.db`) cũng chạy được về mặt kỹ thuật (`src/db/connection.py`
  tự nhận diện prefix `sqlite`) nhưng chưa được test với toàn bộ migrations/seed — chỉ dùng
  cho việc thử nhanh, không dùng để phát triển F1–F7 thật.

**Tuỳ chọn:**

- `GOOGLE_API_KEY` — cần để các tính năng gọi Gemini thật hoạt động. Không set thì app vẫn
  khởi động được (mặc định `test-key`) nhưng mọi request chạm tới LLM sẽ lỗi.
- `REDIS_URL` — chỉ dùng cho rate limiting; không set thì middleware tự fallback, không crash.
- `EMAIL_PROVIDER=smtp` + `SMTP_*` — cần nếu muốn gửi email xác thực/quên mật khẩu thật.
  Để `EMAIL_PROVIDER=none` khi dev để khỏi tốn quota SMTP.

### 2.3. Migrate database (nếu DB đang trống hoặc mới tạo)

```bash
alembic upgrade head
```

Kiểm tra đã ở đúng revision mới nhất:

```bash
alembic current
```

Muốn có dữ liệu mock để test UI (courses, users, plans...):

```bash
python seed.py
```

### 2.3b. Tạo tài khoản thật (Cursus không có đăng ký công khai)

Cursus là B2B2C — không ai tự tạo tài khoản được. Có 3 cách tạo tài khoản thật:

1. **Tổ chức mới + Admin đầu tiên (Job #0)** — chạy 1 lần khi triển khai cho 1 trường:
   ```bash
   python provision_organization.py <slug> "<Tên trường>" production \
     --admin-email admin@truong.edu.vn --admin-name "Tên Admin"
   ```
2. **Mời Teacher/Student** — Admin đăng nhập, vào Admin Console → tab "Lời mời" (hoặc
   `POST /api/v1/admin/invites`), nhập email + vai trò. Người được mời kích hoạt tại
   `/accept-invite?token=...` (link gửi qua email, hoặc — nếu `EMAIL_PROVIDER=none`
   khi dev — không hiện được, xem log `NullEmailService` để lấy link thủ công).
3. **Seed nhanh cho dev/test** — `python seed_demo_accounts.py` tạo lại 3 tài khoản
   demo có sẵn trong `mock_data/README.md`, gán vào tổ chức FPT University hiện có.

Xem đầy đủ luồng invite/sandbox: `docs/archive/planning-v2/10-Cursus-Auth-Onboarding-Sandbox-Spec.md`.

### 2.4. Chạy server

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Hoặc `make run`.

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health

## 3. Chạy Frontend (Vite)

```bash
cd frontend
npm install
npm run dev
```

Mặc định: **http://localhost:5173** (config trong `frontend/vite.config.js`; nếu port
5173 đang bận, Vite tự chuyển sang 5174 và in ra URL thật trong terminal).

API base (optional `frontend/.env`):

```
VITE_API_URL=http://localhost:8000/api/v1
```

### 3.1. Route map — trải nghiệm 3 role

Cursus không có đăng ký công khai (xem `docs/decisions/ADR.md` ADR-007). Hai cách vào:

**Sandbox (không cần tài khoản, dữ liệu giả lập, tách biệt hoàn toàn khỏi dữ liệu thật):**

- `/demo/select-role` → chọn Student/Teacher/Admin → vào thẳng `/student`, `/instructor`
  hoặc `/admin` với 1 trong 3 tài khoản seed sẵn trong tổ chức "Cursus Demo University"
  (chạy `python provision_organization.py cursus-demo "Cursus Demo University" sandbox --admin-email demo.admin@cursusdemo.local --admin-name "Demo Admin"` nếu DB chưa có).
- Trong dashboard sẽ thấy banner vàng "Chế độ demo" ở đầu trang, nút "Thoát demo".

**Tài khoản thật (tổ chức đã cấp):**

- `/login` → email/mật khẩu thật → tự chuyển hướng theo role (`/student`, `/instructor`,
  `/admin`). Sai role vào nhầm route khác → trang "Không có quyền truy cập" tại chỗ.
- Chưa đăng nhập vào route cần bảo vệ → chuyển tới `/login?returnTo=<route gốc>`.
- `/accept-invite?token=...` — kích hoạt tài khoản từ lời mời của Admin.
- `/request-access` — form yêu cầu Cursus liên hệ triển khai cho trường (không tạo
  tài khoản, chỉ lưu lead cho Admin xem ở `/admin` → tab tương ứng).

| Route                                     | Ai vào được                              | Ghi chú                                  |
| ----------------------------------------- | -------------------------------------------- | ----------------------------------------- |
| `/`                                     | Công khai                                   | Landing page                              |
| `/demo/select-role`                     | Công khai                                   | 3 tài khoản sandbox                     |
| `/login`                                | Công khai (redirect nếu đã đăng nhập) |                                           |
| `/accept-invite?token=`                 | Công khai, cần token hợp lệ              | Thay thế`/register` cũ                |
| `/request-access`                       | Công khai                                   | Lead form, không tạo tài khoản        |
| `/forgot-password`, `/reset-password` | Công khai                                   |                                           |
| `/student/*`                            | `role=student` (thật hoặc demo)          |                                           |
| `/instructor/*`                         | `role=instructor` (thật hoặc demo)       |                                           |
| `/admin/*`                              | `role=admin` (thật hoặc demo)            | Tab "Lời mời" để mời Teacher/Student |
| `/unauthorized`                         | Bất kỳ (đã đăng nhập)                 | Sai role truy cập route khác            |

### 3.2. Danh sách toàn bộ màn hình (đi hết để xem UI/UX, không sót màn nào)

Mục 3.1 ở trên chỉ liệt kê route gốc theo vai trò. Danh sách dưới đây liệt kê **từng màn hình thật bên trong**, để đi hết không bỏ sót màn nào khi review/chấm.

**Công khai (chưa đăng nhập):**

| Route                         | Màn hình                                                                                                                                                                                          |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`                         | Landing page                                                                                                                                                                                        |
| `/demo/select-role`         | Chọn vai trò sandbox (3 tài khoản demo)                                                                                                                                                         |
| `/login`                    | Đăng nhập                                                                                                                                                                                        |
| `/accept-invite?token=...`  | Kích hoạt tài khoản từ lời mời                                                                                                                                                               |
| `/request-access`           | Form yêu cầu triển khai (lead, không tạo tài khoản)                                                                                                                                          |
| `/forgot-password`          | Quên mật khẩu                                                                                                                                                                                    |
| `/reset-password?token=...` | Đặt lại mật khẩu                                                                                                                                                                               |
| `/email-verification`       | Xác thực email                                                                                                                                                                                    |
| `/onboarding`               | Hoàn tất hồ sơ sau đăng ký — form tồn tại nhưng hiện không truy cập được trong luồng thật (profile/enrollment đã seed sẵn ở server), xem`docs/PROJECT_CONTEXT.md` mục 6.1 |
| `/privacy`, `/terms`      | Chính sách bảo mật, Điều khoản dịch vụ                                                                                                                                                     |
| `/unauthorized`             | Trang từ chối truy cập (sai role cố vào route khác)                                                                                                                                           |

**Sinh viên** (`/student/*`, đăng nhập `role=student` — thật hoặc sandbox):

| Route                              | Màn hình                                                                                                     | Vào từ đâu                                   |
| ---------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| `/student` (= `/student/home`) | Tổng quan                                                                                                     | Sidebar                                          |
| `/student/planner`               | Lập kế hoạch tuần (Plan)                                                                                   | Sidebar                                          |
| `/student/semester-setup`        | Thiết lập học kỳ                                                                                           | Sidebar                                          |
| `/student/lecture-plan`          | Kế hoạch buổi học                                                                                          | Sidebar                                          |
| `/student/reflection`            | Phản tư tuần (Reflect)                                                                                      | Sidebar                                          |
| `/student/practice`              | Luyện tập                                                                                                    | Sidebar                                          |
| `/student/companion`             | Trợ lý theo môn — đa hội thoại lưu thật, đủ tính năng nhất trong 3 điểm chạm Cursus Assistant | Sidebar                                          |
| `/student/settings`              | Cài đặt (hồ sơ, ngôn ngữ/giao diện, yêu cầu xoá dữ liệu)                                          | Menu góc phải Topbar, không có trong Sidebar |

Widget Cursus Assistant nổi (góc dưới-phải) đi theo mọi trang trong nhóm này và trả lời thật qua `POST /qa` (không còn kịch bản FAQ như ở 6 trang công khai) — xem `docs/PROJECT_CONTEXT.md` mục 6.2.

**Giảng viên** (`/instructor/*`, đăng nhập `role=instructor`):

| Route                                    | Màn hình                                                                                                               |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `/instructor` (= `/instructor/home`) | Trang duy nhất: bộ chọn lớp (nếu dạy >1 lớp), roster sinh viên, cảnh báo rủi ro, hàng đợi duyệt guardrail |
| `/instructor/settings`                 | Cài đặt (menu Topbar)                                                                                                 |

**Quản trị viên** (`/admin/*`, đăng nhập `role=admin`): 1 trang `AdminConsole`, chuyển màn bằng bấm tab (không đổi URL):

| Tab             | Nội dung                                                                               |
| --------------- | --------------------------------------------------------------------------------------- |
| Môn học       | Curriculum — thêm/ẩn môn, upload tài liệu                                         |
| Học kỳ        | Lớp/hoạt động theo học kỳ                                                         |
| Chính sách AI | Guardrail Rules + Risk Policy (2 khối trong cùng 1 tab, có preview/publish/rollback) |
| Mock LMS        | Đồng bộ preview/publish/rollback với hệ thống ngoài (xem mục 3.3 bên dưới)   |
| Người dùng   | Mời/quản lý Giảng viên & Sinh viên                                                |
| Nhật ký       | Audit log (đã org-scope 22/08)                                                        |
| Phân tích     | KPI                                                                                     |
| Cấu hình      | Cài đặt vận hành (toggle + text field)                                             |

Cộng thêm `/admin/settings` (trang riêng qua menu Topbar, dùng chung `SettingsScreen.jsx` với 2 role kia — khác với tab "Cấu hình" ở trên).

### 3.3. Mock LMS — hệ thống ngoài đóng vai "Canvas" (app riêng biệt, KHÔNG phải Cursus)

Đây chính là màn hình "Canvas" — không đặt tên Canvas thật (đổi tên có chủ đích 15/08, xem `docs/PROJECT_CONTEXT.md` mục 6.6) vì đây không phải tích hợp Canvas thật của FPT, mà là 1 LMS mô phỏng team tự dựng để chứng minh Cursus gọi được **1 hệ thống ngoài thật** qua REST API + OAuth — DB/UI/khoá ký OAuth hoàn toàn tách biệt khỏi Cursus, không phải dữ liệu giả trong cùng 1 database (khác lần thử đầu `src/api/canvas_routes.py`, đã tắt vì sai kiến trúc — xem mục 6.6).

```bash
cd mock-lms
pip install -r requirements.txt        # đã có sẵn nếu dùng chung .venv gốc repo
python scripts/seed_courses.py         # 36 mã môn thật
python scripts/seed_assignments.py     # assignment/deadline sinh mới có chủ đích (syllabus gốc không có dữ liệu này để trích)
python scripts/create_oauth_client.py --name cursus --client-id cursus-tool   # in ra client_secret 1 lần, lưu lại
uvicorn app.main:app --reload --port 9000
```

- **[SỬA 23/08] Yêu cầu đăng nhập Cursus (SSO), không còn tài khoản Basic Auth riêng** — trước 22/08 2 trang này không có xác thực nào; 22/08 thêm tạm 1 tài khoản admin/mật khẩu dùng chung; 23/08 thay hẳn bằng đăng nhập qua chính danh tính Cursus (mã 1 lần đổi lấy vai trò, không chia sẻ cookie/JWT giữa 2 origin — chi tiết `mock-lms/README.md` mục "Web UI auth"). Đăng nhập Cursus trước (vai trò bất kỳ), rồi mở `http://localhost:9000/courses` — STUDENT/INSTRUCTOR chỉ xem được, chỉ ADMIN sửa được deadline. Cần set `MOCK_LMS_SSO_SHARED_SECRET` giống nhau ở cả 2 phía (`.env` gốc + env của `mock-lms`). API OAuth (`/api/v1/*`, cái Cursus thật sự gọi) không đổi, vẫn dùng Bearer token như cũ.
- `http://localhost:9000/courses` — danh sách 36 môn, có banner "Đây là LMS mô phỏng do team Cursus tự dựng..."
- `http://localhost:9000/courses/<code>` — assignment/deadline theo môn, sửa được deadline ngay tại đây (form thật)
- Đồng bộ sang Cursus: đăng nhập Admin Console → tab "Mock LMS" → "Xem trước đồng bộ" → nhập lý do → "Áp dụng" → xem lịch sử/rollback.
- **Xác nhận thấy rõ Cursus thật sự dùng dữ liệu này (không chỉ "chạy được"):** sửa 1 deadline ở Mock LMS → publish qua Admin Console → hỏi Trợ lý Cursus (widget nổi hoặc `/student/companion`) đúng câu về assignment đó → trích dẫn hiện `"Mock LMS (nguồn chính thức, đồng bộ gần nhất)"` thay vì nhãn syllabus mặc định. Đã verify thật, bằng chứng ở `docs/PROJECT_CONTEXT.md` mục 6.6 (✅ Verified 22/08) và `docs/evidence/screenshots/2026-08-22_mock-lms-checkpoint4-admin-ui/`.

Phạm vi có chủ đích **chưa làm** (không phải thiếu sót — xem mục 6.6): LTI 1.3 launch đầy đủ (stretch goal), 8 môn tổ hợp/elective, nối source-precedence vào citation phía Plan/StudyTask (Checkpoint 4b), deploy Mock LMS lên production.

## 4. Docker (chỉ backend)

`docker-compose.yml` ở root hiện **chỉ build service `backend`** — không có Postgres,
Redis hay frontend trong đó. Trước khi chạy, `.env` vẫn phải trỏ `DATABASE_URL` tới một
Postgres có thể kết nối từ bên ngoài (vd. Supabase) vì compose không tự cấp DB.

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f backend
```

- Backend: http://localhost:8000
- Health: http://localhost:8000/health

Dừng:

```powershell
docker compose down
```

Frontend vẫn chạy riêng bằng `npm run dev` (mục 3) — chưa có Dockerfile cho frontend.

## 5. Test & Lint

```bash
make test
make lint
make format
make check
```

## 6. AI Logging hooks (một lần)

```bash
bash scripts/setup_hooks.sh
# hoặc: powershell -ExecutionPolicy Bypass -File scripts\setup_hooks.ps1
```

## 7. Hai terminal (chạy full stack, không Docker — cách dùng hàng ngày)

**Backend:**

```bash
source .venv/Scripts/activate
uvicorn src.main:app --reload --port 8000
```

**Frontend:**

```bash
cd frontend
npm run dev
```

Mở http://localhost:5173 sau khi cả hai terminal đã sẵn sàng.
