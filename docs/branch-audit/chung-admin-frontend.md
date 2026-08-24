# Admin Console Frontend — nhánh `chung` (tài liệu chi tiết để vibe-code lại)

Nguồn: `frontend/src/components/admin/**` trên nhánh `chung` (worktree
`../P-093-chung-worktree`). Mục tiêu: đủ chi tiết để dựng lại y hệt UI/UX +
luồng gọi API trên nhánh khác mà không cần đọc lại source gốc.

## 1. Tổng quan layout & navigation

### Route gate (`App.jsx`)
Không có `ProtectedRoute` riêng — gate viết inline theo chuỗi điều kiện lồng
nhau tại `<Route path="/admin/*">`:
```
chưa login → /login
đã login nhưng chưa xác thực email → /email-verification
chưa onboarded → /onboarding
role !== 'admin' → Navigate tới DEFAULT_ROUTE[user.role]
role === 'admin' → <AppShell><AdminRoutes/></AppShell>
```

### Cây route `/admin/*`
```
<Route element={<AdminLayout/>}>
  index                        → Navigate to /admin/overview
  overview                     → <AdminOverview/>
  people                       → <AdminPeopleExplorer/>
  students/:studentId/*        → <AdminStudent360/>
  instructors/:instructorId/*  → <AdminInstructor360/>
  data-requests                → <AdminDataRequests/>
  cases/*                      → Navigate to /admin/overview   (backward-compat)
  access-audit                 → Navigate to /admin/governance/logs#data-access-history (backward-compat)
  governance/*                 → <AdminGovernanceRoutes/>
  *                            → <NotFoundPage/>
</Route>
```

### Cây route con `/admin/governance/*` (`AdminGovernanceRoutes.jsx`)
Thiết kế có chủ đích (comment gốc): Governance (quản trị tài khoản/chương
trình học) tách biệt khỏi Student 360 (hồ sơ cá nhân) — không dùng chung bề
mặt. Settings và Logs tách 2 trang riêng thay vì 1 trang cuộn dài.

```
curriculum   → <AdminCurriculum/>
access       → <div className="flex flex-col gap-8"><AdminUsers/><AdminInvitations/></div>
ai-policy    → <AdminAiPolicy/>
settings     → <SettingsScreen/>  (nội bộ — xem bên dưới)
logs         → <AdminLogsScreen/> (nội bộ — 2 tab, xem bên dưới)
*            → Navigate to /admin/governance/curriculum
```
Không có index route tường minh → mọi path lạ kể cả rỗng fallback về
`curriculum`.

**`SettingsScreen` (nội bộ)**: đọc `hash` qua `useLocation()`.
`LOG_ANCHORS = ['#audit-log', '#data-access-history']`. Nếu hash nằm trong
đó → `Navigate to=/admin/governance/logs${hash}` (redirect link cũ). Ngược
lại render `<div className="flex flex-col gap-8"><AdminSettings/><AdminAnalytics/></div>`.

**`AdminLogsScreen` (nội bộ)**: state `activeView` (`'access'` nếu
`hash==='#data-access-history'`, mặc định `'audit'`). 2 useEffect: (1) đồng
bộ `activeView` theo `hash` đổi; (2) `requestAnimationFrame` + `scrollIntoView`
tới id tương ứng sau khi hash đổi. `selectView(view)` đổi tab + `navigate({hash}, {replace:true})`.
Tab bar `role="tablist"`, 2 tab underline-style (`border-b-2`, active
`border-accent text-accent`). Chỉ render 1 trong 2 (`<AdminAccessAudit/>`
hoặc `<AdminAuditLog/>`) tại một thời điểm — unmount hoàn toàn tab kia.

### `AdminLayout.jsx`
- Bọc toàn bộ trong `<div className="admin-operations {dark? admin-operations-dark : ''}">` — đây là scope CSS theme riêng (xem mục 5).
- Skip-link `#admin-main` (ẩn trừ khi focus).
- Header: tiêu đề `t('admin.pageTitle')` ("Admin Console") + subtitle icon `Database` + `t('admin.pageSubtitle')`; cụm toggle ngôn ngữ VI/EN dạng pill 2 nút.
- `<div id="admin-main" tabIndex={-1} className="admin-cockpit-main"><Outlet/></div>` — cố ý dùng `div` thường (không phải `<main>`) vì `AppShell` cha đã có 1 landmark `<main>` duy nhất.

### Sidebar — `AdminNavigation.jsx` + `adminNavigationConfig.js`
Data-driven, 2 nhóm cố định (thứ tự có chủ đích: quan sát trước, quản trị sau — comment gốc nhấn mạnh "Overview is deliberately the first destination"):

```js
NAV_GROUPS = [
  { id:'observe', labelKey:'admin.navGroupObserve', items:[
      {to:'/admin/overview', labelKey:'admin.navOverview'},
      {to:'/admin/people', labelKey:'admin.navPeople'},
      {to:'/admin/data-requests', labelKey:'admin.navDataRequests'},
  ]},
  { id:'governance', labelKey:'admin.navGroupGovernance', items:[
      {to:'/admin/governance/curriculum', labelKey:'admin.navCurriculum'},
      {to:'/admin/governance/access', labelKey:'admin.navAccounts'},
      {to:'/admin/governance/ai-policy', labelKey:'admin.navAiPolicy'},
      {to:'/admin/governance/settings', labelKey:'admin.navSettings'},
      {to:'/admin/governance/logs', labelKey:'admin.navSystemLog'},
  ]},
]
```
Icon map theo path (`ITEM_ICONS`): overview→`LayoutDashboard`, people→`Users`,
data-requests→`ClipboardList`, curriculum→`BookOpen`, access→`UserPlus`,
ai-policy→`ShieldCheck`, settings→`Settings2`, logs→`ScrollText`.

Component nhận `{onNavigate, variant='default', collapsed=false}`. 2 biến thể
style (`linkClass`):
- `variant='sidebar'`: active = `border-blue-500/30 bg-blue-600 text-white`; inactive = `text-slate-300 hover:bg-white/5`.
- `variant='default'`: active = `border-accent bg-[var(--accent-soft)] text-accent`; inactive = `text-fg-secondary hover:text-fg`.

Group label: khi `collapsed` → `sr-only` (ẩn khỏi mắt nhưng còn cho screen
reader, vì sidebar thu gọn không đủ chỗ hiện chữ "Quản trị"). Chỉ item thật
sự điều hướng mới có icon/hover/tooltip — **group label KHÔNG có icon** (bài
học thiết kế ghi rõ trong comment: trước đây group label từng có icon +
cùng màu chữ + khung bo góc khi collapsed, trông giống hệt 1 nút bấm nhưng
bấm vào không làm gì — "false affordance", đã bỏ).
Mỗi `NavLink`: `min-h-11`, `end={item.to==='/admin/overview'}` (exact match
cho overview để không active nhầm với path con), khi collapsed thêm
`title`/`data-tooltip` = label.

---

## 2. Chi tiết từng trang

### 2.1 `AdminOverview.jsx` (route `/admin/overview`)

**Mục đích**: Dashboard tổng quan — pulse trường học, hàng đợi việc cần xử
lý (work queue), audit gần đây. Triết lý thiết kế (comment gốc rất chi
tiết, nên giữ khi port): "Dashboard order: what the school looks like, then
what needs doing, then the trail" — bản cũ hiện 10 card work-queue cao hết
màn hình khiến số liệu tổng quan bị đẩy xuống dưới fold, đã sửa thành
preview 5 dòng + "xem tất cả".

**Layout** (bọc `<AdminAsyncRegion loading error onRetry={load}>`):
1. Header trạng thái hệ thống: `h2` = `t('admin.overviewSummaryTitle')`; bên
   phải: dot tròn xanh/vàng (`bg-success`/`bg-warning` theo
   `system_status==='HEALTHY'`) + `adminSystemStatusLabel` + `Cập nhật lúc:
   {last_updated}`.
2. **School pulse** — grid `grid-cols-2 lg:grid-cols-4`, 4 `SummaryMetric`
   (icon trong khung vuông bo góc nền `accent-soft`, label 11px uppercase,
   value **30px bold mono** — tỷ lệ cỡ chữ 30/11 cố ý để số liệu "nhảy vào
   mắt trước" mà không cần màu sắc phụ trợ): Students (`Users`,
   `active_students`), Instructors (`UserPlus`, `active_instructors`),
   Courses (`BookOpen`, `courses`), Sections (`Layers`, `sections`).
3. Grid `lg:grid-cols-3`:
   - **Work Queue** (`lg:col-span-2`, card viền): header icon `AlertTriangle`
     + tiêu đề + count mono lớn màu accent + mô tả phụ.
     - Rỗng: `t('admin.workQueueEmpty')`.
     - Có dữ liệu: `<ul>` danh sách `QueueItem` — mỗi dòng desktop là
       **1 hàng grid 6 cột** `4.5rem_minmax(8.5rem,max-content)_6.5rem_minmax(0,1fr)_5rem_auto`
       (mobile wrap tự do): badge Priority (màu theo `PRIORITY_STYLE`:
       CRITICAL=đỏ, HIGH=vàng, MEDIUM/LOW=viền thường) · Trigger type
       (`adminTriggerLabel`) · Subject ID (mono, `—` nếu rỗng) · Summary
       (`adminWorkQueueSummary`, truncate + `title` tooltip) · Age
       (`age(seconds,t)` — "vừa xong"/"N phút"/"N giờ"/"N ngày") · Link
       "Mở" (`workQueueHref(item)`, icon `ChevronRight`).
     - **Preview 5 dòng** (`QUEUE_PREVIEW_SIZE=5`) mặc định; nếu tổng > 5 →
       nút "Xem tất cả ({count})" / "Thu gọn" (`ChevronRight`, toggle
       `queueExpanded`) → khi mở, phân trang `QUEUE_PAGE_SIZE=10`/trang với
       nút Prev/Next (`h-11 w-11`, disable ở biên).
   - **Signals panel** (card viền): header `t('admin.overviewSignalsTitle')`.
     - `QueueBreakdown` — `<dl>` liệt kê `work_queue.by_type` sort giảm dần
       theo count: label (`adminTriggerLabel`) trái, count mono bold phải.
     - 2 `SignalMetric` (Risk chưa xử lý, tỷ lệ kích hoạt lời mời): mỗi cái
       hiện `{value*100}%` lớn màu accent bên phải (hoặc
       `t('admin.metricNoDenominator')` nếu không có mẫu số — **không bao
       giờ hiện 0% giả** khi chưa đo được), kèm `{numerator}/{denominator}`
       mono nhỏ. Có `<details>` xổ xuống "Provenance" (ẩn mặc định — comment
       gốc: đây là metadata tham khảo, không phải tin tức, phải thu gọn
       tránh cạnh tranh sự chú ý với work queue) hiện: Period (khoảng thời
       gian hoặc "as of" timestamp), Measured at, Method note.
4. **Recent critical changes** (card viền, header icon `History`): preview
   `CHANGES_PREVIEW_SIZE=5` dòng đầu (API trả tối đa 10, không hiện hết —
   lý do trong comment: card cũ chiếm 54% chiều cao trang chỉ để trả lời
   "có gì đổi trong lúc tôi vắng mặt", 5 dòng đã đủ trả lời câu đó, muốn xem
   hết thì qua Audit Log có filter). Mỗi `CriticalChange`: dòng 1 =
   `adminCriticalChangeEventLabel · adminAuditDecisionLabel`; `<dl>` chi
   tiết: Actor (nếu có), Subject (nếu có), Resource (nếu có,
   `adminResourceLabel + resource_id`), Time. Cuối card: **Link** (không
   phải toggle) "Xem tất cả lịch sử" → `/admin/governance/logs#audit-log`
   (vì đây là điều hướng sang trang khác có filter, không phải mở rộng tại
   chỗ — API chỉ trả tối đa 10 dòng nên "mở rộng tại chỗ" sẽ không bao giờ
   là "toàn bộ lịch sử" thật).

**State**: `overview`(null), `loading`(true), `error`(null), `queuePage`(1),
`queueExpanded`(false). `useEffect([load])` load khi mount; `useEffect`
riêng kẹp `queuePage` không vượt `totalQueuePages` khi tổng số đổi.

**API**: `getAdminOverview()` — 1 endpoint duy nhất, mọi số liệu trên trang
đều lấy từ response này (không có API riêng cho từng khối).

---

### 2.2 `AdminPeopleExplorer.jsx` (route `/admin/people`)

**Mục đích**: Danh bạ người dùng có tìm kiếm + lọc role + phân trang, điểm
vào để nhảy tới 360 view.

**Layout**:
- `h2` = `t('admin.navPeople')`.
- Form filter (`flex flex-wrap items-end gap-3`): ô Search (`type=search`,
  submit mới áp dụng — bấm nút hoặc Enter), select Role (`ROLES=['','STUDENT','INSTRUCTOR','ADMIN']`,
  đổi role **auto-reload ngay**, không cần submit).
- Bảng (bọc `AdminAsyncRegion`, cuộn ngang `min-width 40rem`), 5 cột: Tên+email
  (2 dòng), Role (mono), Status (Active xanh/Locked đỏ), Academic summary
  (mono, liệt kê `Object.entries(academic_summary)` dạng `"label: value"`
  nối ` · `), Mở hồ sơ (link `/admin/students/{id}` hoặc
  `/admin/instructors/{id}`; role ADMIN hiện `—` — không có 360 view).
- Phân trang: Prev/Next dưới bảng, disable theo `page<=1`/`!meta.has_next`.

**Lưu ý hành vi cần giữ đúng khi port**: ô Search **KHÔNG debounce** — theo
comment agent audit, đổi `role`/`page` tự động load lại qua
`useEffect([load])`, và `search` cũng nằm trong dependency của `load`
(useCallback) nên gõ mỗi ký tự tạo `load` mới → tự động gọi lại API mỗi
keystroke (không có debounce, không cờ chặn double-fetch ngoài generation
pattern). Đây có thể là chỗ nên CẢI THIỆN khi port sang (thêm debounce)
chứ không nhất thiết sao chép y hệt nhược điểm.

**State**: `search`(''), `role`(''), `page`(1), `data`(null), `loading`(true),
`error`(null), `requests` = `useRef(createRequestGeneration())`.

**API**: `listAdminPeople({search, role, page, page_size:25})`.

---

### 2.3 `AdminStudent360.jsx` (route `/admin/students/:studentId/*`)

**Mục đích**: Hồ sơ tổng hợp 1 học viên, nhiều tab con.

**Route con nội bộ**:
```
index (rỗng)  → Navigate to {base}/summary
summary       → <StudentSummary/>
plans         → resources: [plans, tasks, progress-events, reminders]
coursework    → resources: [assignments, submissions]
reflection    → resources: [reflections]
conversations → resources: [conversations]
risk          → resources: [risk, interventions]
sessions      → resources: [sessions]
documents     → resources: [documents]
access-history→ accessAudit: true
*             → thông báo "route not found"
```
8 tab raw sinh **data-driven** từ `ADMIN_RAW_TABS` (file
`adminSensitiveResources.js`) — vòng `.map()` tạo cả NavLink lẫn Route,
không hard-code từng route trong JSX.

**Layout cha**: thanh nav ngang (`flex flex-wrap gap-2`) — 1 NavLink
"Summary" + N NavLink từ `ADMIN_RAW_TABS`. Style active:
`border-accent bg-accent-soft text-accent`; inactive: `border-line hover:border-accent`.

**`StudentSummary`** (tab mặc định): breadcrumb "People" → studentId; 2
`AdminSummaryCard` (Activity, Risk summary); section Enrollments (list mono
`section_code · statusLabel`); ghi chú cuối trang giải thích đây chỉ là số
liệu tổng hợp, chi tiết nằm ở các tab raw phía trên.

**API**: `getAdminStudentSummary(studentId)`.

---

### 2.4 `AdminInstructor360.jsx` (route `/admin/instructors/:instructorId`)

**Mục đích**: Hồ sơ tổng hợp 1 giảng viên — **cố ý KHÔNG có drill-down
xuống từng học viên cụ thể** (comment gốc: đây là workload tổng hợp, không
định danh học viên nào, để tránh suy luận dữ liệu cá nhân 1 SV cụ thể từ dữ
liệu lớp — khác hẳn triết lý của Student 360).

**Layout**: breadcrumb People → instructorId; header tên + email·role; 3
`AdminSummaryCard`: Roster, Risk workload, Interventions; section
"Sections" (list mono `section_code · course_code · N học viên`); text
`admin.instructorCaseLimit` + link "Mở People" (`/admin/people`) thay cho
drill-down.

**API**: `getAdminInstructorSummary(instructorId)`.

Không có filter/form/modal — trang chỉ đọc hoàn toàn thụ động.

---

### 2.5 `AdminRawDataViewer.jsx` (component lõi, nhúng trong mỗi tab raw của Student360)

**Cơ chế bảo vệ dữ liệu nhạy cảm**: hoàn toàn ở tầng BACKEND/API error, KHÔNG
có modal "nhập lý do truy cập" hay toggle reveal/hide ở UI. `AdminAsyncRegion`
phân biệt: 403/`SENSITIVE_ACCESS_DENIED`/`SENSITIVE_SESSION_EXPIRED` → khối
cảnh báo màu warning, **không cho Retry** (vì retry không giải quyết được
vấn đề quyền/phiên); 503/`SENSITIVE_AUDIT_UNAVAILABLE` → khối đỏ, có Retry.

**API**: nếu `accessAudit=true` → `listAuditEvents({eventType:'ADMIN_SENSITIVE_READ', subjectUserId, limit:25})`.
Ngược lại: `Promise.all` gọi `readAdminRawData('/admin/students/{id}/{resourcePath}', {page:1,page_size:25})`
cho MỖI resource trong tab, gộp `items` lại + gắn `resource_type`. Nếu bất
kỳ response nào có `meta.nested_truncated=true` → hiện cảnh báo "dữ liệu con
bị cắt bớt".

**Render mỗi item**: qua `describeRawItem(resourceType, item)` (từ
`adminRawPresentation.js`) — trả `{titleKey, title, subtitle, rows, body,
transcript}`. **CHỈ field được khai báo whitelist mới hiển thị** — field lạ
bị loại bỏ hoàn toàn (chống leak dữ liệu server thêm mà chưa duyệt UI). Bảng
đặc tả đầy đủ 13 resource type (plans, tasks, assignments, submissions,
reflections, conversations, documents, progress-events, reminders, risk,
interventions, sessions, access-audit) — xem chi tiết field/label trong
`adminRawPresentation.js` gốc; mỗi resource có `titleKey` + field nào làm
title/subtitle + danh sách rows (label←field) + có body text không + có
transcript (hội thoại) không.

**`ConversationTranscript`** (chỉ cho resource `conversations`): accordion
Show/Hide, khi mở gọi `readAdminRawData('/admin/students/{id}/conversations/{convId}', {page,page_size:25})`.
Message bị guardrail chặn (`guardrail.classification==='BLOCKED'`) → viền đỏ
nhạt + badge "Blocked". Phân trang riêng cho transcript (Prev/Next).

**Nội dung template hóa**: `assignments`/`reflections` là dữ liệu seed sinh
theo template tiếng Anh cố định — `localizeAdminRawContent()` dùng
regex/map tra cứu để "dịch" sang tiếng Việt hiển thị (khớp nguyên câu, không
phải dịch máy). Đây là hành vi đặc thù chỉ hoạt động đúng với dữ liệu demo
có sẵn — nếu port sang nhánh khác có seed data khác, phần dịch này sẽ không
khớp và cần viết lại map tương ứng.

**Generation pattern**: mọi nơi có id/tham số đổi nhanh (đổi student, đổi
tab, đổi trang) dùng `createRequestGeneration()` (`requestGeneration.js`) để
tránh set state của request cũ đè lên request mới.

---

### 2.6 `AdminDataRequests.jsx` (route `/admin/data-requests`)

**Mục đích**: Hàng đợi DSAR (Access/Export/Correction/Deletion).

**Layout**: `h2`; bọc `AdminAsyncRegion`; `<ul>` mỗi request là `<li>` viền:
dòng đầu = badge status màu (`STATUS_STYLE`: PENDING=vàng, IN_PROGRESS=accent,
COMPLETED=xanh, REJECTED/khác=viền thường) + type (`adminDataRequestTypeLabel`)
+ subject_user_id; dòng ngày `requested_at`; nhúng `<AdminDataRequestActions/>`;
nếu có `result_summary` → dòng "đã xoá N bản ghi". **KHÔNG hiển thị nội dung
ghi chú tự do của subject** (cố ý, comment gốc).

**`AdminDataRequestActions`** (mỗi item): return `null` nếu status đã
terminal (`COMPLETED`/`REJECTED`). Textarea note (`minLength=10`). Nút theo
status: PENDING→"Start" (→`IN_PROGRESS`); luôn có "Reject" (trừ terminal);
IN_PROGRESS+DELETION→"Preview" (không cần note hợp lệ) → hiện box cảnh báo
đỏ liệt kê `record_counts`/`category_counts` + nút "Confirm purge" (cần
`preview_hash` khớp); IN_PROGRESS+không phải DELETION→"Complete".

**API**: `listAdminDataRequests({limit:50})`, `transitionAdminDataRequest(id,{status,resolutionNote})`,
`previewDataRequestDeletion(id)`, `confirmDataRequestDeletion(id, previewHash)`.

---

### 2.7 `AdminUsers.jsx` (nhúng trong route `governance/access`, cùng `AdminInvitations`)

**Mục đích**: Quản lý user hiện có — khoá/mở tài khoản, đổi role+phạm vi lớp.

**Layout**: header + select filter role (`ROLES=['','STUDENT','INSTRUCTOR','ADMIN']`,
auto-reload khi đổi). Bảng 6 cột cố định width qua `<colgroup>`: Identity
(tên+email 2 dòng), Role (mono), Classes (mono, `class_ids.join(', ')`),
Last active (`toLocaleString`), Status (Active xanh/Locked đỏ), Actions.
- Role `ADMIN` → cột Actions hiện `"Admin được bảo vệ"` (icon `ShieldCheck`),
  **không có nút nào** — không tự khoá/đổi quyền chính admin.
- 2-step confirm khoá/mở tài khoản: bấm icon `LockKeyhole` → dòng đó chuyển
  thành box confirm inline (`role="group"`, width cố định 288px) với
  textarea reason (`autoFocus`, `minLength=5, maxLength=500`) + nút Confirm
  (disable nếu reason<5 ký tự)/Cancel.
- Nút `KeyRound` "Đổi quyền" → mở **modal thật** (overlay `bg-black/40`,
  `role="dialog" aria-modal`, đóng bằng Escape khi không `busy`): select
  Role (`ACCESS_ROLES=['STUDENT','INSTRUCTOR']` — chỉ 2 role này đổi qua
  lại được, không đổi thành ADMIN qua đây), input Classes (comma-separated,
  cảnh báo vàng nếu role=INSTRUCTOR mà rỗng), textarea reason
  (`minLength=10`). Submit disable nếu reason<10 ký tự hoặc (role=INSTRUCTOR
  và không có class nào).
- **Focus-return pattern**: sau khi đóng confirm/modal, focus tự động trả về
  đúng nút đã mở nó (`actionButtonRefs` Map + `focusReturnKey` state).

**API**: `listAdminUsers(role)`, `setAdminUserActive(userId, isActive, changeReason)`,
`updateAdminUserAccess(userId, {role, classIds, changeReason})`.

---

### 2.8 `AdminInvitations.jsx` (nhúng trong route `governance/access`)

**Mục đích**: Tạo/quản lý lời mời (invite) theo email + role + lớp.

**Layout**: form tạo (grid `md:grid-cols-[2fr_1fr_2fr_auto]`): Email
(`type=email, required`), Role (select STUDENT/INSTRUCTOR), Classes (text,
placeholder `"SE1801, SE1802"`, parse qua `parseClassIds` — tách phẩy, trim,
loại rỗng/trùng), nút Submit. Cảnh báo inline nếu role=INSTRUCTOR mà chưa
nhập lớp.

Sau tạo/resend thành công: box vàng hiện **token kích hoạt 1 lần** (URL đầy
đủ, mono, nút Copy — `navigator.clipboard.writeText`, không có toast xác
nhận) + Delivery status.

Bảng danh sách: Email, Role (mono), Classes (hoặc ô sửa inline khi
`editingId` khớp), Status, Delivery (+ lỗi delivery màu đỏ nếu có), Last
sent, Resend count (mono), Actions (chỉ hiện khi `status==='pending'`: Edit
scope / Resend / Revoke).

Sửa scope: bấm Edit → ô Classes thành input inline (autoFocus) + nút
Save/Cancel — **không phải modal**, chỉ inline-edit tại chỗ trong bảng.

**API**: `listAdminInvitations()`, `createAdminInvitation({email,role,classIds})`,
`resendAdminInvitation(id)`, `revokeAdminInvitation(id)`,
`updateAdminInvitationScope(id, classIds)`.

---

### 2.9 `AdminCurriculum.jsx` (route `governance/curriculum`) — trang lớn nhất

**Mục đích**: Quản lý course + vòng đời tài liệu (upload/validate/publish/
archive/rollback/replace/delete), có polling sau upload.

**Layout**:
- Header + nút "Add course" (toggle form).
- Form thêm course: 3 field (Code — auto uppercase, Name, Semester mặc định
  `'Fall 2026'`); Save disable nếu field nào rỗng.
- Bảng Courses (7 cột: Code, Name, Semester, Source+badge, Chunk count,
  Status (`StatusBadge kind="ingest"`), Actions). Actions/dòng: Upload
  document (label file input ẩn, `accept=".md,.txt"`), View/Hide documents
  (toggle expand), Delete (2-step confirm inline).
- **Document Workspace** (khi expand 1 course): mỗi document là `<article>`
  grid 3 cột (info | workflow trạng thái Ingest→Publication | action
  buttons). Actions theo `actionsForDocument()` (từ `adminCurriculumLifecycle.js`):
  - `DRAFT` → validate, replace, delete
  - `READY_FOR_REVIEW` → validate, publish, replace, delete
  - `PUBLISHED` → archive, history
  - `ARCHIVED` → history
  - Document không phải `admin_curriculum` (source_kind khác) → badge
    "Read-only", không action nào.
- **Validate**: chạy check, kết quả hiện `ValidationPreview` (danh sách
  check pass/fail, lỗi nếu có).
- **Publish/Archive/Rollback**: mở modal `LifecycleConfirmation` — textarea
  "Change reason" (**`minLength=5, maxLength=500`, dùng chung `isChangeReasonValid()`
  — pattern lặp lại ở NHIỀU trang khác: AdminUsers, AdminSettings,
  AdminGuardrailRules, AdminRiskPolicy**), có focus-trap thủ công (Tab/Shift+Tab
  vòng trong dialog qua `focusTrapTargetIndex()`), đóng bằng Cancel/Escape/click
  overlay ngoài (chặn khi đang xử lý).
- **Replace**: click ẩn kích hoạt input file → upload → polling (xem dưới).
- **Version history**: `VersionHistory` — mỗi version có nút Rollback nếu
  `isRollbackEligible()` (đã ARCHIVED + ingested + validation không fail).
- **Preview nội dung file**: nút View → `<pre>` hiện raw content.

**Polling sau upload/replace/delete**: 10 lần × 3 giây, dừng khi
`hasUploadCompleted`/`hasReplaceCompleted`/`hasDeleteCompleted` (từ
`adminCurriculumLifecycle.js`) trả true (so khớp id/filename chuẩn hoá +
ingest_status đã terminal `ingested`/`failed`) hoặc hết 10 lần.

**Khoá đồng thời**: `claimOperation`/`releaseOperation` — khoá theo cả `key`
(vd `document:validate:{id}`) LẪN `documentId` riêng (double-lock), tránh 2
action chạy song song trên cùng 1 document.

**API** (10 hàm): `listAdminCourses`, `createAdminCourse`, `deleteAdminCourse`,
`listCourseDocuments`, `uploadCourseDocument` (multipart), `replaceCourseDocument`
(multipart PUT), `deleteCourseDocument`, `validateCourseDocument`,
`publishCourseDocument`/`archiveCourseDocument`/`rollbackCourseDocument`
(đều nhận `changeReason`), `listCourseDocumentVersions`, `getCourseDocumentContent`.

---

### 2.10 `AdminAiPolicy.jsx` (route `governance/ai-policy`)

Chỉ là wrapper: `<div className="space-y-6"><AdminGuardrailRules/><AdminRiskPolicy/></div>`.
Không state/logic riêng.

### 2.11 `AdminGuardrailRules.jsx`

**Mục đích**: Bật/tắt rule chặn nội dung AI, có bước preview bắt buộc trước
publish.

**Layout**: header + badge active version. Cảnh báo vàng nếu có rule đang
tắt (`any_disabled`). Textarea "Change reason" **dùng CHUNG cho mọi hành
động** (preview/publish/restore/rollback) — đổi nội dung reason tự động huỷ
preview đang có. Mỗi rule: 1 nút duy nhất "Bật/Tắt · Xem trước thay đổi" —
disable nếu rule `core_locked` đang bật (không cho tắt rule lõi, nhưng bật
lại được). Khối preview kết quả (khi có) → nút Publish riêng. Nút "Restore
defaults". Lịch sử phiên bản có nút Rollback từng dòng (trừ dòng active).

**Xác nhận**: dùng `window.confirm()` NATIVE (không phải modal tuỳ biến) cho
Publish/Restore/Rollback — không có cho Preview.

**API**: `listGuardrailRules`, `getGuardrailPolicyHistory`,
`previewGuardrailRule(code, enabledMới, reason)`, `setGuardrailRule(code,
enabled, reason)` (= publish), `restoreGuardrailDefaults(reason)`,
`rollbackGuardrailPolicy(version, reason)`.

### 2.12 `AdminRiskPolicy.jsx`

**Mục đích**: Cấu hình ngưỡng phát hiện rủi ro (late days + completion
rate), preview tác động trước khi publish.

**Layout**: box "How it works" giải thích LIVE theo giá trị form đang gõ
(không cần preview mới thấy) — 2 điều kiện + 3 mức Low/Medium/High (mô tả
tĩnh) + ví dụ cụ thể. Form 2 field: Late days threshold (number, min1 max90),
Completion rate (number %, min0 max100, lưu nội bộ dạng thập phân 0–1).
Textarea reason (`>=5 ký tự`, KHÔNG giới hạn max trong file này — khác
Guardrail có validate y hệt nhưng risk-policy chỉ check min). Nút Preview
(chỉ cần reason hợp lệ) → nút Publish (**bắt buộc phải bấm Preview trước**,
disable nếu chưa có `preview`). Đổi BẤT KỲ field nào (kể cả reason) → huỷ
preview hiện có. `window.confirm()` cho Publish/Rollback.

**API**: `getRiskPolicy`, `getRiskPolicyHistory`, `previewRiskPolicy(payload)`,
`publishRiskPolicy(payload)`, `rollbackRiskPolicy(version, reason)`.

---

### 2.13 `AdminAuditLog.jsx` + `AdminAccessAudit.jsx` + `AdminLogExplorer.jsx` (dùng chung)

2 trang wrapper mỏng (`AdminAuditLog` cho tab "Audit", `AdminAccessAudit` cho
tab "Access" — cả 2 chỉ set `kind` khác nhau) đều render
`<AdminLogExplorer kind="audit"|"access" .../>` — toàn bộ logic thật nằm ở
đây.

**Tải dữ liệu 1 lần, lọc/phân trang client-side**: `listAuditEvents({limit:100,
...(kind==='access'?{eventType:'ADMIN_SENSITIVE_READ'}:{})})` — tải TỐI ĐA
100 bản ghi, mọi filter/trang sau đó xử lý hoàn toàn ở client (KHÔNG gọi lại
API khi đổi filter/trang, chỉ khi đổi `kind`/`lang`).

**8 field filter** (grid `md:grid-cols-2 xl:grid-cols-4`): Search (full-text
trên chuỗi ghép nhiều field), Actor, Target, Event type (14 loại cố định +
loại thực tế xuất hiện trong data, khoá cứng = `ADMIN_SENSITIVE_READ` nếu
`kind='access'`), Decision (ALLOW/DENY), Resource, From date, To date. Nút
"Clear filters" khi có filter active.

**Bảng**: 6 cột (Time, Event [2 dòng: label dịch + raw mono], Decision
[badge đỏ/xanh], Resource, Subject [`getLogTarget()`], Actor). Mỗi hàng
click/Enter/Space → mở **panel chi tiết dạng slide-in bên phải** (không phải
modal giữa màn hình) — overlay mờ, đóng bằng nút X/Escape/click overlay.
Panel hiện đầy đủ: Time, Decision, Actor, Subject, Resource, Resource ID,
Request ID, Correlation ID, Change reason, khối Metadata (`<pre>` JSON).

Phân trang: `LOG_PAGE_SIZE=25`, Prev/Next, reset về trang 1 mỗi khi đổi
filter.

**Phân biệt 2 loại "trống"**: "không có dữ liệu gốc" (qua `AdminAsyncRegion`)
khác với "có dữ liệu nhưng filter không khớp" (`admin.logNoMatches`, style
khác — border dashed, KHÔNG đi qua `AdminAsyncRegion`).

---

### 2.14 `AdminAnalytics.jsx` (nhúng cuối `governance/settings`)

Chỉ 1 "strip" số liệu (không phải dashboard riêng — comment gốc): 4 `Stat`
ngang hàng (Courses ingested/total, Documents, Chunks, At-risk students).
Nếu `measurement_status==='not_measured'` → khối cảnh báo riêng giải thích
chưa đo được. `method_note` hiển thị cuối. Không filter, chỉ đọc.

**API**: `getAdminAnalyticsSummary()`.

### 2.15 `AdminSettings.jsx` (nhúng đầu `governance/settings`)

Form: checkbox Auto risk alert (toggle), input Default semester (text,
required), textarea Change reason (`minLength=5, maxLength=500`). Submit
disable nếu `!settings || !reasonValid`. Sau lưu: đồng bộ lại `settings` từ
response server (không tự tin giữ giá trị local), reset reason, hiện message
xanh thành công.

**API**: `getAdminSettings()`, `updateAdminSettings(settings, changeReason)`.

### 2.16 `AdminAcademicCalendar.jsx` (nhúng cuối `AdminSettings.jsx`)

2 form độc lập:
- **Term**: Name, Start date, Study weeks (1-20), Exam weeks (1-6). Sau lưu
  hiện dòng "start→end · PE/FE examStart→examEnd".
- **Exam**: Course (select), Kind (PE/FE), Exam date (`min/max` ràng theo
  `term.exam_start/exam_end`), Slot (select 6 ca cố định
  `EXAM_SLOTS`: 07:30–09:00, 09:10–10:40, 10:50–12:20, 12:50–14:20,
  14:30–16:00, 16:10–17:40), + mảng "extra sessions" (nút "Thêm ca thi" —
  CHỈ mở rộng form, không gọi API ngay). Submit gộp session chính + extra
  (lọc bỏ phần tử thiếu exam_date) thành mảng `sessions` gửi 1 lần. Danh
  sách lịch thi đã tạo bên dưới, mỗi dòng có nút Xoá.

**API**: `getAcademicTerm`, `getAcademicExams`, `upsertAcademicTerm(payload)`,
`upsertCourseExam({course_id,kind,sessions})`, `deleteCourseExam(examId)`.

---

## 3. Danh sách hàm API `admin.*` cần có ở `lib/api.js`

Toàn bộ hàm dưới đây đều là wrapper mỏng gọi `request(path, options)` — 1
hàm base dùng chung xử lý cookie-session auth + CSRF header + auto-refresh
token khi 401 + parse lỗi thống nhất (`ApiError{code,status,message,details}`).
2 hàm upload document dùng `fetch` trực tiếp với `FormData` (multipart,
không qua `request()`).

| Nhóm | Hàm | Method | Path |
|---|---|---|---|
| Courses | `listAdminCourses()` | GET | `/admin/courses` |
| | `createAdminCourse({subject_code,subject_name,semester})` | POST | `/admin/courses` |
| | `deleteAdminCourse(code)` | DELETE | `/admin/courses/{code}` |
| | `restoreAdminCourse(code)` | POST | `/admin/courses/{code}/restore` |
| Documents | `listCourseDocuments(code)` | GET | `/admin/courses/{code}/documents` |
| | `getCourseDocumentContent(code, docId)` | GET | `.../documents/{docId}/content` |
| | `deleteCourseDocument(code, docId)` | DELETE | `.../documents/{docId}` |
| | `uploadCourseDocument(code, file)` | POST multipart | `/admin/courses/{code}/documents` |
| | `replaceCourseDocument(code, docId, file)` | PUT multipart | `.../documents/{docId}` |
| | `validateCourseDocument(code, docId)` | POST | `.../documents/{docId}/validate` |
| | `publishCourseDocument(code, docId, changeReason)` | POST | `.../documents/{docId}/publish` |
| | `archiveCourseDocument(code, docId, changeReason)` | POST | `.../documents/{docId}/archive` |
| | `rollbackCourseDocument(code, docId, changeReason)` | POST | `.../documents/{docId}/rollback` |
| | `listCourseDocumentVersions(code, docId)` | GET | `.../documents/{docId}/versions` |
| Academic calendar | `getAcademicTerm()` | GET | `/admin/academic-term` |
| | `upsertAcademicTerm(payload)` | PUT | `/admin/academic-term` |
| | `getAcademicExams()` | GET | `/admin/academic-term/exams` |
| | `upsertCourseExam(payload)` | PUT | `/admin/academic-term/exams` |
| | `deleteCourseExam(examId)` | DELETE | `/admin/academic-term/exams/{examId}` |
| Analytics | `getAdminAnalyticsSummary()` | GET | `/admin/analytics/summary` |
| Guardrail | `listGuardrailRules()` | GET | `/admin/guardrail-rules` |
| | `previewGuardrailRule(code, enabled, changeReason)` | POST | `.../{code}/preview` |
| | `getGuardrailPolicyHistory()` | GET | `/admin/guardrail-rules/history` |
| | `setGuardrailRule(code, enabled, changeReason)` | PATCH | `/admin/guardrail-rules/{code}` |
| | `restoreGuardrailDefaults(changeReason)` | POST | `/admin/guardrail-rules/restore-defaults` |
| | `rollbackGuardrailPolicy(version, changeReason)` | POST | `.../versions/{version}/rollback` |
| Audit | `listAuditEvents({eventType,actorUserId,subjectUserId,resourceType,resourceId,decision,limit=100})` | GET | `/audit/events?...` |
| Users/Access | `listAdminUsers(role='')` | GET | `/admin/users?role=...` |
| | `setAdminUserActive(userId, isActive, changeReason)` | PATCH | `/admin/users/{userId}` |
| | `updateAdminUserAccess(userId,{role,classIds,changeReason})` | PATCH | `/admin/users/{userId}/access` |
| Invitations | `listAdminInvitations()` | GET | `/admin/invites` |
| | `createAdminInvitation({email,role,classIds})` | POST | `/admin/invites` |
| | `revokeAdminInvitation(id)` | POST | `/admin/invites/{id}/revoke` |
| | `resendAdminInvitation(id)` | POST | `/admin/invites/{id}/resend` |
| | `updateAdminInvitationScope(id, classIds)` | PATCH | `/admin/invites/{id}` |
| Risk policy | `getRiskPolicy()` | GET | `/admin/risk-policy` |
| | `getRiskPolicyHistory()` | GET | `/admin/risk-policy/history` |
| | `previewRiskPolicy(payload)` | POST | `/admin/risk-policy/preview` |
| | `publishRiskPolicy(payload)` | POST | `/admin/risk-policy` |
| | `rollbackRiskPolicy(version, changeReason)` | POST | `/admin/risk-policy/{version}/rollback` |
| Settings | `getAdminSettings()` | GET | `/admin/settings` |
| | `updateAdminSettings(settings, changeReason)` | PUT | `/admin/settings` |
| Overview/People/360 | `getAdminOverview()` | GET | `/admin/overview` |
| | `getAdminWorkQueue()` | GET | `/admin/work-queue` |
| | `listAdminPeople(params)` | GET | `/admin/people?...` |
| | `getAdminStudentSummary(studentId)` | GET | `/admin/students/{id}/summary` |
| | `getAdminInstructorSummary(instructorId)` | GET | `/admin/instructors/{id}/summary` |
| | `readAdminRawData(path, params)` | GET | `{path}?...` (path đầy đủ do caller truyền, vd `/admin/students/{id}/reflections`) |
| Data requests | `listAdminDataRequests(params)` | GET | `/admin/data-requests?...` |
| | `transitionAdminDataRequest(id,{status,resolutionNote})` | PATCH | `/admin/data-requests/{id}` |
| | `previewDataRequestDeletion(id)` | POST | `/admin/data-requests/{id}/deletion-preview` |
| | `confirmDataRequestDeletion(id, previewHash)` | POST | `/admin/data-requests/{id}/confirm-deletion` |

**So với `develop` hiện tại**: cần đối chiếu từng hàm trên với
`frontend/src/lib/api.js` của `develop` — tên hàm/path SẼ khác (develop dùng
path riêng như `/admin/students/{id}/{resource}` qua
`readAdminStudentResource`, `/admin/instructors/{id}/summary` qua
`getAdminInstructorSummary` đã trùng tên, `/admin/data-requests` cũng đã
có...). Không copy nguyên xi — phải map lại theo backend thật của `develop`
sau khi có `chung-admin-backend.md`.

---

## 4. Component/helper dùng chung (bắt buộc port cùng để các trang trên chạy đúng)

| File | Vai trò |
|---|---|
| `AdminAsyncRegion.jsx` | State machine loading/error/empty chuẩn cho MỌI vùng dữ liệu async. Phân biệt lỗi "sensitive" (403, không cho retry) / "unavailable" (503, có retry) / lỗi chung (có retry). |
| `AdminSummaryCard.jsx` | Card summary dạng `<dl>` grid 2-3 cột; dùng `safeAdminSummaryEntries()` để lọc — field lạ không khai báo bị loại, không render object thô. |
| `adminDisplay.js` | TOÀN BỘ hàm dịch enum→label (priority, status, trigger, role, resource, audit event, work-queue summary, data-request type, risk type, recommended action...). Bắt buộc đọc kỹ trước khi port vì đây là nguồn nhãn hiển thị của gần như mọi trang. |
| `adminCurriculumLifecycle.js` | Logic vòng đời tài liệu (actions theo trạng thái, validate reason, khoá đồng thời, điều kiện polling dừng, rollback eligibility, focus-trap index). |
| `adminWorkQueueLinks.js` | `workQueueHref(item)` — quyết định URL đích khi bấm 1 work-queue item. |
| `requestGeneration.js` | `createRequestGeneration()` — chống race-condition khi id/filter đổi nhanh. |
| `modalFocus.js` | `focusFirstInDialog()`, `trapModalFocus()` — accessibility cho mọi modal. |
| `AdminDataRequestActions.jsx` | Cụm nút hành động DSAR (dùng riêng cho `AdminDataRequests.jsx`). |
| `adminRawPresentation.js` | Bảng đặc tả field hiển thị cho 13 resource-type raw data + dịch nội dung template hoá (assignments/reflections). |
| `adminSensitiveResources.js` | `ADMIN_RAW_TABS` — cấu hình 8 tab raw data (data-driven cho `AdminStudent360`). |
| `adminSensitiveViewerState.js` | `conversationDetailPath()` — build URL chi tiết 1 hội thoại. |
| `adminLogModel.js` | `filterLogEvents()`, `paginateLogEvents()`, `getLogTarget()` — logic filter/phân trang client-side cho Audit/Access log. |

---

## 5. Ghi chú thiết kế/style đáng giữ lại

### Theme riêng cho Admin — `admin-operations.css`
Scope hoàn toàn trong class `.admin-operations` (chỉ áp dụng bên trong
`AdminLayout`), theme "Ink & Citrine" — **khác màu accent với phần
Student/Instructor của app** (dùng vàng đồng thay vì xanh dương):

```css
/* Light */
--admin-ink:#15181C; --admin-ink-secondary:#5B5647;
--admin-paper:#FAF8F3; --admin-surface:#FFFFFF;
--admin-border:#E6E2D8; --admin-border-strong:#D6D1C2;
--admin-accent:#B7791F; --admin-accent-hover:#9C6414; --admin-accent-soft:#F7ECD6;
--admin-success:#2F6B3A; --admin-danger:#9B3B34;
--admin-heading-font:"Source Serif 4",Georgia,serif;
--admin-ui-font:Inter,sans-serif;
--admin-mono-font:"IBM Plex Mono",monospace;

/* Dark (.admin-operations-dark) — chỉ đổi 6 biến nền/viền, accent/success/danger GIỮ NGUYÊN */
--admin-ink:#F2F0EA; --admin-ink-secondary:#C7C1B5;
--admin-paper:#181A1D; --admin-surface:#23262A;
--admin-border:#3A3D42; --admin-border-strong:#585B60;
```
Các biến trên được alias sang bộ biến chung toàn app (`--bg-app`, `--bg-card`,
`--text-primary`, `--accent`, `--border-ui`, `--success`, `--danger`...) để
tái dùng class Tailwind utility có sẵn — `warning`/`warning-soft` **dùng lại
màu accent** (không có màu cam/vàng cảnh báo riêng biệt).

Class layout chính: `.admin-cockpit-main` (max-width 1600px, căn giữa,
padding responsive 1rem→1.5rem→"1.5rem 2rem 2rem"), `.admin-scroll-x`
(overflow-x cho bảng rộng), `.font-display` (font serif riêng cho heading
trong scope admin), `.mono` (font mono cho ID/số liệu — IBM Plex Mono).
`prefers-reduced-motion: reduce` → tắt gần hết animation trong toàn scope.

### Pattern lặp lại xuyên suốt (Tailwind utility quan sát được, không nằm
trong CSS file nhưng dùng nhất quán khắp mọi trang):
- Card: `rounded-lg border border-line p-4` (hoặc `p-3`).
- Badge/pill trạng thái: nền `-soft` + chữ đậm cùng tông (`bg-warning-soft text-warning`, `bg-danger-soft text-danger`, `bg-success-soft text-success`).
- Nút: `min-h-11` (44px touch target bắt buộc), `rounded-lg`, `disabled:opacity-40`, `focus-visible:ring-2 focus-visible:ring-accent`.
- Nút chính/CTA: `bg-accent text-[var(--accent-ink)] font-bold`.
- Nút nguy hiểm: `bg-danger text-white font-bold`.
- Label form: `text-[11px] font-semibold`; input/textarea: `rounded-lg border border-line bg-surface p-2`.
- Label nhỏ phụ: `text-[10px] font-bold uppercase tracking-wide text-fg-secondary`.
- Icon: thư viện `lucide-react`, size chuẩn 13-16px.
- Toàn bộ text qua `useLanguage()` → `t('admin.xxx')` — không có text hard-code, cần tra file locale để lấy nội dung chính xác.
- **`window.confirm()` native** dùng cho các hành động "phá huỷ nhẹ" ở vài trang (Guardrail publish/restore/rollback, Risk policy publish/rollback) thay vì modal tuỳ biến — trong khi các hành động khác (lifecycle document, đổi quyền user) dùng modal thật có focus-trap. Không nhất quán 100% — port giữ đúng theo từng trang, không tự ý đồng bộ hoá thành 1 kiểu.

---

## 6. Điểm mạnh UI/UX của Admin Console `chung` (so với 1 admin console thông thường)

1. **Data-driven navigation & routing** — `NAV_GROUPS`, `ADMIN_RAW_TABS`
   không hard-code trong JSX, dễ thêm/bớt mục mà không sửa logic render.
2. **Phân tách rõ 2 lớp lỗi "quyền" vs "lỗi mạng/máy chủ"** qua
   `AdminAsyncRegion` — không cho Retry khi lỗi 403 (đúng bản chất, retry vô
   nghĩa), có Retry khi 503/lỗi chung.
3. **Whitelist field hiển thị dữ liệu nhạy cảm** (`adminRawPresentation.js`
   `SPECS`) — chống leak field lạ ra UI, đây là pattern bảo mật-by-design
   đáng học.
4. **"Change reason" bắt buộc + audit-friendly** trên MỌI hành động ghi có
   tính rủi ro (khoá user, publish policy, xoá dữ liệu...) — nhất quán độ
   dài tối thiểu 5-10 ký tự tuỳ mức độ nhạy cảm.
5. **Generation pattern chống race-condition** khi điều hướng nhanh giữa
   các hồ sơ/tab — chi tiết dễ bị bỏ sót nhưng ảnh hưởng thật đến độ tin cậy
   dữ liệu hiển thị.
6. **Overview ưu tiên "quan sát trước, xử lý sau"** — pulse số liệu luôn ở
   trên cùng, work-queue preview ngắn có nút mở rộng, audit trail chỉ xem
   nhanh rồi link sang trang Audit Log đầy đủ có filter — tránh dashboard
   "vô tình mọc thành trang danh sách".
7. **Tách Governance (quản trị hệ thống) khỏi Student/Instructor 360 (hồ sơ
   cá nhân)** một cách có chủ đích về mặt kiến trúc thông tin, không chỉ
   route — giảm rủi ro lẫn lộn "công việc vận hành" với "dữ liệu riêng tư 1
   người".
8. **Polling có giới hạn (10×3s) sau upload/replace/delete** thay vì
   WebSocket/SSE — đơn giản, đủ dùng cho tần suất thao tác admin, dễ port.
