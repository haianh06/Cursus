# Kế hoạch vá lỗ hổng RLS/BYPASSRLS — các bước bạn tự làm trên Supabase

**Mục đích:** hướng dẫn từng bước để chuyển từ "RLS đã bật nhưng bị vô hiệu hoá vì role có BYPASSRLS" (ADR-007/ADR-013, `docs/PROJECT_CONTEXT.md` mục 9 ý 1) sang "RLS thực sự chặn dữ liệu chéo giữa các tổ chức". Tôi đã chuẩn bị sẵn code/SQL, **chưa tự chạy gì vào Supabase thật** — bạn tự chạy tay theo đúng thứ tự dưới đây rồi báo lại kết quả từng bước.

**Phát hiện quan trọng khi chuẩn bị việc này (bạn cần biết trước khi làm):** RLS policy hiện có (`migrations/versions/20260812_organizations_and_tenancy.py`) dùng điều kiện `organization_id = current_setting('app.current_org_id', true)` — nghĩa là **ngoài việc bỏ BYPASSRLS, backend còn phải tự set biến phiên `app.current_org_id` trên mỗi kết nối/request**, nếu không RLS sẽ chặn **toàn bộ** dữ liệu cho **mọi người** (vì `organization_id = NULL` không bao giờ đúng) — tự làm sập app chứ không phải vá bảo mật. Tôi đã viết sẵn phần backend cần để làm việc này (Bước 6), nhưng **chưa gắn vào route nào** — đây là phần việc kỹ thuật còn lại sau khi bạn xong các bước trên Supabase.

---

## Tổng quan các file tôi đã chuẩn bị sẵn (chưa chạy)

| File | Vai trò |
|---|---|
| `scripts/sql/create_restricted_db_role.sql` | Tạo role Postgres mới `cursus_app`, không có BYPASSRLS, đủ quyền CRUD — chạy trên Supabase SQL Editor |
| `migrations/versions/20260822_rls_academic_terms.py` | Vá 1 lỗ hổng phụ tìm được: bảng `academic_terms` có cột `organization_id` nhưng chưa từng có RLS policy (khác 4 bảng gốc `users/courses/programs/curriculum_versions` đã có từ migration 12/08) |
| `src/db/tenant_scope.py` | Dependency FastAPI mới (`get_scoped_db`) set biến phiên `app.current_org_id` — **chưa gắn vào route nào**, xem Bước 6 |

---

## Các bước bạn tự làm trên Supabase Dashboard

### Bước 1 — Chạy migration mới để vá `academic_terms`

Migration `20260822_rls_academic_terms` đã sẵn sàng, nối đúng vào cuối chuỗi hiện tại (`20260821_semester_practice` → `20260822_rls_academic_terms`). Chạy như mọi migration khác:

```powershell
python -m alembic upgrade head
```

Xác nhận đã lên đúng head mới:

```powershell
python -m alembic current
# phải thấy: 20260822_rls_academic_terms (head)
```

> Migration này chỉ bật RLS + tạo policy cho `academic_terms` — chưa có tác dụng thật cho tới khi xong Bước 2-3 (vẫn đang bị BYPASSRLS như các bảng khác).

### Bước 2 — Tạo role mới trên Supabase

1. Vào **Supabase Dashboard → SQL Editor** (không phải Table Editor).
2. Mở file `scripts/sql/create_restricted_db_role.sql`, copy toàn bộ nội dung.
3. **Trước khi dán vào SQL Editor**, sửa dòng `CREATE ROLE cursus_app WITH LOGIN PASSWORD '<MẬT_KHẨU_MỚI>'` — thay `<MẬT_KHẨU_MỚI>` bằng 1 mật khẩu bạn tự chọn (đủ mạnh, khác hẳn mật khẩu role `postgres` hiện tại). Ghi lại mật khẩu này ở đâu đó an toàn — sẽ cần dán vào `.env` ở Bước 5.
4. Dán và chạy (Run). Script an toàn chạy lại nhiều lần (idempotent).
5. Xác nhận role tạo đúng — chạy riêng câu lệnh cuối file (đã comment sẵn, bỏ comment ra chạy):
   ```sql
   SELECT rolname, rolbypassrls, rolsuper, rolcreatedb, rolcreaterole
   FROM pg_roles WHERE rolname = 'cursus_app';
   ```
   Kết quả đúng phải là: `rolbypassrls = false`, `rolsuper = false`.

### Bước 3 — Lấy connection string mới cho role `cursus_app`

Supabase không tự sinh sẵn connection string cho role tự tạo — bạn tự ghép lại từ connection string pooler hiện có:

1. Lấy connection string pooler hiện tại từ **Project Settings → Database → Connection string → tab URI → Transaction pooler** (giống cách lấy `DATABASE_URL` cũ đã làm trước đây).
2. Nó có dạng: `postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
3. Đổi phần user từ `postgres.<project-ref>` thành `cursus_app` **giữ nguyên project-ref không đổi gì khác** — Supabase pooler hỗ trợ multi-role qua cùng 1 pooler, chỉ cần đổi username: `postgresql://cursus_app.<project-ref>:<MẬT_KHẨU_MỚI>@aws-0-<region>.pooler.supabase.com:5432/postgres`

   > Nếu cách trên báo lỗi đăng nhập, vào **Database → Roles** trên Dashboard xem Supabase có yêu cầu định dạng username khác cho role tự tạo hay không (đôi khi chỉ cần `cursus_app` không kèm project-ref, tuỳ version pooler) — thử cả 2 dạng.

### Bước 4 — Test thử role mới TRƯỚC khi đổi `.env` thật

**Đừng đổi `.env` production ngay** — test trước bằng 1 connection riêng:

```powershell
# Cài psql nếu chưa có, hoặc dùng bất kỳ Postgres client nào (TablePlus, DBeaver...)
psql "postgresql://cursus_app.<project-ref>:<MẬT_KHẨU_MỚI>@aws-0-<region>.pooler.supabase.com:5432/postgres"
```

Trong phiên `psql` đó, chạy thử:

```sql
-- Chưa set app.current_org_id — phải KHÔNG thấy dòng nào (RLS chặn hết, đúng như thiết kế)
SELECT count(*) FROM users;

-- Set org demo rồi thử lại — phải thấy đúng số user thuộc org đó
SELECT set_config('app.current_org_id', 'org_cursus_demo', false);
SELECT count(*) FROM users;

-- Đổi sang org khác (ví dụ org thật FPT) — số liệu phải KHÁC dòng trên,
-- không lẫn user của org demo
SELECT set_config('app.current_org_id', 'org_fpt_university', false);
SELECT count(*) FROM users;
```

**Đây chính là bài test xác nhận RLS đã chặn thật:** nếu bước đầu (chưa set org) mà vẫn thấy toàn bộ user của mọi tổ chức → RLS chưa có tác dụng, dừng lại, đừng đổi `.env`, báo lại cho tôi kèm kết quả `SELECT` ở Bước 2.5. Nếu đúng như mô tả (đổi org → đổi số liệu, không set → rỗng) → an toàn để qua Bước 5.

### Bước 5 — Đổi `.env` sang role mới

Chỉ làm sau khi Bước 4 xác nhận đúng. Sửa `DATABASE_URL` trong `.env`:

```
DATABASE_URL=postgresql://cursus_app.<project-ref>:<MẬT_KHẨU_MỚI>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

Restart backend. **Kỳ vọng lúc này: app sẽ lỗi/trả rỗng dữ liệu ở các bảng có RLS** (`users`, `courses`, `programs`, `curriculum_versions`, `academic_terms`) — đúng như đã nói ở đầu file, vì chưa có ai set `app.current_org_id` cho mỗi request. Đây là lý do Bước 6 dưới đây **bắt buộc phải làm cùng lúc**, không phải để sau.

### Bước 6 — Gắn `get_scoped_db` vào route (việc code còn lại, tôi làm được nhưng cần bạn xác nhận trước)

`src/db/tenant_scope.py` đã có sẵn dependency `get_scoped_db` — set đúng biến phiên cần thiết. Việc còn lại là đổi các route đang dùng `Depends(get_db)` sang `Depends(get_scoped_db)` ở đúng những route chạm vào 5 bảng có RLS (`users`, `courses`, `programs`, `curriculum_versions`, `academic_terms`) — chủ yếu nằm trong `src/api/admin.py`, `src/api/auth.py`, một phần `src/api/student.py`/`instructor.py`.

Tôi **chưa tự làm bước này** vì: (a) đây là thay đổi chạm vào nhiều route, cần test được với Postgres thật trước khi merge (Docker local ở máy này hiện không khởi động được — xem phần Load test bên dưới), (b) đổi sai 1 route có thể làm route đó luôn trả rỗng dữ liệu, khó phát hiện nếu không test kỹ. Khi bạn xong Bước 1-5 và xác nhận role mới hoạt động, báo lại — tôi sẽ làm Bước 6 và **tự test bằng Postgres local trước khi bạn merge**, không cần bạn tự làm bước này.

---

## Việc CHƯA làm, cần biết rõ (không phải bạn thiếu sót, tôi chủ động giới hạn phạm vi)

- **`organization_memberships` và `org_invites`** cũng có cột `organization_id` nhưng **chưa được thêm vào danh sách bảng có RLS** ở lần vá này — giữ nguyên phạm vi như thiết kế gốc (chỉ 4 bảng "root" + `academic_terms` mới vá). Nếu muốn mở rộng RLS sang 2 bảng này, cần 1 migration riêng — báo tôi nếu muốn làm tiếp.
- Các bảng con khác (`weekly_plans`, `study_tasks`, `reflections`, `risk_alerts`...) **không có RLS trực tiếp** — chúng scope theo tổ chức gián tiếp qua khoá ngoại tới `users`/`courses`, đúng theo thiết kế ban đầu ghi trong migration `20260812`. RLS trên 5 bảng gốc không tự động bảo vệ các bảng con này nếu code backend join sai hoặc quên filter — filter `organization_id` ở tầng ứng dụng (từng repository) vẫn là lớp bảo vệ chính cho nhóm bảng này, không thể bỏ qua dù RLS ở bảng gốc đã đúng.
