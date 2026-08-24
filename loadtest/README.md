# Load test — môi trường local, không đụng Supabase/deploy thật

**Mặc định load test luôn nhắm vào Docker Postgres local + backend chạy trên máy bạn — không bao giờ nhắm vào Supabase hay bản deploy Railway/Vercel trừ khi bạn xác nhận rõ ràng bằng lời trước.** Lý do ghi ở `docs/decisions/ADR.md` (ADR mới nhất về load test).

## 1. Dựng môi trường Postgres local bằng Docker

`docker-compose.yml` ở gốc repo đã có sẵn service `db` (Postgres 16, profile `local-db`) — không cần viết thêm compose file mới, chỉ cần bật đúng profile:

```powershell
docker compose --profile local-db up -d db
```

Kiểm tra đã sẵn sàng:

```powershell
docker compose ps
# service "db" phải ở trạng thái healthy
```

> **Ghi chú lúc chuẩn bị (15/08/2026):** tôi định tự dựng và chạy thử luôn bước này, nhưng Docker Desktop trên máy hiện không phản hồi (`docker ps` treo, không lỗi rõ ràng — có thể do Docker Desktop engine chưa khởi động xong hoặc gặp sự cố nền WSL2). Đã thử khởi động lại Docker Desktop qua PowerShell (`Start-Process`) và đợi ~25s, engine vẫn không phản hồi trong phiên làm việc này. Bạn cần tự mở Docker Desktop (kiểm tra icon khay hệ thống chuyển xanh, không còn "starting..."), rồi chạy lệnh trên. Nếu vẫn lỗi, thử **Docker Desktop → Troubleshoot → Restart** hoặc khởi động lại máy — đây là vấn đề riêng của Docker Desktop trên máy này, không phải lỗi trong repo.

## 2. Trỏ backend vào Postgres local, chạy migration

Tạo `.env.loadtest` riêng (không đụng `.env` thật đang trỏ Supabase):

```
DATABASE_URL=postgresql://cursus:cursus@localhost:5432/cursus
APP_ENV=development
JWT_SECRET_KEY=loadtest-only-not-a-real-secret
GOOGLE_API_KEY=test-key
EMAIL_PROVIDER=none
```

(copy các biến còn lại cần thiết từ `.env.example`; `GOOGLE_API_KEY` không cần key thật vì load test chủ yếu đo API layer + DB, câu hỏi phức tạp cần LLM thật sẽ tự fallback sang câu trả lời trích xuất — xem `docs/PROJECT_CONTEXT.md` mục 15).

```powershell
# Windows PowerShell — nạp .env.loadtest thay vì .env cho phiên này
Get-Content .env.loadtest | ForEach-Object {
    if ($_ -match '^([^#=]+)=(.*)$') { Set-Item "Env:$($Matches[1])" $Matches[2] }
}
python -m alembic upgrade head
```

## 3. Seed 3 tài khoản demo (bắt buộc — `/auth/demo-session` cần org "cursus-demo" tồn tại sẵn)

```powershell
python provision_organization.py cursus-demo "Cursus Demo University" sandbox `
    --admin-email admin.demo@cursusdemo.local --admin-name "Demo Admin"
```

Script tự idempotent (chạy lại không lỗi, không tạo trùng) — xem chi tiết ở đầu file `provision_organization.py`.

## 4. Chạy backend trỏ vào Postgres local

Cửa sổ terminal riêng, vẫn với `.env.loadtest` đã nạp ở bước 2:

```powershell
python -m uvicorn src.main:app --port 8000
```

Kiểm tra nhanh: `curl http://localhost:8000/health` → `{"status":"ok",...}`.

## 5. Chạy Locust

`locust` đã thêm vào `requirements.txt` (nhóm "Load testing"), cài qua `pip install -r requirements.txt` như bình thường nếu chưa có.

**Chạy có giao diện web (xem trực tiếp p50/p95/p99 khi test đang chạy):**

```powershell
locust -f loadtest/locustfile.py --host http://localhost:8000
# Mở http://localhost:8089 , nhập số user + spawn rate, bấm Start
```

**Chạy headless, tiệm cận 1.000 kết nối đồng thời, xuất CSV có đủ số liệu:**

```powershell
locust -f loadtest/locustfile.py --host http://localhost:8000 `
    --headless --users 1000 --spawn-rate 50 --run-time 5m `
    --csv loadtest/results/run1
```

Kết quả: `loadtest/results/run1_stats.csv` (có cột `50%`, `95%`, `99%` — chính là p50/p95/p99 độ trễ theo mili-giây), `run1_failures.csv` (tỷ lệ lỗi theo endpoint), `run1_stats_history.csv` (biểu đồ theo thời gian, có thể vẽ lại bằng Excel/pandas).

> Tăng dần: chạy thử 100 → 300 → 1.000 user, đừng nhảy thẳng lên 1.000 — dễ thấy điểm nghẽn cổ chai xuất hiện ở đâu (thường là connection pool của SQLAlchemy — `pool_size=5, max_overflow=10` trong `src/db/connection.py`, hoặc CPU của uvicorn nếu chạy single-worker).

## 6. Nếu sau này muốn test nhắm vào bản deploy thật (Railway/Vercel)

**Không tự đổi `--host`.** Việc này phải hỏi xác nhận rõ ràng trước, vì:
- Free tier Supabase/Railway dễ bị ảnh hưởng bởi 1.000 kết nối đồng thời (connection limit, rate limit, có thể tốn phí vượt hạn mức).
- Dữ liệu demo trên bản deploy thật là dữ liệu duy nhất đang dùng để demo/nộp bài — load test lỗi có thể làm hỏng state đang cần cho Demo Day.

Nếu được xác nhận, đổi `--host` thành domain Railway thật, và **giảm quy mô trước** (bắt đầu 50-100 user) để không làm sập môi trường thật ngay từ lần chạy đầu.
