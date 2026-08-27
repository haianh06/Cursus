/**
 * API client — cookie session + CSRF (no JWT in localStorage).
 * Auth cookies are HttpOnly (set by backend).
 *
 * CSRF is double-submit, but the token can't be recovered from the cookie
 * client-side in production: the frontend (vercel.app) and backend
 * (onrender.com) are different registrable domains, so the csrf_token
 * cookie — set by a response FROM the API's domain — is stored scoped to
 * that domain and is invisible to `document.cookie` running on the
 * frontend's origin, no matter what SameSite says. The backend also echoes
 * the same value in the JSON body of every session-establishing/-restoring
 * response (login, demo-session, google-login, refresh, /auth/me); we hold
 * that in memory here and attach it ourselves instead of reading the cookie.
 */

const API_BASE_URL =
  import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

const CSRF_HEADER = 'X-CSRF-Token';
const LEGACY_TOKEN_KEY = 'cursus_access_token';

// Drop any leftover XSS-exposed tokens from older builds.
try {
  localStorage.removeItem(LEGACY_TOKEN_KEY);
} catch {
  /* ignore */
}

export class ApiError extends Error {
  constructor(message, code, status) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.status = status;
  }
}

function errorMessageFromPayload(payload, status) {
  if (!payload) return `HTTP ${status}`;
  if (typeof payload.detail === 'string') return payload.detail;
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => item.msg || JSON.stringify(item)).join('; ');
  }
  if (payload.message) return payload.message;
  if (payload.error?.message) return payload.error.message;
  return `HTTP ${status}`;
}

let csrfToken = null;

/** Every auth response that (re)issues the CSRF cookie also echoes its
 * value in the body under this key — capture it whenever we see it. */
function captureCsrfToken(payload) {
  if (payload && typeof payload.csrf_token === 'string' && payload.csrf_token) {
    csrfToken = payload.csrf_token;
  }
}

function isUnsafeMethod(method) {
  return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(String(method || 'GET').toUpperCase());
}

function applyCsrfHeader(headers, method) {
  if (!isUnsafeMethod(method)) return;
  if (csrfToken) headers.set(CSRF_HEADER, csrfToken);
}

const REQUEST_TIMEOUT_MS = 15000;

async function rawFetch(path, { method = 'GET', body, headers } = {}) {
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;
  const finalHeaders = new Headers(headers || {});
  // FormData bodies must NOT get a hand-set Content-Type -- the browser
  // generates one itself with the multipart boundary, and setting our own
  // (or JSON-stringifying the FormData object, which produces "[object
  // FormData]") breaks the upload silently on the server side.
  if (body !== undefined && !isFormData && !finalHeaders.has('Content-Type')) {
    finalHeaders.set('Content-Type', 'application/json');
  }
  applyCsrfHeader(finalHeaders, method);

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: finalHeaders,
      credentials: 'include',
      body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body),
      signal: controller.signal,
    });
  } finally {
    clearTimeout(timer);
  }
}

let refreshInFlight = null;

async function refreshSession() {
  if (!refreshInFlight) {
    refreshInFlight = rawFetch('/auth/refresh', { method: 'POST', body: {} })
      .then(async (response) => {
        if (!response.ok) return false;
        captureCsrfToken(await parsePayload(response));
        return true;
      })
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}

async function parsePayload(response) {
  if (response.status === 204) return null;
  return response.json().catch(() => null);
}

/** Called on authenticated 401/403 so the app can force logout + login. */
let authFailureHandler = null;

export function setAuthFailureHandler(handler) {
  authFailureHandler = typeof handler === 'function' ? handler : null;
}

function notifyAuthFailure(status, message) {
  try {
    authFailureHandler?.({ status, message });
  } catch {
    /* ignore handler errors */
  }
}

async function request(
  path,
  { method = 'GET', body, auth = true, suppressAuthHandler = false, _retried = false } = {},
) {
  let response;
  try {
    response = await rawFetch(path, { method, body });
  } catch {
    throw new ApiError('Không kết nối được tới máy chủ.', 'NETWORK_ERROR', 0);
  }

  // Cookie access JWT expired → rotate via refresh cookie, then retry once.
  if (auth && response.status === 401 && !_retried && path !== '/auth/refresh') {
    const refreshed = await refreshSession();
    if (refreshed) {
      return request(path, { method, body, auth, suppressAuthHandler, _retried: true });
    }
  }

  const payload = await parsePayload(response);
  if (response.ok) captureCsrfToken(payload);
  if (!response.ok) {
    const message = errorMessageFromPayload(payload, response.status);
    const shouldNotify =
      auth &&
      !suppressAuthHandler &&
      (response.status === 401 || response.status === 403) &&
      path !== '/auth/login' &&
      path !== '/auth/register' &&
      path !== '/auth/refresh';
    if (shouldNotify) {
      notifyAuthFailure(response.status, message);
    }
    throw new ApiError(
      message,
      payload?.error?.code ?? `HTTP_${response.status}`,
      response.status,
    );
  }

  if (payload && typeof payload === 'object' && 'success' in payload) {
    if (!payload.success) {
      throw new ApiError(
        payload?.error?.message ?? 'Có lỗi xảy ra, vui lòng thử lại.',
        payload?.error?.code ?? 'UNKNOWN_ERROR',
        response.status,
      );
    }
    return payload.data;
  }

  return payload;
}

/** Auth — cookie session (HttpOnly). Response body token is ignored. */
export async function login({ email, password, rememberMe = false }) {
  const data = await request('/auth/login', {
    method: 'POST',
    auth: false,
    body: { email, password, remember_me: rememberMe },
  });
  // Never persist access JWT in JS storage.
  return data;
}

export async function googleLogin({ email, fullName, googleId }) {
  return request('/auth/google-login', {
    method: 'POST',
    auth: false,
    body: { email, full_name: fullName, google_id: googleId },
  });
}

export async function forgotPassword({ email }) {
  return request('/auth/password/forgot', {
    method: 'POST',
    auth: false,
    body: { email },
  });
}

export async function resetPassword({ token, newPassword }) {
  return request('/auth/password/reset', {
    method: 'POST',
    auth: false,
    body: { token, new_password: newPassword },
  });
}

export async function verifyEmail({ token }) {
  return request('/auth/email/verify', {
    method: 'POST',
    auth: false,
    body: { token },
  });
}

export async function resendEmailVerification({ email }) {
  return request('/auth/email/resend', {
    method: 'POST',
    auth: false,
    body: { email },
  });
}

export async function changeEmail({ email }) {
  return request('/auth/email/change', {
    method: 'POST',
    body: { email },
  });
}




/** Auth ΓÇö public register is STUDENT-only. Password policy: min 12. */
export async function register({ email, password, fullName, inviteToken }) {
  return request('/auth/register', {
    method: 'POST',
    auth: false,
    body: {
      email,
      password,
      full_name: fullName,
      invite_token: inviteToken,
    },
  });
}

/** Public lookup — who/what role/which org an invite link is for, before
 * the person sets a password. 404 for anything invalid/expired/used. */
export function getInviteDetails(token) {
  return request(`/auth/invites/${encodeURIComponent(token)}`, { auth: false });
}

/** No credentials — logs the visitor into one of the 3 pre-seeded demo
 * accounts inside the isolated 'Cursus Demo University' sandbox org. */
export function startDemoSession(role) {
  return request('/auth/demo-session', {
    method: 'POST',
    auth: false,
    body: { role },
  });
}

/** Public lead-gen form ("Yêu cầu quyền truy cập cho tổ chức"). Creates no
 * account and grants no access by itself. */
export function requestOrgAccess({ institutionName, contactName, email, roleInterested, message }) {
  return request('/public/access-requests', {
    method: 'POST',
    auth: false,
    body: {
      institution_name: institutionName,
      contact_name: contactName,
      email,
      role_interested: roleInterested,
      message,
    },
  });
}

/** Admin-only invite management (see AdminConsole's Invites tab). */
export function createInvite({ email, fullName, role }) {
  return request('/admin/invites', {
    method: 'POST',
    body: { email, full_name: fullName, role },
  });
}

export function getInvites() {
  return request('/admin/invites');
}

export function revokeInvite(inviteId) {
  return request(`/admin/invites/${encodeURIComponent(inviteId)}`, { method: 'DELETE' });
}

export function resendInvite(inviteId) {
  return request(`/admin/invites/${encodeURIComponent(inviteId)}/resend`, { method: 'POST' });
}

/** Admin-only org member list + lock/unlock (see AdminConsole's Users tab). */
export function getOrgUsers() {
  return request('/admin/users');
}

export function updateUserStatus(userId, isActive, reason) {
  return request(`/admin/users/${encodeURIComponent(userId)}/status`, {
    method: 'PATCH',
    body: { is_active: isActive, reason },
  });
}

/** Admin triggers the same reset-link flow the user would get themselves via
 * "Forgot password" -- never sets a password directly. Response is
 * `{success: true, emailSent: bool}` with no `data` key, so `request()`'s
 * envelope-unwrap resolves this to `undefined`; treat the call as
 * fire-and-forget (its rejection is the only thing that matters here). */
export function resetAdminUserPassword(userId) {
  return request(`/admin/users/${encodeURIComponent(userId)}/reset-password`, { method: 'POST' });
}

/** Admin-only system audit trail (see AdminConsole's Audit Log tab). Not
 * organization-scoped server-side yet -- see docs/PENDING_DECISIONS.md #2. */
export function getAuditEvents({ eventType = null, limit = 100 } = {}) {
  const params = new URLSearchParams();
  if (eventType) params.set('event_type', eventType);
  params.set('limit', String(limit));
  return request(`/audit/events?${params.toString()}`);
}

export function getMe() {
  // Bootstrap probe ΓÇö 401 means guest, not a forced logout toast.
  return request('/auth/me', { suppressAuthHandler: true });
}

export function updateProfile({ fullName, major, studentCode }) {
  return request('/auth/me', {
    method: 'PATCH',
    body: { full_name: fullName, major, student_code: studentCode },
  });
}

export function updatePreferences(patch) {
  return request('/auth/me/preferences', {
    method: 'PUT',
    body: {
      theme: patch.theme,
      language: patch.language,
      show_mascot: patch.showMascot,
    },
  });
}

export async function logout() {
  try {
    await request('/auth/logout', {
      method: 'POST',
      body: {},
      suppressAuthHandler: true,
    });
  } finally {
    csrfToken = null;
    try {
      localStorage.removeItem(LEGACY_TOKEN_KEY);
    } catch {
      /* ignore */
    }
  }
}

/** Open the exact syllabus chunk behind a citation chip (source drawer). */
export function getSourceChunk(chunkId) {
  return request(`/qa/sources/${encodeURIComponent(chunkId)}`);
}

export async function streamCursusChat({ message, conversationId, onEvent }) {
  const headers = new Headers({ 'Content-Type': 'application/json' });
  applyCsrfHeader(headers, 'POST');
  const response = await fetch(`${API_BASE_URL}/student/cursus/stream`, { method: 'POST', credentials: 'include', headers, body: JSON.stringify({ message, conversation_id: conversationId }) });
  if (!response.ok || !response.body) throw new ApiError('Không thể kết nối Cursus.', 'CHAT_ERROR', response.status);
  const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
  while (true) { const { value, done } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); const parts = buffer.split('\n\n'); buffer = parts.pop(); for (const part of parts) { const event = part.match(/^event: (.+)$/m)?.[1] || 'message'; const raw = part.match(/^data: (.+)$/m)?.[1]; if (raw) onEvent(event, JSON.parse(raw)); } }
}

export function exportCursusHistory() { return request('/student/cursus/export'); }
export function deleteCursusHistory() { return request('/student/cursus/history', { method: 'DELETE' }); }

/** Student courses (for plan context). */
export function getStudentCourses() {
  return request('/student/courses');
}

export function getStudentDashboard() {
  return request('/student/dashboard');
}

export function getStudentCourseDetail(courseId) {
  return request(`/student/courses/${encodeURIComponent(courseId)}`);
}

export function getStudentCourseDocument(courseId, documentId) {
  return request(
    `/student/courses/${encodeURIComponent(courseId)}/documents/${encodeURIComponent(documentId)}`,
  );
}

/** Monday (local) of the week containing ``date``. */
export function startOfMonday(date = new Date()) {
  const value = new Date(date);
  value.setHours(0, 0, 0, 0);
  const day = value.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  value.setDate(value.getDate() + diff);
  return value;
}

export function toDateInputValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

/**
 * Term-relative week number, mirroring `academic_week_number()` in
 * `src/services/ai/weekly_plan_engine.py`: weeks since the semester's raw
 * `start_date`, 1-indexed and floored at 1.
 */
export function academicWeekNumber(startDate, today = new Date()) {
  const start = new Date(`${startDate}T00:00:00`);
  const monday = startOfMonday(today);
  const days = Math.round((monday - start) / 86400000);
  return Math.max(1, Math.floor(days / 7) + 1);
}

/** ISO week number for the Monday-based week (aligned with backend). */
export function currentIsoWeekNumber(date = new Date()) {
  const monday = startOfMonday(date);
  const utc = new Date(Date.UTC(monday.getFullYear(), monday.getMonth(), monday.getDate()));
  const dayNum = utc.getUTCDay() || 7;
  utc.setUTCDate(utc.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(utc.getUTCFullYear(), 0, 1));
  return Math.ceil((((utc - yearStart) / 86400000) + 1) / 7);
}

/** Planner — generate a draft weekly plan from a free-text goal + course
 * (a46db63 contract). `availability` is optional; when given it defines
 * capacity precisely ([{ date: 'YYYY-MM-DD', availableMinutes: 120 }, ...]). */
export async function generatePlan({
  goalText,
  subjectCode,
  availableHours = 12,
  preferredSessions = ['EVENING'],
  availability = null,
  weekStart = null,
}) {
  if (!goalText || !goalText.trim()) {
    throw new ApiError('Nhập mục tiêu tuần này để lập kế hoạch.', 'NO_GOAL', 400);
  }
  if (!subjectCode) {
    throw new ApiError('Chưa chọn môn học để lập kế hoạch.', 'NO_SUBJECT', 400);
  }
  return request('/plans/generate', {
    method: 'POST',
    body: {
      goal_text: goalText,
      subject_code: subjectCode,
      available_hours: availableHours,
      preferred_sessions: preferredSessions.map((item) => String(item).toUpperCase()),
      availability: availability || undefined,
      week_start: weekStart || undefined,
    },
  });
}

/* ── Gate-2 canonical student state ──────────────────────────────────────
 * One read that every student screen shares, so Dashboard / Planner /
 * Reflection can never disagree about "the week".                        */

export function getDemoState() {
  return request('/student/demo/state');
}

export function getDemoSeed() {
  return request('/demo/seed');
}

export function resetDemo() {
  return request('/demo/reset', { method: 'POST', body: { confirm: true } });
}

/** Rehearsal helper: applies the scripted week outcome. Response is flagged
 * `simulated: true` and the UI must say so. */
export function fastForwardDemoWeek() {
  return request('/demo/fast-forward', { method: 'POST', body: {} });
}

export function getPlan(planId) {
  return request(`/plans/${encodeURIComponent(planId)}`);
}

export function getDeferReasons() {
  return request('/plans/defer-reasons');
}

/* ── Reflection ─────────────────────────────────────────────────────── */

export function getReflectionPreview({ weekNumber = null, planId = null, lang = 'vi' } = {}) {
  const params = new URLSearchParams();
  if (weekNumber != null) params.set('week_number', String(weekNumber));
  if (planId) params.set('plan_id', planId);
  params.set('lang', lang);
  const query = params.toString();
  return request(`/student/reflections/preview${query ? `?${query}` : ''}`);
}

/** Draft the memory text WITHOUT storing it, so the student can edit first. */
export function previewReflectionSummary({ planId, answers = [], adjustments = [], lang = 'vi' }) {
  return request('/student/reflections/preview-summary', {
    method: 'POST',
    body: { plan_id: planId, answers, adjustments, language: lang },
  });
}

export function saveReflection({
  planId,
  answers = [],
  adjustments = [],
  summary = null,
  studentConfirmed = false,
  shareWithAdvisor = false,
  lang = 'vi',
}) {
  return request('/student/reflections', {
    method: 'POST',
    body: {
      plan_id: planId,
      answers,
      adjustments,
      summary,
      student_confirmed: studentConfirmed,
      share_with_advisor: shareWithAdvisor,
      language: lang,
    },
  });
}

export function getReflections() {
  return request('/student/reflections');
}

/** mục 6.3/6.4 Cài đặt: self-service hard delete of the caller's own
 * reflections + Cursus Assistant chat history. Returns how many rows of
 * each kind were removed. */
export function deleteMyPersonalData() {
  return request('/student/personal-data/delete', { method: 'POST' });
}

/** Next week's plan, built from confirmed reflection adjustments. Returns the
 * new plan plus `previousPlan` + `reflectionChanges` for the before/after. */
export function generatePlanFromReflection({ reflectionId = null, planId = null } = {}) {
  return request('/plans/from-reflection', {
    method: 'POST',
    body: { reflection_id: reflectionId, plan_id: planId },
  });
}

export function getWeeklyPlan(weekNumber = currentIsoWeekNumber()) {
  const query = weekNumber == null ? '' : `?week_number=${encodeURIComponent(weekNumber)}`;
  return request(`/plans/weekly${query}`);
}

export function acceptPlan(planId) {
  return request('/plans/accept', {
    method: 'POST',
    body: { plan_id: planId },
  });
}

/** Start / complete / defer a task.
 * Deferring REQUIRES a `reasonCode` from GET /plans/defer-reasons — the
 * backend rejects a defer without one. */
export function updatePlanTaskStatus(
  taskId,
  status,
  actualMinutes = null,
  { reasonCode = null, reasonNote = null } = {},
) {
  return request(`/plans/tasks/${encodeURIComponent(taskId)}`, {
    method: 'PATCH',
    body: {
      status,
      actual_minutes: actualMinutes,
      reason_code: reasonCode,
      reason_note: reasonNote,
    },
  });
}

export function getTimetable(weekStart, { previewPlanId = null } = {}) {
  const monday = weekStart || toDateInputValue(startOfMonday());
  const params = new URLSearchParams({ week_start: monday });
  if (previewPlanId) params.set('preview_plan_id', previewPlanId);
  return request(`/plans/timetable?${params.toString()}`);
}

export function bootstrapTimetable(weekStart) {
  const monday = weekStart || toDateInputValue(startOfMonday());
  return request(`/plans/timetable/bootstrap?week_start=${encodeURIComponent(monday)}`, {
    method: 'POST',
    body: {},
  });
}

/** Create a self-study block. `repeatWeeklyUntil` is accepted but currently
 * ignored server-side — recurring self-study series aren't implemented yet
 * (backend only stores a single occurrence). */
export function createTimetableBlock({ title, start, end, repeatWeeklyUntil = null }) {
  return request('/plans/timetable/blocks', {
    method: 'POST',
    body: { title, start, end, repeatWeeklyUntil },
  });
}

/** `recurrenceScope` is accepted but currently ignored server-side (same
 * caveat as createTimetableBlock) — every edit only ever affects this one
 * occurrence. */
export function updateTimetableBlock(blockId, { title, start, end, recurrenceScope = 'this' } = {}) {
  return request(`/plans/timetable/blocks/${encodeURIComponent(blockId)}`, {
    method: 'PATCH',
    body: { title, start, end, recurrenceScope },
  });
}

/** `scope` is accepted but currently ignored server-side (same caveat as
 * createTimetableBlock) — always deletes just this one occurrence. */
export function deleteTimetableBlock(blockId, scope = 'this') {
  const query = scope && scope !== 'this' ? `?scope=${encodeURIComponent(scope)}` : '';
  return request(`/plans/timetable/blocks/${encodeURIComponent(blockId)}${query}`, {
    method: 'DELETE',
  });
}

/* ── Self-study Pomodoro ──────────────────────────────────────────────── */

/** Self-study blocks whose 10-minute reminder window is currently open. */
export function getUpcomingSelfStudy() {
  return request('/student/self-study/upcoming');
}

export function getSelfStudyWeeklyStats(weekStart) {
  const query = weekStart ? `?week_start=${encodeURIComponent(weekStart)}` : '';
  return request(`/student/self-study/weekly-stats${query}`);
}

export function startSelfStudySession(blockId) {
  return request('/student/self-study/sessions', { method: 'POST', body: { blockId } });
}

export function getSelfStudySession(sessionId) {
  return request(`/student/self-study/sessions/${encodeURIComponent(sessionId)}`);
}

export function abandonSelfStudySession(sessionId) {
  return request(`/student/self-study/sessions/${encodeURIComponent(sessionId)}/abandon`, {
    method: 'POST',
    body: {},
  });
}

/* ── Lecturer HITL ──────────────────────────────────────────────────── */

/** Class overview: roster, completion, open/handled alert counts. */
export function getInstructorDashboard(courseId = null) {
  const query = courseId && courseId !== 'ALL' ? `?course_id=${encodeURIComponent(courseId)}` : '';
  return request(`/instructor/dashboard${query}`);
}

/** Priority queue, already sorted by severity × time-open. */
export function getInstructorAlerts(courseId = null) {
  // /instructor/alerts was retired; GET /instructor/risks is its
  // replacement (bare array, camelCase fields -- see _serialize_risk_row
  // in src/api/instructor.py).
  const query = courseId && courseId !== 'ALL' ? `?course_id=${encodeURIComponent(courseId)}` : '';
  return request(`/instructor/risks${query}`);
}

/** Alert detail: behavioural evidence + timeline + intervention log.
 * Never contains raw chat/reflection text. */
export function getAlertDetail(alertId) {
  return request(`/instructor/risks/${encodeURIComponent(alertId)}`);
}

export function getInterventionAudit(limit = 50) {
  return request(`/instructor/audit?limit=${encodeURIComponent(limit)}`);
}

/** Blocked Q&A cases awaiting (or already given) an instructor decision —
 * this is the "guardrail appeal queue" InstructorHome renders. */
export function getGuardrailReviewQueue() {
  return request('/instructor/guardrail-reviews');
}

/** `decision` is 'KEEP' (stay blocked) or 'UNBLOCK' (approve the answer). */
export function resolveGuardrailReview(caseId, decision) {
  return request(`/instructor/guardrail-reviews/${encodeURIComponent(caseId)}`, {
    method: 'POST',
    body: { decision },
  });
}

/* ── Admin console ─────────────────────────────────────────────────── */

/** Curriculum list — visible (non-hidden) courses with ingest status. */
export function getAdminCourses() {
  return request('/admin/courses');
}

export function addAdminCourse({ subjectCode, subjectName, semester }) {
  return request('/admin/courses', {
    method: 'POST',
    body: { subject_code: subjectCode, subject_name: subjectName, semester },
  });
}

/** "Delete" hides the course from the visible list (soft delete). */
export function deleteAdminCourse(code) {
  return request(`/admin/courses/${encodeURIComponent(code)}`, { method: 'DELETE' });
}

export function getAdminCourseDocuments(courseCode) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents`);
}

export function getAdminCourseDocumentContent(courseCode, documentId) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}/content`);
}

export function uploadAdminCourseDocument(courseCode, file, docType = 'SYLLABUS') {
  const form = new FormData();
  form.append('file', file);
  form.append('doc_type', docType);
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents`, {
    method: 'POST',
    body: form,
  });
}

export function replaceAdminCourseDocument(courseCode, documentId, file) {
  const form = new FormData();
  form.append('file', file);
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}`, {
    method: 'PUT',
    body: form,
  });
}

export function deleteAdminCourseDocument(courseCode, documentId) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}`, {
    method: 'DELETE',
  });
}

export function validateAdminCourseDocument(courseCode, documentId) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}/validate`, {
    method: 'POST'
  });
}

export function publishAdminCourseDocument(courseCode, documentId, changeReason) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}/publish`, {
    method: 'POST',
    body: { change_reason: changeReason }
  });
}

export function archiveAdminCourseDocument(courseCode, documentId, changeReason) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}/archive`, {
    method: 'POST',
    body: { change_reason: changeReason }
  });
}

export function getAdminCourseDocumentVersions(courseCode, documentId) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}/versions`);
}

export function rollbackAdminCourseDocument(courseCode, documentId, changeReason) {
  return request(`/admin/courses/${encodeURIComponent(courseCode)}/documents/${encodeURIComponent(documentId)}/rollback`, {
    method: 'POST',
    body: { change_reason: changeReason }
  });
}

/** CLO list + session-by-session breakdown + syllabus metadata, read from
 * the course's own parsed chunk file. 404s (via request()'s ApiError) for a
 * course with no real syllabus behind it (e.g. added manually). */
export function getAdminCourseCurriculum(code) {
  return request(`/admin/courses/${encodeURIComponent(code)}/curriculum`);
}

export function getAdminKpi() {
  return request('/admin/kpi');
}

/** Measured Admin summary contract. KPI snapshot cards are intentionally not
 * part of this dashboard; they were illustrative rather than live metrics. */
export function getAdminAnalyticsSummary() {
  return request('/admin/analytics/summary');
}

/** Legacy endpoint kept for compatibility with older consumers. */
export function getAdminAnalytics() {
  return request('/admin/analytics');
}

/* ── Admin: Overview dashboard (ported from `chung` — docs/branch-audit/chung-admin-frontend.md §2.1) ── */

export function getAdminOverview() {
  return request('/admin/overview');
}

export function getAdminWorkQueue() {
  return request('/admin/work-queue');
}

/** `params`: `{ search, role, page }` — all optional. */
export function listAdminPeople(params = {}) {
  const query = new URLSearchParams();
  if (params.search) query.set('search', params.search);
  if (params.role) query.set('role', params.role);
  if (params.page) query.set('page', String(params.page));
  const qs = query.toString();
  return request(`/admin/people${qs ? `?${qs}` : ''}`);
}

/* ── Admin: Student 360 (docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.3) ──
   Every raw-data call below is audited server-side before the response is
   released (fail-closed) — see src/api/admin_student360.py. */

export function getAdminStudentSummary(studentId) {
  return request(`/admin/students/${encodeURIComponent(studentId)}/summary`);
}

/** `resourcePath` is one of: plans, tasks, progress-events, reminders, sessions,
 * assignments, submissions, reflections, conversations, documents, risk,
 * interventions, access-history — or `conversations/{id}` for one
 * conversation's transcript. */
export function readAdminStudentResource(studentId, resourcePath, { page = 1, pageSize = 25 } = {}) {
  const params = new URLSearchParams();
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return request(`/admin/students/${encodeURIComponent(studentId)}/${resourcePath}?${params.toString()}`);
}

/* ── Admin: Instructor 360 (docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.4) ── */
export function getAdminInstructorSummary(instructorId) {
  return request(`/admin/instructors/${encodeURIComponent(instructorId)}/summary`);
}

/* ── Admin: Sections (Task 9 -- class assignment, closes the Work Queue's
 * UNASSIGNED_SECTION loop). Backend: src/api/admin_sections.py. `request()`
 * already unwraps the `{success, data}` envelope (see its "'success' in
 * payload" branch above) -- none of these responses use that shape, so each
 * function below just returns request()'s result as-is; wrapping it again
 * would be the exact "double-unwrapped" mistake commit c79ec39 reverted. ── */
export function getAdminSectionCourses() {
  return request('/admin/sections/courses');
}

export function getAdminSections() {
  return request('/admin/sections');
}

export function createAdminSection({ courseId, sectionCode, term, instructorId = null }) {
  return request('/admin/sections', {
    method: 'POST',
    body: { courseId, sectionCode, term, instructorId },
  });
}

export function updateAdminSection(sectionId, { sectionCode, term, instructorId } = {}) {
  const body = {};
  if (sectionCode !== undefined) body.sectionCode = sectionCode;
  if (term !== undefined) body.term = term;
  if (instructorId !== undefined) body.instructorId = instructorId;
  return request(`/admin/sections/${encodeURIComponent(sectionId)}`, { method: 'PATCH', body });
}

export function deleteAdminSection(sectionId) {
  return request(`/admin/sections/${encodeURIComponent(sectionId)}`, { method: 'DELETE' });
}

export function getAdminSectionRoster(sectionId) {
  return request(`/admin/sections/${encodeURIComponent(sectionId)}/roster`);
}

/** Response is `{success: true}` with no `data` key, so `request()`'s
 * envelope-unwrap resolves this to `undefined` -- callers must treat this as
 * fire-and-forget (reload the roster on success) rather than read a value
 * off the resolved promise. */
export function addAdminSectionStudent(sectionId, studentId) {
  return request(`/admin/sections/${encodeURIComponent(sectionId)}/roster`, {
    method: 'POST',
    body: { studentId },
  });
}

export function removeAdminSectionStudent(sectionId, studentId) {
  return request(
    `/admin/sections/${encodeURIComponent(sectionId)}/roster/${encodeURIComponent(studentId)}`,
    { method: 'DELETE' },
  );
}

/* ── Admin: Data Requests (DSAR) (docs/SPEC_ADMIN_REBUILD_TU_CHUNG_23AUG.md mục 3.5) ── */
export function getAdminDataRequests(skip = 0, limit = 50) {
  return request(`/admin/data-requests?skip=${skip}&limit=${limit}`);
}
export function processDataRequest(id, notes) {
  return request(`/admin/data-requests/${id}/process`, { method: 'POST', body: { notes } });
}
export function rejectDataRequest(id, notes) {
  return request(`/admin/data-requests/${id}/reject`, { method: 'POST', body: { notes } });
}
export function completeDataRequest(id, notes) {
  return request(`/admin/data-requests/${id}/complete`, { method: 'POST', body: { notes } });
}
export function previewDeleteDataRequest(id) {
  return request(`/admin/data-requests/${id}/delete-preview`, { method: 'POST' });
}
export function confirmDeleteDataRequest(id, notes, previewHash) {
  return request(`/admin/data-requests/${id}/delete-confirm`, { method: 'POST', body: { notes, preview_hash: previewHash } });
}

/* ── Admin: guardrail rules (mục 6.5 "Chính sách AI") ─────────────────── */

/** `{ rules: [{code, name, description, enabled, pattern_count, updated_at, updated_by}], any_disabled }` */
export function getGuardrailRules() {
  return request('/admin/guardrail-rules');
}

// Stable names used by the Admin AI Policy screen. Keep the older helpers
// below as compatibility aliases for callers outside that screen.
export function listGuardrailRules() {
  return getGuardrailRules();
}

export function previewGuardrailRule(code, enabled, changeReason) {
  return request(`/admin/guardrail-rules/${encodeURIComponent(code)}/preview`, {
    method: 'POST',
    body: { enabled, reason: changeReason },
  });
}

export function getGuardrailPolicyHistory() {
  return request('/admin/guardrail-rules/history').then((data) => data.versions);
}

export function setGuardrailRuleEnabled(code, enabled, reason) {
  return request(`/admin/guardrail-rules/${encodeURIComponent(code)}`, {
    method: 'PATCH',
    body: { enabled, reason },
  });
}

export function setGuardrailRule(code, enabled, changeReason) {
  return setGuardrailRuleEnabled(code, enabled, changeReason);
}

export function restoreGuardrailDefaults(changeReason = '') {
  return request('/admin/guardrail-rules/restore-defaults', {
    method: 'POST',
    body: { reason: changeReason },
  });
}

export function rollbackGuardrailPolicy(version, changeReason) {
  return request(`/admin/guardrail-rules/versions/${encodeURIComponent(version)}/rollback`, {
    method: 'POST',
    body: { reason: changeReason },
  });
}

/* ── Admin: settings (mục 6.5 "Cấu hình") ─────────────────────────────── */

export function getAdminSettings() {
  return request('/admin/settings');
}

export function updateAdminSettings({ demoModeEnabled, autoRiskAlertsEnabled, defaultSemester } = {}) {
  return request('/admin/settings', {
    method: 'PATCH',
    body: { demoModeEnabled, autoRiskAlertsEnabled, defaultSemester },
  });
}

/* ── Admin: risk policy versioning (mục 6.5/14.1) ─────────────────────── */

/** Current policy — signalWeights/signalThresholds/severityBands are always
 * present, even with no policy published yet (server falls back to the
 * built-in defaults so there is always something concrete to show/edit). */
export function getRiskPolicy() {
  return request('/admin/risk-policy');
}

export function getRiskPolicyHistory() {
  return request('/admin/risk-policy/history');
}

export function previewRiskPolicy({ signalWeights, signalThresholds, severityBands }) {
  return request('/admin/risk-policy/preview', {
    method: 'POST',
    body: { signalWeights, signalThresholds, severityBands },
  });
}

export function publishRiskPolicy({ signalWeights, signalThresholds, severityBands, reason }) {
  return request('/admin/risk-policy', {
    method: 'POST',
    body: { signalWeights, signalThresholds, severityBands, reason },
  });
}

export function rollbackRiskPolicy(version, reason) {
  return request(`/admin/risk-policy/${encodeURIComponent(version)}/rollback`, {
    method: 'POST',
    body: { reason },
  });
}

/* ── Admin: Mock LMS sync (mục 6.6) ───────────────────────────────────── */

export function getMockLmsSyncHistory() {
  return request('/admin/mock-lms/history');
}

export function previewMockLmsSync() {
  return request('/admin/mock-lms/sync/preview', { method: 'POST', body: {} });
}

export function publishMockLmsSync(reason) {
  return request('/admin/mock-lms/sync/publish', { method: 'POST', body: { reason } });
}

export function rollbackMockLmsSync(version, reason) {
  return request(`/admin/mock-lms/sync/${encodeURIComponent(version)}/rollback`, {
    method: 'POST',
    body: { reason },
  });
}

/* ── Admin: academic term + course exams ──────────────────────────────── */

export function getActiveAcademicTerm() {
  return request('/admin/academic-terms/active');
}

export function getAcademicTerms() {
  return request('/admin/academic-terms');
}

export function setActiveAcademicTerm({ name, startDate, studyWeeks = 10, examWeeks = 2 }) {
  return request('/admin/academic-terms/active', {
    method: 'PUT',
    body: { name, startDate, studyWeeks, examWeeks },
  });
}

export function getCourseExams() {
  return request('/admin/course-exams');
}

export function upsertCourseExam({ courseId, kind, sessions }) {
  return request('/admin/course-exams', {
    method: 'PUT',
    body: { courseId, kind, sessions },
  });
}

export function deleteCourseExam(examId) {
  return request(`/admin/course-exams/${encodeURIComponent(examId)}`, { method: 'DELETE' });
}

/* ── Admin/Instructor: class activity log ─────────────────────────────── */

export function logClassActivity({ courseId, activityDate, kind, title = '' }) {
  return request('/admin/class-activities', {
    method: 'POST',
    body: { courseId, activityDate, kind, title },
  });
}

export function getClassActivities(courseId) {
  return request(`/admin/class-activities?course_id=${encodeURIComponent(courseId)}`);
}

/* ── Student: semester setup ───────────────────────────────────────────── */

export function getSemesterCatalog() {
  return request('/student/semesters/catalog');
}

export function getSemesterStatus() {
  return request('/student/semesters/status');
}

export function listSemesters() {
  return request('/student/semesters');
}

export function getSemester(semesterId) {
  return request(`/student/semesters/${encodeURIComponent(semesterId)}`);
}

export function createSemester({ name, startDate, endDate, courseIds, weeklySlots = [], exceptions = [] }) {
  return request('/student/semesters', {
    method: 'POST',
    body: {
      name,
      start_date: startDate,
      end_date: endDate,
      course_ids: courseIds,
      weekly_slots: weeklySlots,
      exceptions,
    },
  });
}

export function updateSemester(semesterId, { name, startDate, endDate, courseIds, weeklySlots = [], exceptions = [] }) {
  return request(`/student/semesters/${encodeURIComponent(semesterId)}`, {
    method: 'PATCH',
    body: {
      name,
      start_date: startDate,
      end_date: endDate,
      course_ids: courseIds,
      weekly_slots: weeklySlots,
      exceptions,
    },
  });
}

/* ── Student: lecture-driven weekly plan ──────────────────────────────────
 * Second, independent plan-generation flow (timetable/lecture sessions, not
 * assignments) — separate route from Gate2's `/plans/*` endpoints above, so
 * it can never be mistaken for or collide with the Gate2 planner. */

export function generateLecturePlan({ weekStart, availableHours = 6, language = 'vi' } = {}) {
  return request('/student/lecture-plan/generate', {
    method: 'POST',
    body: {
      week_start: weekStart || undefined,
      available_hours: availableHours,
      language,
    },
  });
}

export function getLecturePlan(planId) {
  return request(`/student/lecture-plan/${encodeURIComponent(planId)}`);
}

export function getLatestLecturePlan({ weekNumber } = {}) {
  const query = weekNumber ? `?week_number=${encodeURIComponent(weekNumber)}` : '';
  return request(`/student/lecture-plan${query}`);
}

/* ── Student: practice sets ───────────────────────────────────────────── */

export function getPracticeSet({ courseCode, weekNumber }) {
  return request(`/student/practice?course_code=${encodeURIComponent(courseCode)}&week_number=${encodeURIComponent(weekNumber)}`);
}

export function requestPracticeSet({ courseCode, weekNumber, language = 'vi' }) {
  return request('/student/practice/request', {
    method: 'POST',
    body: { courseCode, weekNumber, language },
  });
}

/* ── Instructor: practice review queue ────────────────────────────────── */

export function getInstructorPracticeSets(status = null) {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return request(`/instructor/practice${query}`);
}

export function getInstructorPracticeSet(setId) {
  return request(`/instructor/practice/${encodeURIComponent(setId)}`);
}

export function updatePracticeItem(setId, itemId, patch) {
  return request(`/instructor/practice/${encodeURIComponent(setId)}/items/${encodeURIComponent(itemId)}`, {
    method: 'PATCH',
    body: patch,
  });
}

export function reviewPracticeSet(setId, decision) {
  return request(`/instructor/practice/${encodeURIComponent(setId)}/review`, {
    method: 'POST',
    body: { decision },
  });
}

export function regeneratePracticeSet(setId) {
  return request(`/instructor/practice/${encodeURIComponent(setId)}/regenerate`, {
    method: 'POST',
    body: {},
  });
}

/* ── Shared: user-facing error normalization ──────────────────────────── */

/** Turns an ApiError/network error into `{ message }` safe to show in UI,
 * falling back to a locale-appropriate generic message when the server
 * gave nothing usable. */
export function userFacingApiError(err, lang = 'vi') {
  if (err instanceof ApiError && err.message) {
    return { message: err.message, code: err.code, status: err.status };
  }
  const fallback = lang === 'en' ? 'Something went wrong. Please try again.' : 'Có lỗi xảy ra, vui lòng thử lại.';
  return { message: err?.message || fallback, code: err?.code ?? 'UNKNOWN_ERROR', status: err?.status ?? 0 };
}

/* ── Instructor: risk review (single + bulk) ──────────────────────────── */

/** `decision` is APPROVE | EDIT | REJECT. */
export function reviewAlert(riskId, decision, note = null) {
  return request(`/instructor/risks/${encodeURIComponent(riskId)}/intervention`, {
    method: 'POST',
    body: { decision, note },
  });
}

/** `decision` is APPROVE | REJECT, applied to every owned case in `riskIds`
 * (cases the instructor doesn't own are silently skipped server-side). */
export function bulkReviewAlerts(riskIds, decision, note = null) {
  return request('/instructor/risks/bulk-intervention', {
    method: 'POST',
    body: { riskIds, decision, note },
  });
}

export function getInterventionHistory(riskId) {
  return request(`/instructor/risks/${encodeURIComponent(riskId)}/interventions`);
}

/* ── Instructor: dashboard export / announcements / kudos / class compare ─ */

/** CSV download — not JSON, so this bypasses `request()` and reads the
 * filename straight off Content-Disposition. */
export async function exportInstructorReport(courseId = null) {
  const query = courseId && courseId !== 'ALL' ? `?course_id=${encodeURIComponent(courseId)}` : '';
  const response = await rawFetch(`/instructor/dashboard/export${query}`, { method: 'GET' });
  if (!response.ok) {
    const payload = await parsePayload(response);
    throw new ApiError(errorMessageFromPayload(payload, response.status), payload?.error?.code ?? `HTTP_${response.status}`, response.status);
  }
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^"]+)"?/);
  const filename = match ? match[1] : 'instructor-dashboard.csv';
  const blob = await response.blob();
  return { blob, filename };
}

export async function getInstructorAnnouncements() {
  const data = await request('/instructor/announcements');
  return data.announcements;
}

export async function getInstructorKudos(courseId = null) {
  const query = courseId && courseId !== 'ALL' ? `?course_id=${encodeURIComponent(courseId)}` : '';
  const data = await request(`/instructor/kudos${query}`);
  return data.kudos;
}

export async function getClassComparison() {
  const data = await request('/instructor/classes/compare');
  return data.classes;
}

/* ── Instructor: digest ────────────────────────────────────────────────── */

export function getInstructorDigest(days = 7) {
  return request(`/instructor/digest?days=${encodeURIComponent(days)}`);
}

export function sendInstructorDigestEmail(days = 7) {
  return request(`/instructor/digest/email?days=${encodeURIComponent(days)}`, { method: 'POST', body: {} });
}

/* ── Instructor: student profile + private notes ──────────────────────── */

export function getStudentProfile(studentId) {
  return request(`/instructor/students/${encodeURIComponent(studentId)}/profile`);
}

export async function listStudentNotes(studentId) {
  const data = await request(`/instructor/students/${encodeURIComponent(studentId)}/notes`);
  return data.notes;
}

export function createStudentNote(studentId, content) {
  return request(`/instructor/students/${encodeURIComponent(studentId)}/notes`, {
    method: 'POST',
    body: { content },
  });
}

export function deleteStudentNote(studentId, noteId) {
  return request(`/instructor/students/${encodeURIComponent(studentId)}/notes/${encodeURIComponent(noteId)}`, {
    method: 'DELETE',
  });
}

/* ── Instructor: assignment submissions roster ────────────────────────── */

export async function listInstructorAssignments(courseId = null) {
  const query = courseId && courseId !== 'ALL' ? `?course_id=${encodeURIComponent(courseId)}` : '';
  const data = await request(`/instructor/assignments${query}`);
  return data.assignments;
}

export function getAssignmentSubmissions(assignmentId) {
  return request(`/instructor/assignments/${encodeURIComponent(assignmentId)}/submissions`);
}

/* ── Instructor: class activity log (instructor-scoped, distinct from the
 * admin/instructor shared `/admin/class-activities` endpoints above) ──── */

export function listClassActivities({ start, end } = {}) {
  const params = new URLSearchParams();
  if (start) params.set('start', start);
  if (end) params.set('end', end);
  const query = params.toString();
  return request(`/instructor/class-activities${query ? `?${query}` : ''}`);
}

export function createClassActivity({ course_id, activity_date, kind, title = '', opens_at, closes_at }) {
  return request('/instructor/class-activities', {
    method: 'POST',
    body: { course_id, activity_date, kind, title, opens_at, closes_at },
  });
}

export function updateClassActivity(activityId, patch) {
  return request(`/instructor/class-activities/${encodeURIComponent(activityId)}`, {
    method: 'PATCH',
    body: patch,
  });
}

export function deleteClassActivity(activityId) {
  return request(`/instructor/class-activities/${encodeURIComponent(activityId)}`, { method: 'DELETE' });
}

/* ── Instructor: quiz management ──────────────────────────────────────── */

export function listInstructorQuizClasses() {
  return request('/instructor/quizzes/classes');
}

export function listInstructorQuizzes(sectionId) {
  const query = sectionId ? `?section_id=${encodeURIComponent(sectionId)}` : '';
  return request(`/instructor/quizzes${query}`);
}

export function getInstructorQuiz(quizId) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}`);
}

export function createQuiz(payload) {
  return request('/instructor/quizzes', { method: 'POST', body: payload });
}

export function updateQuiz(quizId, payload) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}`, { method: 'PATCH', body: payload });
}

export function deleteQuiz(quizId) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}`, { method: 'DELETE' });
}

export function setQuizPublished(quizId, published) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/${published ? 'publish' : 'unpublish'}`, {
    method: 'POST',
    body: {},
  });
}

export function addQuizQuestion(quizId, payload) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/questions`, {
    method: 'POST',
    body: payload,
  });
}

export function generateQuizQuestions(quizId, count = 10) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/questions/generate`, {
    method: 'POST',
    body: { count },
  });
}

export function updateQuizQuestion(quizId, questionId, payload) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/questions/${encodeURIComponent(questionId)}`, {
    method: 'PATCH',
    body: payload,
  });
}

export function deleteQuizQuestion(quizId, questionId) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/questions/${encodeURIComponent(questionId)}`, {
    method: 'DELETE',
  });
}

export function reorderQuizQuestions(quizId, questionIds) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/questions/reorder`, {
    method: 'POST',
    body: { question_ids: questionIds },
  });
}

export function getQuizProgress(quizId) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/progress`);
}

export function gradeQuizSubmission(quizId, submissionId, { scores, feedback = null } = {}) {
  return request(`/instructor/quizzes/${encodeURIComponent(quizId)}/submissions/${encodeURIComponent(submissionId)}/grade`, {
    method: 'PATCH',
    body: { scores, feedback },
  });
}

// ── Student-facing quizzes ──────────────────────────────────────────────

export function listStudentQuizzes() {
  return request('/student/quizzes');
}

export function getStudentQuiz(quizId) {
  return request(`/student/quizzes/${encodeURIComponent(quizId)}`);
}

export function submitStudentQuiz(quizId, answers) {
  return request(`/student/quizzes/${encodeURIComponent(quizId)}/submit`, {
    method: 'POST',
    body: { answers },
  });
}
