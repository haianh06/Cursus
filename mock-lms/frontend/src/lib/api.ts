import type {
  CourseDetail,
  CourseSummary,
  CurriculumProgramDetail,
  CurriculumProgramSummary,
  Identity,
  PrerequisiteNode,
  SyllabusDetail,
  SyllabusSummary,
} from '../types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

// Same-origin: FastAPI serves this SPA's own index.html for /courses*, so
// relative paths carry the mock_lms_session cookie automatically (no CORS,
// no separate base URL needed) both in the built app and under the dev
// proxy in vite.config.ts.
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      ...init?.headers,
    },
  });
  if (response.status === 401) {
    // Session expired mid-visit (SESSION_TTL_SECONDS = 3600 in app/sso.py) —
    // the server-rendered gate on /courses* only runs once per page load, so
    // an expired cookie surfaces here instead. Re-run the same SSO redirect
    // the page route itself would have done.
    window.location.href = '/sso/refresh?next=' + encodeURIComponent(window.location.pathname + window.location.search);
    throw new ApiError('session_expired', 401);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(body?.detail || `HTTP ${response.status}`, response.status);
  }
  return response.json();
}

export function getIdentity(): Promise<Identity> {
  return request('/web-api/me');
}

export function listCourses(): Promise<CourseSummary[]> {
  return request('/web-api/courses');
}

export function getCourse(code: string): Promise<CourseDetail> {
  return request(`/web-api/courses/${encodeURIComponent(code)}`);
}

export function updateDueDate(
  code: string,
  assignmentId: string,
  dueAt: string,
): Promise<CourseDetail> {
  return request(`/web-api/courses/${encodeURIComponent(code)}/assignments/${encodeURIComponent(assignmentId)}/due-date`, {
    method: 'POST',
    body: JSON.stringify({ due_at: dueAt }),
  });
}

export function listSyllabi(q?: string): Promise<SyllabusSummary[]> {
  const query = q ? `?q=${encodeURIComponent(q)}` : '';
  return request(`/web-api/syllabi${query}`);
}

export function getSyllabus(code: string): Promise<SyllabusDetail> {
  return request(`/web-api/syllabi/${encodeURIComponent(code)}`);
}

export function listCurriculumPrograms(): Promise<CurriculumProgramSummary[]> {
  return request('/web-api/curriculum-programs');
}

export function getCurriculumProgram(code: string): Promise<CurriculumProgramDetail> {
  return request(`/web-api/curriculum-programs/${encodeURIComponent(code)}`);
}

export function listPrerequisites(): Promise<PrerequisiteNode[]> {
  return request('/web-api/prerequisites');
}
