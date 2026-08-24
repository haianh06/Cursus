/**
 * Where a queue item is handled.
 *
 * Kept out of the JSX so the mapping is assertable: a wrong destination here
 * sends an operator to the wrong learner, which is exactly the kind of thing a
 * rendered component test would not notice.
 */

const STUDENT_TAB_BY_TRIGGER = {
  RISK_SIGNAL: 'risk',
  GUARDRAIL_EVENT: 'conversations',
};

const FIXED_HREF_BY_TRIGGER = {
  DATA_REQUEST: '/admin/data-requests',
  INGEST_JOB: '/admin/governance/curriculum',
};

export function workQueueHref(item) {
  const source = item || {};
  const fixed = FIXED_HREF_BY_TRIGGER[source.trigger_type];
  if (fixed) return fixed;
  const tab = STUDENT_TAB_BY_TRIGGER[source.trigger_type];
  // An unknown trigger, or a subject-bound one that arrived without a subject,
  // goes nowhere in particular on purpose: a student URL built from a missing id
  // is worse than not moving at all.
  if (!tab || !source.subject_user_id) return '/admin/overview';
  return `/admin/students/${encodeURIComponent(source.subject_user_id)}/${tab}`;
}
