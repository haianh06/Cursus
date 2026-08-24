# Kim chỉ nam đọc tài liệu — đọc file này TRƯỚC, trước cả README.md

Repo có **~80 file `.md`**. Không ai — kể cả người trong team — cần đọc hết. File này là bộ lọc: bạn là ai (giám khảo, hay 1 trong 4 thành viên) → đọc đúng vài file → bỏ qua phần còn lại mà không sợ bỏ sót gì quan trọng.

**Cập nhật:** 11/08/2026. Nếu bạn thấy file này với danh sách file không khớp thực tế (đường dẫn sai/file không tồn tại) — nghĩa là docs đã đổi mà file này chưa cập nhật theo, báo lại để sửa, đừng tự suy đoán.

---

## 1. Dành cho Ban Giám Khảo / Mentor (~20-30 phút, đọc đúng thứ tự)

Không cần đọc gì ngoài 8 dòng dưới đây để đánh giá đủ CP1 (bài toán/giá trị), CP2 (triển khai), CP3 (ứng dụng AI) và 8 PLO.

| # | Đọc gì                                                                                                       | Biết được gì                                                                                                            | Thời gian |
| - | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ---------- |
| 1 | [`README.md`](README.md)                                                                                       | Sản phẩm là gì, vấn đề/giải pháp, tech stack thật, trạng thái hiện tại                                         | 3 phút    |
| 2 | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) mục 2 | Đề bài gốc, tuyên bố sản phẩm, phạm vi Gate 2, giới hạn cố ý (đối chiếu yêu cầu BTC EDU-01) | 5 phút    |
| 3 | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) mục 3–6                                       | Phạm vi sản phẩm, persona, role/quyền hạn, trang/chức năng (spec sản phẩm hiện hành)                                                      | 5 phút    |
| 4 | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) mục 13, 16, 21                     | Feature Plan → Do → Reflect cụ thể, input/output/API thật của từng tính năng, acceptance criteria                                                       | 5 phút    |
| 5 | [`docs/decisions/ADR.md`](docs/decisions/ADR.md)                                                               | Quyết định kỹ thuật quan trọng + lý do + đánh đổi (nhật ký quyết định BTC yêu cầu)                         | 5 phút    |
| 6 | [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md) mục 14 (Guardrail matrix + Risk score)                  | An toàn/kiểm soát AI (PLO6): guardrail chặn "làm hộ bài", HITL, giới hạn hệ thống                                 | 3 phút    |
| 7 | [`docs/archive/planning-v2/08-Cursus-Deliverables-Checklist.md`](docs/archive/planning-v2/08-Cursus-Deliverables-Checklist.md) | 10 deliverable BTC yêu cầu, cái nào xong/chưa, thang điểm 50 (checklist gốc, giữ ở archive vì chưa có bản thay thế) | 3 phút    |
| 8 | [`eval/results/report.md`](eval/results/report.md)                                                             | Số liệu eval/benchmark thật (PLO7) — kết quả Gate 2 (guardrail + RAG citation), xem mục 4 bên dưới                      | 1 phút    |

**Nếu chỉ có 5 phút:** đọc mục 1 và 2. **Nếu cần xem giao diện hiện có trông thế nào:** không có tài liệu spec pixel-accurate riêng nữa (xem ghi chú 18/08/2026 dưới đây) — đọc trực tiếp `frontend/src/components/` + `frontend/src/index.css`, hoặc mục 6 của `docs/PROJECT_CONTEXT.md` cho yêu cầu tính năng/dữ liệu từng trang. **Nếu cần script demo/dữ liệu mẫu:** `docs/PROJECT_CONTEXT.md` mục 18-19.

**Cập nhật 15/08/2026 — gộp docs 2 đợt, `docs/product/` không còn tồn tại, còn 2 file spec sống:** bộ 4 file cũ trong `docs/product/` (`blueprint.md`, `data-contract.md`, `build-and-demo-plan.md`, `ai-coding-prompt.md`) và `docs/product/{landing-auth-ui-ux,floating-widgets-ui-ux}.md` đã được gộp vào **`PROJECT_CONTEXT.md`** (business/product/role/page + mục 13-22: data/API/business rules/demo script/deploy — từng tách riêng `TECHNICAL_SPEC.md`, nay đã gộp lại vào đây) và **`FRONTEND_SPEC.md`** (UI/UX, mới lúc đó — trước đây frontend không có spec riêng). `docs/01_PRODUCT_UX_DECISIONS.md`/`02_SYSTEM_DECISIONS.md`/`03_CURRENT_STATE_AND_OPTIONS.md`/`docs/discovery/*`/`docs/decisions/deploy-platform-comparison.md` cũng đã gộp/xoá theo (quyết định trong đó đã chốt xong, không còn giá trị so sánh phương án nữa). `docs/archive/planning-v2/` (00-11 + `roles/`/`progress/`) **vẫn giữ nguyên, không đụng tới** — vẫn là nguồn cho B2B2C pivot/ERD multi-tenant chi tiết và hệ thống theo dõi tiến độ ở mục 2 dưới đây.

**Cập nhật 18/08/2026 — `docs/FRONTEND_SPEC.md` đã bị xoá hẳn (commit `e53b6a0`, 16/08/2026, khi viết lại toàn bộ frontend) và có chủ đích KHÔNG tạo lại.** Quyết định: để docs mô tả tính năng/dữ liệu cần có (mục 6 + 16 của `docs/PROJECT_CONTEXT.md`), không khoá cứng giải pháp thị giác (màu/layout/copy) trong 1 file spec riêng — tránh việc 1 bản thiết kế cũ (có thể lỗi thời/sai) bị hiểu nhầm là ràng buộc bắt buộc cho lần thiết kế lại sau. Mọi dòng bên dưới còn nhắc `docs/FRONTEND_SPEC.md` là tham chiếu lịch sử, không phải đường dẫn còn tồn tại.

---

## 2. Dành cho từng thành viên team

> ⚠️ **Quan trọng (chốt 12/08/2026, tránh hỏi lại):** 4 file `roles/*.md` bên dưới là để **mỗi người tự vibe-code UI/UX riêng, mục đích chính là để họ test backend/luồng hoạt động phần mình phụ trách** — không phải bản giao diện cuối cùng sẽ merge. **Đăng (nhóm trưởng) là người trực tiếp thiết kế + code hoàn chỉnh toàn bộ frontend production cho cả 4 role** (Public/Auth + Student + Instructor + Admin), dùng mock-data layer chất lượng cao để test độc lập với backend, rồi tự kiểm tra/merge toàn bộ luồng hoạt động cuối cùng. Vì vậy: nếu thấy giao diện Đăng code khác với những gì role doc mô tả, **giao diện của Đăng mới là bản chính thức** — role doc của bạn vẫn đúng về API/luồng nghiệp vụ, chỉ khác ở phần UI cuối cùng. Không cần hỏi lại "ai được sửa file frontend nào" — Đăng được sửa toàn bộ `frontend/src/components/**`.

**Mỗi người có 1 file riêng, chỉnh chu, đủ để "vibe code" thẳng** — mô tả UI/UX cụ thể (kèm ASCII layout từng màn), sản phẩm tham khảo thật (quốc tế + Việt Nam + link GitHub, ghi rõ học gì/đừng bắt chước gì), đặc tả tính năng có ví dụ input/output cụ thể, lịch theo ngày, checklist Definition of Done, và **prompt vibe-code sẵn dùng copy-paste cho Gemini/Antigravity** ở cuối mỗi file. Đây là file **chính** cần đọc cho việc code hàng ngày — `09-Cursus-Team-Assignment.md` chỉ còn là bản tóm tắt/tra cứu nhanh khi cần nhìn tổng thể.

### 2.1 Bảng tổng quan 4 role — nhìn 1 lần biết hết ai làm gì

| | 🔵 Trịnh Hải Đăng | 🟢 Nguyễn Hải Anh | 🟠 Nguyễn Anh Bình | 🟣 Nguyễn Đức Chung |
|---|---|---|---|---|
| **Vai trò** | Nhóm trưởng — Hạ tầng/Auth/Khung frontend/Data/Canvas ảo | Sinh viên | Giảng viên | Admin |
| **Tính năng sở hữu** | F1 (Auth) + nền tảng dùng chung | F2 (Plan), F3 (Q&A), Reflect | F4 (Dashboard lớp), F5 (Risk + HITL) | F6 (Curriculum), F7 (KPI) |
| **Doc chi tiết** | [`roles/DANG_infra-auth-frontend.md`](docs/archive/planning-v2/roles/DANG_infra-auth-frontend.md) | [`roles/HAIANH_student.md`](docs/archive/planning-v2/roles/HAIANH_student.md) | [`roles/BINH_instructor.md`](docs/archive/planning-v2/roles/BINH_instructor.md) | [`roles/CHUNG_admin.md`](docs/archive/planning-v2/roles/CHUNG_admin.md) |
| **File tiến độ (tick hàng ngày)** | [`progress/DANG.md`](docs/archive/planning-v2/progress/DANG.md) | [`progress/HAIANH.md`](docs/archive/planning-v2/progress/HAIANH.md) | [`progress/BINH.md`](docs/archive/planning-v2/progress/BINH.md) | [`progress/CHUNG.md`](docs/archive/planning-v2/progress/CHUNG.md) |
| **File frontend chính** | 6 màn `components/auth/*` | `components/student/StudentHome.jsx`, `StudentReflection.jsx` | `components/instructor/InstructorHome.jsx` (+ Risk Detail mới) | `components/admin/AdminConsole.jsx` |
| **File backend chính** | Toàn bộ `src/` (đã hợp nhất từ `develop`) | `src/api/plans.py`, `qa.py`, `student.py` | `src/api/instructor.py` | `src/api/admin.py` |
| **Trạng thái backend (13/08)** | ✅ Đã hợp nhất từ nhánh `develop` vào `haidang2425` | ✅ Đã hợp nhất | ✅ Đã hợp nhất | ✅ Đã hợp nhất |
| **Việc chặn bạn** | Không còn — hợp nhất backend/frontend đã xong trong phiên làm việc này | Không còn | Không còn | Không còn |
| **Milestone 13/08 (T5)** | Auth thật chạy đầu-cuối | F2 + F3 nối API thật | F4 + F5/HITL nối API thật | Curriculum + KPI nối API tự viết |
| **Sản phẩm tham khảo chính** | Supabase Auth, Clerk | Sunsama, Khanmigo | Starfish (EAB), Civitas Learning | LangSmith, Base.vn/Haravan |

**Nếu 5 ô "Milestone 13/08" ở cả 4 doc chi tiết đều xanh (xem `make progress`) → luồng demo 6 bước ở `09-Cursus-Team-Assignment.md` mục 4 chạy được đầu-cuối, đúng mục tiêu Thứ Năm.**

### 2.2 Theo dõi tiến độ — không cần hỏi ai bằng lời nói nữa

Mỗi người tick `[x]` vào đúng file của mình trong `docs/archive/planning-v2/progress/` khi việc **đã test thật** (không phải "code xong nhưng chưa chắc chạy"), commit thường xuyên. Nhóm trưởng (hoặc bất kỳ ai) xem tiến độ bằng:

```bash
# Bảng tổng quan tất cả mọi người — chạy được trên PowerShell/CMD/Bash, không cần cài gì thêm
python scripts/progress_report.py

# Xem riêng từng người, kèm danh sách chi tiết còn thiếu việc gì
python scripts/progress_report.py --person DANG
python scripts/progress_report.py --person HAIANH
python scripts/progress_report.py --person BINH
python scripts/progress_report.py --person CHUNG

# Có cài `make` thì gõ tắt: make progress · make progress-snapshot (ghi file để commit làm mốc lịch sử)
```

Chi tiết đầy đủ cách dùng + quy tắc tick: [`docs/archive/planning-v2/progress/README.md`](docs/archive/planning-v2/progress/README.md).

### 🔵 Trịnh Hải Đăng (nhóm trưởng — hạ tầng/auth/khung frontend/data/Canvas ảo)

**Đọc chính:** [`docs/archive/planning-v2/roles/DANG_infra-auth-frontend.md`](docs/archive/planning-v2/roles/DANG_infra-auth-frontend.md) (đặc biệt mục 1 "Job #0" — làm trước mọi thứ khác) → `docs/decisions/ADR.md` → `docs/project/structure-team.md`/`structure-btc.md` (bản đồ toàn repo, bạn cần biết rõ nhất).
**Không cần đọc kỹ:** `docs/archive/guide/` (giáo trình BTC, đã setup xong thì thôi).

### 🟢 Nguyễn Hải Anh (Sinh viên — F2 Plan, F3 Q&A, Reflect)

**Đọc chính:** [`docs/archive/planning-v2/roles/HAIANH_student.md`](docs/archive/planning-v2/roles/HAIANH_student.md) — có sẵn UI hiện có/cần đổi gì, API cụ thể, ví dụ input/output thật, prompt vibe-code.
**Không cần đọc:** `docs/archive/planning-v2/06` (hạ tầng, việc của Đăng), `docs/archive/guide/langgraph/` (trừ khi bạn tự đụng vào agent backend).

### 🟣 Nguyễn Đức Chung (Admin — F6 curriculum, F7 KPI)

**Đọc chính:** [`docs/archive/planning-v2/roles/CHUNG_admin.md`](docs/archive/planning-v2/roles/CHUNG_admin.md) (⚠️ mục 1 — đọc kỹ, bạn là người duy nhất phải TỰ XÂY API mới, không chỉ nối cái có sẵn).
**Không cần đọc:** `docs/archive/planning-v2/05` (đối thủ, không liên quan việc bạn code). (Bộ audit design system `docs/frontend/01-08` đã gộp/xoá trong đợt dọn trước — nội dung tương đương nay nằm ở `docs/FRONTEND_SPEC.md` mục 5.)

### 🟠 Nguyễn Anh Bình (Giảng viên — F4 dashboard, F5 risk + HITL)

**Đọc chính:** [`docs/archive/planning-v2/roles/BINH_instructor.md`](docs/archive/planning-v2/roles/BINH_instructor.md) — UI hiện có/cần build mới (Risk Case Detail), API cụ thể, ví dụ input/output thật, prompt vibe-code.
**Không cần đọc:** `docs/archive/planning-v2/04` (thuật ngữ, tra khi cần chứ không đọc hết).

### Cả 4 người, bất kể role

- **Trước khi tạo file/API/component mới:** kiểm tra bảng phân loại ở mục 4 bên dưới xem đã có sẵn chưa.
- **Trước khi báo "xong" 1 việc:** tick vào file `docs/archive/planning-v2/progress/<TÊN>.md` tương ứng và commit (xem mục 2.2).
- **Cuối mỗi ngày:** thêm 1 dòng vào [`WORKLOG.md`](WORKLOG.md). **Cuối mỗi tuần:** cập nhật [`JOURNAL.md`](JOURNAL.md).
- **Không tự sửa** `frontend/src/index.css` hay bất kỳ file trong `components/shared/` mà không báo Đăng trước (dùng chung cho cả 4 màn).

---

## 3. Nguyên tắc chung: file nào được sửa, file nào chỉ đọc

- 🟢 **Đọc + có thể sửa khi việc của bạn động tới:** `docs/PROJECT_CONTEXT.md`, `docs/archive/planning-v2/*`, `docs/project/*`, `docs/decisions/ADR.md`, `JOURNAL.md`, `WORKLOG.md`, `README.md`. (`docs/FRONTEND_SPEC.md` đã xoá 16/08/2026, không còn tồn tại — xem mục 1.)
- ⚪ **Đọc 1 lần lúc setup, sau đó bỏ qua:** toàn bộ `docs/archive/guide/` (38 file — giáo trình 10 chương của BTC, generic cho mọi đề tài, không mô tả Cursus — **[SỬA 23/08] đã dời từ `docs/guide/` vào `docs/archive/` để gọn gốc `docs/`, nội dung không đổi**).
- 🔒 **File gốc BTC, không được sửa nội dung (nếu cần thay đổi, xem `docs/project/structure-team.md` mục 2.8):** `docs/reference/btc-template/*`.

---

## 4. Bảng phân loại toàn bộ tài liệu trong repo

| Vị trí                                                               | Là gì                                                                                                  | Trạng thái                                                                   |
| ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `README.md`                                                          | Điểm vào chính — đọc đầu tiên                                                                  | 🟢 Chủ động                                                                 |
| `ARCHITECTURE.md`                                                    | Deliverable#3 BTC yêu cầu — đã điền 15/08/2026                                                                              | 🟢 Chủ động, cập nhật khi kiến trúc đổi                          |
| `JOURNAL.md`, `WORKLOG.md`                                         | Nhật ký tuần/ngày                                                                                    | 🟢 Điền liên tục                                                           |
| `docs/PROJECT_CONTEXT.md`                                          | **Business/product/role/page — file quan trọng nhất, dán thẳng cho AI coding assistant làm context** | 🟢 Chủ động — đọc trước mọi thứ khác |
| ~~`docs/FRONTEND_SPEC.md`~~                                      | Đã xoá 16/08/2026 (commit `e53b6a0`), có chủ đích không tạo lại — xem ghi chú 18/08 ở mục 1. Thay thế: đọc `frontend/src/` + `docs/PROJECT_CONTEXT.md` mục 6/16 | ⚫ Không còn tồn tại                                    |
| `docs/PROJECT_CONTEXT.md` mục 13-22                                 | Data/API contract, business rules (risk score, guardrail), demo script, deploy                                                          | 🟢 Chủ động trước Gate 2/demo                                             |
| `docs/archive/planning-v2/README.md`                                         | Mục lục bộ PRD/SRS/kế hoạch **cũ (đã superseded bởi `docs/product/`)**                                                                        | 🟡 Lịch sử — tham khảo khi cần bối cảnh phân công/hạ tầng/tiến độ                                                            |
| `docs/archive/planning-v2/00`–`11` | Playbook, PRD, SRS, kế hoạch, thuật ngữ, đối thủ, hạ tầng, checklist, phân công team, auth/onboarding/sandbox B2B2C + ERD multi-tenant — **bản gốc lịch sử, spec hiện hành đã chuyển sang `docs/product/blueprint.md`** | 🟡 Tham khảo khi cần chi tiết lịch sử/phân công team không có trong `docs/product/` |
| `docs/archive/planning-v2/roles/*` (4 file) | **Docs riêng từng người** (lịch sử) — UI/UX cụ thể lúc bắt đầu code, tham khảo sản phẩm thật, đặc tả tính năng, lịch theo ngày, prompt vibe-code | 🟡 Tham khảo lịch sử — vai trò hiện tại đã hợp nhất vào frontend/backend thật |
| `docs/archive/planning-v2/progress/*` (5 file + README) | Checklist tiến độ từng người (lịch sử), tick khi việc đã test thật — nguồn dữ liệu cho `make progress` | 🟡 Tham khảo lịch sử tiến độ team |
| `docs/planning/v2/data/`, `scripts/`                               | Dữ liệu mẫu + script sinh/parse dữ liệu — **vẫn ở vị trí gốc** (hardcode trong `src/services/rag.py`, `demo_data.py`, `eval/run_eval.py`, không di chuyển) | 🟡 Tham khảo khi cần ingest thêm môn                                       |
| `docs/project/run-guide.md`                                          | Hướng dẫn chạy dự án chi tiết (khắc phục lỗi `.venv` Windows) — bản quick-start hiện hành ở `RUNNING.md` (root) | 🟢 Chủ động lúc setup máy mới                                            |
| `docs/project/logging-guide.md`                                      | Cơ chế AI usage logging                                                                                | 🟡 Tham khảo khi hook lỗi                                                    |
| `docs/project/structure-btc.md`, `structure-team.md`               | Bản đồ toàn bộ repo, phân BTC/team                                                                 | 🟡 Tham khảo khi lạc đường / audit repo                                   |
| `docs/decisions/ADR.md`                                              | Quyết định kỹ thuật quan trọng                                                                     | 🟢 Chủ động, deliverable bắt buộc                                         |
| `docs/reference/btc-template/*`                                      | README/boilerplate gốc BTC, chưa sửa                                                                  | 🔒 Chỉ đối chiếu                                                           |
| `docs/archive/guide/` (38 file)                                              | Giáo trình kỹ thuật 10 chương của BTC, generic                                                    | ⚪ Đọc 1 lần lúc mới bắt đầu                                           |
| `eval/results/report.md`                                             | Báo cáo eval/benchmark — số liệu Gate 2 thật (guardrail 30/30, RAG citation 24/25)                     | 🟢 Chủ động, đã có số liệu thật                             |
| `presentation/README.md`                                             | Hướng dẫn chuẩn bị pitch deck/video                                                                 | 🟡 Đọc gần Demo Day                                                         |
| `AI20K-Log-Bridge/`                                                  | Extension log AI ngoài CLI (ChatGPT/web)                                                                | 🟡 Chỉ cần nếu bạn dùng AI qua trình duyệt                              |

---

## 5. Còn thiếu, chưa gán cho ai (nói thẳng ra để không ai tưởng đã xong)

| Việc                               | Vị trí cần điền             | Ghi chú                                                                                                                   |
| ----------------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Pitch deck + video demo             | `presentation/`                | Chưa làm, dời Mốc 3                                                                                                    |

`ARCHITECTURE.md` đã điền xong 15/08/2026 (system overview, 2 sơ đồ mermaid, component/data-flow/deployment/security/design decisions) — không còn nằm trong bảng "chưa gán cho ai" nữa.

---

## 6. Đã dọn trong đợt rà soát 11/08/2026 (để biết vì sao 1 số đường dẫn cũ không còn đúng)

- `docs/design/` (5 file) → gộp vào `docs/history/design-v1-deprecated/` (đã deprecated từ trước, giờ dọn khỏi vị trí "đang dùng" để đỡ gây nhầm).
- `docs/architecture/` (2 file) → gộp vào `docs/frontend/09`, `10` (cùng 1 đợt audit, tách 2 nơi không có lý do).
- `docs/project/repo-audit.md` → dời sang `docs/history/2026-08-repo-audit-snapshot.md` (là snapshot lịch sử, không phải doc vận hành).
- Root: xoá `implementation_plan.md`, `walkthrough.md` (gộp vào `docs/history/`), `logo.png` (rác mồ côi), dời `RUN_GUIDE.md` → `docs/project/run-guide.md`.
- File gốc BTC (`README.md`, `README_boilerplate.md`) khi bị viết đè — không xoá, giữ nguyên văn ở `docs/reference/btc-template/`.
- **Thêm mới:** `docs/archive/planning-v2/roles/` — 4 file docs riêng cho từng thành viên (thay cho việc mỗi người tự đọc rải rác nhiều file rồi tự suy ra UI/UX phải làm sao).
- **Thêm mới:** `docs/archive/planning-v2/progress/` (5 file + README) + `scripts/progress_report.py` + `make progress`/`make progress-snapshot` — hệ thống theo dõi tiến độ bằng checklist + tool đọc tự động, thay cho việc phân công/kiểm tra tiến độ bằng lời nói. Xem mục 2.2 ở trên.

---

## 7. Đã dọn thêm trong đợt rà soát 11/08/2026 (buổi chiều — sau khi audit thấy frontend lệch design system)

- **`docs/history/` đã bị xoá hẳn** (7 file: `2026-08-frontend-premium-redesign.md`, `2026-08-repo-audit-snapshot.md`, `design-v1-deprecated/` 5 file) — không còn tồn tại trong repo (khác với đợt 11/08 buổi sáng ở mục 6, lúc đó mới chỉ *dời* vào `docs/history/`, chưa xoá hẳn). Mọi tham chiếu tới `docs/history/` trong `docs/frontend/00-08`, `docs/project/structure-team.md`, `docs/archive/planning-v2/roles/CHUNG_admin.md` đã được sửa lại để không trỏ vào đường dẫn chết. Lý do: không ai đọc (tự nhận 🔴 "đừng đọc trừ khi tò mò"), và `ADR.md`/`00_AI_CONTEXT_PACK.md` đã giữ đủ phần "vì sao" cần thiết.
- **Code chết đã xoá:** `frontend/src/components/AuthScreen.jsx` (bản pre-redesign, không route nào dùng), `frontend/src/components/shared/UIComponents.jsx` (thư viện component dùng chung nhưng **không màn nào import**, và bản thân nó trỏ tới token/class không còn tồn tại — không sửa được, chỉ có thể xoá), `frontend/src/App.css` (template Vite gốc, không được import ở đâu).
- **`frontend/docs/` đã xoá hẳn (12/08/2026)** — đã xoá nốt 4 file `_CLAUDE` còn lại (`STUDENT_FRONTEND_RESEARCH_CLAUDE.md`, `STUDENT_FRONTEND_VISUAL_SPEC_CLAUDE.md`, `STUDENT_FRONTEND_DATA_MAPPING_CLAUDE.md`, `STUDENT_FRONTEND_IMPLEMENTATION_PLAN_CLAUDE.md`, giữ lại từ đợt dọn 11/08 buổi chiều ở trên), theo đúng option (b) từng nêu ở đây. Lý do xoá hẳn thay vì dời vào `docs/frontend/`: 4 file này là kế hoạch "Stage A — chờ duyệt trước khi code Stage B" cho redesign trang Student, **chưa từng được duyệt/implement** (`StudentHome.jsx` vẫn giữ nguyên, không component nào trong kế hoạch tồn tại thật), tự trích dẫn 3 file "chị em" không còn tồn tại (`STUDENT_DASHBOARD_BENCHMARK_RESEARCH.md`, `STUDENT_DASHBOARD_RESEARCH_V2.md`, `11_STUDENT_DASHBOARD_SPECIFICATION.md` — đã bị xoá ở đợt 11/08), phần quan trọng nhất (so sánh 3 phương án A/B/C) chỉ tồn tại trong tin nhắn chat của phiên đó chứ không lưu thành file, và bản thân nội dung (ví dụ giả định `CuriChatLauncher.jsx` vẫn còn tính năng kéo-thả) đã bị code thật vượt qua ngay trong ngày. Chưa từng `git add` nên xoá không mất lịch sử gì. Nếu sau này cần redesign trang Student, làm nghiên cứu mới sẽ nhanh hơn gỡ rối bộ này.
