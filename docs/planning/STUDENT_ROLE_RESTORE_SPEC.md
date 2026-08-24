# Student Role — Restoration Spec (pre-merge `develop` → current `develop`)

**Purpose of this document.** On `d764153` ("merge: bring in develop history, keep haidang2425
architecture as the base"), the entire pre-merge `develop` branch — 150+ commits of Student-role
work, still reachable at commit `a46db63` — was replaced by a different architecture. Several
frontend component files survived as orphaned dead code (never imported anywhere); almost all of
the backend (services, extra API routers, 5 database tables) was deleted outright.

This document is a complete, standalone specification of the Student role **as it existed at
`a46db63`**, rewritten so it can be implemented from scratch against the **current** `develop`
schema (multi-tenant, `organization_id`-scoped). It is meant to be sufient on its own — no need to
go back and re-read the old commit — to reimplement every screen, endpoint, and business rule.

Everything in sections 1–7 describes **old behavior** (facts, not proposals). Section 8
("Adaptation for multi-tenancy") is the only place where new decisions/design is introduced, since
the old code had **zero** multi-tenancy concept at all.

---

## 0. What changed architecturally between old `develop` and current `develop`

| Aspect | Old `develop` (`a46db63`) | Current `develop` (HEAD) |
|---|---|---|
| Tenancy | None — single global DB, no `organization_id` anywhere | Full multi-tenant: `organizations`, `organization_memberships`, every root table `organization_id`-scoped |
| Account creation | **Public self-registration** (`POST /auth/register`, role locked to `STUDENT` only) + Google OAuth | **No public registration** (ADR-007) — Admin invites only |
| Onboarding gate | `user.onboarded` computed live = "has an active `SemesterSetup` row" | Separate concept, not present the same way — needs to be re-derived |
| First-login content | `StudentMockDataService` auto-provisions a fake 4-course semester on first register/Google-login (non-production only) | No equivalent — current HEAD provisions real orgs/courses via `provision_organization.py` / admin console |

**Read section 8 before implementing anything — it resolves these four conflicts.** The short
version: keep the org-scoping current HEAD already has, keep the invite-only account model
current HEAD already has, and adapt onboarding/mock-seeding to fit *inside* that — do not
reintroduce public registration or drop `organization_id`.

---

## 1. Full Route Map (old `develop`, `frontend/src/App.jsx`)

### 1.1 Session bootstrap
On app mount, `runSessionProbe()` calls `GET /auth/me`. Success builds:
```js
{
  id, name: profile.full_name, email, role: profile.role.toLowerCase(),
  onboarded: profile.onboarded, major: profile.major || null,
  studentCode: profile.student_code || null,
  email_confirmed: profile.is_email_verified,
  isDemo: Boolean(profile.is_demo),
  organizationName: profile.organization_name || null,
  preferences: profile.preferences || {},
}
```
`authStatus`: `'authenticated'` if `email_confirmed`, else `'email_unverified'`; `401` →
`'unauthenticated'`; network/5xx → `'error'` (shows `ApiErrorScreen`/`ConnectionBanner` with retry).
Theme/lang are read from `user.preferences` on login and pushed back via
`PUT /auth/me/preferences` on every change (skipped for demo users). A global 401/403 handler on
any authenticated call forces `setUser(null)`, `authStatus='session_expired'`, redirect to
`/login?returnTo=...&reason=session_expired`.

### 1.2 Post-login/onboarding redirect logic
`AuthedElsewhereRedirect` (used whenever a signed-in user lands on a public route):
```js
if (!user.email_confirmed) return <Navigate to="/email-verification" replace />;
if (!user.onboarded)        return <Navigate to="/onboarding" replace />;
return <Navigate to={DEFAULT_ROUTE[user.role]} replace />;   // student → '/student'
```
`/onboarding` itself: `user.onboarded` → redirect to `DEFAULT_ROUTE[role]`; unverified email →
redirect `/email-verification`; else render `OnboardingScreen`.

### 1.3 Protected dashboard mount
```jsx
<Route path="/student/*" element={
  authStatus === 'error'
    ? <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
    : <ProtectedRoute authStatus={authStatus} user={user} allowedRoles={['student']}>
        <AppShell user={user} onLogout={logout} />
      </ProtectedRoute>
}/>
```

### 1.4 Inside `AppShell` — student route table (relative to `/student`)
`AppShell` wraps its `<Routes>` in `<Gate2Provider>` **only when `user.role === 'student'`**.

| Relative path | Component |
|---|---|
| `settings` | `SettingsScreen` (shared across roles) |
| `planner` | `StudentPlanner` |
| `today` | `TodayPlanScreen` |
| `reflection` | `StudentReflection` |
| `practice` | `StudentPractice` |
| `semester-setup` | `SemesterSetupWizard` |
| `self-study/:blockId` | `SelfStudySession` |
| `lecture-plan` | `LecturePlanPanel` |
| `home`, `/` (i.e. `/student`) | `StudentHome` — **the default landing screen** |
| `*` | `NotFoundPage` |

Only for `role === 'student'`, `AppShell` also mounts globally (outside `<Routes>`, own
`<Suspense fallback={null}>`): `<CompanionChatBubble />` (floating chat, every page) and
`<SelfStudyReminder />` (invisible poller, every page).

### 1.5 Sidebar (student role) — exactly 5 items, literal Vietnamese copy
1. **"Tổng quan"** → `/student` (icon `LayoutDashboard`)
2. **"Lập kế hoạch tuần"** → `/student/planner` (icon `Target`)
3. **"Kế hoạch hôm nay"** → `/student/today` (icon `CheckSquare`)
4. **"Phản tư"** → `/student/reflection` (icon `RotateCcw`)
5. **"Luyện tập"** → `/student/practice` (icon `FlaskConical`)

`semester-setup`, `lecture-plan`, `self-study/:blockId` have **no sidebar entry** — reachable only
via deep links (onboarding step 2, `LecturePlanPanel`'s own "Sửa học kỳ" link, and the Timetable
block-edit modal's "Start studying" button, respectively).

`AppShell` runs an `IntersectionObserver` (student only) over section ids
`['top', 'weekly-plan-section', 'qa-section']` inside the scrollable `<main>` to track which
sidebar item is "active" as the user scrolls `StudentHome`.

### 1.6 Topbar (student-relevant)
Semester indicator dot + text; disabled search box (future); `NotificationsBell` (client-only seed
data, no backend — see §4.2); theme + language toggles; profile button → `/student/settings`.

---

## 2. Frontend Screens

### 2.1 `StudentHome.jsx` — `/student`, `/student/home` (the dashboard)

**Purpose**: main dashboard — one prioritized "next best action" task, weekly progress KPIs, a
Plan→Do→Reflect stepper, a daily-study-hours chart, nearest upcoming deadline.

**Data**: consumes `Gate2Context` (`useGate2()`) — no direct API calls except the embedded
`DailyStudyChart`, which independently calls `GET /student/self-study/weekly-stats` on mount and
fails silently (returns `null`, never blocks the page).
From context: `assignment, currentPlan, deferReasons, completedCount, totalCount, progressPct,
nextBestAction, phase, loading, error, mutating, reload, startTask, completeTask, deferTask`.
- `loading` → 3 skeleton blocks (hero `h-40`, 3×`h-24` grid, 4×`h-20` rows).
- `error` → "Không tải được không gian học tập" / "Could not load your workspace" + retry = `reload()`.

**UI, top → bottom**:
1. **`NextBestAction` hero card**:
   - Greeting `"Chào {getTimeOfDay(lang)}, {lastName}!"` — `getTimeOfDay`: <12h "buổi sáng"/"morning",
     <18h "buổi chiều"/"afternoon", else "buổi tối"/"evening".
   - Deterministic daily quote: `dayOfYear % 10` index into a 10-item curated Vietnamese/English
     quote array (no localStorage — same quote all day, changes daily).
   - If `nextBestAction` exists: title, `estimatedMinutes` (via `formatMinutes`),
     `ProvenanceBadge sourceType="ai_suggested"`, scheduled-date label ("Hôm nay"/"Today",
     "Ngày mai"/"Tomorrow", or `dd/mm`), optional `sourceLabel` line. Buttons: **Start**
     (`task.status !== 'IN_PROGRESS'`) or **Complete** (else); always **Defer** → opens
     `DeferTaskDialog`. All disabled while `busy`.
   - If none: "Hết việc cho tuần này" / "Nothing left this week" + hint to go to Reflect.
2. Inline action-error banner on mutation failure.
3. **`WeekProgress`** 3-metric row: Week progress `{progressPct}%` (`{completed}/{total} việc`);
   Actual time = `formatMinutes(sum actualMinutes)` (sub: "ước tính {formatMinutes(totalEstimated)}");
   Deferred count (warning color if >0).
4. Two-column (`lg:grid-cols-5`, 3/2 split):
   - Left: `id="weekly-plan-section"`, "Tổng quan tuần"/"Week overview", **"Xem kế hoạch tuần"**
     button → `/student/planner`, then `DailyStudyChart`.
   - Right: `PdrStepper`; if `assignment` truthy (never happens — Gate2Context always sets it
     `null`, "no backend equivalent yet") an upcoming-deadline card.
5. `SourceDrawer` (citations) and `DeferTaskDialog`, both modal, bottom of tree.

**`PdrStepper`** — 3-step vertical timeline:
- **Plan**: no plan → "Chưa có kế hoạch"; `DRAFT` → "Kế hoạch nháp — chờ bạn xác nhận"; else "Đã
  xác nhận". `done = plan && plan.status !== 'DRAFT'`. CTA "Mở Planner" when no plan/draft.
- **Do**: `"{completed}/{total} việc hoàn thành"` + progress bar; `done` when `total>0 && completed===total`.
- **Reflect**: "Đã phản tư — kế hoạch tuần sau đã tạo" when `phase==='next-plan'`, else "Chưa phản
  tư tuần này"; CTA always "Mở Phản tư" → `/student/reflection`.
- Step matching current `phase` gets a "ĐANG Ở ĐÂY"/"YOU ARE HERE" badge.

**`DailyStudyChart`** — hand-rolled SVG line chart (no charting lib):
- `GET /student/self-study/weekly-stats` → `{dailyMinutes: [{date, minutes}]}`.
- Streak = consecutive days with `hours>0` walking backward from today; flame badge shown only if
  `streak >= 2`.
- SVG area+line, gridlines at `0, yMax/2, yMax` (`niceCeiling`: rounds to 1/2/2.5/5/10 × 10ⁿ),
  dashed average line, hover crosshair + tooltip, bigger dots for hover/today/peak-day.
- Toggle "Xem bảng"/"Xem biểu đồ" swaps to an accessible `<table>` of the same data.
- Empty: "Chưa có phiên tự học nào được ghi nhận tuần này."

**Rules**: `formatMinutes`: 0h → "{m} phút"; 0 remainder → "{h} giờ"; else "{h}h{mm}" zero-padded.

---

### 2.2 `StudentPlanner.jsx` — `/student/planner`

**Purpose**: weekly plan builder — goal + course + daily availability → AI-generated draft plan,
review/regenerate, confirm. Embeds full `Timetable` alongside the draft.

**Data**: `useGate2()` → `currentPlan, loading, error, mutating, reload, createPlan, confirmPlan`.
Own effect: `GET /student/courses` → `courses`, default `subjectCode` = `plan.subjectCode` or
first course. Prefill effect (once, keyed on `plan.id`): `goalText`/`subjectCode` from the plan,
never overwriting what the user is typing.

**UI**:
1. Header "Lập kế hoạch tuần" + "Trợ lý Cursus đề xuất, bạn sửa và xác nhận. Kế hoạch chưa xác
   nhận thì chưa có hiệu lực."
2. Goal card: text input (max 500 chars, `#plan-goal`), course `<select>` (`#plan-subject`,
   options `"{code} — {name}"`).
3. Availability card: 7 numeric inputs (Mon–Sun minutes, min0/max720/step15), default
   `[60,0,120,0,60,180,60]`. `ProvenanceBadge sourceType="user_entered"`. Preferred-session
   `<select>` (`MORNING|AFTERNOON|EVENING`, default `EVENING`). Live "Tổng rảnh" sum. Generate
   button ("Tạo kế hoạch nháp" / "Tạo lại kế hoạch" if a plan exists; "Đang tạo…" while busy),
   disabled unless `goalText.trim() && subjectCode` and not already busy.
4. Action-error banner.
5. Two-column (`lg:grid-cols-3`): left 2 cols = `<Timetable />` (no `previewPlanId`); right 1 col:
   - Generating → skeleton. No plan → empty state.
   - Plan present: header "Kế hoạch đề xuất" + task count + status badge (`DRAFT` gold "Nháp —
     chưa xác nhận" / else green "Đã xác nhận").
     - **`CapacityMeter`**: `planned = Σ task.estimatedMinutes` (client-computed — backend plan
       doesn't carry a total), `capacity = Σ declared availability`. Green/warning/danger bar; over
       capacity shows "Kế hoạch vượt quỹ thời gian {overBy}. Hãy dời hoặc bỏ bớt một việc trước khi
       xác nhận."
     - `TaskDraftRow` per task: title, `scheduledDate`, `estimatedMinutes`,
       `ProvenanceBadge sourceType="ai_suggested"`, optional deliverable badge
       (`sourceType="simulated"` — explicitly "sample data, not syllabus-sourced"), priority badge
       (HIGH = danger), italic `suggestionReason` ("Vì sao Trợ lý Cursus đề xuất: "), `sourceFact`
       line (`ProvenanceBadge sourceType="official_document"`), `sourceLabel`, `sourceRefs[]` as
       clickable `CitationChip`s → `SourceDrawer`.
     - `plan.assumptions[]` bullet list.
     - Footer: **Confirm plan** (if draft, disabled while mutating) or **"Tới Bảng điều khiển"**
       (if confirmed) → `/student`.
     - Toast after confirm: "Đã xác nhận. Bảng điều khiển đã chuyển sang bước Thực hiện."

**Actions**:
- Generate → `createPlan({goalText, subjectCode, availableHours: minutes/60,
  preferredSessions:[session], weekStart: plan?.weekStart})` → `POST /plans/generate`.
- Confirm → `confirmPlan(plan.id)` → `POST /plans/accept {plan_id}`.
- Client-side validation throws before any network call: no goal →
  `ApiError('Nhập mục tiêu tuần này để lập kế hoạch.', 'NO_GOAL', 400)`; no subject →
  `'Chưa chọn môn học để lập kế hoạch.'` / `'NO_SUBJECT'`.

---

### 2.3 `StudentReflection.jsx` — `/student/reflection`

**Purpose**: end-of-week reflection: real evidence → structured questions → AI-written memory
summary preview → confirm & save → optionally generate + apply next week's plan.

**Data**: `useGate2()` → `currentPlan, reflections, loading, mutating, submitReflection,
buildNextWeekPlan, confirmPlan`. Own `loadPreview()`:
`GET /student/reflections/preview?plan_id=...` → `{weekNumber, facts, bandLabel, questions[],
supplementaryPrompt, existing?}`. If `existing` present, restores `memory`, `supplementaryNote`,
per-question `responses`, jumps to `step='done'` if `existing.studentConfirmed`.
Error 404 → "Chưa có kế hoạch để phản tư" + retry = "Mở Planner" → `/student/planner`; other errors
→ generic + retry `loadPreview`.

**Layout**: 2 columns (`flex-[3]` main / `flex-[2]` history sidebar).

**Main column**:
1. Header "Phản tư tuần {n}" + `StepIndicator` (3 pills: `questions`("Trả lời") →
   `memory`("Xem ghi nhớ") → `done`("Áp cho tuần sau")).
2. **`EvidenceSummary`** (always visible): "Tuần vừa rồi thực tế thế nào" +
   `ProvenanceBadge sourceType="system_derived"` + `bandLabel`. 4-metric grid: Completed
   `{n}/{total}`, Deferred (warning if >0), Estimated, Actual (warning if actual>estimated). Below,
   if any `overEstimateTasks`: "{title}: {est} → {actual}" rows.
3. Action-error banner.
4. **Step `questions`**: each `preview.questions` (order:
   `['accomplishment','time_spent','went_well','went_poorly','biggest_lesson',
   'stop_start_continue','next_week_outcomes']`) via `ReflectionQuestion`:
   - `single_choice` → single-select `ChoiceChips`.
   - `grouped_multi_choice` → per-group multi-select `ChoiceChips`.
   - `insight` → read-only breakdown bar chart (`{courseCode, minutes, percent}` rows); empty
     "Chưa có dữ liệu thời gian tuần này."
   - `outcome_list` → up to `maxItems` numbered text inputs (max 200 chars,
     "VD: Hoàn thành đồ án phần 1").
   - `text`/`allowNote` → textarea.
   Plus a supplementary free-text textarea (server-provided prompt). Footer: **"Xem trước bản ghi
   nhớ"** → `goToMemory()`.
5. **Step `memory`**: editable textarea (max 4000 chars); checkbox **"Chia sẻ bản tóm tắt này với
   cố vấn"** bound to `shareWithAdvisor` (**default false**, explicit copy: "Mặc định KHÔNG chia sẻ
   — giảng viên chỉ thấy chỉ số hành vi học tập."). **Back** / **"Xác nhận & dùng cho tuần sau"**
   (disabled if empty/mutating) → `confirm()`.
6. **Step `done`**: green success card with saved memory text. No draft yet → **"Sửa lại phản
   tư"** + **"Tạo bản nháp lịch tuần sau"** (`generateDraft()`). Draft exists, not applied →
   **`NextWeekDraft`**: `<Timetable initialView="week" initialAnchor={draft.weekStart}
   previewPlanId={draft.id} />` + **"Tạo lại bản nháp"** / **"Áp dụng cho tuần sau"**. After apply:
   "Đã áp dụng — lịch tuần sau đã được cập nhật."

**History sidebar**: `reflections[]` cards — "Tuần {n}", "Đã xác nhận" badge if confirmed,
`summary`, `adjustmentLabels[]` pills, date. Empty: "Chưa có phản tư nào được lưu."

**Actions**:
- `goToMemory()` → `POST /student/reflections/preview-summary
  {planId, answers: buildAnswerPayload(), supplementaryNote}` → sets `memory` (unless hand-edited).
- `confirm()` → `POST /student/reflections {planId, answers, supplementaryNote, summary: memory,
  studentConfirmed: true, shareWithAdvisor}` → `step='done'`.
- `generateDraft()` → `POST /plans/from-reflection {reflection_id, plan_id}` → local `draft`.
- `applyDraft()` → `POST /plans/accept {plan_id: draft.id}` → `applied=true`.
- `buildAnswerPayload()`: `{questionId, answer: response.answer||null,
  selectedCodes: response.selectedCodes||[], items: (response.items||[]).filter(non-empty trimmed)}`.

---

### 2.4 `StudentPractice.jsx` — `/student/practice`

**Purpose**: per-course, per-week MCQ + flashcard practice sets, instructor-review-gated.

**Data**: `GET /student/courses` on mount → default `courseCode` = first. `loadSet()` (re-run on
`courseCode`/`weekNumber` change): `GET /practice/sets?course_code=...&week_number=...` — 404 =
"no set yet" (silent, no error banner); other errors show. Week stepper starts at 1 (sequential,
not ISO week).

**UI**: Header + course `<select>` + week stepper (clamped `[1,10]`) + Request/Regenerate button
("Yêu cầu bộ luyện tập" / "Tạo lại bộ luyện tập", spinning `RefreshCw` while requesting). No set →
empty state with same action. Set present:
- Status badge (`STATUS_LABEL`: `PENDING_REVIEW`→"Chờ giảng viên duyệt", `PUBLISHED`→"Đã xuất
  bản", `REJECTED`→"Bị từ chối", `DRAFT`→"Bản nháp") + item count.
- **MCQ grid**: click an option → all disabled, correct = green, wrong-selected = red, explanation
  line appears (`item.explanation` or "Không có giải thích."). Per-item `sourceLabel`. **State is
  local-only — resets on reload, no submission/attempt endpoint exists.**
- **Flashcard grid**: click to flip prompt ↔ answer+explanation; "Chạm để lật thẻ".

**API**: `GET /practice/sets?course_code=X&week_number=N`;
`POST /practice/sets {course_code, week_number, language}`. Item shape: `{id, kind:'MCQ'|
'FLASHCARD', sortOrder, prompt, options:[{key|id|value, text|label}], correctKey, explanation,
sourceLabel, answer}`.

---

### 2.5 `CourseCompanionChat.jsx` (embedded only, via `CompanionChatBubble`)

**Purpose**: per-course, multi-thread companion chat over the same `/qa` pipeline used elsewhere,
persisted server-side as named threads.

**Note**: the standalone `StudentCompanionPage` export was **not routed** in `App.jsx` at
`a46db63` — only reachable embedded inside the floating bubble. Only add a dedicated route if the
rebuild wants one; as-shipped it did not have one.

**Data**: `GET /qa/conversations?subjectCode=X` → `threads`, auto-select first if none active. On
`activeId` change: `GET /qa/conversations/:id` → messages passed through
`_toThreadMessage` (`metadata: {mode: raw.mode, ...raw.metadata}`). Auto-scroll on new message.

**UI**: left thread list (+ new-thread button, per-thread delete on hover) — "Chưa có hội thoại
nào." if empty; right pane message list (user = right blue bubble, assistant = left + `ModeBadge`)
+ input form.

**`ModeBadge`** from `message.metadata.mode`: `blocked` → "Hướng dẫn học tập — không làm hộ"
(`ShieldAlert`); `out_of_scope` → "Ngoài phạm vi tài liệu môn"; `guidance` → "Gợi ý Socratic";
`grounded`/`web_search` → none.

**Actions**: New → `POST /qa/conversations {subjectCode, title:''}` → prepend + activate. Delete →
`DELETE /qa/conversations/:id`. Send → optimistic local append, then
`POST /qa {subjectCode, question, conversationId}` (60s timeout) →
`_toThreadMessage({id: data.messageId, sender:'ASSISTANT', content: data.answer, mode: data.mode,
blocked: data.blocked, citations: data.citations})`; failure restores typed text + shows error.

---

### 2.6 `CuriContextPanel.jsx` (reusable, not routed in this snapshot)

**Purpose**: embeddable single-session (non-persisted) "ask in context" panel, optionally scoped
to a task (`contextTask`). Not wired into any route at `a46db63` — presumably meant for a future
task-detail view; implement only if the rebuild has a use for it.

**Props**: `subjectCode` (default `'SSA101'`), `contextTask`, `onOpenCitation`, `lang`.

**Flow** (`send(rawQuestion)`): append user message → `scoped = contextTask ?
"[${contextTask.title}] ${question}" : question` → `POST /qa {subjectCode, question: scoped}`
(60s timeout) → append assistant message with full shape `{blocked, answer, source_label,
block_reason, mode, citations[], intent, guidance{}, alternatives[], followUpQuestions[], engine}`.
Failure → `failed:true` message + restore input.

**UI**: empty state shows 3 hardcoded SSA101 starter questions. Message rendering: `blocked` →
warning badge; `out_of_scope && !blocked` → neutral badge; answer text; **`GuardrailGuidance`**
(`concept` box, `steps[]` ordered list, `socraticQuestions[]`, `template` pre-block); `citations[]`
→ `CitationChip` row; `alternatives[]` bullets; `followUpQuestions[]` (max 3) clickable pills that
re-send. **`EngineLabel`**: `engine==='llm'` → "Trả lời bằng mô hình ngôn ngữ"; else "Trả lời tiền
định (không gọi LLM)" — **hard rule: a deterministic/templated answer must never look like a live
model wrote it.** Thumbs up/down — **local-only UI state, no backend persistence.**

---

### 2.7 `DeferTaskDialog.jsx` (reusable modal — `StudentHome`, `TodayPlanScreen`)

**Purpose**: enforce "deferring a task requires a reason."

**Props**: `task` (null = closed), `reasons[]` (from `GET /plans/defer-reasons` via context, fetched
once), `onCancel`, `onConfirm(reasonCode, note)`, `busy`, `lang`.

**UI**: focus-trapped modal (Esc closes, Tab wraps, restores focus to trigger on close).
`<fieldset>` of radio reasons (falls back to one hardcoded `{code:'underestimated_time',
label:'Ước tính thiếu thời gian'}` if `reasons` not yet loaded), optional note textarea (max 500
chars). Disclaimer: "Lý do này chỉ dùng để gợi ý điều chỉnh kế hoạch của bạn ở bước phản tư. Giảng
viên không xem nội dung ghi chú." Confirm disabled until a reason is chosen or while `busy`.

**Hard constraint (both client and server)**: server independently rejects a reason-less defer.

---

### 2.8 `LecturePlanPanel.jsx` — `/student/lecture-plan`

**Purpose**: a **second, independent** weekly-plan generator built from the student's real
timetable (class + exam sessions), not from a Gate2 goal. Never wired into Gate2Context/
StudentHome — reachable only via its own route + a link from `SemesterSetupWizard`'s post-save
banner.

**Data**: `GET /student/lecture-plan` on mount (404 = "no plan yet", not an error).

**UI**: header + "Sửa học kỳ" link → `/student/semester-setup`. Numeric "available hours this
week" input (0–80, step 0.5, default 6) + **"Tạo kế hoạch tuần này"** button (spinner while
generating). Plan display: goal text, week number/start, task list (title, scheduledDate,
estimatedMinutes, priority badge). Empty states for "no plan" and "no tasks."

**API**: `POST /student/lecture-plan/generate {week_start, available_hours, language}`;
`GET /student/lecture-plan?week_number=N`; `GET /student/lecture-plan/:id`.

---

### 2.9 `SelfStudyReminder.jsx` (invisible, mounted globally for students)

**Purpose**: background poller that fires a browser `Notification` the instant a self-study
block's 10-minute pre-window opens.

**Mechanics**: `GET /student/self-study/upcoming` every 60s (+ once on mount). No-ops entirely if
notification permission ≠ granted. For each `item.canStart === true` not already notified this
session (`Set` keyed by `blockId`): `notify('Sắp đến giờ tự học', {body: "{title} · bắt đầu lúc
{HH:mm}", tag: "self-study-{blockId}"})`; click focuses the window. Renders nothing. The 10-min
lead time is a **backend** concept (`REMINDER_LEAD`) — this component only reflects
`item.canStart`, never computes timing itself.

---

### 2.10 `SelfStudySession.jsx` — `/student/self-study/:blockId`

**Purpose**: full Pomodoro-timer runner for one scheduled self-study block. **Server is
authoritative on the clock/phase** — this screen only ticks a cosmetic display countdown between
resyncs.

**Entry**: from the Timetable block-edit modal's "Bắt đầu tự học (Pomodoro)" button (only shown
editing an existing, non-locked block).

**Flow**:
1. Mount → `POST /student/self-study/sessions {blockId}`.
   - **409** (already a finished session) → `GET /student/self-study/upcoming`, find matching
     block; if it has a `sessionId` fetch it for recap, else `notFinishedInfo={kind:'finished'}` —
     "Buổi tự học này đã kết thúc trước đó."
   - **400** (window not open) → `notFinishedInfo={kind:'window', message}` — "Chưa tới giờ tự
     học." + "Có thể bắt đầu sớm nhất 10 phút trước giờ hẹn."
   - Other → generic error + "Về Thời khoá biểu" button.
2. While `IN_PROGRESS`: resync every 10s via `GET .../sessions/:id`; separate 1s local interval
   decrements the display countdown (never authoritative, corrected every resync).
3. Phase-transition detection plays a chime (`playPomodoroChime`): `'complete'` (two-tone
   ascending) on `COMPLETED`, `'break'` (440Hz) entering break/long_break, `'work'` (659.25Hz)
   otherwise — **plays regardless of notification permission** (Web Audio, no permission needed).
   If permission granted, also fires a silent notification "Đổi giai đoạn tự học."

**UI**: back link; title; if permission `default` and non-terminal, inline "Bật nhắc lịch tự học"
button. Circular timer (Flame=work, Coffee=break; accent/gold/success colors); mono clock
`mm:ss`; phase label (`work`→"Tập trung", `break`→"Nghỉ ngắn", `long_break`→"Nghỉ dài",
`done`→"Đã hoàn thành"); pomodoro counter (🍅) + remaining time. Terminal → recap card
("Hoàn thành buổi tự học!" / "Đã kết thúc sớm.") + actualMinutes/pomodoro count + "Về Bảng điều
khiển" → `/student`. Else: **"Kết thúc sớm"** → `POST .../sessions/:id/abandon`.

**Session shape** (shared by start/get/abandon): `{id, status:'IN_PROGRESS'|'COMPLETED'|
'ABANDONED', phase:'work'|'break'|'long_break'|'done', phaseRemainingSeconds,
sessionRemainingSeconds, title, pomodorosCompleted, actualMinutes}`.

---

### 2.11 `SemesterSetupWizard.jsx` — `/student/semester-setup` (also embedded as onboarding step 2)

**Purpose**: 3-step wizard — pick courses, paint them onto a weekly time-slot grid, declare
holiday/exam-week exceptions. **Additive/optional** for the Gate2 demo flow, but **mandatory** in
new-user onboarding (see §2.13).

**Props**: `onSaved` callback (OnboardingScreen uses it to advance).

**Data** (parallel on mount): `GET /student/semesters/catalog` → `{courses:[{id,code,name}]}`;
`GET /student/semesters/status`; `GET /student/semesters` → `{active_id,...}`. If an active
semester id is found, `GET /student/semesters/:id` hydrates the form: `name, start_date, end_date,
course_ids[]`, `weekly_slots[]` → `slots` map keyed `"{weekday}:{slot_id}" → course_id`,
`exceptions[]`.

**UI, 3 tabs**:
1. **"Môn học & thời gian"**: name input, start/end date pickers, searchable course grid
   (checkbox-select, max 8) — deselecting a course purges its painted grid cells and clears the
   active brush if it was selected.
2. **"Lịch tuần"**: paint-brush UI — click a selected course chip to make it the active brush,
   click grid cells to toggle-assign it. 6 fixed slots × Mon–Fri (see §6 `CLASS_SLOT_TIMES`).
   Cells with no brush and no existing assignment are disabled.
3. **"Ngày nghỉ"**: add/remove/edit `{kind:'HOLIDAY'|'EXAM_WEEK', start_date, end_date, label}` rows.

**Submit**: builds `weeklySlots` from the `slots` map (`{weekday, slot_id, course_id}`); calls
create or update depending on whether a semester already exists, disabled unless 1–8 courses +
name + both dates set. Success → green "Đã lưu học kỳ." banner + link to `/student/lecture-plan`
("Tạo kế hoạch tuần này") + `onSaved?.(result)`.

**API**: `POST /student/semesters {name, startDate, endDate, courseIds, weeklySlots, exceptions}`;
`PATCH /student/semesters/:id` (same body); `GET /student/semesters/:id`.

---

### 2.12 `Timetable.jsx` (reusable — embedded in Planner, TodayPlanScreen, Reflection's NextWeekDraft)

**Purpose**: Day/Week/Month timetable combining LOCKED real class/exam blocks with the student's
own draggable/resizable self-study blocks, with weekly recurrence.

**Props**: `initialView` (`'day'|'week'|'month'`, default `'week'`), `initialAnchor` (default
today), `previewPlanId` (reveal one specific DRAFT plan's blocks without accepting it — used by
Reflection's next-week preview).

**Data**: Day/Week → `GET /plans/timetable?week_start=YYYY-MM-DD[&preview_plan_id=...]`. Month →
6 parallel week-fetches covering the visible grid, each `.catch(() => null)`-tolerant. Response:
`{isEmpty, blocks:[{id, title, start, end (naive LOCAL iso — NOT UTC), kind, locked, courseCode,
description, recurrenceSeriesId, isDraft}]}`. **Critical**: parse these times as local wall-clock
via regex, never `new Date(isoString)` directly (would misinterpret as UTC).

**UI**: header (title, view segmented control, prev/next, range label, "Hôm nay" jump,
**"Thêm tự học"** button opening the create modal at 19:00 on the first visible day). Empty
day/week → "Chưa có lịch nào trong tuần này." + **"Tải lịch mẫu"** →
`POST /plans/timetable/bootstrap?week_start=...`.
- **Month**: 6×7 grid, up to 3 truncated chips/cell + "+{n} khác" overflow; click → jump to Day.
- **Day/Week**: hour grid 06:00–22:00 at 48px/hour, 15-min snap. Empty cells open create modal.
  `blockTone`: `EXAM_*` → danger red, not interactive; `CLASS`/`CLASS_ACTIVITY`/`locked` → accent
  blue, not interactive; else (self-study) → success green, draggable. `isDraft` → dashed border +
  reduced opacity. `Repeat` icon if part of a series; "Nháp" badge if draft.
- **Drag/resize** (unlocked blocks only): body drag = move; top/bottom 1.5px edge = resize.
  Live local preview during drag; near-edge auto-page ±7 days after 450ms in week view. Drop on a
  recurring block → scope prompt ("Chỉ mục này" / "Toàn bộ chuỗi") before saving; one-off block →
  direct `PATCH .../blocks/:id {start, end, recurrenceScope:'this'}`. A click with no movement
  opens the edit modal instead.
- **Create/edit modal**: title, start/end `datetime-local`; create-only optional "Lặp lại mỗi tuần
  đến" date. Edit mode: prominent "Bắt đầu tự học (Pomodoro)" button → `/student/self-study/:id`.
  Delete (edit only) — recurring routes through scope prompt; one-off uses native `confirm()` then
  `DELETE .../blocks/:id?scope=this`.
- **Scope prompt**: "This occurrence only" → `scope='this'`; "The whole series" → `scope='all'`;
  Cancel reloads without saving.

**API**: `GET /plans/timetable?week_start=...&preview_plan_id=...`;
`POST /plans/timetable/bootstrap?week_start=...`;
`POST /plans/timetable/blocks {title, start, end, repeatWeeklyUntil?}` (naive local ISO);
`PATCH /plans/timetable/blocks/:id {title?, start?, end?, recurrenceScope}`;
`DELETE /plans/timetable/blocks/:id?scope=all` (querystring omitted when `scope==='this'`).

---

### 2.13 `TodayPlanScreen.jsx` — `/student/today`

**Purpose**: day-focused counterpart to Home/Planner — hour-by-hour day calendar + today's task
checklist, same start/complete/defer actions.

**Data**: `useGate2()` → `tasks, deferReasons, loading, mutating, startTask, completeTask,
deferTask`; filters `tasks` client-side via `isToday(task.scheduledDate)`.

**UI**: header "Kế hoạch hôm nay". Two-column (`lg:grid-cols-5`): left 3 = `<Timetable
initialView="day" />`; right 2 = "Việc cần làm hôm nay" list of `TodayTaskRow`: title
(strikethrough+dim if COMPLETED), status badge once done/deferred, estimated-minutes +
`ProvenanceBadge`, optional source label, Start/Complete/Defer buttons (shown only while open).
Empty: "Không có việc nào được lên lịch cho hôm nay."

**Side effect**: on first load only (guarded by a ref), if there are open tasks scheduled today,
calls `requestCompanionReminder({tasks: openTasks.slice(0,3).map(...)})` from
`companionChatBus.js` — proactively pops the floating `CompanionChatBubble` with a "coming up
today" banner listing up to 3 **real** tasks (not scripted).

---

### 2.14 `OnboardingScreen.jsx` (`/onboarding`)

Two-step flow gating first access: step 1 = account basics (profile completion — exact fields not
in the researched file set beyond what auth needs, treat as a thin wrapper), step 2 = embeds
`SemesterSetupWizard` with `onSaved` → calls `onOnboardingComplete` (re-runs the session probe,
which then sees `onboarded: true` and redirects to `/student`). **Completing semester setup IS
completing onboarding** — there is no separate "onboarding done" flag (see §6 `onboarding_status.py`).

---

## 3. Global Frontend State

### 3.1 `Gate2Context.jsx` — the canonical Student data slice

Mounted by `AppShell` only for `role==='student'`, wrapping the whole `/student/*` subtree. Every
screen that touches plans/tasks/reflections reads/writes through this **one** provider so a task
completed on Home is the same record Planner/Reflection/Today all see.

**State** (`EMPTY_STATE`):
```js
{ student: null, course: null, assignment: null, weekNumber: null,
  currentPlan: null, nextPlan: null, reflections: [], deferReasons: [], fixtureVersion: null }
```
`assignment` and `nextPlan` are **permanently null** — no backend field maps to `assignment`, and
`nextPlan` isn't resolvable from the weekly-plan endpoint (targets a future week); Reflection
keeps its own local `draft` state instead. Preserve this as dead-but-intentional state unless the
rebuild adds real backing for it.

**`load({silent})`**: `Promise.all([GET /plans/weekly, GET /student/reflections,
GET /student/courses])` (each `.catch`-guarded), composes `{course: courses.find(c=>c.code===
plan?.subjectCode) || courses[0] || null, weekNumber: plan?.weekNumber, currentPlan: plan,
reflections}`, **merges** (not replaces) onto previous state so `deferReasons` (fetched once
separately via `GET /plans/defer-reasons`) survives every silent reload.

**`mutate(fn)`**: `mutating=true` → `fn()` → `load({silent:true})` → `mutating=false`. Every write
goes through this:
- `createPlan` → `POST /plans/generate`
- `confirmPlan(id)` → `POST /plans/accept {plan_id}`
- `startTask(id)` → `PATCH /plans/tasks/:id {status:'IN_PROGRESS'}`
- `completeTask(id, actualMinutes)` → same, `status:'COMPLETED'`
- `deferTask(id, reasonCode, reasonNote)` → same, `status:'DEFERRED'` + reason fields
- `submitReflection(payload)` → `POST /student/reflections`
- `buildNextWeekPlan(payload)` → `POST /plans/from-reflection`

**Derived (`useMemo`)**:
- `tasks = plan?.tasks ?? []`
- `completedCount` = `status==='COMPLETED'` count
- `openTasks` excludes `COMPLETED` and `DEFERRED`
- `nextBestAction` = earliest `scheduledDate` then highest priority (`HIGH=0<MEDIUM=1<LOW=2`)
  among `openTasks`, or `null`
- `confirmedReflection` = first reflection with `studentConfirmed===true`
- `phase`: `'plan'` (no plan or DRAFT) → `'do'` (confirmed, not all tasks done) → `'reflect'`
  (confirmed, all done) → `'next-plan'` (confirmed reflection exists **and** `state.nextPlan` set
  — effectively unreachable in this snapshot since `nextPlan` is always null; wire it up for real
  if the rebuild wants this phase to actually trigger)

### 3.2 `CursusContext.jsx` — root-level, all roles

Mounted at the app root (wraps `BrowserRouter`), used for role-specific dashboard data (instructor/
admin) AND shared UI chrome that appears for every role including students.

**Student-relevant behavior**: on `role==='student'` (or anonymous), `load()` explicitly **clears**
`classInfo/alerts/queue/courses/kpi` and makes **zero network calls** — this prevents leaking a
previous instructor/admin session's data across a role switch on a shared device.

**Shared chrome for students**:
- `notifications` — **client-only seed data**, 3 hardcoded Vietnamese items (deadline reminder,
  reflection reminder, system ingestion message), **no backend endpoint**. `markNotificationRead`/
  `markAllNotificationsRead` mutate the local array only. Backs `NotificationsBell` in the Topbar.
- `showMascot` (persisted to `localStorage['cursus_show_mascot']` + synced to
  `user.preferences.showMascot` via `PUT /auth/me/preferences` for non-demo users) / `toggleMascot()`.

### 3.3 `companionChatBus.js`

Trivial in-memory pub/sub, no persistence:
```js
requestCompanionReminder(payload)       // payload.tasks: [{id, title, estimatedMinutes}]
onCompanionReminderRequest(listener)    // returns unsubscribe fn
```
Lets any page (only `TodayPlanScreen` in this snapshot) ask the globally-mounted
`CompanionChatBubble` to pop open with a reminder, without prop-drilling.

### 3.4 `notifications.js`

Never-throwing wrapper: `notificationsSupported()`, `notificationPermission()` (`'unsupported'` if
API absent), `requestNotificationPermission()` (only prompts if currently `'default'`),
`notify(title, options)` (no-op unless already granted), `playPomodoroChime(kind)` — **synthesized
Web Audio tones, no audio file, no permission needed**: `'complete'` = two ascending tones
(523.25Hz→783.99Hz), `'break'` = single 440Hz, default/`'work'` = single 659.25Hz. Lazy singleton
`AudioContext`.

### 3.5 `CompanionChatBubble.jsx` — global floating widget

Mounted unconditionally for every student page: fixed bottom-right 56px toggle
(`MessageCircle`/`X`) + resizable floating panel wrapping `CourseCompanionChat` (`embedded`).
Drag-resize via top-left grip, clamped `[380,viewport-40]×[460,viewport-112]`, persisted to
`localStorage['cursus_companion_chat_size']`. Separate maximize toggle → near-fullscreen fixed
size. Lazily fetches `GET /student/courses` on first open for its own course picker (no shared
cache with other screens). Subscribes to `companionChatBus`; a reminder request force-opens the
panel with a dismissible banner above the chat.

---

## 4. Backend API Reference

All under role guard `STUDENT` (`require_roles`/equivalent) unless noted. Response envelope per
current HEAD's `api.js` conventions (`{success, data, error}` or bare JSON — match whatever the
CURRENT codebase's `request()` helper expects, not the old one).

### 4.1 `/student/*` (old `src/api/student.py`)

| Method & path | Body/Query | Notes |
|---|---|---|
| `GET /student/dashboard` | — | Legacy overview endpoint (superseded by Gate2 state in this UI, but still used for the raw `/student/dashboard` payload structure if you want it) — see §6 for the exact aggregation logic if reimplementing. |
| `GET /student/courses` | — | `SemesterService.current_courses` — courses in the ACTIVE semester only, falls back to all enrollments if none active. |
| `GET /student/courses/enrolled` | — | `SemesterService.enrolled_courses` — every real enrollment, ignoring semester scoping. Used by the companion chat course picker. |
| `GET /student/knowledge-status` | — | `{ready, readyCourses, courses:{code:'ready'}}` from current-semester course codes. |
| `GET /student/courses/{course_id}` | — | Ownership-checked; hides `student_upload` docs uploaded by other students. |
| `GET /student/courses/{course_id}/documents/{document_id}` | — | Hidden doc → 404 (not 403 — don't leak existence). |
| `POST /student/courses/{course_id}/documents` | multipart `file` + `title?` | 201. |
| `DELETE /student/courses/{course_id}/documents/{document_id}` | — | 204. |
| `GET /student/assignments/{assignment_id}` | — | Ownership-checked. |
| `GET /student/risks` | — | `compute_student_risks`. |
| `GET /student/lecture-plan` | `week_number?` | 404 if none. |
| `GET /student/lecture-plan/{plan_id}` | — | 404 if not found. |
| `POST /student/lecture-plan/generate` | `{week_start?, available_hours=6 (1-80), language="vi"}` | 400 on validation error. |
| `GET /student/reflections/preview` | `week_number?` or `plan_id?` | 404 if neither resolves a plan. |
| `POST /student/reflections/preview-summary` | `{plan_id, answers[], supplementary_note?}` | Does not persist. |
| `POST /student/reflections` | `{plan_id, answers[], supplementary_note?, summary, student_confirmed, share_with_advisor}` | 400 if `summary` blank; upserts one row per (student, week). |
| `GET /student/reflections/week-progress` | `week_number?` | Thin `_week_task_stats` wrapper. |
| `GET /student/reflections` | — | List all, week desc. |
| `POST /student/reflections/generate` | `{week_number, rating?, challenge?, plan?, adjustments?}` | Legacy path, **idempotent** (existing reflection for the week returned unchanged). |

### 4.2 `/plans/*` (old `src/api/plans.py`)

| Method & path | Body/Query | Notes |
|---|---|---|
| `GET /plans/timetable` | `week_start?, preview_plan_id?` | |
| `POST /plans/timetable/bootstrap` | `week_start?` | **204 empty if `app_env==='production'`** — hard block. |
| `POST /plans/timetable/blocks` | `{title(1-255), start, end, repeatWeeklyUntil?}` | 201; 400 on conflict/range error. |
| `PATCH /plans/timetable/blocks/{id}` | `{title?, start?, end?, recurrenceScope="this"}` | 404/400 mapped. |
| `DELETE /plans/timetable/blocks/{id}` | `scope="this"` | 204. |
| `GET /plans/defer-reasons` | — | Static list, 5 codes (see §6). |
| `GET /plans/weekly` | `week_start?, week_number?` | 404/409/400 error-mapped. |
| `POST /plans/generate` | `{goal_text(1-500), subject_code(2-32), available_hours=10(1-80), preferred_sessions=["EVENING"], week_start?, language="vi"}` | |
| `POST /plans/from-lectures` | `{week_start?, available_hours=10(1-80), language}` | |
| `POST /plans/from-reflection` | `{reflection_id?, plan_id?}` | |
| `POST /plans/accept` | `{plan_id}` | Core approval flow — see §6 `_plan_is_acceptable_this_week`. |
| `PATCH /plans/tasks/{id}` | `{status?, title?(1-255), planned_minutes?(15-480), actual_minutes?(>=0), reason_code?(<=64), reason_note?(<=500)}` | at least one field required; ownership-checked. |
| `DELETE /plans/tasks/{id}` | — | 204; ownership-checked. |

### 4.3 `/student/self-study/*` (old `src/api/self_study.py`)

Error mapping: `SelfStudyWindowError`→400 (**never 403** — 403 trips the frontend's global
auto-logout handler), `SelfStudyConflictError`→409, `LookupError`→404.

| Method & path | Body/Query |
|---|---|
| `GET /student/self-study/upcoming` | — |
| `GET /student/self-study/weekly-stats` | `week_start?` |
| `GET /student/self-study/sessions/active` | — (nullable) |
| `POST /student/self-study/sessions` | `{blockId}` |
| `GET /student/self-study/sessions/{id}` | — |
| `POST /student/self-study/sessions/{id}/abandon` | — |

### 4.4 `/student/semesters/*` (old `src/api/semester.py`)

| Method & path | Body/Query |
|---|---|
| `GET /student/semesters/catalog` | → `{courses, class_slots}` |
| `GET /student/semesters/status` | → `{required, active_semester_id, term_configured, term}` |
| `GET /student/semesters` | list + `active_id` |
| `POST /student/semesters` | `CreateSemesterRequest` (201) |
| `GET /student/semesters/{id}` | — |
| `PATCH /student/semesters/{id}` | `CreateSemesterRequest` |

`CreateSemesterRequest`: `name(1-80), start_date, end_date, course_ids(1-8), weekly_slots:
[{weekday(0-4), slot_id(1-4), course_id}], exceptions:[{kind:'HOLIDAY'|'EXAM_WEEK', start_date,
end_date, label<=120}]`. Validators: `end_date>=start_date` (both semester and each exception);
unique `course_ids`; unique `(weekday,slot_id)` per request; each slot's `course_id` must be in
`course_ids`.

### 4.5 `/student/memory/*` (old `src/api/student_memory.py`)

| Method & path | Body/Query |
|---|---|
| `GET /student/memory/consent` | → `{granted}` |
| `PUT /student/memory/consent` | `{granted}` |
| `GET /student/memory` | `subjectCode?(2-32)` → `{granted, entries}` |
| `DELETE /student/memory/{entry_id}` | — 404 if not found/not owned |
| `DELETE /student/memory` | — forget-all, → `{ok, deleted: count}` |

### 4.6 Auth subset relevant to Student (old `src/api/auth.py`)

**Do not port `/auth/register` or `/auth/google` verbatim — see §8.2.** The rest is compatible
as-is:
- `GET /auth/me` → `_serialize_user`: `{id, email, full_name, role, is_email_verified, major,
  student_code, onboarded: is_onboarded(db,user), preferences}`. **`onboarded` computed live on
  every call**, not stored.
- `PATCH /auth/me` → `{full_name(1-255), major?, student_code?}` — `model_fields_set` so omitted
  fields keep current value.
- `PUT /auth/me/preferences` → `{theme?, language?, show_mascot?}` (renamed to `showMascot` key
  before merging into `User.preferences` JSON).

### 4.7 `/qa/*` (companion chat — not deeply re-derived here)

`GET /qa/conversations?subjectCode=`, `POST /qa/conversations {subjectCode, title}`,
`GET /qa/conversations/:id`, `DELETE /qa/conversations/:id`, `POST /qa {subjectCode, question,
conversationId?}` (60s timeout). Response for `POST /qa`: `{answer, source_label|citations[0].
sourceLabel, block_reason, mode, blocked, citations[], intent, guidance{}, alternatives[],
followUpQuestions[], engine}`. This pipeline already exists on current HEAD in some form (QA
service) — verify field-name parity before assuming it matches exactly.

---

## 5. Frontend ↔ Backend Field-Name Conventions — READ THIS FIRST

**Old `develop`'s `api.js` and Pydantic schemas used a MIX of snake_case (request bodies mostly)
and camelCase (most response bodies)** — e.g. `GET /plans/timetable` returns `weekStart`/`blocks`
(camelCase) but `POST /student/semesters` sends `course_ids`/`weekly_slots` in a body that's
otherwise camelCase-keyed (`courseIds`, `weeklySlots` at the top level, with only nested exception
fields snake_cased) — the old code is **not internally consistent** either.

**Current HEAD's `instructor.py`/`_serialize_risk_row` convention is camelCase responses**
(confirmed during a live QA pass on this same codebase — see the bug-fix history in this
repository's commit log around `getInstructorAlerts`/`ClassComparisonPanel`). **Match current
HEAD's convention (camelCase JSON) for every new Student endpoint**, and update the frontend
`api.js` wrapper functions to read the fields under those exact names — do not blindly copy the
old field names into new frontend code without checking what the new backend will actually emit.
This exact category of bug (frontend reading `snake_case` from a `camelCase` response) was found
and fixed multiple times in the current Instructor pages during pre-restoration QA — don't
reintroduce it here.

---

## 6. Backend Business Logic (services) — preserve these rules exactly

### 6.1 Constants

- **Pomodoro** (`services/pomodoro.py`): work 25 min, short break 5 min, long break 15 min, long
  break every 4th work period.
- **Self-study scheduling** (`academic/study_scheduler.py`): candidate granularity 15 min, 10-min
  padding after any busy interval, 30-min minimum block, 120 min/day cap on class days, 210
  min/day cap on rest/weekend days. Placement scoring rewards landing on a real class-slot start
  (+28), rest days (+18, +8 more if 08:00–18:00), daytime on class days (+14), evening (+6),
  penalizes ≥21:00 start (−22) and load-imbalance (`−minutes/4 − blocks×12`); exam-phase tasks
  must end before their anchor (+55 minus hours-before capped at 30, +12 bonus if 12–48h before,
  −70 if placed after anchor); review-phase tasks must start after their anchor (+42 minus
  hours-after capped at 24, −35 if before anchor).
- **Class slots** (`academic/slots.py`): 4 fixed 2h20 campus slots — Slot1 07:30–09:50, Slot2
  10:00–12:20, Slot3 12:50–15:10, Slot4 15:20–17:40 (lunch 12:20–12:50). Exam slots: 6× 90-min
  slots with 10-min gaps, 07:30–17:40. Timezone: **naive Asia/Ho_Chi_Minh wall-clock everywhere,
  never a UTC offset appended** — see §8 for how this must change under multi-tenancy.
- **Self-study session window**: `REMINDER_LEAD = 10 min` before scheduled start; session
  auto-completes if still `IN_PROGRESS` past `scheduled_end_at`.
- **Weekly reflection**: completion bands `>=80` "high"/"Nhịp độ tốt", `>=30` "mid"/"Đang bắt kịp",
  else "low"/"Cần điều chỉnh". Fixed 7-question catalog per week regardless of band. One reflection
  per (student, week) — upsert by lookup, not a DB constraint.
- **Planner** (`services/planner.py`): 3–7 tasks per plan, top-5 RAG retrieval. A real LLM call
  only fires if a real API key is configured (rejects `test-key`/`changeme`/`sk-test`/
  `sk-your-key-here`/blank/`your-*`/`AQ.your*`, and is always disabled when `app_env=='test'`);
  otherwise 5 canned Vietnamese templates paired with retrieved chunks. `source_label` must be
  copied verbatim from a retrieved chunk — a fabricated one is rejected and replaced.
- **Lecture plan** (`services/lecture_plan_service.py`): max 7 tasks, 45 min/session unit, locked
  session kinds = `CLASS`, `CLASS_ACTIVITY`, `EXAM_PE`, `EXAM_FE`, `EXAM`. Exam sessions → 60-min
  "Ôn thi" task, `priority=HIGH`; non-exam → 45-min "Chuẩn bị buổi" task, `priority=MEDIUM`. If
  total exceeds `available_hours*60`, all durations scale down proportionally (15-min snap, 30-min
  floor).
- **Semester setup** (`services/semester_service.py`): `MAX_COURSES = 8`. If an active
  `AcademicTerm` exists, **its dates override the request's name/start/end** entirely; creating a
  student-facing semester with no active term is a hard `ValueError`. Exam-slot conflicts across
  the selected courses are rejected before saving.
- **Student memory**: max 2 memory updates recorded per chat turn, max 6 entries surfaced as
  context per question. Opting **out** (`granted=False`) hard-deletes every existing entry.

### 6.2 Onboarding gate

`is_onboarded(db, user)`: non-STUDENT → always `True`. STUDENT → `True` iff an active
`SemesterSetup` row exists for that student. **No separate "onboarding wizard completed" flag** —
this is the entire gate; `_serialize_user` recomputes it on every `/auth/me` call. Preserve this
exact semantic in the rebuild — do not add a stored boolean flag that could drift from reality.

### 6.3 Plan lifecycle invariants (preserve exactly — the whole Gate2 UI depends on these)

1. **Only one DRAFT plan per (student, week) survives.** Every plan-generating entry point
   (`WeeklyPlanService.generate`, `LecturePlanService.generate`, `generate_from_reflection`) first
   hard-deletes any existing DRAFT plan tree for that week (`discard_drafts_for_week`).
2. **DRAFT plans are invisible on the real timetable** except when explicitly requested via
   `preview_plan_id` — this is what lets `generate_from_reflection` pre-schedule next week without
   it leaking into the live timetable before the student accepts it.
3. **Task content edits (title/duration) are DRAFT-only**; status/actual-minutes changes work
   regardless of plan state (marking a task done/deferred works on an approved plan; retitling or
   re-durationing does not).
4. **Deferring a task requires `reason_code`** — rejected server-side with no reason, independent
   of the frontend's own disabled-button guard.
5. **`/plans/accept` week-acceptability check**: a plan may be accepted if its stored week equals
   the current week, the *next* week (lets a reflection-draft be pre-accepted before its week
   starts), or the semester's suggested week-start snapped to Monday. If `goals.scheduled` is
   already `true` (set by `generate_from_reflection` after it pre-packs the timetable), acceptance
   skips re-packing so manual student edits to the preview survive.
6. **Reflection→next-plan generation**: if the reflection's `next_week_outcomes` answers are
   non-empty, each outcome is run back through the RAG-grounded planner; otherwise every task from
   the previous plan is carried forward unchanged (error if the previous plan had none). Then, IF
   present in the reflection's `stop_start_continue` answer: `"reduce_hours"` cuts every task's
   minutes by 20% (15-min snap, 15-min floor); `"split_longest_task"` replaces the single longest
   task with two half-duration tasks. Both changes get a human-readable diff entry for the UI.
7. **Self-study block ↔ session is strictly 1:1** (DB unique constraint on `schedule_block_id`) —
   a double-click "start" race is resolved by catching the resulting `IntegrityError` and adopting
   the winning row rather than erroring.
8. **Recurring self-study blocks**: `repeatWeeklyUntil` generates one occurrence per week, each its
   own transaction — if one week's occurrence conflicts with a real class, only that occurrence is
   skipped (unless it's the *only* occurrence, i.e. non-repeating, in which case the conflict is
   fatal). Editing/deleting with `scope='all'` applies the same relative time/duration shift (or
   deletion) to every occurrence in the series, each re-validated for class conflicts individually.
9. **Mock/demo data**: `POST /plans/timetable/bootstrap` is a **hard no-op (204) in production**.
   `TimetableService.bootstrap_demo_week` itself also no-ops if the student already has an active
   real semester — demo seeding is strictly for students with zero real setup.

### 6.4 Repository-level gotchas worth preserving

- Course-list dedup must happen in **Python, not SQL `DISTINCT`**, if `Course.assessment_structure`
  (or any column) is plain JSON — Postgres has no equality operator for JSON and a real join-caused
  duplicate row will raise `UndefinedFunction` on `SELECT DISTINCT`.
- `find_similar` (student memory) is a simple whitespace/case-normalized exact-string match within
  a `(student, subject, kind)` bucket, not fuzzy matching — keep it cheap and deterministic.

---

## 7. Database Schema — target state

This section lists, per table, the **exact columns from `a46db63`** and what to do with each given
current HEAD's actual state (from the DB-schema research pass). "Restore" = create via new
migration; "add column(s)" = alter an existing current-HEAD table; "already correct" = no change
needed structurally, just re-add ORM relationships/constraints if current HEAD dropped them.

| Table | Status on current HEAD | Action |
|---|---|---|
| `users` | exists, has `organization_id` already | **Add columns**: `major`, `student_code`, `preferences` (JSON, nullable) |
| `weekly_plans` | exists, identical shape | none (already transitively org-scoped via `student_id`) |
| `daily_plans` | exists, identical | none |
| `study_tasks` | exists, missing 2 cols | **Add columns**: `defer_reason_code`, `defer_note` (both nullable String) |
| `task_dependencies` | exists, identical | none |
| `schedule_blocks` | exists, missing 1 col | **Add column**: `recurrence_series_id` (nullable String, indexed) |
| `semester_setups`/`semester_courses`/`semester_week_slots`/`semester_exceptions` | exist, same columns, but ORM classes on HEAD declare no `relationship()`/`UniqueConstraint` | **Re-add** the `relationship()`s and 3 `UniqueConstraint`s in `models.py`; verify (and if needed, migrate) whether the unique constraints still exist at the DB level |
| `academic_terms` | exists, **already has `organization_id` directly** (not transitive) | **Must pass `organization_id`** explicitly whenever `SemesterService` creates/queries a term — this is a real behavior change vs. old code |
| `course_exams`/`course_exam_sessions`/`course_exam_session_students` | exist, same columns | none |
| `class_activities` | exists, HEAD adds `opens_at`/`closes_at` (nullable) not present at a46db63 | none needed for restore — those are extra columns, safe to ignore/leave null |
| `practice_sets` | exists, HEAD drops the `UniqueConstraint` | **Re-add** `UniqueConstraint(course_code, slide_key)` if it doesn't already exist at the DB level |
| `practice_items` | exists, missing 1 col | **Add column**: `source_document_id` (nullable FK → `documents.id`, SET NULL) |
| `reminders`/`reminder_deliveries` | exist, identical | none |
| `weekly_reflections` | exists, identical | none |
| `conversations` | exists; `subject_code` loses its index on HEAD, `updated_at` is nullable on HEAD vs NOT NULL at a46db63 | **Re-add** the index on `subject_code`; decide whether to tighten `updated_at` back to NOT NULL (recommend yes, with a backfill, to match old guarantees) |
| `messages` | exists, identical | none |
| **`self_study_sessions`** | **does not exist on HEAD** | **Restore via new migration** — full table, unique constraint on `schedule_block_id`, FK `student_id`→`users.id` CASCADE (transitively org-scoped) |
| **`student_memory_consent`** | **does not exist** | **Restore** — PK is the FK to `users.id` |
| **`student_memory_entries`** | **does not exist** | **Restore** — FK `student_id`→`users.id`, `source_conversation_id`→`conversations.id` SET NULL |
| **`message_feedback`** | **does not exist** | **Restore** — unique `(message_id, student_id)` |
| **`llm_quota_usage`** | **does not exist** | **Restore** — unique `(student_id, usage_date)` |

**Every "restore" table above is transitively org-scoped through `student_id → users.organization_id`**
— none of them need their own `organization_id` column, matching the existing pattern already
documented on current HEAD for `weekly_plans`/`study_tasks` ("Tenant scoping is transitive via
student_id -> User.organization_id"). The only table in this whole feature set that needs a direct
`organization_id` column is `academic_terms`, and it already has one.

See §7.1 in `a24551b892f8399ec`'s original data-dictionary output (superseded by the summary table
above) for the full column-by-column definitions of every restored table if you need exact types —
they are reproduced in full below for convenience:

**`self_study_sessions`**: `id PK`, `student_id FK users.id CASCADE, indexed`, `schedule_block_id
FK schedule_blocks.id CASCADE, UNIQUE`, `title String`, `planned_minutes Integer`, `started_at
DateTime`, `scheduled_end_at DateTime`, `ended_at DateTime NULL`, `actual_minutes Integer NULL`,
`pomodoros_completed Integer default 0`, `status String` (`IN_PROGRESS|COMPLETED|ABANDONED`).

**`student_memory_consent`**: `student_id String PK, FK users.id CASCADE`, `granted Boolean
default False`, `updated_at DateTime`.

**`student_memory_entries`**: `id PK`, `student_id FK users.id CASCADE, indexed`, `subject_code
String NULL, indexed`, `kind String` (`preference|weak_topic|strength_topic`), `content String`,
`source_conversation_id FK conversations.id SET NULL, NULL`, `reinforce_count Integer default 1`,
`created_at DateTime`, `last_reinforced_at DateTime`.

**`message_feedback`**: `id PK`, `message_id FK messages.id CASCADE, indexed`, `student_id FK
users.id CASCADE, indexed`, `rating String` (`"up"|"down"`), `reason String NULL`, `created_at`,
`updated_at`, `UNIQUE(message_id, student_id)`.

**`llm_quota_usage`**: `id PK`, `student_id FK users.id CASCADE, indexed`, `usage_date Date,
indexed`, `count Integer default 0`, `updated_at`, `UNIQUE(student_id, usage_date)`. Comment from
old code: daily quota is a Settings value, 5/day was an explicit product decision — exceeding it
degrades to extractive answers, never a hard block. **Re-confirm this number with the current
product owner before hardcoding it** — it was a decision baked into the old code, not a technical
default.

---

## 8. Adaptation for multi-tenancy — decisions made (and one left open)

### 8.1 Organization scoping — resolved

Every restored table reaches `organization_id` transitively through `student_id → users.
organization_id`, exactly like current HEAD already does for `weekly_plans`/`study_tasks`. **No
new direct `organization_id` columns are needed** except that `academic_terms` (which the restored
`SemesterService` reads/writes) already carries one on current HEAD — every service call that
touches `AcademicTerm` must filter/set it explicitly. All list/query methods in the restored
services (`SemesterService`, `TimetableService`, `SelfStudyService`, `WeeklyPlanService`,
`LecturePlanService`, `StudentMemoryService`) must scope every query by the current user's
`organization_id` wherever they touch a shared/root table (`courses`, `academic_terms`) — the
student-owned tables are already implicitly scoped by filtering on `student_id=current_user.id`.

### 8.2 Public registration vs. invite-only — **RESOLVED: drop old `/auth/register`/`/auth/google`, keep invite-only**

Old `develop`'s `/auth/register` and `/auth/google` (new-account branch) let **anyone** create a
STUDENT account and immediately auto-provisioned them a fake demo semester
(`StudentMockDataService`). Current HEAD's architecture is explicitly invite-only (ADR-007) — an
Admin invites a student by email, the student activates via `/accept-invite?token=`.

**Decision (confirmed with product owner): do not port these two endpoints.** Do not add a
public `/auth/register` or reinstate the `/auth/google` new-account branch. A newly-invited
student's onboarding starts at `/accept-invite` (already implemented on current HEAD), then falls
straight into `/onboarding` (the restored `SemesterSetupWizard` step) since `is_onboarded()`
correctly reports `false` for a student with no `SemesterSetup` yet — no code change needed there,
it just works once §7's tables exist.

`StudentMockDataService`'s auto-seeding logic (4 hardcoded FPT courses etc.) is **not** wired to
any account-creation hook in the restore — current HEAD already has an equivalent, more
deliberate mechanism (`/demo/select-role` + `provision_organization.py ... sandbox`). Do not port
`StudentMockDataService` unless a real gap is found later; treat it as superseded.

### 8.3 Timezone — resolved, but changed behavior

Old code hardcoded `Asia/Ho_Chi_Minh` naive wall-clock time everywhere (`campus_now()`,
`wall_clock_iso`). Current HEAD is multi-tenant (multiple organizations, potentially multiple
campuses/timezones down the line) — **for this restore, keep the same hardcoded
`Asia/Ho_Chi_Minh` behavior** (matches the single-country deployment this product actually has
today) rather than building a per-organization timezone system nobody asked for. Flag this as a
known limitation in code comments exactly like the old code did, so it's easy to find if a future
org needs a different timezone.

### 8.4 Mock/demo data provisioning

`StudentMockDataService` (4 hardcoded FPT courses, 8 demo assignments, deterministic per-student
rest day/section ids) is **useful to keep** as a way to give a freshly-onboarded student without a
real semester something to look at, but every id/name it generates must be scoped inside the
student's own `organization_id` (e.g. course codes it creates should probably be namespaced or
reuse the org's already-seeded catalog rather than inventing a global 4-course catalog shared
across every organization). Decide at implementation time whether this mock layer is even still
wanted given current HEAD already has a separate, more deliberate sandbox/demo-org mechanism
(`/demo/select-role`, `provision_organization.py ... sandbox`) — **it may be entirely redundant
with capability current HEAD already has**, in which case skip porting it and just seed real
courses via the existing sandbox org tooling instead.

---

## 9. Implementation order (suggested)

1. **Migrations**: the 5 new tables + column additions in §7, scoped correctly (transitively via
   `student_id`), plus the `academic_terms.organization_id` wiring into `SemesterService`.
2. **Backend services**, in dependency order: `onboarding_status.py` → `semester_service.py` →
   `timetable_service.py` → `weekly_plan_service.py` → `lecture_plan_service.py` →
   `self_study_service.py` → `student_memory_service.py`. Port the supporting pure-logic modules
   verbatim first (`academic/slots.py`, `academic/study_scheduler.py`, `services/pomodoro.py`,
   `services/planner.py`, `services/reflection.py`) since everything else depends on their
   constants/algorithms.
3. **Backend API routers**: `plans.py`, `self_study.py`, `semester.py`, `student_memory.py`,
   student-relevant additions to `student.py`. Resolve §8.2 before touching `auth.py`.
4. **Frontend**: `Gate2Context.jsx` first (everything else depends on it), then `Timetable.jsx`
   (embedded everywhere), then the screens in roughly the order a new user encounters them:
   `SemesterSetupWizard` → `StudentHome` → `StudentPlanner` → `TodayPlanScreen` →
   `StudentReflection` → `SelfStudySession`/`SelfStudyReminder` → `StudentPractice` →
   `LecturePlanPanel` → `CompanionChatBubble`/`CourseCompanionChat`/`companionChatBus.js`/
   `notifications.js` → `DeferTaskDialog`.
5. Wire the route table and sidebar exactly as in §1.
6. Manual QA pass identical in spirit to the one already run on Instructor/Admin this session:
   load every screen, open the browser console, confirm zero unexpected network errors, confirm
   every field actually renders (not `undefined`) by cross-checking against this document's exact
   field names.
