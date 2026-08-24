-- Cursus — tạo role Postgres mới cho backend, KHÔNG có BYPASSRLS.
-- Chạy trong Supabase Dashboard → SQL Editor, đăng nhập bằng role
-- có quyền tạo role (mặc định `postgres`, chủ sở hữu project).
--
-- Đọc docs/decisions/rls-migration-plan.md TRƯỚC khi chạy file này —
-- có thứ tự các bước đầy đủ, phần này chỉ là 1 bước trong đó.
--
-- An toàn khi chạy lại nhiều lần: mọi lệnh đều idempotent
-- (IF NOT EXISTS / kiểm tra tồn tại trước khi tạo).

-- ============================================================
-- BƯỚC 1 — Tạo role mới, đặt mật khẩu riêng (KHÔNG dùng lại mật
-- khẩu của role `postgres`).
-- ============================================================
-- Thay '<MẬT_KHẨU_MỚI>' bằng mật khẩu bạn tự chọn, đủ mạnh
-- (khuyến nghị: dùng nút "Generate a password" của Supabase, hoặc
-- `openssl rand -base64 24`), rồi giữ lại để dán vào .env ở Bước cuối.
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cursus_app') THEN
    CREATE ROLE cursus_app WITH LOGIN PASSWORD '<MẬT_KHẨU_MỚI>';
  END IF;
END
$$;

-- Xác nhận role mới KHÔNG có BYPASSRLS (mặc định của CREATE ROLE là
-- NOBYPASSRLS, nhưng ghi tường minh ở đây để không ai lỡ tay đổi sau này).
ALTER ROLE cursus_app NOBYPASSRLS;

-- Không cho phép role này tự tạo role khác hay database khác — nguyên
-- tắc least-privilege, backend không cần 2 quyền này.
ALTER ROLE cursus_app NOCREATEROLE NOCREATEDB NOSUPERUSER;

-- ============================================================
-- BƯỚC 2 — Cấp quyền kết nối + dùng schema `public`.
-- ============================================================
GRANT CONNECT ON DATABASE postgres TO cursus_app;
GRANT USAGE ON SCHEMA public TO cursus_app;

-- ============================================================
-- BƯỚC 3 — Cấp quyền CRUD trên toàn bộ bảng hiện có trong schema
-- public. Backend cần đủ SELECT/INSERT/UPDATE/DELETE (không cần
-- TRUNCATE/DROP/ALTER — những quyền DDL đó chỉ cần lúc chạy
-- Alembic migration bằng role `postgres`, không cần ở runtime).
-- ============================================================
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cursus_app;

-- Áp dụng luôn cho các bảng được tạo SAU NÀY (ví dụ khi chạy Alembic
-- migration mới) — tránh phải chạy lại GRANT thủ công mỗi lần thêm bảng.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cursus_app;

-- ============================================================
-- BƯỚC 4 (tuỳ chọn, chỉ cần nếu có bảng dùng cột serial/identity —
-- Cursus hiện dùng ID dạng chuỗi tự sinh trong code Python, không
-- dùng SERIAL/IDENTITY, nên phần này thường không cần thiết. Chạy
-- thử BƯỚC 5 trước; nếu gặp lỗi "permission denied for sequence",
-- quay lại chạy đoạn dưới rồi thử lại).
-- ============================================================
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO cursus_app;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public
--   GRANT USAGE, SELECT ON SEQUENCES TO cursus_app;

-- ============================================================
-- BƯỚC 5 — Xác nhận role mới đúng như kỳ vọng (chạy để tự kiểm tra,
-- không phải lệnh bắt buộc phải chạy để role hoạt động).
-- ============================================================
-- Phải trả về rolbypassrls = false, rolsuper = false:
-- SELECT rolname, rolbypassrls, rolsuper, rolcreatedb, rolcreaterole
-- FROM pg_roles WHERE rolname = 'cursus_app';
