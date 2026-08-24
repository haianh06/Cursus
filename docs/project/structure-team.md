# Project Structure — Phần do Team tạo/chỉnh sửa

Tài liệu này mô tả các file/thư mục **do team tự tạo hoặc chỉnh sửa** để xây dựng
sản phẩm Cursus — tức không nằm trong template gốc của ban tổ chức (BTC).

Xác định qua `git log --diff-filter=A` / so sánh với **Initial commit** (`4741ab8`,
snapshot nguyên bản của template BTC) — mọi mục dưới đây **không tồn tại** trong
commit gốc.

Xem phần mô tả các file/thư mục do BTC cung cấp sẵn tại [structure-btc.md](structure-btc.md).

## Mục lục

- [2.1 `frontend/` — React + Vite UI (Cursus)](#21-frontend--react--vite-ui-cursus)
- [2.2 `AI20K-Log-Bridge/` — Chrome/Edge extension log AI ngoài luồng CLI](#22-ai20k-log-bridge--chromeedge-extension-log-ai-ngoài-luồng-cli)
- [2.3 `docs/planning/` — Tài liệu định hình sản phẩm](#23-docsplanning--tài-liệu-định-hình-sản-phẩm)
- [2.4 `docs/project/` — Tài liệu vận hành repo](#24-docsproject--tài-liệu-vận-hành-repo)
- [2.5 `docs/frontend/` — đã gộp/xoá, nội dung tương đương nay ở `docs/product/blueprint.md`](#25-docsfrontend--đã-gộpxoá-nội-dung-tương-đương-nay-ở-docsproductblueprintmd)
- [2.6 `docs/decisions/` — ADR (lịch sử quyết định)](#26-docsdecisions--adr-lịch-sử-quyết-định)
- [2.7 File root do team viết đè lên template BTC](#27-file-root-do-team-viết-đè-lên-template-btc)
- [2.8 `docs/reference/` — Bản gốc BTC giữ lại đối chiếu](#28-docsreference--bản-gốc-btc-giữ-lại-đối-chiếu)
- [2.9 Không xác định được nguồn gốc](#29-không-xác-định-được-nguồn-gốc)

---

## 2.1 `frontend/` — React + Vite UI (Cursus)

> **Cập nhật 11/08/2026 — thay thế toàn bộ mục 2.1 cũ:** bản mô tả trước đây (prototype Next.js 14 + TypeScript "StudyMate X", với `types.ts`/`demo-service.ts`/`app/` router) **đã bị bỏ hẳn** — xem commit `7aa2017` ("Ship Vite Cursus stack... drop Next leftovers"). Nội dung dưới đây là cấu trúc thật trên nhánh `haidang2425` (HEAD hiện tại) tính đến 11/08/2026.
>
> ⚠️ **Quan trọng — repo đang phân mảnh trên nhiều branch, mục này chỉ mô tả 1 nhánh:** `origin/chung`/`origin/haianh`/`origin/thanhbinh` có một bản `frontend/` **khác hẳn** (TypeScript, `AuthContext.jsx`, `lib/api.js` gọi API thật, `lib/rbac.js`, `vercel.json`) đi kèm một backend `src/` đầy đủ mà nhánh `haidang2425` không có. Xem phân tích đầy đủ + kế hoạch tích hợp ở `docs/archive/planning-v2/09-Cursus-Team-Assignment.md` mục "Job #0" — đừng dùng mục 2.1 này để giả định đó là toàn bộ sự thật của repo.

Không nằm trong template BTC (template chỉ gợi ý "Next.js/Streamlit" trong README, không có code). Stack: **React 19 + Vite + Tailwind CSS v4** (cấu hình CSS-native, không có `tailwind.config.js`), `react-router-dom` v7, Supabase JS (auth client), `lucide-react` (icon), oxlint (lint) — không TypeScript, không state-management library ngoài React Context.

**Cấu trúc `frontend/src/` (verified):**

```
frontend/src/
├── main.jsx                      # Entry point
├── App.jsx                       # App shell, routing, sidebar/topbar
├── App.css, index.css            # Tailwind + toàn bộ design token/utility class
├── assets/                       # hero.png, react.svg, vite.svg
├── constants/roles.js            # Nhãn role, demo user, route mặc định theo role
├── context/
│   ├── CursusContext.jsx         # ⚠️ Toàn bộ dữ liệu SV/GV/Admin — MOCK local state, chưa gọi API thật
│   ├── ThemeContext.jsx          # Light/dark, persist localStorage, anti-FOUC
│   └── LanguageContext.jsx       # EN/VI, default VI
├── lib/supabaseClient.js         # Supabase JS client
├── locales/{en,vi}.js            # Toàn bộ chuỗi UI song ngữ
└── components/
    ├── AuthScreen.jsx            # ⚠️ File rời ở gốc components/ — kiểm tra còn được import ở đâu không trước khi sửa, có thể là bản cũ trước khi tách thành components/auth/*
    ├── auth/                     # AuthLayout, LoginScreen, RegisterScreen, ForgotPasswordScreen, ResetPasswordScreen, EmailVerificationScreen, OnboardingScreen
    ├── shared/                   # LandingPage, Mascot (CursusMascot/MascotMini), CuriChatLauncher, ThemeToggle, LanguageToggle, UIComponents, NotFoundPage
    ├── student/                  # StudentHome.jsx, StudentReflection.jsx
    ├── instructor/                # InstructorHome.jsx
    └── admin/                    # AdminConsole.jsx
```

**Mối liên hệ:** mọi màn `student/`/`instructor/`/`admin/` đọc/ghi dữ liệu qua `useCursus()` (`CursusContext.jsx`) — state `useState` thuần, khởi tạo từ mảng `INITIAL_*` cứng trong file, **không có `fetch()` nào trong toàn bộ codebase nhánh này**. Đây là điểm khác biệt lớn nhất so với nhánh `chung` (có `lib/api.js` gọi API thật) — xem doc 09 để biết kế hoạch nối 2 phần lại.

Chi tiết design system/token/component đầy đủ: `docs/product/blueprint.md` mục 6 ("UI/UX direction") và mục 5 (IA/component spec) — thay thế bộ `docs/frontend/*` cũ đã gộp/xoá, xem mục 2.5 bên dưới.

> **Sửa lại 18/08/2026 — cả banner (dòng 28-30) lẫn 2 đoạn trên đã lỗi thời:** việc hợp nhất backend/frontend từ nhánh `develop` (nay `origin/chung`) vào `haidang2425` **đã xảy ra** (ghi nhận ở mục 2.3 dòng ~104 của chính file này) — `frontend/src/lib/api.js` giờ là client gọi API thật (cookie-session + CSRF), `CursusContext.jsx` đọc/ghi qua đó chứ không còn "MOCK local state, chưa gọi API thật". Claim "không có `fetch()` nào" **không còn đúng cho HEAD hiện tại**. Cây thư mục ở trên cũng thiếu nhiều file phát sinh sau 11/08 (`lib/authClient.js`/`dates.js`/`planning.js`, `hooks/`, `components/legal/`, phần lớn `components/landing/*`, `components/auth/OnboardingScreen.jsx`/`ProtectedRoute.jsx`/`RequestAccessScreen.jsx`/`ResetPasswordScreen.jsx`, `components/instructor/InstructorClassActivityPanel.jsx`/`InstructorPracticeQueuePanel.jsx`, `components/admin/AdminAcademicPanel.jsx`, `components/student/DeferTaskDialog.jsx`/`LecturePlanPanel.jsx`) — không liệt kê lại toàn bộ ở đây (đổi liên tục), chỉ ghi nhận cây trên là **snapshot 11/08, không phải hiện trạng**. `AuthScreen.jsx` (dòng 50, từng bị đánh dấu "cần kiểm tra trước khi sửa") **đã bị xoá khỏi codebase, không còn tồn tại** — cảnh báo đó hết hiệu lực.

## 2.2 `AI20K-Log-Bridge/` — Chrome/Edge extension log AI ngoài luồng CLI

Bộ công cụ **độc lập với `scripts/log_hook.py`**, giải quyết một khoảng trống: `scripts/` chỉ log được các AI tool có hook CLI (Claude Code, Cursor, Codex, Gemini CLI, Copilot, Antigravity); khi team dùng **ChatGPT/Claude.ai/Gemini/Perplexity/... qua trình duyệt**, không có cơ chế nào bắt prompt tự động — trước đây phải gõ tay qua `scripts/log_manual.py`. Extension này tự động hoá phần đó.

```
AI20K-Log-Bridge/
├── DOC-FILE-NAY-TRUOC.txt          # Hướng dẫn cài đặt nhanh (đọc trước tiên)
├── tests/test_git_info_host.py     # Test Python cho native host (chạy qua pytest)
└── ai-log-extension/
    ├── manifest.json               # Chrome extension manifest v3, ID cố định qua field "key"
    ├── background.js               # Service worker — nơi DUY NHẤT gọi network (tránh CORS)
    ├── content.js                  # Bắt nội dung ô soạn prompt lúc gửi (trên site đã bật)
    ├── detector.js                 # Chạy trên MỌI trang, chỉ đoán "có phải AI chat" từ cấu trúc DOM
    ├── composer.js                 # Phân biệt "vừa gửi" khỏi "tự xoá tay"
    ├── adapters.js                 # Selector riêng cho từng site đã biết (ChatGPT, Claude.ai, Gemini...)
    ├── giturl.js                   # Parse mọi dạng link GitHub người dùng dán vào
    ├── popup.html / popup.js       # UI: cấu hình, hàng đợi duyệt, lịch sử gửi
    ├── icons/                      # Icon extension (16/32/48/128px) + script sinh icon
    ├── native/
    │   ├── git_info_host.py        # Native messaging host — trả lời "repo/branch/commit/email" thật trên máy
    │   ├── doctor.py                # Chẩn đoán cài đặt (14 mục kiểm tra)
    │   └── selftest.py              # Self-test cho native host
    ├── setup.cmd / setup.sh / setup.py  # Cài + kiểm tra native host, 1 lệnh duy nhất
    └── test/                       # Test JS (chạy qua `node test/run.js`, stub chrome.*/fetch)
```

**Cơ chế cốt lõi:**
- **Vì sao là extension, không phải web app:** grading server chặn CORS với mọi origin (`null`, `localhost:*`, `claude.ai`, `chatgpt.com`...) — chỉ service worker của extension (có `host_permissions`) mới gọi `fetch()` được, không bị ràng buộc CORS.
- **Bắt log:** chỉ đọc nội dung **ô soạn prompt** lúc người dùng gửi (Enter hoặc ô bị xoá trắng sau khi bấm nút gửi) — không đọc network request/response của trang, tránh lẫn traffic nội bộ site vào log.
- **Native messaging host** (`git_info_host.py`): vì extension không có quyền truy cập filesystem, host này chạy dưới dạng process riêng (đăng ký qua registry `HKCU`), nhận request qua Chrome Native Messaging (khung 4-byte length-prefixed), chạy đúng các lệnh `git` mà `scripts/log_hook.py` chạy — đảm bảo 2 nguồn log (CLI hook + extension) không bao giờ lệch nhau về repo/branch/commit/email. Có nguồn dự phòng qua GitHub API khi không cài native host (nhưng chỉ thấy commit đã push).
- **2 chế độ gửi:** "Chờ duyệt" (mặc định — vào hàng đợi, người dùng tick chọn rồi mới gửi) và "Tự động" (gửi ngay).
- Test coverage khá đầy đủ: `test/*.test.js` (JS, stub `chrome.*`) + `tests/test_git_info_host.py` (Python, chạy native host như subprocess thật).

**Lưu ý:** đây là công cụ hỗ trợ **quy trình nộp bài** (tuân thủ deliverable AI-log của BTC), không phải một phần sản phẩm Cursus — không nằm trong `src/` hay `frontend/`.

## 2.3 `docs/planning/` — Tài liệu định hình sản phẩm

- **`docs/planning/v1/` không còn tồn tại** — đã bị xoá hẳn ở một thời điểm trước (không phải archive vào `docs/history/`, đã xoá thật khỏi repo). Nội dung còn giá trị (thuật ngữ, roadmap kiến thức) đã được gộp vào `04-Cursus-Terminology.md` trước khi xoá — xem dòng đầu `docs/archive/planning-v2/README.md`. **Sửa lại ở đây 11/08/2026** vì bản mô tả trước ghi nhầm là "giữ lại làm tham khảo lịch sử" — thực tế không còn file nào.
- **`docs/archive/planning-v2/`** (trước đây `docs/planning/v2/`, dời tại đây 13/08/2026): bộ tài liệu **lịch sử** dùng để triển khai giai đoạn đầu — **đã superseded bởi `docs/product/` (spec sản phẩm hiện hành: `blueprint.md`, `data-contract.md`, `build-and-demo-plan.md`, `ai-coding-prompt.md`)**, giữ lại nguyên vẹn để tham khảo phân công team/hạ tầng/tiến độ. Có `README.md` làm mục lục, 10 file `00`→`09` (playbook feature spec F1-F7 + UI/UX, PRD, SRS, execution plan theo 3 mốc, terminology, competitive analysis, hạ tầng Supabase, checklist production-readiness, checklist 10 deliverable BTC, **phân công team theo role** — mới 11/08), cộng thư mục con `data/` (JSON mẫu: chunk syllabus SSA101, danh sách khoá học BIT/SE K20D-K21A, seed sinh viên mẫu), `scripts/` (`flm_parser.py` — parse curriculum/syllabus `.docx` thành JSON; `gen_seed_students.py` — sinh dữ liệu sinh viên mẫu), **`roles/`** (mới 11/08/2026) — 4 file docs riêng cho từng thành viên (Đăng/Hải Anh/Chung/Bình), mỗi file: UI/UX cụ thể từng màn (ASCII layout), sản phẩm tham khảo thật kèm link GitHub, đặc tả tính năng có ví dụ input/output, lịch theo ngày, Definition of Done, prompt vibe-code sẵn dùng cho Gemini/Antigravity — đây là bản đầy đủ để code theo, `09-Cursus-Team-Assignment.md` chỉ còn là bản tóm tắt — và **`progress/`** (mới 11/08/2026) — hệ thống theo dõi tiến độ: 1 file checklist/người (tick khi việc đã test thật) + `README.md` giải thích quy tắc, đọc bằng `scripts/progress_report.py` (mục 2.2 dưới).

- **`scripts/progress_report.py`** (mới 11/08/2026, nằm ở `scripts/` cấp root, không phải trong `docs/planning/`, nhưng đọc dữ liệu từ `docs/archive/planning-v2/progress/` nên liệt kê ở đây cho liền mạch): script Python thuần (không phụ thuộc thư viện ngoài) đọc 4 file `docs/archive/planning-v2/progress/*.md`, đếm checkbox `- [x]`/`- [ ]` theo từng mục (`##` = 1 sprint), in bảng % hoàn thành mỗi người/mỗi sprint — thay thế việc nhóm trưởng phải hỏi tiến độ bằng lời nói. Chạy qua `make progress` (target mới thêm vào `Makefile` BTC gốc, xem mục 2.7) hoặc `python scripts/progress_report.py` trực tiếp; hỗ trợ `--person <TÊN>` và `--out <path>`. Chi tiết: `docs/archive/planning-v2/progress/README.md`.

> **11/08/2026 — mục 2.1 đã được viết lại**, mô tả đúng cấu trúc Vite/React thật hiện tại (không còn Next.js/TypeScript). **Cập nhật 13/08/2026:** việc hợp nhất backend/frontend từ nhánh `develop` vào `haidang2425` đã thực hiện trong phiên làm việc này — xem `docs/decisions/ADR.md` (ADR về chiến lược hợp nhất file-by-file) và `docs/archive/planning-v2/09-Cursus-Team-Assignment.md` mục "Job #0" cho kế hoạch/bối cảnh gốc.

*(Đã tổ chức lại cấu trúc + đổi tên thư mục trong phiên làm việc trước — xem lịch sử hội thoại/commit gần đây nếu cần chi tiết quá trình đổi tên.)*

> **Sửa lại 18/08/2026 — đoạn trên (mục 2.3) ghi chưa chính xác:** chỉ có các file
> `.md` kế hoạch (00→11, `README.md`, `progress/`, `roles/`) thật sự dời sang
> `docs/archive/planning-v2/`. **`docs/planning/v2/data/*.json` và
> `docs/planning/v2/scripts/*.py` KHÔNG di chuyển — vẫn nằm nguyên ở đường dẫn
> cũ `docs/planning/v2/`** vì đây là dữ liệu/script **đang chạy thật lúc runtime**:
> `src/services/rag/rag.py` (`DATA_DIR = Path("docs/planning/v2/data")`) và
> `src/services/mock/demo_data.py` đọc trực tiếp từ đường dẫn này để trả lời
> RAG/demo — di chuyển sẽ break app trừ khi sửa code kèm theo. Đừng nhầm với
> `data/` ở gốc repo (học liệu `.docx`/`.pptx` thô, xem `data/README.md`) —
> hai thư mục "data" khác mục đích hoàn toàn, bảng so sánh đầy đủ nằm trong
> `data/README.md`.

## 2.4 `docs/project/` — Tài liệu vận hành repo

- **`docs/project/logging-guide.md`** (trước đây `LOGGING_GUIDE.md` ở root): hướng dẫn chi tiết 2 hệ thống log song song trong repo — (1) AI-usage-log tự động (`scripts/` + hook), (2) `JOURNAL.md`/`WORKLOG.md` thủ công.
- **`docs/project/structure-btc.md`**, **`docs/project/structure-team.md`**: chính là 2 tài liệu này — mô tả cấu trúc toàn repo, tách theo nguồn gốc BTC/team.
- **`docs/project/run-guide.md`** (11/08/2026, trước đây `RUN_GUIDE.md` ở root): hướng dẫn khởi chạy full-stack chi tiết + fix lỗi Windows venv path.
- **`docs/project/BTC_REQUIREMENTS_EDU-01.md`** — đã gộp/xoá trong đợt dọn trước; nội dung đối chiếu đề bài BTC (EDU-01) tương đương nay nằm ở `docs/product/blueprint.md` mục 0.
- **`docs/project/repo-audit.md` đã xoá hẳn** (dời sang `docs/history/` sáng 11/08/2026, rồi xoá hẳn chiều cùng ngày cùng với cả `docs/history/`) — là snapshot lịch sử một thời điểm (một số nhận định như "không có thư mục `frontend/`" đã lỗi thời từ lâu), không phải tài liệu vận hành đang dùng.

## 2.5 `docs/frontend/` — đã gộp/xoá, nội dung tương đương nay ở `docs/product/blueprint.md`

**`docs/frontend/` (từng chứa `00_AI_CONTEXT_PACK.md`, `02`–`08` design system, và trước đó `01_UI_UX_RESEARCH.md`/`09_API_CONTRACT.md`/`10_FRONTEND_SYSTEM_DESIGN.md`) đã bị xoá hẳn khỏi repo** trong đợt dọn trước ngày 13/08/2026 — toàn bộ thư mục không còn tồn tại. Nội dung design system/brand/UI direction tương đương nay nằm trong `docs/product/blueprint.md` mục 6 ("UI/UX direction") và mục 5 ("Information architecture và component spec"). Nếu cần nội dung cũ chi tiết hơn (token/component/theme/responsive/motion/mascot/checklist đầy đủ), tra lịch sử git (`git log --all --full-name -- "docs/frontend/*"`).

## 2.6 `docs/decisions/` — ADR (lịch sử quyết định)

- **`docs/decisions/ADR.md`**: nhật ký quyết định kiến trúc quan trọng (Supabase, Gemini, chiến lược repo/deploy — hiện là 1 remote + CLI thủ công, reranker bắt buộc, Mock LMS thay Canvas/LTI thật, không hardcode tên model AI) — mỗi ADR có Quyết định/Vì sao/Đánh đổi. Đây là 1 trong các mục hồ sơ bàn giao BTC yêu cầu ("nhật ký quyết định quan trọng").
- **`docs/history/` không còn tồn tại** — thư mục này được tạo 11/08/2026 buổi sáng để gom tài liệu lỗi thời (bản redesign cũ, repo-audit snapshot cũ, design system đời đầu `design-v1-deprecated/`), nhưng buổi chiều cùng ngày đã **xoá hẳn** thay vì chỉ archive, vì không ai đọc và toàn bộ phần "vì sao" cần giữ đã có trong `ADR.md`/`docs/frontend/00_AI_CONTEXT_PACK.md`. Nếu cần biết lý do 1 quyết định cũ, tra `ADR.md` trước.

## 2.7 File root do team viết đè lên template BTC

- **`README.md`** (11/08/2026): ban đầu là template BTC nguyên bản (xem `structure-btc.md`), **đã được viết lại hoàn toàn** thành README thật của Cursus (vấn đề/giải pháp, F1-F7, trạng thái dự án, tech stack thật, quick start, bản đồ tài liệu).
- **`JOURNAL.md`, `WORKLOG.md`**: khung template BTC, team đang điền dần theo tuần/ngày — xem nội dung trực tiếp trong 2 file, không tóm tắt lại ở đây vì thay đổi liên tục.
- **`Makefile`** (11/08/2026): BTC gốc (`run`/`test`/`lint`/`format`/`typecheck`/`check`/`clean`), **thêm 2 target mới** `progress`/`progress-snapshot` gọi `scripts/progress_report.py` — đây là bổ sung (thêm target), không phải viết đè, nên không cần bản gốc lưu ở `docs/reference/` (khác trường hợp `README.md`).
- **Nguyên tắc từ 11/08/2026 (yêu cầu nhóm trưởng): file BTC gốc không bao giờ bị xoá hẳn khi viết đè** — bản nguyên văn được chuyển vào `docs/reference/btc-template/` để sau còn đối chiếu/kiểm soát. Áp dụng cho `README.md` gốc và `README_boilerplate.md` gốc — xem mục 2.8.
- **Đã xoá khỏi root (11/08/2026) — các file này KHÔNG phải của BTC (team tự tạo), nên xoá thẳng theo đúng nguyên tắc trên vẫn ổn:** `implementation_plan.md`, `walkthrough.md` (nội dung từng gộp vào `docs/history/` sáng cùng ngày, nay `docs/history/` cũng đã xoá hẳn — xem mục 2.6), `logo.png` (asset cũ, không được tham chiếu ở đâu, khác hẳn `frontend/public/logo.png` đang dùng thật), `RUN_GUIDE.md` (dời sang `docs/project/run-guide.md`, xem mục 2.4).
- **`ARCHITECTURE.md`** (root): dòng dưới đây đã lỗi thời — **sửa lại 18/08/2026:** file **đã được điền xong 15/08/2026** (142 dòng, 2 sơ đồ mermaid thật, không còn placeholder `[...]`), như chính `docs/PROJECT_CONTEXT.md` mục 3 đã ghi nhận từ trước — 2 tài liệu này từng mâu thuẫn nhau về trạng thái file này, nay đã khớp. ~~vẫn là template BTC, chưa điền — còn placeholder `[...]`. Nội dung kiến trúc thật hiện nằm rải rác ở `frontend/src/lib/api.js` (endpoint thật), `docs/product/blueprint.md` mục 5, `docs/decisions/ADR.md`; chưa có ai hợp nhất lại vào đúng file `ARCHITECTURE.md` mà BTC chỉ định làm deliverable #3 — việc còn tồn đọng, chưa gán cho ai.~~ (`docs/frontend/09_API_CONTRACT.md`/`10_FRONTEND_SYSTEM_DESIGN.md` từng mô tả phần này nhưng đã bị xoá 12/08/2026 vì sai lệch với endpoint thật — xem mục 2.5.)

## 2.8 `docs/reference/` — Bản gốc BTC giữ lại đối chiếu

**Mới 11/08/2026, theo yêu cầu trực tiếp của nhóm trưởng:** khi một file BTC gốc cần bị viết đè/thay thế để có nội dung thật của Cursus, **không xoá hẳn** — bản nguyên văn (lấy trực tiếp từ Initial commit `4741ab8` bằng `git show 4741ab8:<path>`, không gõ lại tay) được giữ ở đây làm ví dụ/tham chiếu, kèm 1 banner ngắn ở đầu file ghi rõ đây là bản gốc, bản đang dùng thật nằm ở đâu.

- `docs/reference/btc-template/README.md` — nguyên văn `README.md` gốc BTC (trước khi bị viết đè thành README thật của Cursus ở `/README.md`).
- `docs/reference/btc-template/README_boilerplate.md` — nguyên văn bản mẫu BTC dùng để điền README (trước khi việc điền hoàn thành).

**Nguyên tắc áp dụng cho mọi lần sau:** trước khi sửa/xoá bất kỳ file nào đã liệt kê trong `structure-btc.md`, kiểm tra trước — nếu là file BTC gốc, sao một bản vào `docs/reference/btc-template/` (giữ nguyên tên) rồi mới sửa/xoá bản đang dùng. File team tự tạo (không nằm trong `structure-btc.md`) thì không cần bước này — xoá thẳng nếu không còn giá trị (xem mục 2.7, `implementation_plan.md`/`walkthrough.md`/`logo.png`/`RUN_GUIDE.md` gốc là ví dụ, không phải file BTC nên xử lý khác).

## 2.9.1 Cập nhật 15/08/2026 — `docs/product/` không còn tồn tại

Mọi tham chiếu tới `docs/product/blueprint.md`/`data-contract.md`/`build-and-demo-plan.md`/`ai-coding-prompt.md` trong các mục trên (2.1, 2.4, 2.5, 2.7) đã lỗi thời — 4 file đó (cộng `docs/product/{landing-auth-ui-ux,floating-widgets-ui-ux}.md` mới hơn) đã được gộp trong 2 đợt dọn docs (15/08/2026) vào **2 file sống ở gốc `docs/`**: `PROJECT_CONTEXT.md` (business + product + kỹ thuật + data + demo script + deploy — trước đó tách riêng `TECHNICAL_SPEC.md`, đã gộp lại vào `PROJECT_CONTEXT.md` mục 13-22 ở đợt dọn thứ 2) và `FRONTEND_SPEC.md` (UI/UX — mới, trước đó frontend không có spec riêng). `docs/01_PRODUCT_UX_DECISIONS.md`/`02_SYSTEM_DECISIONS.md`/`03_CURRENT_STATE_AND_OPTIONS.md`/`docs/discovery/*`/`docs/decisions/deploy-platform-comparison.md` cũng đã gộp/xoá theo (nội dung so sánh phương án đã hết giá trị vì quyết định đã chốt). Không sửa lại từng dòng cũ ở trên — giữ nguyên làm snapshot lịch sử đúng tinh thần file này, chỉ thêm ghi chú này để không ai đi tìm nhầm đường dẫn chết. `docs/archive/planning-v2/` (mục 2.3) **không đổi gì** trong các đợt dọn này.

## 2.9 Không xác định được nguồn gốc

Không có mục nào trong lần khảo sát này — mọi file/thư mục đã được đối chiếu trực tiếp với Initial commit qua `git cat-file -e 4741ab8:<path>` hoặc `git log --diff-filter=A`, nên phân loại ở trên là chắc chắn (không suy đoán theo tên/ngày sửa đổi).
