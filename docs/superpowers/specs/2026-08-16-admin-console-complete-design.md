# Admin Console Complete Design

**Date:** 2026-08-16  
**Status:** Approved in conversation; written form pending final user review  
**Primary persona:** Tenant Admin / Phòng Đào tạo (Thầy Nam)

## 1. Outcome

Admin Console becomes a seven-area operational console backed by real APIs:

1. Curriculum
2. Người dùng
3. Lời mời
4. Analytics
5. Chính sách AI
6. Audit log
7. Cấu hình

The school-wide KPI comparison remains visible above the area navigation at all times. Academic term and exam management stay available inside **Cấu hình** instead of becoming an eighth top-level area.

## 2. Product boundary

The main experience serves the school buyer and operator, not the Cursus engineering team. It answers:

- Is the curriculum ready and synchronized?
- Are invited users activated and using the system?
- Are academic outcomes and risk indicators changing?
- Which AI and risk policies are active, who changed them, and why?
- Can the school produce an auditable operational record?

Technical details such as chunk count remain available as secondary evidence, not as the page's primary language. Admin cannot read raw student reflection or chat content from this console.

## 3. Information architecture

The page has three persistent layers:

1. Header and school-wide KPI comparison with `method_note` always visible.
2. Seven-item area navigation, horizontally scrollable on narrow screens.
3. One focused area panel with loading, empty, success, and error states.

`AdminConsole.jsx` owns navigation and the persistent KPI summary. Focused components own their API state:

- `AdminCurriculum.jsx`
- `AdminUsers.jsx`
- `AdminInvitations.jsx`
- `AdminAnalytics.jsx`
- `AdminAiPolicy.jsx`
- `AdminAuditLog.jsx`
- `AdminSettings.jsx`

Existing `AdminAcademicCalendar.jsx` is composed inside `AdminSettings.jsx`.

## 4. API and data design

### 4.1 Existing capabilities reused

- Curriculum CRUD and document ingestion from `/api/v1/admin/courses`.
- KPI from `/api/v1/admin/kpi`.
- Guardrail rules from `/api/v1/admin/guardrail-rules`.
- Audit events from `/api/v1/audit/events`.
- Academic term and exams from `/api/v1/admin/academic-term`.

Frontend contract tests lock every response shape before UI integration.

### 4.2 User management

- `GET /api/v1/admin/users?role=` lists identity, role, status, creation time, and latest activity.
- `PATCH /api/v1/admin/users/{user_id}` changes `is_active`.
- Admin cannot deactivate their own account.
- Password hashes and security fields are never serialized.
- Every mutation requires both Admin role and the matching manage permission, and writes one audit event in the same transaction.

### 4.3 Invitations

The canonical route is `/api/v1/admin/invites`, matching the current SRS.

- `POST /api/v1/admin/invites` creates and sends an invitation.
- `GET /api/v1/admin/invites` lists invitations without a raw token.
- `POST /api/v1/admin/invites/{id}/revoke` revokes a pending invitation.

Create response:

```json
{
  "success": true,
  "data": {
    "invitation": {},
    "activation_token": "returned exactly once",
    "delivery_status": "sent|disabled|failed"
  }
}
```

Only the SHA-256 token hash is stored. SMTP uses the existing email abstraction. When `EMAIL_PROVIDER=none`, the UI truthfully reports delivery as disabled and offers the one-time activation link for demo use. If SMTP fails after the invitation transaction commits, the create response remains successful with `delivery_status="failed"` and returns the one-time activation link so the Admin can deliver it manually. Instructor invitations require at least one assigned class. Admin invitations are rejected.

### 4.4 Analytics

Analytics exposes:

- Current KPI comparison and mandatory `method_note`.
- Ingested/total courses.
- Total ingested documents and chunks.
- Distinct unresolved at-risk students.
- Weekly comparison series from the existing deterministic seed/source data.

No random or invented metric is permitted. Every metric includes raw counts or sample size when available and a method note describing source, denominator, time window, and simulation status.

### 4.5 AI policy governance

Guardrail toggles require `change_reason` and create an audit event. Pattern/regex content remains code-managed.

Risk policy is append-only and versioned:

- `GET /api/v1/admin/risk-policy`
- `GET /api/v1/admin/risk-policy/history`
- `POST /api/v1/admin/risk-policy/preview`
- `POST /api/v1/admin/risk-policy`
- `POST /api/v1/admin/risk-policy/{version}/rollback`

Publishing validates bounded thresholds, weights summing to `1.0`, and a non-trivial reason. Preview reports how many current students would change risk level. Rollback creates a new version copied from the selected historical version. Each new risk signal stores the `policy_version` used to calculate it so later policy changes never rewrite historical meaning. Publish and rollback both write audit events.

### 4.6 Settings

Settings persist:

- `demo_mode`
- `auto_risk_alert`
- `default_semester`

The UI explains that `auto_risk_alert` controls alert generation, not automatic messaging or intervention. Lecturer remains human-in-the-loop. Settings changes are audited atomically.

### 4.7 Curriculum synchronization

Curriculum rows show source/synchronization state and `last_synced_at` when supplied by the Mock LMS integration. Manual courses remain explicitly labeled manual. Upload uses multipart without a manually supplied `Content-Type`; polling stops after success, failure, or a fixed attempt limit.

## 5. Persistence and migrations

Three ordered revisions extend the current head:

1. Invitations.
2. Risk policy, Admin settings, and `risk_signals.policy_version`.
3. A successor hardening revision removes the legacy `policy_version="v1"` server default so databases already stamped at revision 2 also require an explicit version.

Before assigning revision IDs, the implementation must reconcile the known `20260822` collision with the pending RLS branch. Upgrade, downgrade one revision, and re-upgrade must all pass. SQLite tests and PostgreSQL-compatible column types are required.

## 6. Security and audit

- All routers enforce Admin role server-side.
- Every write route also enforces the corresponding permission.
- Public registration cannot create Instructor or Admin roles.
- User self-lock is blocked.
- Invitation tokens are single-use secrets and never returned by list APIs.
- Admin analytics is aggregated; user management exposes only the minimum identity data needed for account administration.
- Every successful Admin mutation writes one audit event in the same transaction; audit failure rolls back the mutation.

## 7. UI system

The missing `08-Cursus-UI-UX-Master-Spec.md` is recorded as a documentation gap. Until restored, implementation follows the current verified source `docs/frontend/00_AI_CONTEXT_PACK.md` and existing `frontend/src/index.css` tokens.

- React 19, JavaScript, Vite, Tailwind v4, Lucide icons.
- Reuse current colors, typography, spacing, radius, and focus treatment; no new palette.
- No edits to `index.css`, shared components, or contexts.
- All copy exists in both `vi.js` and `en.js`.
- Tables use responsive overflow; touch targets are at least 40px.
- Color is never the only status signal.
- Async regions expose accessible loading and error messages.
- No decorative animation is added.

## 8. Error handling

Each area distinguishes loading, empty, API error, validation error, and mutation-in-progress. Failed optimistic updates restore the prior state or reload from the server. Destructive actions require confirmation. Polling and async effects stop on unmount.

## 9. Test strategy

Every behavior follows RED-GREEN-REFACTOR:

- Backend contract and authorization tests first.
- Repository and migration tests for persistence/versioning.
- Audit atomicity tests for every mutation family.
- Frontend lint and production build after each UI batch.
- Browser verification for all seven areas, responsive layout, network requests, upload polling, invitation lifecycle, user lock/unlock, policy preview/publish/rollback, and settings persistence.

Baseline acceptance is `7 failed, 246 passed, 5 skipped`; no new failure is allowed. Existing Admin-focused baseline is 74 passing tests.

## 10. Definition of done

- Exactly seven top-level Admin areas are present and each consumes a real API.
- Persistent KPI and `method_note` remain visible above navigation.
- No Admin mock course or hardcoded `0.78/0.45` remains in components.
- Invitation delivery status is truthful and activation secrets are handled once.
- Risk preview, version history, rollback, alert `policy_version`, and change reasons work end-to-end.
- All Admin mutations are permission-checked and audited atomically.
- Migrations round-trip cleanly.
- Backend regression, frontend lint/build, and browser checks complete without new failures.
- Progress and project-context documentation reflect verified behavior only.
