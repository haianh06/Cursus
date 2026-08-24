> **Superseded 2026-08-13** bởi [`docs/product/`](../../product/) — giữ lại để tham khảo lịch sử (phân công team, hạ tầng, tiến độ). Xem `docs/product/blueprint.md` cho spec sản phẩm hiện hành.

# Docs Ver 02 — Bộ tài liệu định hình & triển khai dự án Cursus

Đây là bộ tài liệu chính thức team dùng để định hình sản phẩm và triển khai — bản duy nhất, không còn `docs/planning/v1` (đã xoá; toàn bộ nội dung thật sự còn giá trị — thuật ngữ, roadmap kiến thức — đã gộp vào `04-Cursus-Terminology.md`, phần còn lại là nháp lỗi thời không cần giữ).

## Thứ tự đọc

| # | File | Nội dung |
|---|------|----------|
| 00 | [00-Cursus-Playbook.md](00-Cursus-Playbook.md) | Đọc trước tiên — feature spec F1-F7 đầy đủ input/output, tech stack, quy trình dữ liệu, phân công 4 người, kịch bản demo chính + kịch bản demo lỗi |
| 01 | [01-Cursus-PRD.md](01-Cursus-PRD.md) | Phạm vi, MVP theo mốc, persona |
| 02 | [02-Cursus-SRS.md](02-Cursus-SRS.md) | FR/NFR chi tiết |
| 03 | [03-Cursus-Execution-Plan.md](03-Cursus-Execution-Plan.md) | Lịch trình theo mốc |
| 04 | [04-Cursus-Terminology.md](04-Cursus-Terminology.md) | Thuật ngữ |
| 05 | [05-Cursus-Competitive-Analysis.md](05-Cursus-Competitive-Analysis.md) | Đối thủ, câu trả lời khi pitch |
| 06 | [06-Cursus-Ha-tang-Supabase-Scale2000.md](06-Cursus-Ha-tang-Supabase-Scale2000.md) | Hạ tầng chốt cuối (Supabase), đánh giá quy mô 2.000 người, menu lựa chọn kỹ thuật |
| 07 | [07-Cursus-Production-Readiness-Checklist.md](07-Cursus-Production-Readiness-Checklist.md) | Đánh giá kỹ thuật — docs còn thiếu gì để "chuẩn production" (dùng cho Mốc 3) |
| 08 | [08-Cursus-Deliverables-Checklist.md](08-Cursus-Deliverables-Checklist.md) | Tra cứu nhanh 10 deliverable BTC + thang điểm 50 |
| 09 | [09-Cursus-Team-Assignment.md](09-Cursus-Team-Assignment.md) | **Mới 11/08** — phân công theo role SV/GV/Admin/Hạ tầng tới hết dự án, kèm phát hiện quan trọng: backend thật đang nằm chưa merge trên branch `chung`. Đây là bản **tóm tắt** — bản đầy đủ nằm ở `roles/` bên dưới |
| 10 | [10-Cursus-Auth-Onboarding-Sandbox-Spec.md](10-Cursus-Auth-Onboarding-Sandbox-Spec.md) | **Mới 12/08** — B2B2C pivot: không còn public self-registration, invite-only provisioning, sandbox 3 role tại `/demo/select-role`. Research benchmark (Canvas/Moodle/Google Classroom/...), role-permission matrix, screen spec |
| 11 | [11-Cursus-ERD-Multitenancy.md](11-Cursus-ERD-Multitenancy.md) | **Mới 12/08** — ERD + schema multi-tenant (`organizations`/`organization_memberships`/`org_invites`), migration đã chạy thật, và finding quan trọng: RLS chưa có tác dụng thật (role DB có `BYPASSRLS`) |

> Bộ docs này không còn mô tả kỹ thuật thiết kế frontend chung (design system, layout màn hình...) — đã xoá `08-Cursus-UI-UX-Master-Spec.md` và `ui-ux-brief.md` theo yêu cầu; `docs/frontend/00_AI_CONTEXT_PACK.md` từng thay thế nhưng bản thân thư mục `docs/frontend/` cũng đã bị gộp/xoá sau đó — nội dung tương đương nay nằm ở `docs/product/blueprint.md` mục 6. Phạm vi tính năng/API/data shape vẫn còn ở `00`, `01`, `02` (bản lịch sử; spec hiện hành ở `docs/product/blueprint.md`). **UI/UX theo từng role cụ thể** (khác với design system chung) nằm trong `roles/` — xem mục dưới.

## Thư mục con

- **`roles/`** (mới 11/08/2026) — 4 file docs riêng cho từng thành viên, chỉnh chu để "vibe code" thẳng: mô tả UI/UX cụ thể từng màn (kèm ASCII layout), tham khảo sản phẩm thật (quốc tế + Việt Nam + link GitHub), đặc tả tính năng với ví dụ input/output cụ thể, lịch theo ngày, checklist Definition of Done, và prompt mẫu sẵn dùng để dán cho Gemini/Antigravity:
  - [`roles/DANG_infra-auth-frontend.md`](roles/DANG_infra-auth-frontend.md) — Trịnh Hải Đăng (hạ tầng/auth/khung frontend/data/Canvas ảo)
  - [`roles/HAIANH_student.md`](roles/HAIANH_student.md) — Nguyễn Hải Anh (Sinh viên — F2 Plan, F3 Q&A, Reflect)
  - [`roles/CHUNG_admin.md`](roles/CHUNG_admin.md) — Nguyễn Đức Chung (Admin — F6 curriculum, F7 KPI)
  - [`roles/BINH_instructor.md`](roles/BINH_instructor.md) — Nguyễn Anh Bình (Giảng viên — F4 dashboard, F5 risk + HITL)
- `data/` — dữ liệu mẫu/seed dùng cho phát triển và test:
  - `chunks_SSA101.json` — dữ liệu chunk từ syllabus môn SSA101
  - `courses_BIT_SE_K20D_K21A.json` — dữ liệu khoá học ngành BIT/SE khoá K20D, K21A
  - `seed_students_SSA101.json` — dữ liệu sinh viên mẫu môn SSA101
- `scripts/` — script hỗ trợ tạo/parse dữ liệu ở trên:
  - `flm_parser.py` — parse curriculum/syllabus (.docx) thành JSON (courses/chunks)
  - `gen_seed_students.py` — sinh dữ liệu sinh viên mẫu cho SSA101
