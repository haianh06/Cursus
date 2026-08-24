# Worklog — Team093 (Group06) — Cursus

> Ghi lại tất cả công việc đã làm theo ngày. Ai làm gì, kết quả gì. **Cách điền:** cuối mỗi ngày code, mỗi người tự thêm 1 dòng vào bảng của ngày hôm đó (không cần đợi PM nhắc) — 1-2 phút, mô tả ngắn + trạng thái + link PR/commit nếu có. Không dồn viết lại cuối tuần vì sẽ quên chi tiết thật.
>
> Các dòng có nguồn `git log` bên dưới là dựng lại từ lịch sử commit thật (`git log --all --pretty=...`) ngày 10/08/2026 để không bắt đầu từ file rỗng — **cột Time để trống vì git log không ghi lại thời gian thực tế bỏ ra**, member tự bổ sung nếu nhớ. Từ ngày 10/08/2026 trở đi, điền trực tiếp mỗi ngày, không suy ngược từ git log nữa.

---

## 2026-08-01 — 2026-08-08 (chuẩn bị trước Gate 2, dựng lại từ git log — nhiều ngày gộp 1 bảng vì khối lượng việc rải rác)

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| haidang2425 | Dọn docs cũ, dựng bộ `docs/planning/v2` (PRD/SRS/Execution Plan bản đầu), viết UI/UX brief | ✅ Done | Commit `a298878`→`2a87bba` | - |
| haidang2425 | Dựng lại frontend 3 phiên bản (v01→v03), chốt bản giữ | ✅ Done | Commit `c016b09`, `179569a`, `2a87bba` | - |
| haianh06 | Auth flow (login/register/reset password/email verification), JWT config, RBAC middleware, session model | ✅ Done | Commit `8b6a0ec`(gốc)…`13:48 06/08` | - |
| chungnguyenvp | Merge nhánh `haidang2425` vào `chung`, wire M1 demo flow | ✅ Done | Commit `96923cd`, `9d44dd1` | - |
| haianh06 | Tích hợp Google Gemini vào env config, refactor Docker, thêm upload file tài liệu môn, QA service (normalization + intent handling) | ✅ Done | Commit `c7c011c`, `74f5248` | - |

**Tổng kết:** nền tảng auth + RBAC + kết nối Gemini đã có trước khi bước vào lịch Gate 2 chính thức (09/08) — đúng tinh thần "đã có kinh nghiệm làm phần này trước" mà `03-Cursus-Execution-Plan.md` dùng làm căn cứ nâng mục tiêu Gate 2 lên ~60%.

---

## 2026-08-08 — Hợp nhất backend/auth vào 1 stack Vite duy nhất

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| haianh06 | Merge backend/auth (nhánh `haianh`) vào UI Vite chung, bỏ hẳn phần Next.js còn sót | ✅ Done | Commit `1650d18`, `7aa2017` ("Ship Vite Cursus stack: RBAC, Ink theme, Postgres deploy, drop Next leftovers") | - |

**Tổng kết:** đây là mốc gộp code quan trọng — từ đây frontend chỉ còn 1 stack (Vite), không còn 2 bản song song. Cần xác nhận lại `frontend/` hiện tại đúng là bản Vite này, không phải bản Next.js `00-Cursus-Playbook.md`/`03` vẫn đang nhắc tới (`types.ts`/`demo-service.ts`) — **rủi ro lệch docs vs code thật, kiểm tra lại trước khi Người C tiếp tục theo hướng dẫn ở `00` PHẦN 6**.

---

## 2026-08-09 — Ngày 1 Gate 2 (theo lịch `03-Cursus-Execution-Plan.md`)

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| NguyenThanhBinh108 | Sửa AI-log hook (bật ghi model + token usage, khôi phục PostToolUse) | ✅ Done | Commit `3e3754b` | - |
| NguyenThanhBinh108 | Kích hoạt lại trạng thái loading/error đang bị "chết cứng" ở FE | ✅ Done | Commit `ab425f0` | - |
| NguyenThanhBinh108 | Dựng lại Admin Console — F6 (bảng curriculum) + F7 (KPI) | ✅ Done | Commit `6f1fdc7` | - |
| NguyenThanhBinh108 | Fix biểu đồ lớp bị "làm phẳng" và sĩ số bị bịa số liệu | ✅ Done | Commit `8b6a0ec` | - |
| NguyenThanhBinh108 | Thêm cấu hình Vercel + hướng dẫn deploy | ✅ Done | Commit `7f0da18` | - |
| NguyenThanhBinh108 | Dọn lại AI-log: điền prompt thật vào mỗi entry, bỏ phần thừa | ✅ Done | Commit `560b93d` | - |

**Tổng kết ngày:** F6/F7 (Admin Console) đã có code thật dù theo `01-Cursus-PRD.md` mục 8.1 các tính năng này thuộc **Mốc 3**, không phải Gate 2 Must — cần xác nhận với team đây là làm sớm chủ động (tốt) chứ không phải lệch phạm vi khỏi kế hoạch `03`. Đồng thời phát hiện 1 chi tiết đáng chú ý: sửa lỗi "sĩ số bị bịa số liệu" ở biểu đồ GV đúng là loại lỗi mà nguyên tắc "không bịa" của cả sản phẩm (mục 1.3 `02-SRS.md`) đặt ra — tốt vì đã bắt và sửa sớm.

---

## 2026-08-10 — Ngày 2 Gate 2

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| haidang2425 | Rà soát toàn bộ docs `planning/v2`, sửa gap: cập nhật ngày lịch trình, đổi tên model Gemini đã hết hạn (`gemini-1.5-*`/`text-embedding-004` → `gemini-2.5-*`/`gemini-embedding-001`), thêm ADR log, mapping CP1/CP2/CP3, FR-1.3 xoá dữ liệu SV | ✅ Done | `docs/decisions/ADR.md` (mới), sửa `01`/`02`/`00`/`03`/`04`/`06`/`07` | - |

**Tổng kết ngày:** _(điền tiếp — việc code thật trong ngày của Người A/B/C, chưa có trong git log lúc file này được cập nhật)_

---

<!-- Từ đây trở đi: mỗi ngày code copy khối bảng bên dưới, điền tay, KHÔNG suy ngược từ git log nữa. -->

<!-- [Khung 22/08] Khoảng trống 11/08-21/08 chưa có ngày nào được điền — tự điền lại theo `git log` + trí nhớ thật nếu muốn dựng lại, đừng để trống khi nộp bài. Ngày 22/08 đã có tóm tắt sẵn trong docs/archive/SESSION_REPORT_20260822.md nếu cần đối chiếu khi viết dòng cho ngày đó. -->

## 2026-08-22

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| | | | | |

**Tổng kết ngày:**

---

## [YYYY-MM-DD]

| Member | Task | Status | Output | Time |
|--------|------|--------|--------|------|
| | | | | |

**Tổng kết ngày:**
