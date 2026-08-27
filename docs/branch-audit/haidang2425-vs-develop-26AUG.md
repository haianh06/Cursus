# So sánh `haidang2425` ↔ `develop` — 26/08/2026

> Chụp tại: `haidang2425` = `2093f6d` (26/08 18:18) · `origin/develop` = `e549690` (26/08 18:17)
> Điểm tách chung (merge base): `c03e9c0` — 25/08/2026 00:23
> Toàn bộ số liệu dưới đây lấy bằng `git diff` / `git merge-tree --write-tree` (chạy khô, không đụng working tree).

## 1. Tổng quan phân kỳ

| | Commit riêng | File đổi | Dòng |
|---|---|---|---|
| `haidang2425` | **74** | 195 | +21.426 / −1.914 |
| `origin/develop` | **5** | 81 | +3.483 / −1.377 |

Hai nhánh cùng đụng **29 file**. Merge khô → **11 file conflict thật**, 18 file còn lại git tự gộp được.

Phân kỳ chỉ mới ~1,5 ngày nên còn dễ xử lý. Càng để lâu càng đắt.

## 2. `haidang2425` làm gì (74 commit)

| Khu vực | Số file | Nội dung |
|---|---|---|
| `mock-lms/` | 53 | EduSync: thay UI Jinja2 bằng React frontend, redesign hero/navbar, dark mode + EN/VI, wire dữ liệu curriculum/prerequisite/syllabus thật, chạy như service trong Docker Compose |
| `frontend/src/components/` | 25 | Admin console (section management, roster, course catalog, password reset), align UI với design system |
| `docs/` | 21 | Audit trạng thái 26/08, checklist đồng bộ role, task plan |
| `tests/test_api/` | 16 | Test cho admin roster/section/course CRUD, guardrail audit |
| `src/services/` | 15 | Guardrail audit trail, audit override, semester work-queue |
| `src/api/` | 9 | `admin.py` +429 dòng (section/roster/password-reset endpoints) |
| `src/repositories/`, `migrations/` | 12 | `CourseSection.instructor_id` nullable, cascade delete section → module → lesson |
| `eval/` | 7 | Evidence test thủ công + evaluation report |

Chủ đề chính: **admin governance + EduSync mock LMS**.

## 3. `develop` làm gì (5 commit, đều của haianh06)

| Commit | Ngày | Nội dung |
|---|---|---|
| `e549690` | 26/08 18:17 | `scripts/seed_gap_fill_demo.py` (mới, 893 dòng) seed sandbox "Cursus Demo University"; unit test cho `risk_signal_service`, `risk_engine`, `plan_builder`; sửa `plan_builder.py` (+159), `weekly_plan_engine.py`, `qa_answer_service.py` |
| `43215be` | 25/08 23:41 | Fix self-study block delete 500, CORS trên error response, popover positioning |
| `7500a20` | 25/08 21:36 | Fix CSRF bootstrap deadlock + logout cookie leak khi deploy cross-domain |
| `ed8dd20` | 25/08 19:50 | Fix self-study timezone, topbar semester/week động, Practice week bound, EN reflection catalog |
| `9650bfd` | 25/08 11:07 | Fix cross-domain CSRF, redesign reflection, gỡ secret bị leak, trả nợ lint |

Chủ đề chính: **student experience + hạ tầng deploy (CSRF/CORS/timezone) + test coverage cho risk engine**.

## 4. 11 file conflict — phân loại và hướng xử lý

### Nhóm A — conflict giả, gộp máy móc (6 file)

| File | develop | haidang2425 | Xử lý |
|---|---|---|---|
| `src/services/onboarding_status.py` | +6/−13 | +8/−13 | Cả hai **cùng** rút gọn `is_onboarded()` thành `return True`. Chỉ khác docstring → chọn 1 docstring, xong |
| `src/api/admin.py` | +8/−8 | +429/−31 | develop chỉ dọn khoảng trắng cuối dòng → **lấy nguyên bản haidang2425** |
| `src/api/self_study.py` | +1/−1 | +3/−3 | develop dán `# noqa: N815`; haidang đổi `blockId` → `block_id = Field(alias="blockId")` (giữ nguyên wire format) → **lấy haidang2425**, bản này đúng hơn |
| `src/api/student_memory.py` | +1/−1 | +2/−2 | Y hệt trên (`subjectCode` → `subject_code` + alias) → **lấy haidang2425** |
| `RUNNING.md` | +19/−8 | +18/−13 | Docs, gộp tay theo mục |
| `Dockerfile` | +1/−1 | +9/−7 | Cả hai cùng chuyển sang `scripts/docker_entrypoint.py`; haidang thêm multi-stage + `COPY --chown` → **lấy haidang2425**, đổi `CMD` thành `ENTRYPOINT` như bản haidang |

### Nhóm B — cần gộp cả hai bên (3 file)

| File | Vấn đề | Xử lý |
|---|---|---|
| `.gitignore` | develop dùng `.env*` + whitelist `!.env.example` (chặt hơn, sau vụ leak); haidang thêm `.pytest-tmp-*/`, `frontend/playwright-report/`, `.codex-*/`, `.worktrees/`, `.superpowers/` | Lấy block `.env*` của develop + toàn bộ entry mới của haidang |
| `docker-compose.yml` | develop bỏ `profiles: ["local-db"]` (db/redis chạy mặc định), thêm service `frontend`, thêm healthcheck `depends_on`; haidang thêm service `mock-lms` | Gộp cả hai — không đè lên nhau về mặt logic |
| `frontend/src/components/student/StudentPractice.jsx` | develop neo "tuần hiện tại" theo `activeSemester.start_date` (đúng hơn ISO week); haidang chỉ clamp `Math.min(10, Math.max(1, currentIsoWeekNumber()))` **nhưng** có thêm `data-testid="practice-week-number"` mà Playwright spec đang dùng | Lấy logic của develop + giữ `data-testid` của haidang |

### Nhóm C — xung đột kiến trúc thật, phải quyết định (2 file)

**`frontend/src/context/CursusContext.jsx`** — develop +39/−8, haidang +10/−75. Hai hướng ngược nhau:
- `haidang2425` **thu hẹp** context xuống chỉ còn admin: gỡ toàn bộ instructor slice (`classInfo`, `alerts`, `queue`, `selectedCourseId`, `getInstructorDashboard`, `getGuardrailReviewQueue`...), chuyển việc fetch về chính các trang instructor (`InstructorHome`, `InstructorRiskPage`).
- `develop` **mở rộng** context: thêm student slice `activeSemester` (gọi `listSemesters()`) để topbar hiển thị "Học kỳ … • Tuần …" thật thay vì chuỗi hardcode.

→ Giữ hướng thu hẹp của haidang2425, rồi ghép thêm nhánh `role === 'student'` + state `activeSemester` của develop vào. Nếu bỏ phần này thì `StudentPractice.jsx` (Nhóm B) và topbar của develop sẽ gãy vì cùng phụ thuộc `useCursus().activeSemester`.

**`frontend/src/components/auth/OnboardingScreen.jsx`** — develop +39/−252, haidang +30/−3.
- `develop` **xoá hẳn wizard onboarding**, biến file thành callback mỏng cho Google OAuth (đổi redirect lấy session rồi bounce về dashboard).
- `haidang2425` giữ wizard cũ, chỉ thêm nút "Đăng xuất" làm lối thoát (`907e490`) — nhưng sau đó chính haidang cũng gỡ cổng chặn onboarding (`094ee61`).

→ **Lấy bản develop**. Hai bên đã đồng thuận về mặt sản phẩm (không còn cổng onboarding bắt buộc); bản develop dọn sạch phần code chết mà haidang vẫn đang mang theo.

## 5. Cảnh báo bảo mật

`.env.bak` từng được commit ở `0f9c24f` ("add .env.bak for environment variables"). Cả hai nhánh đã gỡ:
- `9650bfd` (develop) — commit message ghi rõ "leaked secrets"
- `cf523b7` (haidang2425) — "stop tracking .env.bak and ignore it"

Hiện không nhánh nào còn file này trong tree, **nhưng nó vẫn nằm trong lịch sử git và repo là public trên GitHub**. Comment trong `.gitignore` của develop liệt kê Google / Postgres / Redis / SMTP. Cần **xoay (rotate) toàn bộ những credential đó**, không chỉ xoá file.

## 6. Kiểm chứng bằng merge khô (26/08)

Chạy `git merge-tree --write-tree haidang2425 origin/develop` → cây `dbc15a9`, giải nén ra thư mục tạm để kiểm tra tĩnh. Kết quả:

| Kiểm tra | Kết quả |
|---|---|
| Migration Alembic đụng nhau | **Không.** develop không sửa file nào trong `migrations/`. 5 migration mới đều của `haidang2425`, xếp tuyến tính, không có 2 head |
| Cú pháp Python toàn bộ `src/` sau merge | **0 lỗi** (trừ 4 file còn conflict marker) |
| Tham chiếu `src.*` không giải được | **0** |
| `frontend/src/lib/api.js` sau merge | Tự gộp sạch, giữ đủ cả `academicWeekNumber` (develop) lẫn `currentIsoWeekNumber` — 193 export, không mất hàm nào |
| Import từ `lib/api` không có export tương ứng | 1 — `ProgressGarden.jsx` → `getStudentReflections`. **Lỗi có sẵn ở cả hai nhánh**, không phải do merge; file này không được import ở đâu cả (code chết) |
| develop sửa 4 file test trùng với haidang | Chỉ gỡ import thừa / biến không dùng (dọn lint). Tự gộp an toàn |

### Cái bẫy thật sự: `App.jsx` tự gộp sạch nhưng phụ thuộc file đang conflict

`frontend/src/App.jsx` **không hề conflict** — git gộp êm. Nhưng bản gộp ra có:

```js
const { activeSemester } = useCursus();      // dòng 417
...
{activeSemester ? { name: activeSemester.name,
                    week: academicWeekNumber(activeSemester.start_date) } : ...}
```

`activeSemester` chỉ tồn tại nếu `CursusContext.jsx` (file **đang conflict**, Nhóm C) được giải quyết theo hướng giữ phần student của develop.

Nếu ai đó giải conflict `CursusContext.jsx` bằng cách "lấy bản của mình" (rất dễ xảy ra vì bản haidang là +10/−75, nhìn như chỉ đang dọn dẹp), thì:
- `App.jsx` — topbar rơi vào nhánh else, mất hiển thị "Học kỳ … • Tuần …"
- `StudentPractice.jsx` — `weekInitialized` không bao giờ chạy, tuần luyện tập kẹt ở 1

**Git sẽ không báo một lỗi nào.** Cả hai file đều chạy được, chỉ là sai. Đây là rủi ro lớn nhất của lần merge này.

### E2E test

`haidang2425` thêm 5 spec Playwright. Chỉ 1 selector cứng có thể vỡ: `getByTestId('practice-week-number')` trong `student-practice.spec.js` — nằm đúng file conflict `StudentPractice.jsx`. Các spec còn lại dùng `getByLabel('Môn học')`, `getByRole('button', {name:'Tuần sau'})`, `h1` — develop không đổi những chỗ này.

### develop mang thêm test

`test_security_infrastructure` +51, `test_session_module` +106, `test_self_study_service` +103 (mới), `test_risk_signal_service` +99 (mới), `test_risk_engine` +87, `test_plan_builder_llm` +58, `test_timetable_module` +43, `test_query_normalization` +41.

## 7. Quy trình merge đề xuất

**Nguyên tắc: không merge trong thư mục chính.** Dựng worktree riêng, làm xong và xanh test mới đẩy về.

```bash
git worktree add .worktrees/merge-develop-26aug -b merge/develop-into-haidang haidang2425
cd .worktrees/merge-develop-26aug
git merge origin/develop
```

Thứ tự giải 11 conflict:

**Bước 1 — 6 file máy móc (Nhóm A).** `onboarding_status.py` chọn 1 docstring; `admin.py` / `self_study.py` / `student_memory.py` lấy bản haidang2425; `Dockerfile` lấy haidang2425; `RUNNING.md` gộp theo mục.

**Bước 2 — 3 file gộp cả hai (Nhóm B).** `.gitignore`: block `.env*` của develop + entry mới của haidang. `docker-compose.yml`: service `frontend` + healthcheck của develop, service `mock-lms` của haidang. `StudentPractice.jsx`: **logic develop + giữ `data-testid="practice-week-number"`**.

**Bước 3 — `OnboardingScreen.jsx`.** Lấy nguyên bản develop. `App.jsx` sau merge vẫn truyền `onLogout={logout}` — bản develop bỏ qua prop này, vô hại.

**Bước 4 — `CursusContext.jsx`, làm cuối và làm kỹ.** Lấy bản đã thu gọn của haidang2425 làm nền, rồi ghép thêm từ develop: state `activeSemester`, nhánh `role === 'student'` gọi `listSemesters()`, và `activeSemester` trong giá trị context trả về. **Bắt buộc**, xem lý do ở mục 6.

**Bước 5 — xác minh, theo thứ tự:**

```bash
grep -rn '<<<<<<<' --include='*.py' --include='*.jsx' --include='*.js' --include='*.yml' .
grep -n 'activeSemester' frontend/src/context/CursusContext.jsx
pytest -q
cd frontend && npm run build && npx playwright test e2e/student-practice.spec.js
```

Kiểm tra bằng mắt: topbar hiện đúng "Học kỳ … • Tuần …", màn Practice mở ra đúng tuần học chứ không phải tuần 1, đăng nhập Google chạy được (develop vừa sửa CSRF/cookie).

**Bước 6 — đẩy về nhánh chính** chỉ sau khi bước 5 xanh hết:

```bash
cd ../..
git merge --ff-only merge/develop-into-haidang
git worktree remove .worktrees/merge-develop-26aug
```

Hỏng ở bất kỳ bước nào: `git merge --abort`, hoặc xoá luôn worktree. Thư mục chính không hề bị động tới.


## 8. Kết quả merge thật (26/08)

Đã dựng worktree `.worktrees/merge-develop-26aug`, nhánh `merge/develop-into-haidang`, merge thật và giải hết conflict. Thư mục chính **không bị đụng tới** (vẫn ở `2093f6d`, `git status` sạch).

### Khối lượng conflict thực tế: 11 file, 22 cụm, 634 dòng

| File | Cụm | Dòng | Cách giải |
|---|---|---|---|
| `.gitignore` | 1 | 14 | Lấy block `.env*` của develop, entry riêng của haidang nằm ngoài cụm nên giữ nguyên |
| `Dockerfile` | 1 | 7 | Ours |
| `RUNNING.md` | 3 | 39 | Ours (khớp với lựa chọn compose) |
| `docker-compose.yml` | 4 | 134 | Ours |
| `OnboardingScreen.jsx` | 4 | 222 | Theirs |
| `StudentPractice.jsx` | 1 | 12 | Theirs + gắn lại `data-testid` |
| `CursusContext.jsx` | 2 | 46 | **Viết tay** |
| `src/api/admin.py` | 3 | 138 | Ours |
| `src/api/self_study.py` | 1 | 4 | Ours |
| `src/api/student_memory.py` | 1 | 4 | Ours |
| `src/services/onboarding_status.py` | 1 | 14 | Ours |

### `docker-compose.yml` — kết luận đảo lại so với mục 4

Mục 4 đề xuất "gộp cả hai". Sai. Xem conflict thật mới thấy hai bản là hai ý đồ khác nhau:

- **haidang2425**: stack gần production — service `edusync`, `SEED_ON_START`, healthcheck đủ 4 service, `depends_on: condition: service_healthy`, cổng bind vào `127.0.0.1`, frontend `target: runner` cổng 3000
- **develop**: stack dev — frontend `target: dev` cổng 5173 có HMR, bind-mount `./src:/app/src`, **không có edusync**

Lấy bản develop sẽ **mất hẳn service EduSync** — tức mất phần lớn công sức 53 file của bạn. → Lấy `--ours`, và `RUNNING.md` theo cùng.

### `CursusContext.jsx` — không bên nào dùng được

Đây là điểm mục 6 đã cảnh báo, nhưng thực tế còn tệ hơn. Sau merge:

- `const [activeSemester, setActiveSemester] = useState(null);` **tự gộp vào** (dòng 44)
- `listSemesters` **tự gộp vào** danh sách import (dòng 8)
- `activeSemester` **tự gộp vào** object context trả về (dòng 164)

Nhưng khối `role === 'student'` của develop lại gọi `setClassInfo`, `setAlerts`, `setQueue` — ba setter mà nhánh haidang2425 **đã xoá khai báo**. Kiểm chứng: `grep -cE 'const \[[a-zA-Z]+, setClassInfo\]'` → **0**.

Nên:

| Cách giải | Hậu quả |
|---|---|
| Lấy `--theirs` (bản develop) | `ReferenceError: setClassInfo is not defined` ngay khi student đăng nhập → **màn hình trắng** |
| Lấy `--ours` (bản haidang) | `activeSemester` tồn tại nhưng không ai gán → luôn `null`. Topbar mất "Học kỳ … • Tuần …", Practice kẹt tuần 1. **Không lỗi, không cảnh báo** |
| Viết tay | Giữ khối `role === 'student'` của develop, bỏ 3 setter đã xoá |

ESLint của dự án **không bật rule `no-undef`**, nên cả hai cách sai đều lint sạch và build thành công. Chỉ lộ ra lúc chạy thật (hoặc không lộ ra chút nào, ở trường hợp `--ours`).

### `git checkout --theirs` lấy nguyên cả file, không phải chỉ cụm conflict

Chạy `--theirs` cho `StudentPractice.jsx` làm mất `data-testid="practice-week-number"` — thay đổi này nằm **ngoài** vùng conflict nhưng vẫn bị ghi đè. Phải gắn lại thủ công. Rút ra: chỉ dùng `--ours`/`--theirs` khi bên kia không có thay đổi nào khác trong file.

### Xác minh sau merge

| Kiểm tra | Kết quả |
|---|---|
| Conflict marker còn sót | 0 |
| `pytest -q` | **576 passed, 7 skipped, 0 failed** (137s) |
| `npm run build` | **OK**, 808ms |
| `npm run lint` | Chỉ warning, không error — đều là warning có sẵn từ trước |
| Tham chiếu treo trong `CursusContext.jsx` | 0 |

Kết quả nằm ở commit `71e74f9` trên nhánh `merge/develop-into-haidang`: 63 file, +3.359/−1.425 so với `haidang2425`.

### Việc còn lại trước khi đẩy về nhánh chính

Chưa chạy được vì cần môi trường thật:

1. **E2E Playwright** — cần backend + frontend đang chạy
2. **Kiểm tra bằng mắt**: topbar hiện đúng "Học kỳ … • Tuần …"; màn Practice mở đúng tuần học chứ không phải tuần 1; đăng nhập Google chạy được (develop vừa sửa CSRF/cookie)
3. **Rà `CursusContext.jsx` cùng haianh06** — đây là quyết định kiến trúc, không phải lỗi merge

Xong 3 việc đó thì:

```bash
git merge --ff-only merge/develop-into-haidang
git worktree remove .worktrees/merge-develop-26aug
```

## 9. Chạy thật trên stack (26/08)

Backend SQLite trên `:8010`, Vite dev trên `:5183` (cổng 5173/5174/8000/8001/9000 đang bận vì stack chính của bạn — không đụng vào). Không Docker, không EduSync.

### Ba thứ cần nhìn — đều đạt

| Kiểm tra | Kỳ vọng | Thực tế |
|---|---|---|
| Topbar học kỳ/tuần | `Tuần 4 - Kỳ Fall 2026` (học kỳ bắt đầu 03/08, hôm nay 26/08) | **`Tuần 4 - Kỳ Fall 2026`** |
| Practice mở đúng tuần | 4, không phải 1 (lấy `--ours` sai) và không phải 35 (ISO week) | **`data-testid="practice-week-number"` = `4`** |
| Đăng xuất | Xoá cookie phiên, quay về `/login` | **Cookie rỗng, redirect `/login?returnTo=…`** |

Playwright: **14/14 pass** (`admin-people`, `auth`, `student-course-materials`, `student-flows`, `student-practice`).

`WeeklyStudyHoursChart.jsx` — component 206 dòng mới của develop — render bình thường trên Student Home.

### Ba lỗi lộ ra khi chạy thật (không cái nào do merge)

**1. `seed_gap_fill_demo.py` chết trên DB dựng từ migration.** Script mới của develop đọc thẳng `v1.signal_weights` từ DB rồi đưa vào `validate_policy_input()`. v1 do migration `20260823` ghi, JSON hardcode trong đó có **5** mã tín hiệu; develop thêm `SELF_REPORTED_HIGH_STRESS` vào `REQUIRED_SIGNAL_CODES` thành **6** nhưng không sửa migration → `RiskPolicyValidationError`.

Trớ trêu: chính develop **đã** xử lý đúng chỗ này cho UI admin — `GET /admin/risk-policy` merge `DEFAULT_SIGNAL_WEIGHTS` xuống dưới policy đã lưu. Script seed chỉ quên làm y hệt. Đã vá trong `c4b5888`. **Lỗi này tái hiện được trên develop đứng một mình** với DB mới — nên báo lại cho haianh06 để sửa ở develop luôn.

**2. `student-practice.spec.js` mã hoá cứng hành vi cũ.** Test khẳng định tuần mở đầu là `'10'` — đúng khi giá trị là ISO week bị clamp (tuần 35 → 10). Merge lấy logic neo theo ngày bắt đầu học kỳ của develop nên giờ là 4, và sẽ đổi theo lịch. Đã viết lại để kiểm bất biến (nằm trong 1..10, clamp ở 10, lùi về 9) thay vì con số cố định.

Đây là **test đỏ đúng** — nguy hiểm ở chỗ người chạy suite sau merge dễ tưởng merge hỏng rồi quay về logic cũ.

**3. `scripts/seed_curriculum.py` xoá file JSON đang được git theo dõi.** Chạy seeder xoá 8 file `docs/planning/v2/data/chunks_*.json` (COV111, COV121, COV131, DTR103, EXE401, PRN212, PRU221m, SBA301) vì mã môn không có trong catalog CSV — `path.unlink()` ở dòng 281. Các file này đến từ commit `0851614` (Phase 2), không phải `6ba3a17` hôm nay. develop không đụng script này → **hành vi có sẵn trên nhánh của bạn**.

Đã khôi phục trong worktree. Cảnh báo: chạy seeder trong repo chính sẽ xoá 8 file đó khỏi working tree.

### Sai sót của tôi trong quá trình này

Khi demo hậu quả của việc "lấy nguyên bản develop" cho `CursusContext.jsx`, tôi dùng `git show :3:… > file`. Lệnh `git show` thất bại (exit 128) nhưng dấu `>` đã cắt file về **0 byte** trước đó, và `&&` khiến bước khôi phục không chạy. Lần demo sau lại `cp` file rỗng đó đè lên bản backup tốt. Kết quả: commit `71e74f9` chứa `CursusContext.jsx` rỗng.

`pytest`, `npm run build`, `npm run lint` mà tôi báo là xanh đều chạy **trước** lúc đó — kết quả đúng với bản tốt, nhưng không đúng với nội dung đã commit. Đã dựng lại file bằng `git merge-file` từ ba phiên bản, giải lại đúng như cũ, `--amend` thành `329050e`, và build + e2e lại từ đầu. Các con số ở mục 9 này là của bản đã sửa.

### Trạng thái cuối

| | |
|---|---|
| Nhánh | `merge/develop-into-haidang` |
| Commit | `329050e` (merge) + `c4b5888` (2 fix) |
| pytest | 576 passed, 7 skipped |
| playwright | 14/14 passed |
| build / lint | OK / chỉ warning có sẵn |
| Thư mục chính | Không đụng tới — vẫn `2093f6d` |

Còn lại trước khi `merge --ff-only`: rà `CursusContext.jsx` cùng haianh06, và báo lỗi số 1 ngược về develop.

## 10. Đã merge (26/08)

`haidang2425` fast-forward từ `2093f6d` lên `c4b5888`:

```
c4b5888  fix: two breakages the merge surfaced when the stack was actually run
329050e  merge: bring origin/develop (student UX + deploy fixes) into haidang2425
2093f6d  docs(plan): mark Task 14 done...
```

`haidang2425` vs `origin/develop` giờ là **76 / 0** — develop đã hấp thụ hết.

Worktree `.worktrees/merge-develop-26aug`, nhánh `merge/develop-into-haidang`, và 2 server tạm đều đã dọn. `.claude/launch.json` đã hoàn nguyên.

### Chưa làm — cần môi trường thật

| Việc | Vì sao |
|---|---|
| Chạy lại trên Postgres | Toàn bộ kiểm chứng ở mục 9 chạy trên SQLite. develop không thêm migration nào nên rủi ro thấp, nhưng SQLite không phải bằng chứng cho Postgres |
| Thử SSO sang EduSync | Chạy không có EduSync. `mock_lms_sso.py` tự merge êm, nhưng develop sửa CSRF/cookie mà SSO phụ thuộc cookie — đây là chỗ đáng nghi nhất còn lại |
| Thử đăng nhập Google | Chỉ test được đường demo không mật khẩu. `OnboardingScreen.jsx` (lấy nguyên bản develop) chỉ chạy giữa luồng OAuth nên chưa chạm tới |
| Rà `CursusContext.jsx` cùng haianh06 | File duy nhất giải tay, và là quyết định kiến trúc chứ không phải lỗi merge |
| Báo lỗi seed ngược về develop | `seed_gap_fill_demo.py` vẫn lỗi trên develop; bản vá chỉ nằm ở nhánh này |

Chưa push. Test suite chạy an toàn ở máy local — `tests/conftest.py` tự trỏ `DATABASE_URL` sang `data/pytest.db` (SQLite), không đụng Supabase.
