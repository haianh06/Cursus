# Tóm tắt đợt push 26/08 — đọc trong 2 phút

Bản chi tiết: [CHANGELOG_PUSH_26AUG.md](CHANGELOG_PUSH_26AUG.md)

---

## 🔴 Sau khi pull, chạy ngay 1 lệnh này

```bash
./.venv/Scripts/python.exe -m alembic upgrade head
```

Đợt này có 2 migration đổi cấu trúc database. **Không chạy là backend sập.**

Kiểm tra xem có ổn không:

```bash
./.venv/Scripts/python.exe -m pytest tests/ -q
```

Phải thấy `548 passed, 7 skipped`.

---

## Đợt này làm được gì

**20 commit · 50 file · +3813 dòng · 548 test xanh**

### 1. Admin giờ quản lý được lớp học

Trước đây Admin **không có** màn hình nào để làm việc này. Giờ có, ở
`/admin/governance/sections`:

- Tạo lớp mới, sửa mã lớp / học kỳ
- Gán giảng viên cho lớp
- Thêm / bỏ sinh viên khỏi lớp
- Xoá lớp (bị chặn nếu lớp còn sinh viên đang học)
- Reset mật khẩu cho thành viên

Lớp chưa có giảng viên sẽ tự hiện thành **việc cần làm** ở trang Overview, bấm vào
là nhảy thẳng tới màn quản lý lớp.

### 2. Hết tình trạng "mất dấu"

Ba chỗ dữ liệu trước đây bị rơi, giờ đã ghi lại đầy đủ:

| Trước | Sau |
|---|---|
| Sinh viên bị AI chặn câu hỏi → không ai biết | Giảng viên thấy được, kèm đúng lớp |
| Giảng viên mở chặn, can thiệp → không vào log | Vào Audit log |
| Sinh viên tự xoá dữ liệu → không vào log | Vào Audit log |

Kèm một lỗ bảo mật đã vá: trước đây **sinh viên xoá thread chat là xoá luôn bằng chứng
mình bị chặn**. Giờ bản ghi tồn tại độc lập, xoá thread không ảnh hưởng.

### 3. Sửa 2 lỗi thật

- **Sinh viên đã bỏ lớp vẫn làm được quiz** → đã chặn
- **Bấm Xoá lớp thì hệ thống báo lỗi mạng** (thực chất là lỗi 500 phía server) → đã sửa

### 4. Mock LMS chạy bằng Docker

Không phải dựng tay từng người nữa, `docker compose` lo hết.

---

## ⚠️ 2 điều cần biết

**1. Cần đổi `LANGCHAIN_API_KEY`**

File `.env.bak` từng bị commit lên GitHub kèm mật khẩu và API key thật. Đợt này đã bỏ
nó khỏi git, nhưng **key cũ vẫn còn trong lịch sử commit**. Ai có quyền LangSmith thì
tạo key mới thay vào. Repo đang private nên chỉ người trong team thấy được, không phải
cả internet — nhưng vẫn nên đổi.

**2. Lớp demo `SE1801` có mã mới**

Mã mới: `sec_adm_e3ed68a01fe2`. Nếu bạn có script hay bookmark dùng mã cũ thì sửa lại.

---

## Muốn thử tay xem có chạy không

1. Vào `/admin/governance/sections` → bấm **Thêm lớp**, **để trống giảng viên**
2. Sang `/admin/overview` → lớp vừa tạo phải xuất hiện trong danh sách việc cần làm
3. Bấm vào việc đó → phải nhảy về màn Lớp học
4. Gán giảng viên → tải lại Overview, việc đó phải biến mất
5. Mở **Danh sách sinh viên**, thêm 1 người, rồi thử **Xoá lớp** → phải bị chặn
6. Bỏ người đó ra, **Xoá lớp** lại → phải thành công
7. Đổi qua lại Tiếng Việt ⇄ English → không được sót chữ nào

---

## Còn dở dang

- Chưa đổi `LANGCHAIN_API_KEY` (mục ⚠️ ở trên)
- Plan còn Task 10–14 chưa làm. Việc kế tiếp: **Task 14 từ Step 3**
