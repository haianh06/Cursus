# Weekly Plan UI/UX — browser test cases

**App:** http://127.0.0.1:3000  
**Account:** `student.demo@example.test` / `password123`  
**Route:** `/student/plan`  
**Scope:** F2 (FR-3.1, FR-3.2) + timetable on the same page.

Priority: **P0** must-pass · **P1** important UX · **P2** polish.

| ID | Pri | Area | Steps | Expected |
|---|---|---|---|---|
| WP-01 | P0 | Auth | Open `/`, login as student demo | Lands on student home (or redirects there). No error toast. |
| WP-02 | P0 | Nav | Click sidebar **Kế hoạch tuần** | URL `/student/plan`. H1 "Kế hoạch tuần". Nav item active. |
| WP-03 | P0 | Home CTA | From `/student`, click **Mở kế hoạch tuần** | Same as WP-02. |
| WP-04 | P0 | Page chrome | Inspect header + form | Subtitle present. **Về tổng quan** visible. Goal, course, hours, **Tạo kế hoạch**. Signed-in footer. |
| WP-05 | P0 | Empty / load | If no current plan | Task list shows empty copy. Create button **disabled** while goal empty. Course select has ≥1 enrolled subject. Hours default 1–80. |
| WP-06 | P0 | Validation | Leave goal blank; try create | Button stays disabled. No generate request. |
| WP-07 | P0 | Generate | Fill goal `Hoàn thành Project Part 1 tuần này`, pick course, hours 10, click **Tạo kế hoạch** | Loading "Đang lập kế hoạch...". Then 3–7 tasks. Status badge `DRAFT`. Accept button appears. |
| WP-08 | P0 | Task anatomy | Inspect each generated task | Title, minutes, Eisenhower badge, phase (Chuẩn bị/Học/Ôn/Khác). Source citation **or** amber "Tham khảo" warning. Edit + delete visible in DRAFT. Done toggle **disabled**. |
| WP-09 | P0 | FR-3.2 edit | Edit first task title + minutes, save | Title/minutes update. Stay DRAFT. No full-page error. |
| WP-10 | P0 | FR-3.2 delete | Delete one task | Task removed. Remaining list still valid. |
| WP-11 | P0 | Accept | Click **Xác nhận kế hoạch** | Status becomes `IN_PROGRESS` or `ACTIVE`. Edit/delete gone. Done toggle enabled. |
| WP-12 | P0 | Mark done | Toggle a task complete then undo | Check icon + strikethrough, then revert. No save error. |
| WP-13 | P0 | Persist | Reload `/student/plan` | Accepted plan + tasks still there. Goal/course hydrated. |
| WP-14 | P0 | Timetable load | Scroll to timetable | Grid T2–T7, hours 07–21. Week range shown. Prev/Next/Tuần này. |
| WP-15 | P1 | Bootstrap | If empty, click **Tải lịch demo** | Blocks appear. Class blocks look locked (indigo). Self-study emerald. |
| WP-16 | P1 | Week nav | Next week then **Tuần này** | Date range changes then returns to current week. |
| WP-17 | P1 | Create block | Click empty slot → modal → save | Modal "Tạo buổi tự học". After save, emerald block on grid. |
| WP-18 | P1 | Edit / Esc | Click self-study block, press Escape | Edit modal opens; Esc closes without save. |
| WP-19 | P1 | Class locked | Click a CLASS block | No edit modal (locked). |
| WP-20 | P1 | Back home | Click **Về tổng quan** | `/student`. Can re-enter plan from nav. |
| WP-21 | P1 | i18n EN | Switch language to EN on plan page (or profile then back) | Title "Weekly Plan", Create/Accept strings English. No leftover Vietnamese in chrome. |
| WP-22 | P1 | i18n VI | Switch back to VI | Strings restore. |
| WP-23 | P1 | Keyboard | Tab through goal → course → hours → create | Focus visible. Enter on goal submits generate only if goal+course valid. |
| WP-24 | P2 | Dark mode | Toggle dark if available | Cards/text contrast OK. No unreadable amber/red alerts. |
| WP-25 | P2 | Narrow viewport | Width ~390px | No horizontal page overflow hiding primary CTA. Timetable may scroll internally. |
| WP-26 | P1 | Warnings | After generate/accept | Warning card uses localized copy when possible (not raw JSON). Action errors are red, readable. |
| WP-27 | P2 | Overlap hint | Read timetable hint | Copy says self-study does not overlap class. |
| WP-28 | P1 | Console | DevTools console during flow | No uncaught exceptions / failed chunk loads. Failed API calls must surface in UI. |

## Out of scope this run
LLM quality of task titles, reranker scores, recurrence-series scope dialogs (unless they appear), instructor/admin roles.
