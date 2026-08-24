> **LƯU Ý:** Nhánh cleanup/repo-audit-20260820 đề cập trong tài liệu này đã hoàn thành nhiệm vụ, được merge toàn bộ vào nhánh haidang2425 và đã bị xóa.

# Audit nhánh `chung` (role Admin) — 23/08/2026

> Viết bởi Claude (agent), dựa trên: đọc trực tiếp code tại `origin/chung` (commit `5c6ea39`, README nội bộ ghi `edf55f2`) qua 1 worktree tách riêng (không đụng nhánh đang dùng), đối chiếu với `docs/Cursus_Admin_Role_Guide_2026-08-23.docx` do chính chung viết cùng ngày, và số liệu thử merge thật vào nhánh `cleanup/repo-audit-20260820`. Không suy đoán — mọi con số dưới đây đo được trực tiếp.

## 1. Tóm tắt 1 phút

Nhánh `chung` là **1 bản viết lại gần như toàn bộ vai trò Admin**, khác kiến trúc so với `AdminConsole.jsx` (8-tab) đang dùng ở nhánh hiện tại. Chất lượng code và tài liệu ở mức tốt, có bằng chứng test thật, nhưng:
- **Không thể merge trực tiếp** — migration chain và nhiều service lõi (`guardrail_service.py`, `llm.py`, `qa_answer_service.py`, `qa_service.py`) đã bị xoá/tách lại khác đi ở nhánh hiện tại, còn nhánh `chung` vẫn dựa trên bản cũ của các file đó.
- Bản thân team `chung` cũng tự nhận **chưa production-ready** (xem mục 6).
- Cách khả thi nhất là **port có chọn lọc từng phần UI/UX + endpoint**, không merge nguyên khối.

## 2. Quy mô thay đổi (đo thật)

| Chỉ số | Giá trị |
|---|---|
| Commit chưa có ở nhánh hiện tại | 188 |
| File khác biệt | 582 |
| Dòng thêm/xoá | +90.577 / -9.300 |
| Migration mới (sau điểm rẽ nhánh chung `20260816_guardrail_reviews`) | 20 file, tới `20260903_guardrail_event_retention` |
| File Admin frontend | 31 file, chia rõ `people/`, `governance/`, `audit/` |
| File backend Admin chính | 6 router + 2 service/security, tổng **2.981 dòng** |
| Kết quả thử merge thật (worktree cách ly) | **115 file xung đột** ngay bước tự động, gồm 4 service bị "xoá ở HEAD, sửa ở chung" |

## 3. Kiến trúc — theo tài liệu của chính chung + đối chiếu code

### 3.1 Điều hướng
Đổi từ **8 tab trong 1 trang** (`AdminConsole.jsx` hiện tại) sang **routed cockpit**: 7 route thật, chia 2 nhóm sidebar —

```
QUAN SÁT                    QUẢN TRỊ
├ Tổng quan                 ├ Chương trình học
├ Người dùng                ├ Tài khoản & lời mời
└ Yêu cầu dữ liệu           ├ Chính sách AI & rủi ro
                            └ Cấu hình & hệ thống
```

Thêm 2 route con: `/admin/students/:id` (Student 360) và `/admin/instructors/:id` (Instructor 360) — không có ở nhánh hiện tại.

### 3.2 Mô hình truy cập dữ liệu nhạy cảm — khác biệt lớn nhất

Nhánh hiện tại: Admin không có màn hình đọc dữ liệu gốc (raw) của từng sinh viên.

Nhánh `chung`: có **Student 360** — 1 tab tóm tắt + **8 tab dữ liệu gốc** (plans, coursework, reflection, conversations có transcript, risk/interventions, sessions, documents, access-history), theo mô hình "direct full read":

1. Đăng nhập Admin (role ADMIN)
2. Cộng thêm quyền `READ_SENSITIVE` đúng resource
3. **Ghi audit event TRƯỚC** (fail-closed: audit lỗi → rollback, không trả dữ liệu)
4. Trả về qua **DTO allow-list** (không dump JSON thô)

Đây từng qua 1 phiên bản cũ hơn có case/TOTP/session 30 phút (ADM-00→13, "case-driven cockpit") — **đã bỏ** ngày 23/08 để đơn giản hoá thành direct-read, theo đúng ghi chú trong tài liệu của chung. Đổi lại, `ACCESS_ANOMALY` (phát hiện chiếm tài khoản) hiện luôn rỗng vì direct-read không còn `session_id`.

### 3.3 MFA đã bị gỡ khỏi sản phẩm (23/08)

Nhánh `chung` xoá toàn bộ luồng MFA/TOTP (đăng nhập không còn bước mã 6 số). Bảng `mfa_*` vẫn giữ trong DB "để rollback rẻ", chưa drop. Đây là quyết định trái ngược với nhánh hiện tại (vẫn giữ MFA đầy đủ) — **cần founder quyết định hướng nào đúng**, không phải kỹ thuật đơn thuần.

### 3.4 Curriculum lifecycle

Thêm trạng thái xuất bản song song với trạng thái nạp: `Bản nháp → Sẵn sàng duyệt → Đã xuất bản → Đã lưu trữ`, cộng preview→publish→history→restore (cùng pattern versioning risk-policy đã có ở nhánh hiện tại, áp dụng thêm cho curriculum). Có 6 tiêu chí kiểm định tài liệu trước khi vào RAG (`official_scope`, `admin_source`, `sha256/checksum_matches_file`, `readable_file`, `has_chunks/chunk_limit`, `course_provenance`).

## 4. Đánh giá UI/UX

**Điểm mạnh, xác nhận qua đọc code thật (`AdminOverview.jsx`):**
- Comment giải thích rõ **lý do thiết kế**, không chỉ tả code — ví dụ: giới hạn work-queue preview 5 dòng có chú thích "an overview that renders every open item is a list page wearing a dashboard's name"; metric ẩn/hiện provenance có lý do UX rõ ràng ("provenance is real content but it is reference, not news").
- Xử lý đúng case "chưa đo được" thay vì bịa số 0% (`metricNoDenominator`).
- Accessibility: skip link, 44px touch target, `aria-labelledby` cho sidebar group khi collapsed — cùng chuẩn mà nhánh hiện tại cũng đang áp dụng.

**Điểm cần cân nhắc trước khi mang sang:**
- Admin ở nhánh `chung` có **hệ token màu riêng hoàn toàn** ("Ink & Citrine": nền giấy be `#FAF8F3`, chữ nghiêng chuyên đề, accent vàng đồng `#B7791F`, heading dùng serif `Source Serif 4`), scope riêng trong class `.admin-operations`, tách biệt hẳn khỏi Student/Instructor. Nhánh hiện tại đã tốn 1 đợt dọn riêng (đợt 8, `CHANGELOG.md`) để **hợp nhất 6 mã "xanh brand" khác nhau về đúng 1 token** — mang nguyên bộ màu riêng của Admin bên `chung` sang sẽ **lặp lại đúng vấn đề đó** (Admin nhìn khác hẳn Student/Instructor), trừ khi chủ động ánh xạ lại theo token hiện có.
- Kiến trúc route (`/admin/students/:id`, `/admin/instructors/:id`) đòi hỏi router cấp cao hơn những gì `AdminConsole.jsx` hiện tại có (state 1 trang, không phải nested route) — port UI nghĩa là viết lại phần điều hướng, không chỉ copy component.

## 5. Đánh giá code lõi & backend

- Router chia nhỏ theo trách nhiệm rõ ràng: `admin.py` (curriculum, 27 route), `admin_observability.py` (overview/360/raw-read, 24 route), `admin_invitations.py` (5), `admin_policy.py` (5), `admin_users.py` (3), `admin_settings.py` (2) — tách bạch hơn 1 phần so với `src/api/admin.py` hiện tại đang gộp chung.
- `sensitive_read_executor.py` + `sensitive_access.py` (~250 dòng) hiện thực đúng nguyên tắc "audit trước, trả dữ liệu sau, fail-closed" — đây là 1 pattern bảo mật tốt, đáng cân nhắc học hỏi cho bất kỳ tính năng đọc-dữ-liệu-nhạy-cảm nào sau này, kể cả khi không port nguyên UI.
- **Rủi ro nghiêm trọng chung tự nêu:** "Tài khoản Admin duy nhất hiện được bảo vệ bằng mật khẩu; MFA đã gỡ và kill switch cấu hình cũ (`ADMIN_OBSERVABILITY_ENABLED`/`ADMIN_SENSITIVE_READS_ENABLED`) không còn chặn được direct-read path." — tự nhận đây là rủi ro vận hành thật, không phải tôi suy diễn.

## 6. Trạng thái kiểm chứng — theo đúng số chung tự báo cáo (chưa tự kiểm chứng lại)

| Cổng | Kết quả chung tự đo | Ghi chú |
|---|---|---|
| Backend pytest | 956 passed, 5 skipped, 0 failed | Đo trong session 23/08 của họ, DB/migration riêng |
| Frontend `node --test` | 79 passed, 0 failed | |
| ruff | pass | |
| vite build | pass | |
| Migration | 1 head duy nhất (`20260903_guardrail_event_retention`) | Trong nhánh của họ — **không tương thích chain hiện tại** |
| Direct full read | 69/69 bước, 9/9 task, 5/5 điểm kiểm tay | Test thủ công trên Docker |

**Việc còn lại họ tự liệt kê (nguyên văn dịch):** ADM-14 đang verify (ledger cũ còn mô tả MFA/case/TOTP, cần viết lại); staging E2E thiếu artifact + sign-off; **"Merge develop: Chưa hoàn tất — cần giải overlap frontend và tạo/kiểm migration merge revision"** (tức chính họ cũng đang tự biết nhánh mình chưa merge được, không phải vấn đề riêng của nhánh này); kill switch không còn tác dụng; `ACCESS_ANOMALY` luôn rỗng; bảng `mfa_*`/case/session còn nợ lại trong schema chưa drop.

**Câu tự đánh giá của họ (nguyên văn dịch):** "Admin đã đủ để xem và thao tác trên môi trường dev theo scope hiện tại, nhưng **chưa nên gọi là production-ready**."

## 7. Vì sao không merge nguyên khối được (bằng chứng, không phải suy đoán)

Đã thử `git merge origin/chung --no-commit --no-ff` trong 1 worktree tách riêng (`/tmp/merge-test`, đã huỷ và dọn sạch, không ảnh hưởng nhánh thật). Kết quả:

- **115 file xung đột** ngay bước tự động.
- 4 file bị Git báo **"deleted in HEAD and modified in origin/chung"**: `src/services/guardrail_service.py`, `src/services/llm.py`, `src/services/qa_answer_service.py`, `src/services/qa_service.py`. Nhánh hiện tại đã tách/đổi tên các service này (cấu trúc domain-based `src/services/ai/`, `src/services/core/`...) từ trước khi nhánh `chung` tách ra tiếp tục sửa trên bản cũ — 2 bên không còn cùng 1 "sự thật" về cấu trúc thư mục service.
- Toàn bộ file test admin (`test_admin*.py`, `test_admin_migrations.py`...) xung đột dạng "add/add" — cả 2 bên cùng viết test mới cho cùng khu vực nhưng nội dung khác nhau hoàn toàn.

## 8. Khuyến nghị — cách lấy giá trị từ nhánh `chung` mà không phá nhánh đang dùng

**Không merge nguyên khối, kể cả sau 23/08**, trừ khi có hẳn 1 đợt riêng để: (a) viết lại 20 migration của `chung` thành 1-2 migration tương thích chain hiện tại, (b) rà từng conflict trong 4 service lõi bằng tay, (c) chạy lại toàn bộ pytest+build sau khi giải xong.

**Nếu muốn lấy giá trị nhanh, chọn port từng phần theo độ rủi ro tăng dần:**

1. **Rẻ, an toàn nhất — chỉ đọc để học ý tưởng, không copy code:** cách viết `SignalMetric` xử lý "chưa đo được" (mục 4), pattern audit-trước-trả-sau của `sensitive_read_executor.py` (mục 5) — áp dụng lại theo đúng code style hiện tại, không copy-paste.
2. **Trung bình — 1 tính năng độc lập, ít đụng migration:** Student 360 / Instructor 360 (đọc dữ liệu tổng hợp 1 sinh viên/giảng viên) — nếu port, nên **viết lại route + backend endpoint mới trên schema hiện tại**, không tái dùng migration của họ.
3. **Đắt, rủi ro cao — không khuyến nghị làm hôm nay:** chuyển hẳn kiến trúc điều hướng Admin từ tab sang routed cockpit, hoặc gỡ MFA — cả 2 đều là quyết định sản phẩm/kiến trúc lớn, cần founder chốt trước, không phải việc kỹ thuật đơn thuần gần giờ nộp.

## 9. Nguồn

- `origin/chung` @ `5c6ea39` (worktree tạm, đã dọn)
- `docs/Cursus_Admin_Role_Guide_2026-08-23.docx` (do chung viết, đọc bằng `python-docx`)
- Kết quả `git merge --no-commit --no-ff` thật trong worktree cách ly (đã huỷ)
