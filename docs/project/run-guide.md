# Hướng Dẫn Khởi Chạy Chi Tiết Hệ Thống Cursus (Backend & Frontend)
*Trước đây `RUN_GUIDE.md` ở root — dời vào `docs/project/` để cùng chỗ với các tài liệu vận hành repo khác (`structure-team.md`, `logging-guide.md`).*

> **Quan hệ với `RUNNING.md` (root):** `RUNNING.md` ở gốc repo là bản quick-start hiện hành
> (setup env, migrate DB, auth B2B2C, route map, Docker) — đọc file đó trước cho lần chạy
> hàng ngày. File này (`run-guide.md`) bổ sung phần **Windows** không có ở `RUNNING.md`:
> khắc phục lỗi `Fatal error in launcher` khi đổi tên/di chuyển thư mục dự án + tái tạo
> `.venv`. Phần "Trải nghiệm 5 màn hình" ở cuối bài mô tả bản UI giai đoạn đầu (trước khi
> hợp nhất backend thật) — nay đã lỗi thời, xem `docs/PROJECT_CONTEXT.md` mục 6 (trang/chức
> năng theo role) và 13-14 cho flow/role hiện hành. (`docs/FRONTEND_SPEC.md` đã bị xoá
> 16/08/2026, có chủ đích không tạo lại — xem `DOCS_GUIDE.md` mục 1.)

Tài liệu hướng dẫn đầy đủ từ A-Z để thiết lập môi trường ảo Python (`.venv`), khắc phục lỗi đổi đường dẫn thư mục, cấu hình `.env`, khởi chạy **FastAPI Backend (port 8000)** và **React Frontend (port 5173)**.

> **Cập nhật 13/08/2026:** backend F1–F7 thật (auth, plan, QA, instructor, student, admin) đã hợp nhất từ nhánh `develop` vào `haidang2425` trong phiên làm việc này — xem `docs/decisions/ADR.md` cho quyết định hợp nhất, `RUNNING.md` (root) cho hướng dẫn setup/migrate DB đầy đủ hiện hành (Postgres/Supabase, `alembic upgrade head`, biến môi trường bắt buộc).

---

## ⚠️ GIẢI QUYẾT LỖI `Fatal error in launcher: Unable to create process`

### 🔴 Nguyên nhân:

Lỗi xảy ra do thư mục dự án đã từng đổi tên hoặc di chuyển vị trí (ví dụ từ `D:\Vin_AI\P-093` sang `D:\VINAI_Team_093\P-093`). Môi trường ảo `.venv` cũ bị lưu cứng đường dẫn tuyệt đối cũ nên `pip.exe` không thể kích hoạt.

### 🟢 CÁCH 1: Dùng cú pháp `python -m pip` (Nhanh nhất — Không cần xóa env)

Thay vì gõ `pip`, bạn gõ `python -m pip`:

```powershell
# Cài đặt requirements
python -m pip install -r requirements.txt

# Chạy Backend Uvicorn
python -m uvicorn src.main:app --reload --port 8000
```

---

### 🟢 CÁCH 2: Tạo lại môi trường `.venv` chuẩn đường dẫn mới (Triệt để)

Mở Terminal tại thư mục `D:\VINAI_Team_093\P-093`:

```powershell
# Bước 1: Deactivate env hiện tại (nếu đang bật)
deactivate

# Bước 2: Xóa thư mục .venv cũ bị lỗi đường dẫn
Remove-Item -Recurse -Force .venv

# Bước 3: Tạo mới môi trường .venv theo đường dẫn D:\VINAI_Team_093\P-093
python -m venv .venv

# Bước 4: Kích hoạt môi trường .venv mới
.\.venv\Scripts\Activate.ps1

# Bước 5: Cài đặt lại requirements
pip install -r requirements.txt
```

---

## 🏗️ QUY TRÌNH KHỞI CHẠY HỆ THỐNG FULL-STACK

### 🐍 1. Khởi Chạy FastAPI Backend (Port 8000)

Cửa sổ Terminal 1 (tại `D:\VINAI_Team_093\P-093`):

1. **Copy file `.env`**:
   ```cmd
   copy .env.example .env
   ```
2. **Kích hoạt `.venv`**:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. **Chạy Backend**:
   ```powershell
   python -m uvicorn src.main:app --reload --port 8000
   ```

👉 Trình duyệt truy cập Swagger UI: **[http://localhost:8000/docs](http://localhost:8000/docs)**

---

### ⚡ 2. Khởi Chạy React Frontend (Port 5173)

Cửa sổ Terminal 2:

1. **Di chuyển vào thư mục `frontend`**:
   ```powershell
   cd frontend
   ```
2. **Cài đặt npm dependencies**:
   ```powershell
   cmd /c npm install
   ```
3. **Chạy Frontend Server**:
   ```powershell
   cmd /c npm run dev
   ```

👉 Trình duyệt truy cập giao diện Cursus: **[http://localhost:5173/](http://localhost:5173/)**

---

### 🎓 3. Khởi Chạy Mock LMS — hệ thống ngoài giả lập (Port 9000, tuỳ chọn)

Chỉ cần khi muốn test luồng tích hợp Canvas giả lập (sửa deadline ở LMS ngoài → Cursus đọc lại qua sync). App riêng, DB riêng (`mock-lms/mock_lms.db`), không dùng chung gì với backend chính ở Terminal 1.

Cửa sổ Terminal 3:

```powershell
cd mock-lms
uvicorn app.main:app --reload --port 9000
```

⚠️ **Lỗi hay gặp:** gõ `app.web:app` thay vì `app.main:app` → báo `Attribute "app" not found in module "app.web"`. `app/web.py` chỉ là router con (`/courses`, `/courses/{code}`), FastAPI app thật (đăng ký cả router web lẫn API OAuth) nằm ở `app/main.py`.

👉 Trang danh sách môn: **[http://localhost:9000/courses](http://localhost:9000/courses)** — **[SỬA 23/08]** không còn tài khoản Basic Auth riêng, giờ đăng nhập bằng chính tài khoản Cursus (SSO qua mã 1 lần) — đăng nhập Cursus trước (port 8000/5173), rồi mở lại trang này; STUDENT/INSTRUCTOR chỉ xem, ADMIN mới sửa được deadline. Cần `MOCK_LMS_SSO_SHARED_SECRET` giống nhau ở `.env` gốc và env của `mock-lms` (xem `mock-lms/README.md` mục "Web UI auth"). Chi tiết đầy đủ + cách verify sync thật: `RUNNING.md` (root) dòng ~219-231.

---

## 🎨 Trải Nghiệm 5 Màn Hình Trên Giao Diện (http://localhost:5173/)

Sử dụng thanh **Role Tabs** trên Header:

1. **AuthScreen**: Đăng nhập / Đăng ký phân quyền vai trò.
2. **Student Home**: Weekly Plan SSA101, task khẩn <48h (`Project — Part 1`), Grounded Q&A Chat có trích nguồn syllabus và Cảnh báo Guardrail Shake.
3. **Reflect**: Phản tư tuần theo đối thoại 3 bước Wizard Flow, Context Summary, Streak và Lịch sử.
4. **Instructor**: Dashboard Cố vấn lớp SE1801, chart % hoàn thành, alert Huy/Mai, hàng đợi Guardrail review.
5. **Admin**: Admin Console (Bảng Curriculum Vector Store, nạp doc mới, KPI 78% vs 45%).

Sử dụng công tắc **State Switcher** (gốc trên bên phải) để test 4 trạng thái: **SUCCESS | LOADING | EMPTY | ERROR**.
