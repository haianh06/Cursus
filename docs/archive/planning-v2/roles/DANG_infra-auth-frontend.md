# Docs riêng — Trịnh Hải Đăng · Nhóm trưởng (Hạ tầng · Auth · Khung frontend · Data · Canvas ảo)

**Cập nhật:** 11/08/2026 · **Đọc cùng:** [`docs/frontend/00_AI_CONTEXT_PACK.md`](../../../frontend/00_AI_CONTEXT_PACK.md), [`../09-Cursus-Team-Assignment.md`](../09-Cursus-Team-Assignment.md) (mục 1 "Job #0" là phần quan trọng nhất bạn phải làm trước), [`../06-Cursus-Ha-tang-Supabase-Scale2000.md`](../06-Cursus-Ha-tang-Supabase-Scale2000.md), [`docs/decisions/ADR.md`](../../../decisions/ADR.md).

**Khác 3 người kia:** bạn không sở hữu 1 tính năng/màn hình cụ thể — bạn sở hữu **nền tảng mà cả 3 người kia đứng lên**. Nếu Job #0 chậm 1 ngày, cả team chậm theo. Đọc mục 1 trước tiên, đây là việc duy nhất thật sự "khẩn cấp" trong toàn bộ tài liệu này.

---

## 0. Bạn sở hữu gì

| Việc | Vì sao là của bạn | Ảnh hưởng nếu chậm |
|---|---|---|
| **Job #0** — tích hợp backend `origin/chung` vào frontend `haidang2425` | Việc dễ xung đột nhất, cần 1 người làm dứt điểm | Chặn cả 3 người còn lại — họ chỉ code UI chay được, không test nối API thật |
| F1 — Auth thật (**đổi 12/08: invite-only, không còn register công khai** — login/accept-invite/forgot/reset/verify/onboarding/demo-sandbox/request-access) | Đã nối API thật xong (`ADR-007`, `10-Cursus-Auth-Onboarding-Sandbox-Spec.md`) | Không ai vào được app bằng tài khoản thật |
| Deploy (Vercel + Railway + Supabase) | Deliverable #5 bắt buộc | Không có Live URL để nộp bài |
| Design system enforcement | Bạn là người viết `00_AI_CONTEXT_PACK.md`, hiểu rõ nhất | 4 màn dễ lệch nhau nếu không ai review |
| Data pipeline + "Canvas ảo" | `flm_parser.py`/`gen_seed_students.py`, `canvas_routes.py` đã có trên `chung` | Thiếu dữ liệu thật cho cả 3 role test |
| Backend security review | Bạn merge code, phải hiểu nó trước khi giao người khác build lên trên | Lỗ hổng bảo mật (CSRF/rate-limit/guardrail bypass) lọt qua |

---

## 1. Job #0 — làm trước tất cả mọi thứ khác (chi tiết đầy đủ ở `09-Cursus-Team-Assignment.md` mục 1, đây là bản rút gọn hành động)

**Phát hiện cốt lõi:** `origin/chung` (= `origin/haianh`, commit cuối 08/08) đã có backend gần như đầy đủ F1-F5 + Canvas mock — auth production-grade (MFA/TOTP, quên mật khẩu, xác thực email, session, RBAC, CSRF, rate-limit), `plans.py`, `qa.py`, `instructor.py`, `student.py`, `canvas_routes.py` (13 endpoint mock LMS), `audit.py`. Nhánh bạn đang đứng (`haidang2425`) có frontend đẹp nhưng backend rỗng.

**Việc làm theo thứ tự:**
1. Tạo branch `integration/backend-merge` từ `haidang2425`.
2. Copy `src/` của `origin/chung` đè lên (giữ nguyên `frontend/`) — cụ thể: `src/api/*`, `src/services/*`, `src/security/*`, `src/repositories/*`, `src/db/*`, `src/schemas/*`, `src/knowledge/*`, `src/prompts/*`, `requirements.txt`. Cân nhắc thêm `document_ingest_service.py`, `conversation_intent_service.py` từ `origin/thanhbinh` (Chung cần cái đầu tiên cho F6).
3. `.env`: `DATABASE_URL` Postgres thật (Supabase, ADR-001), `REDIS_URL`, JWT secret, `GOOGLE_API_KEY` (Gemini, ADR-002) — không dùng `OPENAI_API_KEY` mặc định của `.env.example` gốc BTC.
4. Chạy migration (`alembic upgrade head` hoặc tạo từ `src/db/models.py` nếu chưa có script).
5. Verify: `uvicorn src.main:app` chạy được, `/docs` liệt kê đủ 7 router (`routes`, `audit`, `auth`, `student`, `plans`, `qa`, `instructor`, `canvas`), `POST /api/v1/auth/login` trả JWT thật qua Swagger UI.
6. Viết `frontend/src/lib/api.js` mới (tham khảo cách `chung`'s `lib/api.js`/`lib/rbac.js` xử lý token, **không copy UI** từ đó) — đây là lớp duy nhất 3 người kia cần để bắt đầu nối `fetch()` thật.
7. Báo team ngay khi bước 5 xong — đừng đợi bước 6 hoàn thiện 100% mới cho 3 người bắt đầu, họ có thể tự viết phần gọi API của họ song song.
8. Đóng risk item ở `01-Cursus-PRD.md` mục 11, cập nhật `docs/project/structure-team.md` mục 2.1.

**Hạn:** hết ngày 12/08 (T4) — để 13/08 (T5) cả team còn thời gian ráp luồng demo hoàn chỉnh.

---

## 2. Ràng buộc bắt buộc (áp dụng cho toàn hệ thống, không riêng 1 màn)

1. ~~**Auth thật, không phải demo-login vĩnh viễn**~~ — **ĐÃ XONG (12/08/2026):** auth production-grade đã bật, invite-only cho cả 3 role, không còn form tự đăng ký công khai (`ADR-007`). Demo-login **vẫn tồn tại có chủ đích**, không phải nợ kỹ thuật cần dọn — nó là `/demo/select-role`, chỉ đăng nhập được vào tổ chức sandbox cô lập "Cursus Demo University", tách biệt hoàn toàn khỏi tài khoản thật.
2. **Không commit secret thật** — `.env` không bao giờ lên git, `AI_LOG_API_KEY` mỗi người dùng key riêng từ link mời BTC.
3. **1 remote Git, deploy bằng CLI thủ công** (ADR-003, đảo quyết định 11/08/2026) — không tạo repo riêng, không kết nối GitHub App của Vercel/Railway/Supabase vào đâu cả; migration/deploy chạy tay bằng `alembic upgrade head` / `railway up` / `vercel --prod`.
4. **Không đổi tên model AI mà không re-verify** (ADR-006) — Gemini đổi API rất nhanh, kiểm tra lại tên model tại nguồn chính thức trước khi hardcode vào `.env`/config.
5. **Design system là luật, không phải gợi ý** — khi review PR của Hải Anh/Chung/Bình, đối chiếu đúng `00_AI_CONTEXT_PACK.md` mục 11 (danh sách cấm), từ chối merge nếu vi phạm.

---

## 3. Tham khảo thật cho phần bạn phụ trách

| Sản phẩm | Link | Học cái gì cho Cursus | Đừng bắt chước |
|---|---|---|---|
| **Clerk** | Tham khảo | Prebuilt auth theme + `appearance` prop override — tham khảo cách tách biệt "logic auth" khỏi "giao diện auth" khi viết `lib/api.js`/`AuthContext`, để 6 màn auth hiện tại không phải sửa lại khi đổi provider | Clerk là dịch vụ trả phí đóng gói sẵn — Cursus tự viết trên Supabase Auth, không cần bắt chước kiến trúc SDK của họ |
| **Supabase Auth** | [supabase.com/docs/guides/auth](https://supabase.com/docs/guides/auth) | Đã là lựa chọn chính thức (ADR-001) — đọc kỹ phần Row Level Security trước khi merge `src/db/models.py`, đảm bảo RLS thật sự chặn sai quyền ở tầng DB, không chỉ ở code | |
| **Vercel + Railway dashboard** | vercel.com, railway.app | Cách hiển thị trạng thái deploy (build log realtime, rollback 1 click) — tham khảo khi viết hướng dẫn deploy cho team, không cần tự xây UI tương tự | |
| **kotaemon** (đã dẫn cho Hải Anh) | [github.com/Cinnamon/kotaemon](https://github.com/Cinnamon/kotaemon) | Xem cách họ tổ chức pipeline ingest tài liệu → chunk → embed, đối chiếu với `document_ingest_service.py` đã có trên `thanhbinh` khi merge cho Chung dùng | |

---

## 4. UI bạn phụ trách — màn Auth (đã có sẵn, đã nối API thật — 12/08/2026)

**Đổi so với bản gốc:** `RegisterScreen.jsx` (form tự đăng ký công khai) đã bị xoá, không còn tồn tại — thay bằng 3 màn mới đúng mô hình invite-only: `AcceptInviteScreen.jsx` (kích hoạt tài khoản từ lời mời), `DemoSelectRoleScreen.jsx` (sandbox 3 role, không cần tài khoản), `RequestAccessScreen.jsx` (form yêu cầu triển khai cho tổ chức). Toàn bộ màn: `AuthLayout.jsx`, `LoginScreen.jsx`, `AcceptInviteScreen.jsx`, `DemoSelectRoleScreen.jsx`, `RequestAccessScreen.jsx`, `ForgotPasswordScreen.jsx`, `ResetPasswordScreen.jsx`, `EmailVerificationScreen.jsx`, `OnboardingScreen.jsx`. Chi tiết screen spec đầy đủ: `10-Cursus-Auth-Onboarding-Sandbox-Spec.md` mục 5.

| Việc | Chi tiết |
|---|---|
| Nối API thật | `POST /auth/register` (nay bắt buộc `invite_token`), `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/demo-session`, `/admin/invites` — xem bảng đầy đủ ở `09-Cursus-Team-Assignment.md` mục 6 |
| Xử lý cookie access/refresh token | Theo đúng pattern `_set_auth_cookies`/`_extract_access_token` đã có sẵn trong `src/api/auth.py` trên `chung` — không tự chế cách lưu token khác (ví dụ localStorage) vì backend đã thiết kế theo httpOnly cookie |
| Chuyển đúng route theo role | Sau login, gọi `GET /auth/me` lấy role thật → `routeForRole()` (đã có sẵn trong `constants/roles.js`) — không hardcode role nữa |
| Gỡ cursor-parallax mascot | Đã bị flag trong `docs/frontend/06_MOTION_AND_MICROINTERACTIONS.md` §3 — làm cùng lúc khi động vào `AuthLayout.jsx` cho tiện, không cần PR riêng |
| Sửa comment sai trong `ThemeContext.jsx:17` | Bug nhỏ đã biết (doc 04 §1) — tiện tay sửa khi động vào file |

**Mascot Curi trong màn auth:** trạng thái `idle`/`typing-email`/`typing-password`/`error`/`success` đã đúng chuẩn, giữ nguyên (xem `docs/frontend/07_MASCOT_CURI_SPECIFICATION.md` §9 — Curi không bao giờ "nhìn" vào ô mật khẩu, đây là chi tiết đã làm đúng, đừng "sửa" nó).

---

## 5. Data pipeline + "Canvas ảo"

### 5.1 Data pipeline

`docs/planning/v2/scripts/flm_parser.py` (parse curriculum/syllabus `.docx` → JSON) và `gen_seed_students.py` (sinh SV mẫu) đã có sẵn. Việc Gate 2: xác nhận ≥3 môn đã ingest (SSA101 có sẵn). Việc Mốc 3: mở rộng ~10 môn ưu tiên năm 1-2 (theo risk register `01-PRD.md` mục 11).

### 5.2 "Canvas ảo" — đã có sẵn, việc là kiểm chứng không phải xây mới

`src/api/canvas_routes.py` trên `chung` đã có 13 endpoint mock LMS (`/canvas/users/{id}`, `/canvas/courses`, `/courses/{id}/enrollments`, `/modules`, `/assignments`, `/submissions`, `/files`, `/pages`, `/announcements`, `/quizzes`, `/calendar_events`) — đây chính là quyết định ADR-005 (Mock LMS API thay Canvas/LTI thật). Việc của bạn khi merge: chạy thử từng endpoint, xác nhận dữ liệu trả về khớp với dữ liệu đã ingest từ FLM (không lệch số môn/số SV giữa 2 nguồn).

---

## 6. Lịch làm việc theo ngày

| Ngày | Việc cụ thể |
|---|---|
| **11/08 (T3, hôm nay)** | Bắt đầu Job #0: tạo branch tích hợp, copy `src/` từ `chung`, cấu hình `.env` Postgres/Redis thật |
| **12/08 (T4)** | Hoàn tất Job #0 — backend chạy độc lập, `/docs` xác nhận đủ router, login thật trả JWT. Báo cả team ngay khi xong. Bắt đầu nối auth screens |
| **13/08 (T5) — mục tiêu "1 flow hoàn chỉnh"** | Auth thật chạy được (bước 1 trong luồng demo 6 bước, `09-Team-Assignment.md` mục 4). Hỗ trợ sửa lỗi tích hợp phát sinh cho cả 3 người. Deploy thử lên Railway/Vercel |
| **14/08 (Gate 2)** | Sáng: freeze code, chỉ sửa lỗi chặn demo |
| **15-22/08 (Mốc 3)** | Bật MFA/email-verify thật (đã có sẵn từ Job #0, chỉ cần bật UI); ingest mở rộng ~10 môn; kiến trúc chịu tải (API key rotation, rate-limit, cache, circuit breaker — `02-SRS.md` mục 4.2); load test k6 nếu xác nhận vẫn cần |
| **23/08** | Freeze, rượt demo, nộp bài |

---

## 7. Definition of Done — trước khi báo "hạ tầng xong"

- [ ] `uvicorn src.main:app` chạy được từ nhánh tích hợp chính, `/docs` liệt kê đủ 7 router
- [ ] `POST /auth/login` trả JWT thật, `GET /auth/me` trả đúng role
- [x] Màn auth nối API thật xong (12/08/2026) — không còn form tự đăng ký công khai; `/demo/select-role` là sandbox có chủ đích, không phải demo-login tạm cần dọn
- [ ] Có URL deploy truy cập được từ máy khác (không phải "chạy trên máy tôi")
- [ ] `.env`/secret không lọt vào git (kiểm tra `git status` trước mỗi commit)
- [ ] Đã review ít nhất 1 PR của mỗi người trong 3 người còn lại, đối chiếu `00_AI_CONTEXT_PACK.md`

---

## 8. Prompt mẫu — dán thẳng cho Gemini/Antigravity

```
Bạn là full-stack engineer cho Cursus (FastAPI + SQLAlchemy backend, React 19 + Vite + Tailwind v4 frontend).
Tôi là nhóm trưởng, phụ trách hạ tầng/auth/khung frontend dùng chung. Nhiệm vụ hiện tại: tích hợp backend
đầy đủ từ nhánh origin/chung vào frontend hiện tại của nhánh haidang2425 (frontend đẹp nhưng backend rỗng).

Context bắt buộc đọc trước (tôi đã dán/đính kèm):
- docs/frontend/00_AI_CONTEXT_PACK.md (design system)
- Nội dung file docs/archive/planning-v2/roles/DANG_infra-auth-frontend.md mục 1 (các bước Job #0 cụ thể)
- Nội dung docs/archive/planning-v2/09-Cursus-Team-Assignment.md mục 6 (bảng đầy đủ endpoint đã có sẵn)

Nhiệm vụ hôm nay: [ví dụ "Viết frontend/src/lib/api.js — client gọi API thật cho toàn bộ endpoint auth,
xử lý cookie access/refresh token theo đúng pattern _set_auth_cookies trong src/api/auth.py"].

Ràng buộc bắt buộc:
- Không đổi bất kỳ UI/JSX nào của 6 màn auth hiện có — chỉ thay lớp gọi dữ liệu.
- Token lưu qua httpOnly cookie theo đúng cách backend đã thiết kế, không tự ý chuyển sang localStorage.
- Giữ nguyên toàn bộ token màu/spacing/motion đã định nghĩa trong 00_AI_CONTEXT_PACK.md.
- Nếu phát hiện xung đột giữa code src/ của chung và cấu trúc hiện tại, dừng lại và báo cáo cụ thể file
  nào xung đột thay vì tự ý ghi đè.
```

---

## 9. Liên kết liên quan

[`docs/archive/planning-v2/06-Cursus-Ha-tang-Supabase-Scale2000.md`](../06-Cursus-Ha-tang-Supabase-Scale2000.md) · [`docs/decisions/ADR.md`](../../../decisions/ADR.md) · [`docs/project/run-guide.md`](../../../project/run-guide.md) · 3 doc còn lại: [`HAIANH_student.md`](HAIANH_student.md), [`BINH_instructor.md`](BINH_instructor.md), [`CHUNG_admin.md`](CHUNG_admin.md).
