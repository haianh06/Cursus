# 10 — Cursus Auth, Institutional Onboarding & Sandbox Spec

Status: **Implemented** (2026-08-12, B2B2C pivot). Supersedes the self-registration
model described in earlier drafts of `02-Cursus-SRS.md` §3.1 (see that file's
FR-1.1, now updated). This doc is the source of truth for the auth/onboarding/
sandbox product model, the research it's based on, and the screen-level specs.

## 1. Product model

Cursus is **B2B2C**: sold to a university/training center ("Phòng Đào tạo", per
`01-Cursus-PRD.md` mục 3.3, "Tổ chức (Phòng Đào tạo — người mua tiềm năng)"), not to individual end users. Two independent flows:

**A. Public product experience** — no account. Anyone (mentor, school, investor,
evaluator) picks a role at `/demo/select-role` and gets a real, short-lived session
inside an isolated sandbox organization ("Cursus Demo University") pre-seeded with
synthetic data. Institutions that want the real thing use `/request-access`
(lead-gen form, no account created).

**B. Institutional workspace** — real accounts, always organization-provisioned:
- Student: imported/synced/invited by the org (not self-serve).
- Teacher: invited by an Admin, via `POST /admin/invites`.
- Admin: provisioned when the organization is set up (`provision_organization.py`,
  Job #0 — the only account-creation path with no invite gate, because it's what
  issues the very first invite).
- Role is always read from the trusted server-side `users.role` column /
  `organization_memberships` row — never from a query string, form field, or
  localStorage.

## 2. Research: how established platforms do this

Full agent research transcripts are not persisted as files; the load-bearing
findings are captured here and in the benchmark table (§3).

**Provisioning patterns (Canvas, Moodle, Google Classroom, Schoology, Coursera for
Campus, Microsoft Education):** every platform researched treats "who exists in the
system" as an **organization-side decision** — admin console, SIS/roster sync, or
SSO-federated identity — never open self-signup for Teacher/Admin roles, and
increasingly not for Student either (Google Classroom: account is Workspace-admin-
provisioned, only *class membership* is self-service via a join code, strictly
inside an already-verified org domain). Demo/trial experiences are uniformly
isolated at the **tenant** level (Google's "test domain", Microsoft's sandbox
tenant, Canvas/Schoology separate instances) — never a flag bolted onto production
data. This directly informed the decision to make `cursus-demo` a real, separate
`organizations` row rather than a client-side mock flag.

**Auth0 Organizations/RBAC:** role is assigned per-organization-membership, not
globally on the user — the same identity could be a member of two orgs with two
different roles. Cursus's `organization_memberships` table exists for this reason
(even though today, with no org-switcher, it's 1:1 with `users`).

**Supabase Auth + RLS + custom claims:** the documented pattern is role/org living
in a server-controlled table, never in client-writable `user_metadata`, surfaced to
RLS via `auth.jwt()`/a trusted claims hook. Cursus's backend already followed the
adjacent version of this rule before this pivot (`src/security/tokens.py`
deliberately excludes role from the JWT — "authorization always re-reads the
current role from the database, so a cached role claim would be a stale-privilege
risk") — `organization_id` follows the same rule: it lives on `users`, is re-read
per request, never cached in a token claim.

**B2B SaaS demo/sandbox UX (Navattic/TestBox-class tools, general SaaS CTA
conventions):** dual-track CTA hierarchy (one dominant "try it" + one subordinate
"talk to us"/"request access"), a persistent top banner co-located with the exit
control (Ironclad/Salesforce/GitLab convention) for "you're in a demo" signaling,
and a soft (not hard-lock) session end that redirects back to a conversion prompt
rather than an error page.

## 3. Benchmark table

| Pattern source | Screen/pattern referenced | Strength | Weakness | Fit for Cursus | Adaptation (not a copy) | Source |
|---|---|---|---|---|---|---|
| Google Classroom | Workspace-provisioned identity + join-code class enrollment | Self-service *inside* a verified org boundary — convenient without opening the org itself | Requires full domain-verification/Workspace infra we don't have | High — same shape, lighter weight | Replaced "join code" with an admin-issued, single-use invite link (works without domain verification) | support.google.com/edu/setup/answer/6071551 |
| Canvas / Schoology | SIS/roster CSV import for bulk Student/Teacher creation | Scales to thousands of users without per-person emails | Needs a real SIS integration we don't have yet | Low today, roadmap-relevant | Not built this pass — invite-per-person is the MVP; CSV import is a noted fast-follow | uc.powerschool-docs.com/en/schoology/latest/schoology-sis-integrations |
| Microsoft Education / Google Classroom | Separate sandbox/test tenant for piloting | Zero risk of touching real institutional data | Requires standing up a second environment | High — directly adopted | `cursus-demo` is a real `organizations` row (`kind=sandbox`), isolated by the same org-scoping mechanism as any real tenant, not a UI-only mock | learn.microsoft.com/en-us/schooldatasync/ |
| Auth0 Organizations | Per-org role membership table | Clean multi-tenant RBAC primitive | Full implementation (org switcher, per-org billing) is much bigger than needed now | Medium — took the data shape, not the product surface | `organization_memberships` exists but no switcher UI; single membership per user today | auth0.com/blog/demystifying-multi-tenancy-in-b2b-saas/ |
| Ironclad / Salesforce / GitLab | Persistent top banner + co-located exit control for sandbox/impersonation mode | Unambiguous "you are not in production" signal, exit is always reachable | None significant | High — directly adopted | `DemoModeBanner` in `App.jsx`: role + "Cursus Demo University" label + "Thoát demo" button, sticky top strip | support.ironcladapp.com (Sandbox Mode); gitlab.com/gitlab-org/gitlab/-/issues/421029 |
| HubSpot marketing pattern | Dual-track CTA ("get a demo" **or** "start using our free tools") | Self-serve and sales-assisted visitors self-select without a forced single path | N/A | High — directly adopted | Landing page: filled "Trải nghiệm Cursus" (primary) + outline "Yêu cầu quyền truy cập cho tổ chức" (secondary), both visible in the hero | hubspot.com/products/get-started (via huble.com summary) |
| General SaaS demo-sandbox guidance (Navattic/TestBox-class) | Soft session-end → redirect to landing with a conversion prompt, not a hard-lock error | Treats the demo as a qualification instrument, not a walled trial | N/A | High — directly adopted | "Thoát demo" and the (future) TTL-expiry path both land on `/request-access`, not an error page | navattic.com/blog/what-is-a-sandbox-demo |
| shadcn/ui, Flowbite | Card-grid role picker; sticky "Banner" component | Named, well-understood component shapes to build against | Visual system doesn't match Cursus's existing Tailwind utility classes | Medium — pattern only, not the library | Built `DemoSelectRoleScreen`'s 3-card grid and `DemoModeBanner` with Cursus's existing `card`/`badge`/`btn` utility classes, not shadcn/Flowbite components | ui.shadcn.com/docs/components; flowbite.com/docs/components/banner/ |

No UI was copied pixel-for-pixel from any source above — only information
architecture, security posture, and interaction conventions.

## 4. Role-permission matrix (auth/onboarding surface only — see `security/policy.py` for the full resource×permission matrix)

| Action | Student | Instructor | Admin | Enforcement |
|---|---|---|---|---|
| Self-register (any role) | ❌ | ❌ | ❌ | Removed entirely — `AuthService.register` requires a valid invite |
| Accept an invite (`/accept-invite`) | ✅ (if invited) | ✅ (if invited) | ✅ (if invited) | `GET /auth/invites/{token}` (lookup) + `POST /auth/register` (activation, requires `invite_token`), token-scoped |
| Create an invite | ❌ | ❌ | ✅ (own org only) | `POST /admin/invites`, `require_roles(ADMIN)` + `current_user.organization_id` |
| List/revoke invites | ❌ | ❌ | ✅ (own org only) | `GET/DELETE /admin/invites/*` |
| Start a demo session | ✅ (public) | ✅ (public) | ✅ (public) | `POST /auth/demo-session`, no auth, scoped to `cursus-demo` org only |
| View access requests | ❌ | ❌ | ✅ | `GET /admin/access-requests` |
| Submit an access request | ✅ (public) | ✅ (public) | ✅ (public) | `POST /public/access-requests`, no auth |

## 5. Screen specs

### `/demo/select-role` — DemoSelectRoleScreen
- **User:** evaluator/prospect with no account.
- **Goal:** experience a real role's dashboard in under 2 clicks.
- **Primary action:** pick one of 3 role cards → `POST /auth/demo-session` → redirect.
- **Information hierarchy:** headline → 3 equal-weight role cards → small "represent
  a school?" link to `/request-access` at the bottom (secondary, de-emphasized).
- **Component pattern:** card grid (existing `card`-adjacent Tailwind classes, not a
  new component library) — mirrors the "role-based entry paths" pattern from §3.
- **States:** idle → loading (per-card spinner, other cards disabled) → error
  (inline banner with the failure message; cards re-enable so the visitor can
  retry the same card, no separate "Retry" control) → success (full-page
  redirect + reload).
- **Light/dark:** uses existing `bg-surface`/`text-fg` tokens, no new palette.
- **Responsive:** 3-column grid → 1-column stack under `md`.
- **Accessibility:** each card is a real `<button>`, loading state announced via
  visible spinner + disabled state (not a silent skeleton).
- **Source:** Google Classroom test-domain + role-based-tour pattern (§3).

### `/accept-invite?token=...` — AcceptInviteScreen
- **User:** person an admin just invited.
- **Goal:** set a password and land on their dashboard.
- **Primary action:** submit password (email/role/org are read-only, server-sourced).
- **Information hierarchy:** read-only invite summary card (email, role, org) above
  the form, so the person can verify the invite is legitimate before proceeding.
- **States:** loading (validating token) → no-token (explains the model, links to
  `/request-access`) → invalid (expired/used/revoked, links back to `/login`) →
  valid (form) → success (redirect to `/login`).
- **Light/dark/responsive/a11y:** reuses `AuthLayout` (same shared split-screen used
  by Login/Register before it), so it inherits the same theme/contrast/breakpoint
  behavior already audited there.
- **Source:** Auth0/Supabase "trusted server-issued claim" pattern (§3) — nothing on
  this screen is editable that would let a client set its own role/org.

### `/request-access` — RequestAccessScreen
- **User:** institutional buyer (admin/IT/teacher) or a demo visitor who exited.
- **Goal:** get a human at Cursus to follow up.
- **Primary action:** submit institution/contact/email/role/message.
- **States:** idle form → error (inline) → success (confirmation, no further action
  needed from the user).
- **Light/dark/responsive/a11y:** same `AuthLayout` wrapper as above.
- **Source:** HubSpot dual-track CTA pattern (§3) — this is the "talk to us" half.

### `AppShell` demo banner
- **User:** anyone inside a demo session (`user.isDemo === true`).
- **Goal:** never mistake sandbox data for real data; always find the exit.
- **Component pattern:** sticky top strip, role + org label + "Thoát demo",
  amber/warning color distinct from the app's normal chrome.
- **Gated actions in demo mode:** Settings "logout" (relabeled "Thoát demo" and
  redirects to `/request-access` instead of `/login`), AdminConsole course-delete,
  user-suspend, and invite-creation (all rendered `disabled` with a tooltip —
  explicit, not hidden, matching `UnauthorizedPage`'s existing "explicit page"
  philosophy already used elsewhere in this codebase).
- **Source:** Ironclad/Salesforce/GitLab persistent-banner convention (§3).

## 6. Explicit non-goals (this pass)
- Self-service organization creation, billing, custom domains, org switcher UI.
- CSV/SIS roster import (Student/Teacher creation is invite-per-person for now).
- Real dashboard data for demo/production alike still comes from
  `frontend/src/lib/mockApi.js` — unrelated to this pivot, tracked separately
  (`09-Cursus-Team-Assignment.md`, "Job #0").
