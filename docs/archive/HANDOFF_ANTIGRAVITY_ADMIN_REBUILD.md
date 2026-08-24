> **LƯU Ý:** Nhánh cleanup/repo-audit-20260820 đề cập trong tài liệu này đã hoàn thành nhiệm vụ, được merge toàn bộ vào nhánh haidang2425 và đã bị xóa.

# Bàn giao cho Antigravity/Gemini — hoàn thiện Admin rebuild

> Đọc file này TRƯỚC KHI làm gì. Viết để 1 agent hoàn toàn mới (không có lịch sử hội thoại này) vẫn tiếp tục đúng, không hỏi lại, không đoán.

## 0. Việc đang làm là gì, tại sao

Đang code lại vai trò **Admin** trên nhánh `cleanup/repo-audit-20260820`, dựa theo bản thiết kế chức năng đã rút ra từ nhánh đồng đội `chung` (nhánh đó không merge được — xem lý do ở mục 2). Đây là **P-093, đồ án Cursus** — AI academic companion, hạn nộp 23/08/2026 (**hôm nay**).

**Đã xong 1/9 phần** (Student 360). Còn 8 phần. Làm tiếp theo đúng thứ tự trong file spec, từng phần một, commit riêng, verify bằng ảnh/log thật trước khi coi là xong.

## 1. Đọc theo đúng thứ tự này

1. File này (đủ để bắt đầu).
2. `docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md` — **spec chức năng đầy đủ**, mục 3.1→3.9 là 9 màn hình cần có, mục 4 là toàn bộ luồng backend, mục 5 là các lỗi UX của chung KHÔNG được copy lại.
3. `docs/AUDIT_NHANH_CHUNG_ADMIN_23AUG.md` — vì sao không merge trực tiếp nhánh `chung` được (115 file xung đột thật, đã thử và huỷ).
4. `src/api/admin_student360.py` + `frontend/src/components/admin/AdminStudent360.jsx` — code mẫu ĐÃ XONG, verify thật, dùng làm khuôn cho các phần còn lại (xem mục 3 dưới đây để biết pattern nào phải lặp lại y hệt).
5. `docs/PROJECT_CONTEXT.md` mục "TRẠNG THÁI HIỆN TẠI" (đầu file) — bối cảnh toàn dự án, quy tắc an toàn.

## 2. Quy tắc BẮT BUỘC (không đổi, không hỏi lại)

- **Không đụng Supabase** dưới bất kỳ hình thức nào (không migrate, không stamp, không query trực tiếp qua script/psql). Test chỉ dùng SQLite/Postgres local.
- **Không merge/push ra ngoài `cleanup/repo-audit-20260820`.** Tuyệt đối không đụng `main`.
- **Không merge nguyên khối nhánh `chung`/`thanhbinh`/bất kỳ nhánh đồng đội nào** — đã thử, xung đột thật (xem mục 2 file audit). Chỉ port CHỨC NĂNG (viết lại code mới trên schema hiện tại), không copy file/migration của họ.
- **Không tạo bảng `self_study_sessions`** hay bất kỳ bảng nào chỉ để khớp với chung — chung dùng migration chain khác hẳn nhánh này. Nếu spec cần dữ liệu không có sẵn, bỏ qua tính năng đó và ghi chú rõ, không tự ý thêm bảng mới mà không xác nhận.
- **Không gỡ MFA.** Spec (mục 2.2) có nhắc chung đã gỡ MFA bên nhánh của họ — nhánh này giữ nguyên MFA, không làm theo.
- **Không tự quyết định kiến trúc lớn một mình** (ví dụ: đổi hẳn tab sang route cho toàn bộ AdminConsole) — nếu cần quyết định như vậy, dừng lại, hỏi người dùng, đừng tự chọn.
- Mọi route/endpoint mới đọc dữ liệu 1 sinh viên cụ thể → **bắt buộc đi qua audit-trước-trả-sau** (xem mục 3.1 bên dưới) — đây là nguyên tắc bảo mật cốt lõi của toàn bộ phần Admin, không phải tuỳ chọn.
- Sau mỗi phần code xong: chạy `pytest tests/ -q`, chụp ảnh màn hình thật (Playwright hoặc trình duyệt thật) xác nhận chạy đúng, rồi mới commit. Không báo "xong" nếu chưa có bằng chứng.
- Mỗi phần trong 8 phần còn lại = **1 commit riêng**, không gộp nhiều phần vào 1 commit.

## 3. Pattern kỹ thuật đã có, PHẢI tái dùng (không tự nghĩ ra cách khác)

### 3.1 Audit-trước-trả-sau (bắt buộc cho MỌI route đọc dữ liệu nhạy cảm)

Xem nguyên văn trong `src/api/admin_student360.py`, hàm `_audited_read()`:
```python
async def _audited_read(db, *, actor_id, resource_type, resource_id, items, extra_metadata=None):
    try:
        await AuditService(AuditRepository(db)).log_event(
            event_type="ADMIN_SENSITIVE_READ", decision="ALLOW",
            actor_user_id=actor_id, resource_type=resource_type, resource_id=resource_id,
            metadata={"resourceCount": len(items), **(extra_metadata or {})}, commit=False,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail="sensitive_audit_unavailable") from exc
    return items
```
Copy đúng hàm này (hoặc import dùng chung) cho mọi route mới đọc dữ liệu 1 người dùng cụ thể (Instructor 360, v.v.).

### 3.2 So sánh role — LỖI ĐÃ GẶP, TRÁNH LẶP LẠI

`User.role` lưu dưới dạng **chuỗi thường** (`'STUDENT'`), KHÔNG phải enum instance. So sánh phải dùng:
```python
student.role != models.UserRole.STUDENT.value   # ĐÚNG
student.role != models.UserRole.STUDENT          # SAI — luôn True, gây 404 sai
```

### 3.3 `request()` phía frontend đã tự unwrap `{success, data}`

Lỗi thật đã gặp: gọi `readAdminStudentResource(...).then(res => res.data)` → SAI, vì `request()` (`frontend/src/lib/api.js`) đã tự trả về `payload.data` rồi. Chỉ cần dùng thẳng kết quả trả về (`.then(res => res)`), không lấy `.data` lần nữa.

### 3.4 Org-scoping fail-closed

Mọi hàm `_require_xxx(db, current_user, target_id)` phải check: không tồn tại HOẶC sai vai trò HOẶC khác `organization_id` → **cùng 1 lỗi 404 y hệt**, không phân biệt lý do (tránh lộ thông tin tồn tại tài khoản). Xem `_require_student()` trong file mẫu.

### 3.5 UI — dùng đúng token/class đã có, không tự tạo hệ màu riêng

- Bảng dữ liệu: class `data-table` (đã có sẵn trong `index.css`).
- Tab điều hướng: class `tabs-underline` / `tab-underline-item` (đã dùng ở `AdminConsole.jsx`, `AdminStudent360.jsx`).
- Card: class `card`.
- Nút xác nhận hành động không-huỷ-được: tái dùng `frontend/src/components/shared/ConfirmDialog.jsx` (đã có sẵn từ trước) — **không** dùng `window.confirm()` của trình duyệt (đây chính là lỗi UX chung tự mắc phải, xem spec mục 5.1).
- **Tuyệt đối không tạo hệ token màu riêng cho Admin** (chung từng làm "Ink & Citrine" riêng — nhánh này đã tốn công hợp nhất về 1 hệ token dùng chung mọi role, xem `CHANGELOG.md` đợt 8). Dùng đúng biến CSS có sẵn (`--accent`, `--danger`, `--success`, `--warning`, `text-fg`, `bg-surface`...).

### 3.6 Cách verify (bắt buộc trước khi commit)

1. Backend: `curl` trực tiếp route mới qua demo-session thật (xem cách login demo trong `RUNNING.md`), xác nhận status code + payload đúng, xác nhận audit ghi được (gọi lại route `access-history` xem có dòng mới không).
2. Frontend: chạy Playwright hoặc mở trình duyệt thật, đăng nhập demo Admin, bấm qua đúng luồng, chụp ảnh, kiểm tra Console không có lỗi JS.
3. `pytest tests/ -q` — phải giữ nguyên 444 passed / 7 skipped / 0 failed (tăng thêm nếu có test mới, không được giảm).

## 4. 8 phần còn lại — làm theo đúng thứ tự này

| # | Phần | Độ khó | Ghi chú |
|---|---|---|---|
| 2 | Instructor 360 (`/admin/instructors/:id`) | Thấp | Đơn giản hơn Student 360 — chỉ tổng hợp, KHÔNG có tab dữ liệu gốc, KHÔNG link xuống từng sinh viên. Xem spec mục 3.4. |
| 3 | Yêu cầu dữ liệu (DSAR) | Trung bình | Bảng mới `data_requests` (migration mới, xem spec mục 4.2) + luồng xem-trước-xoá có mã băm (spec mục 3.5). |
| 4 | Nâng Chương trình học lên có lifecycle | Cao | Thêm scope/publication_status/version cho `documents`, 6 tiêu chí kiểm định, modal xác nhận đàng hoàng (không dùng window.confirm). Đụng vào tính năng ĐANG CHẠY — cẩn thận, test kỹ trước/sau. |
| 5 | Nâng Tài khoản & lời mời | Trung bình | Thêm audit thu hồi quyền đọc nhạy cảm ngay khi khoá tài khoản (spec mục 3.7). |
| 6 | Chính sách AI & rủi ro | Thấp (đã có sẵn phần lớn) | Risk policy versioning đã có (mục 14.1 PROJECT_CONTEXT.md) — chỉ cần thêm versioning tương tự cho guardrail rules nếu chưa có, kiểm tra lại trước khi thêm. |
| 7 | Cấu hình & hệ thống — tách route | Thấp | Tách "Cấu hình" hiện tại thành sub-tab riêng thay vì 1 trang cuộn dài (spec mục 3.9). |
| 8 | Đổi điều hướng AdminConsole từ tab sang route đầy đủ | Cao, cần hỏi trước | Đây là quyết định kiến trúc lớn — DỪNG, hỏi người dùng trước khi làm, đừng tự quyết. |
| 9 | Cập nhật `PROJECT_CONTEXT.md` mục 6 (Admin) cho khớp code mới | Thấp | Làm cuối cùng, sau khi mọi phần khác xong. |

## 5. Prompt gợi ý — dán nguyên văn vào Antigravity để bắt đầu

```
Đọc file docs/HANDOFF_ANTIGRAVITY_ADMIN_REBUILD.md trong repo này trước,
làm đúng theo thứ tự mục 4 của file đó (bắt đầu từ "Instructor 360").
Tuân thủ tuyệt đối mục 2 (quy tắc bắt buộc) và mục 3 (pattern phải tái
dùng) của cùng file. Sau mỗi phần: chạy pytest, chụp ảnh xác nhận, rồi
mới commit riêng phần đó — không dồn nhiều phần vào 1 commit, không báo
xong nếu chưa có bằng chứng chạy thật. Nếu gặp quyết định kiến trúc lớn
không có trong spec, dừng lại và hỏi tôi, đừng tự quyết.
```

## 6. Gemini model nên dùng trong Antigravity

Tôi không chắc chắn 100% tên/phiên bản model Gemini mới nhất tại đúng thời điểm bạn đọc file này (dữ liệu huấn luyện của tôi dừng ở đầu 2026, còn hôm nay đã là 23/08/2026) — bạn nên tự kiểm tra danh sách model hiện có trong Antigravity trước khi chọn. Nhưng nguyên tắc chọn cho đúng việc này:
- Đây là **coding task nhiều file, nhiều bước, cần đọc hiểu spec dài + giữ nhất quán quy tắc qua nhiều lượt sửa** → chọn **tier "Pro" cao nhất / chế độ reasoning mạnh nhất** mà Antigravity cho phép với Gemini (không chọn bản "Flash"/nhẹ — task này cần suy luận nhiều bước, không phải trả lời nhanh).
- Nếu Antigravity cho chọn mức "reasoning effort"/"thinking budget", đặt **cao nhất có thể trả phí** — vì file spec dài (~250 dòng) + nhiều ràng buộc chéo (audit pattern, org-scoping, token màu...), model cần "suy nghĩ" kỹ trước khi sửa code, không nên dùng chế độ trả lời nhanh.

## 7. Tình trạng chi tiết hiện tại (để agent mới biết chính xác đang ở đâu)

- Branch: `cleanup/repo-audit-20260820`, đã push tới commit `a8ee6bb` (Student 360).
- `pytest tests/`: 444 passed, 7 skipped, 0 failed — mốc chuẩn, không được để giảm.
- 2 việc khác (không liên quan Admin rebuild) vẫn đang chờ người dùng tự làm trên Supabase Dashboard: RLS đa tổ chức, và fix 2 dòng `actual_minutes` sai trong bảng `study_tasks` của tài khoản demo (xem `docs/PROJECT_CONTEXT.md` mục "TRẠNG THÁI HIỆN TẠI" để biết chi tiết) — không liên quan tới việc code Admin, không cần làm trước khi tiếp tục.
