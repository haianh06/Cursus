# Pending Decisions — needs a human call, not an AI guess

Entries here are architecture/schema forks hit while building autonomously
(mục 9 P0 backlog work, 22/08). Per the guardrail agreed for that session,
these are documented and set aside — not decided unilaterally — so the next
task proceeds instead of blocking.

---

## 0. ✅ RESOLVED — Instructor Dashboard was broken on the Supabase dev DB (500)

**Status:** Fixed. User ran `scripts/sql/fix_missing_tables_22aug.sql` on the
Supabase Dashboard (creates `risk_policies`, `mock_lms_sync_versions`,
`admin_settings`, and the missing `risk_signals.policy_version` column,
seeded with the same default policy the old hardcoded values used, so
scoring behavior didn't change). Verified after: `curl` to
`/instructor/dashboard`/`/instructor/alerts` returns 200 (was 500);
Instructor Dashboard loads correctly in-browser; Risk Policy and Mock LMS
Admin tabs both work against the real Supabase DB for the first time
(previously had to be verified on a throwaway SQLite instance). Full
writeup: `docs/archive/SESSION_REPORT_20260822.md`, "ĐỌC TRƯỚC TIÊN #1".

Was not a regression from that session's work -- confirmed pre-existing and
unrelated to any change made that session (see below).

**What was found:** during a post-build regression smoke-check (mục 9 Step
6), `GET /api/v1/instructor/dashboard` and `GET /api/v1/instructor/alerts`
both return `500 Internal Server Error` against the currently-running dev
server (browser reports it as a CORS failure, which is misleading -- the
real cause, confirmed via direct `curl` and a raw query reproduction, is:

```
psycopg2.errors.UndefinedColumn: column risk_signals.policy_version does not exist
```

This is the SAME diverged-migration-chain issue already documented at mục 9
ý 8 (`alembic current` on this branch can't locate a revision the Supabase
DB's history references) -- independently reproduced 4 times tonight
(once via the P0#6 disposable-user cleanup, once seeding Analytics demo
data, once via a direct Python repro, and now via this Instructor check).
This is the first time it's been shown to break an actual user-facing
screen rather than just a script cleanup step.

**Concrete lead for whoever has Supabase access:**
`migrations/versions/20260823_risk_policy_and_admin_settings.py` is the
migration that adds `risk_signals.policy_version`
(`down_revision = "20260822_rls_academic_terms"`). It has apparently never
been applied to the Supabase dev DB. Whether `alembic upgrade head` alone
fixes this, or whether the revision-history mismatch from mục 9 ý 8 needs
resolving first, needs checking directly against Supabase -- not something
to guess from here, and not something this session touches (standing
guardrail: no Supabase dev DB changes).

**Why this matters for tomorrow:** checked in an actual browser
(`docs/evidence/screenshots/2026-08-22_step6-regression-check/instructor-home.png`)
-- the Instructor dashboard does NOT visibly
crash; it renders normally and shows "0" for at-risk students and an
empty risk-alert list, because the frontend has a fallback for the failed
API call. That is arguably worse than a visible crash: an instructor (or
a judge) has no way to tell "0 at-risk students" apart from "the risk
query silently failed" just by looking at the screen. Every other role/
screen checked tonight (Student home, Admin -- all 6 Admin Console tabs)
worked correctly against the same DB; this is specific to whatever
queries `RiskSignal`.

---

## 1. ✅ RESOLVED — P0#8 trace wiring — `RAGTrace`/`LLMUsageEvent` don't fit `plan_builder.py`/`reflection_engine.py`

**Status:** Resolved 22/08, late that same night — user picked **Option B**
(below), with one refinement for `qa_answer_service.py`: structured logging
instead of any DB write, since that service holds no session/row of its own
(see Option B's own text below for why). `RAGTrace`/`LLMUsageEvent` are left
untouched, permanently dead schema for this purpose — this is a decided
outcome, not an oversight, so nobody should re-open "why don't we use those
tables" later without reading this entry first.

**What shipped:**
- `plan_builder.py`: `_llm_generated_tasks()` now returns `(tasks, trace)`;
  `PlanBuilder.generate()` writes `llm_attempted`/`llm_success`/
  `fallback_used`/`retrieval_empty` straight into `WeeklyPlan.goals` (the
  existing JSON column, zero migration). The Gate-2 demo path (never calls
  the LLM) gets its own honest trace — all 4 fields `False` — rather than
  being mislabeled a "fallback" alongside genuine LLM failures/declines.
- `reflection_engine.py`: same 4 fields into `WeeklyReflection.metrics`.
  Found while implementing: `save()` (the actual persist path) **never
  calls the LLM at all** — by pre-existing design (`build_summary_llm` is
  preview-only, its docstring already said saved reflections must never
  depend on an LLM call succeeding). So for every saved row,
  `llm_attempted`/`llm_success` are honestly always `False`; `fallback_used`
  reflects whether the caller supplied summary text or not. The real LLM
  trace (when `build_summary_llm` *is* called, at `/reflections/preview-
  summary`) is returned in that endpoint's own response (`trace` field, new)
  instead — not persisted, since the student can freely edit or replace
  that draft before anything is saved, so there is nothing trustworthy to
  pin to the final row.
- `qa_answer_service.py`: **no DB write** — one structured log line,
  `logger.info("qa_answer_trace subject_code=%s mode=%s llm_attempted=%s
  llm_success=%s fallback_used=%s retrieval_empty=%s", ...)`, inside
  `answer()`. This is the single entry point both callers (Companion chat
  and the standalone `GET/POST /api/v1/qa` route) already share, so one log
  statement covers both with no caller-specific branching, exactly as
  Option B's own text below anticipated as the natural resolution once "no
  DB session at all" was taken seriously.
- `retrieval_empty` only means something where a retrieval step actually
  exists (`plan_builder.py`, `qa_answer_service.py`) — `reflection_engine.py`
  performs no retrieval at all, so that field is always `False` there,
  documented in-code so it isn't misread as missing data.

**Tests:** `tests/test_services/test_plan_builder_llm.py` (updated for the
new tuple return) + `test_plan_builder_trace.py` (new — confirms the fields
land in `WeeklyPlan.goals` after `generate()`, including the Gate-2 demo
path) + `test_reflection_engine_llm.py` (updated) +
`test_reflection_engine_trace.py` (new — confirms `WeeklyReflection.metrics`)
+ `test_qa_answer_service_trace.py` (new — confirms the structured log call
via direct logger monkeypatching, not `caplog`: `configure_logging()`
replaces the root logger's entire handler list at `src.main` import time,
which silently drops caplog's own handler once any earlier test in a full
suite run has imported the app — confirmed by reproducing the difference
between a standalone run and a full-suite run before switching approach).
Full suite: **455 passed, 7 skipped, 0 failed**
(`docs/evidence/test-runs/20260822-2300-p0-8-trace-wiring.xml`).

**This now satisfies the stated precondition for P0#5** (real Gemini eval,
still gated on the user approving API budget) — a quota/API failure
(`llm_attempted=True, llm_success=False`, no other error signal) can now be
told apart from a quality problem (the model answered, but the answer isn't
good) via this trace, instead of both looking like an undifferentiated
fallback.

---

**Original entry, kept for history:**

**Status (as of 22/08, before the above):** Blocked, needs a decision. Moved
on to the next task in the work order (P0#6 minimal data-deletion) instead
of guessing.

**What was asked:** wire `llm_success`/`fallback_used`/`retrieval_empty`
trace fields into `qa_answer_service.py`, `plan_builder.py`, and
`reflection_engine.py`, reusing the existing-but-unused `RAGTrace`/
`LLMUsageEvent` tables (`src/db/models.py:582-596`) instead of building new
schema.

**What investigation found (code-verified, not guessed):**
- `RAGTrace.message_id` and `LLMUsageEvent.message_id` are both **NOT NULL**
  foreign keys to `messages.id` (`src/db/models.py:585,592` — `Mapped[str]`,
  no `nullable=True`, unlike this codebase's explicit-nullable convention
  elsewhere e.g. `:567,:605`). The real DB schema is generated straight from
  these models (`migrations/versions/20260808_baseline_schema.py:18`), so
  this is a hard constraint at the DB level too, not just the ORM's opinion.
- `Message` rows only ever get created in one place: `ConversationRepository
  .add_message()` (`src/repositories/conversation_repository.py:109`),
  called only from `CompanionService` (`src/services/ai/companion_service.py
  :91,100,138`), wired only into `src/api/companion.py`. That's the
  Companion chat feature — a different flow from the 3 services named in the
  mandate.
- `plan_builder.py` and `reflection_engine.py` have **zero** relationship to
  a `Message`/`Conversation` row anywhere in their call chains (confirmed by
  grep across both files — no `message_id`/`conversation_id`/`models.Message`
  /`models.Conversation` at all). Their object graph is entirely
  `Assignment → WeeklyPlan → DailyPlan → ScheduleBlock → StudyTask →
  ProgressEvent → WeeklyReflection` — structurally disjoint from
  Conversation/Message. There is no `message_id` to attach a trace to.
- `qa_answer_service.py` is caller-dependent: when called from
  `CompanionService` (`companion_service.py:23,46,128`), a real message
  exists one level up the stack, so wiring is possible there. When called
  from the standalone `GET/POST /api/v1/qa` route
  (`src/api/qa.py` → `src/services/ai/qa_service.py:40-50`), there is no
  Message/Conversation at all — same problem as the other two services.
- Historical context: these two tables WERE wired up once, in a since-deleted
  `backend/src/services/qa_service.py` from an earlier "unified orchestrator"
  design (visible in git history, commits `d5f0111`/`0768ee1`), removed
  during the `8b77ee3` "reorganize project structure" commit and never
  reconnected. They've been dead schema since that reorg, not a fresh design
  intended for the current 3-service split.

**Why this needs a decision, not a workaround:** every fix available
involves a schema change of some kind, which contradicts the "reuse
existing tables, no new schema" premise the task was given under — so the
premise itself needs revisiting, not a silent substitution:

- **Option A — make `message_id` nullable via migration.** Smallest schema
  touch, keeps one shared trace table. Needs a new Alembic migration
  (testable on SQLite/local Postgres per the standing guardrail; NOT applied
  to the Supabase dev DB, whose migration chain is already diverged/broken —
  mục 9 ý 8). Loses the FK's original guarantee that every trace ties back to
  a real chat message.
- **Option B — don't share tables; piggyback on each service's own JSON
  column.** `plan_builder.py` already writes free-form metadata into
  `WeeklyPlan.goals` (JSON, `src/db/models.py:469`,
  `plan_builder.py:422-441,507-509` — `planner_version`/`provenance`/
  `task_meta` already live there) and `reflection_engine.py` into
  `WeeklyReflection.metrics` (JSON, `:654`, `reflection_engine.py
  :328-342,356`) — both by design, per their own docstrings, specifically to
  avoid new columns. `llm_success`/`fallback_used`/`retrieval_empty` could
  join those existing blobs with zero migration. `qa_answer_service.py`
  itself holds no DB session at all (pure function returning
  `(answer, citations, mode)`), so this would still need a small new place
  for its own trace — either a new lightweight table, or pushed onto
  whichever caller (companion vs standalone qa.py) already has a session.
- **Option C — partial wiring.** Use `RAGTrace`/`LLMUsageEvent` only for the
  one path where a real `message_id` already exists (Companion →
  `QaAnswerService`), and leave `plan_builder.py`/`reflection_engine.py`/
  standalone `qa.py` unwired for now. Fastest, but delivers less than what
  P0#8 asked for and leaves 2 of 3 services (plus half of the third) with no
  trace at all.

No option was applied. Whoever picks one should also decide whether
`llm_success`/`fallback_used`/`retrieval_empty` need to be queryable
*across* all three services in one place (dashboard/eval use case) — that
requirement, if real, rules out Option B's per-service JSON split and points
back to A or a proper new shared table.

---

## 2. `AuditLog` has no `organization_id` — cross-tenant visible to any ADMIN

**Status: ✅ RESOLVED 22/08 (later the same night).** User explicitly chose
"Vẫn muốn thử vá org-scoping trước 23/08" over leaving it -- code + migration
+ tests are done; only the actual Supabase Dashboard SQL step is left for the
user to run themselves, same division of labor as mục 9 ý 0 above (prepared,
not self-executed, per the standing "no Supabase touches" guardrail).

**What was done:** `organization_id` added to `AuditLog`
(`src/db/models.py`), nullable, backfilled from each row's actor's *current*
org (best-effort, cannot recover the org a user belonged to at the time of a
since-changed membership). `AuditRepository.list_events()` filters by exact
match -- a NULL row (system event with no actor, or an actor who no longer
exists) is excluded for every viewer rather than shown to everyone, same
fail-closed choice already used for `update_user_status()`/`get_analytics()`.
`GET /api/v1/audit/events` (`src/api/audit.py`) now reads
`current_user.organization_id` and 404s outright if that admin has none,
instead of silently falling through to "no filter, show everything".
`AuditService.log_event()` stamps `organization_id` automatically at write
time via a new `AuditRepository.get_org_for_user()` lookup -- no caller
across the codebase needed to change (the "update every call site" cost
flagged below turned out to be avoidable).

Alembic migration: `migrations/versions/20260825_audit_log_org_scoping.py`
(column-existence-guarded the same way `20260823_...` guards
`risk_signals.policy_version`). Raw-SQL equivalent for the Supabase dev DB,
which can't run this migration directly (already-diverged `alembic_version`
chain, mục 9 ý 8): `scripts/sql/add_audit_log_org_scoping_22aug.sql` --
step-by-step Vietnamese instructions inside, not yet run by anyone.

**🔴 UPGRADED URGENCY 22/08, sau đó** — không còn chỉ là "audit log hiện sai
dữ liệu". Verify trực tiếp sau khi restart backend sạch (không phải process
cũ còn treo) cho thấy: bất kỳ lệnh nào gọi `AuditService.log_event(commit=
True)` (đăng nhập, MFA, và vài admin mutation) **crash 500 thẳng** trên DB
Supabase thật, vì cột `organization_id` chưa tồn tại — bao gồm cả
`POST /auth/login`. Đã vá phần "không được crash flow chính" (xem commit
sau item #2 này, `AuditRepository.add()` giờ nuốt lỗi ghi audit log một
cách có log lại, không raise) — nhưng đó chỉ là giảm nhẹ triệu chứng: audit
log vẫn KHÔNG được ghi cho tới khi chạy SQL. Chạy
`scripts/sql/add_audit_log_org_scoping_22aug.sql` trên Supabase Dashboard
càng sớm càng tốt — không chỉ để tab Audit Log đúng dữ liệu, mà để audit
trail không có lỗ hổng thời gian (mọi đăng nhập/hành động admin trong lúc
chưa chạy SQL sẽ không có bản ghi audit nào, dù bản thân hành động đó vẫn
thành công).

**✅ ĐÃ ĐÓNG HOÀN TOÀN 22/08, đêm muộn hơn nữa** — bạn đã tự chạy SQL trên
Supabase Dashboard. Kết quả 2 CHECK query trong chính file SQL: **420/446**
dòng audit log có `organization_id`; 26 dòng còn `NULL` đều là
`LOGIN_FAILED` với `actor_user_id` NULL (đăng nhập thất bại chưa xác định
được danh tính — đúng thiết kế, các dòng này bị loại khỏi mọi view theo
fail-closed, không phải bug); 0 tài khoản Admin thiếu tổ chức. Verify sống
sau đó: đăng nhập cả 3 role (Student/Lecturer/Admin) qua trình duyệt thật —
0 lỗi 500; tab Audit log hiện đúng dữ liệu thật, dòng đầu khớp chính xác
3 lần đăng nhập vừa test; `pytest tests/` đầy đủ: 445 passed, 7 skipped
(không đổi so với trước khi chạy SQL, như kỳ vọng — bộ test dùng SQLite
riêng, không chạm Supabase). Bằng chứng:
`docs/evidence/screenshots/2026-08-22_post-sql-fix-verification/`,
`docs/evidence/test-runs/20260822-2100-post-sql-fix-full-suite.xml`.
Không còn bước nào treo cho item #2 này.

Tests: `tests/test_api/test_audit_module.py` (own-org visible, cross-org
excluded, org-less admin 404s) + 3 pre-existing test files' shared
`admin_demo` fixture updated to have an organization (it previously had
none, which the new fail-closed check would have broken). Full suite: 415
passed, 7 skipped, 0 failed.

**Original finding (kept for history), documented as a security finding:**
`docs/evidence/security-findings/2026-08-22_audit-log-not-org-scoped.md`.
The Admin Console Audit Log UI (mục 6.5) was still built against the
existing endpoint as-is -- shipping the viewer doesn't create the exposure,
the API already had it.

**What was asked:** build a UI reading the already-existing
`GET /api/v1/audit/events`.

**What was found:** `AuditLog` (`src/db/models.py:224-239`) has no
`organization_id` column, and the route (`src/api/audit.py:26-38`) has no
way to filter by org even if it wanted to -- unlike every other `/admin/*`
endpoint in this codebase, which is always scoped to
`current_user.organization_id`. Any ADMIN, from any organization, can see
every organization's login failures, guardrail overrides, and other
audited actions.

**Why this needs a decision, not a same-night fix:** adding
`organization_id` requires a new column + migration + backfill (many
existing rows, e.g. failed logins for an email that was never a valid
account, have no obvious org to backfill to) + updating every
`audit_service.log_event(...)` call site across the codebase to pass it.
That is a schema decision, and this session's guardrail is explicit: no
new DB schema decisions without sign-off, and no touching the Supabase dev
DB (already-diverged migration chain).

**Options, not decided here:**
- **Add `organization_id` to `AuditLog`.** The complete fix, but the
  backfill question above needs an answer first (null/"unknown" bucket?
  best-effort from `actor_user_id`'s current org?).
- **Accept audit-log as intentionally platform-wide** (some
  products do treat security/audit logs as ops-team-only, cross-tenant by
  design) and restrict the route to a narrower role than plain `ADMIN`
  instead of adding org scoping at all.
- **Leave as-is for the demo, flag verbally to judges** if this comes up --
  lowest-severity option given the deadline, but leaves the gap live.

---

## 3. `model_fallbacks` (`src/config.py`) is dead config — and a pattern worth auditing before real deploy

**Status:** Not fixed, not urgent for 23/08 -- documented so it's a
deliberate deferral, not a rediscovery next time someone reads
`config.py` and wonders why a fallback list that's never used exists.

**What was found (22/08, during the P0#5 small eval batch):**
`Settings.model_fallbacks` is a comma-separated string
(`"gemini-1.5-flash,gemini-2.0-flash-lite"`) whose own inline comment
says it's "tried after MODEL_NAME on 404/429/unavailable" -- but
`get_llm()` (`src/services/core/llm.py`) never reads it. There is no
fallback-retry logic anywhere in the codebase. The setting has been
silently inert since whenever it was added.

Worth noting even though it's not being fixed now: both models it lists
are *also* not in this API key's current `client.models.list()` output --
so even wiring the field up literally as-written would not have helped
when `gemini-2.5-flash` (the primary `model_name`) went stale on 22/08
(see `eval/results/report.md`'s P0#5 section for that story). Any real
fix here needs current model names, not just "make the field do
something."

**Broader pattern, same night, third occurrence:** a hardcoded Gemini
model name has now silently gone stale and been caught **three separate
times** in this project's history:
1. `GEMINI_EMBED_MODEL` (`embedding_service.py`) -- fixed 20/08.
2. `model_name` default (`gemini-2.5-flash` -> `gemini-3.6-flash`,
   `config.py`) -- fixed 22/08, this session.
3. (Implicitly) `model_fallbacks`'s own two listed names, discovered
   stale in the same sweep above, not yet used by any code path.

Each time, the failure was silent -- every caller has its own
try/except-and-degrade-gracefully fallback, so a stale model name never
crashes the app, it just quietly stops using the LLM at all until someone
happens to check with a live API call. That's exactly the "looks fine,
isn't" class of bug this project has repeatedly flagged (PROMPT_PATH,
embedding model, this).

**Recommendation, not a decision made here:** before any real (non-demo)
deploy, do one deliberate pass across the repo for every hardcoded Gemini
model name string (`grep -rn "gemini-" src/ --include=*.py`, plus
`config.py`'s defaults), verify each one against a live
`client.models.list()` call, and decide then whether `model_fallbacks`
is worth actually wiring up (a real fallback chain has genuine value --
quota exhaustion or a mid-cycle model deprecation stops being a full
outage) or should just be removed as dead config. Not urgent for 23/08 --
the two model names actually in active use are both confirmed working as
of tonight -- but exactly the kind of thing that should not wait for a
fourth silent occurrence to be caught.

---
