import { ADMIN_PATHS } from './adminRoutes';

/**
 * Where a queue item is handled.
 *
 * Kept out of the JSX so the mapping is assertable: a wrong destination here
 * sends an operator to the wrong learner, which is exactly the kind of thing a
 * rendered component test would not notice.
 */

const STUDENT_TRIGGER_TYPES = new Set(['RISK_SIGNAL', 'GUARDRAIL_EVENT']);

const FIXED_HREF_BY_TRIGGER = {
  DATA_REQUEST: ADMIN_PATHS.dataRequests,
  INGEST_JOB: ADMIN_PATHS.curriculum,
  UNASSIGNED_SECTION: ADMIN_PATHS.sections,
};

export function workQueueHref(item) {
  const source = item || {};
  const fixed = FIXED_HREF_BY_TRIGGER[source.trigger_type];
  if (fixed) return fixed;
  // An unknown trigger, or a subject-bound one that arrived without a subject,
  // goes nowhere in particular on purpose: a student URL built from a missing id
  // is worse than not moving at all. Student 360's tab is component-local state
  // (not URL-addressable), so we can only route to the profile, not a tab.
  if (!STUDENT_TRIGGER_TYPES.has(source.trigger_type) || !source.subject_user_id) {
    return ADMIN_PATHS.overview;
  }
  return `/admin/students/${encodeURIComponent(source.subject_user_id)}`;
}
