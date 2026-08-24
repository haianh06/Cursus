const SUMMARY_FIELD_KEYS = {
  reflections: 'fieldReflections', conversations: 'fieldConversations', messages: 'fieldMessages',
  enrollments: 'fieldEnrollments', unresolved_risks: 'fieldUnresolvedRisks',
  weekly_plans: 'fieldWeeklyPlans', self_study_sessions: 'fieldSelfStudySessions',
  submissions: 'fieldSubmissions', last_message_at: 'fieldLastMessageAt',
  last_active_at: 'fieldLastActiveAt', latest_signal_at: 'fieldLatestSignalAt',
  total: 'fieldTotal', unresolved: 'fieldUnresolved',
  open: 'fieldOpen', closed: 'fieldClosed', sections: 'fieldSections', students: 'fieldStudents',
  last_action_at: 'fieldLastActionAt',
};

const PRIORITY_KEYS = { CRITICAL: 'priorityCritical', HIGH: 'priorityHigh', MEDIUM: 'priorityMedium', LOW: 'priorityLow' };
const STATUS_KEYS = { OPEN: 'statusOpen', IN_REVIEW: 'statusInReview', RESOLVED: 'statusResolved', CLOSED: 'statusClosed', REOPENED: 'statusReopened', PENDING: 'statusPending', IN_PROGRESS: 'statusInProgress', COMPLETED: 'statusCompleted', REJECTED: 'statusRejected', ACTIVE: 'statusActive', INACTIVE: 'statusInactive', ENROLLED: 'statusEnrolled', DROPPED: 'statusDropped' };
const TRIGGER_KEYS = { RISK_SIGNAL: 'triggerRisk', GUARDRAIL_EVENT: 'triggerSafety', DATA_REQUEST: 'triggerDataRequest', INGEST_JOB: 'triggerCurriculum' };
const RISK_TYPE_KEYS = {
  ACADEMIC_DECLINE: 'workQueueRiskAcademicDecline',
  LATE_SUBMISSION: 'workQueueRiskLateSubmission',
  WEEKLY_GOAL_FAILURE: 'workQueueRiskWeeklyGoalFailure',
  ABANDONMENT: 'workQueueRiskAbandonment',
  ATTENDANCE: 'workQueueRiskAttendance',
};
const RECOMMENDED_ACTION_KEYS = [
  [/^schedule urgent academic counseling and request instructor review on foundational labs\.?$/i, 'riskActionAcademicCounseling'],
  [/^prompt student to utilize ai decomposition to organize final deployment tasks\.?$/i, 'riskActionAiDecomposition'],
  [/^encourage student to establish daily study slots in schedule\.?$/i, 'riskActionStudySlots'],
  [/^alert instructor to provide feedback on ethan'?s api specifications\.?$/i, 'riskActionInstructorFeedback'],
  [/^instructor intervention required: send direct email check-in and propose revised ai planning\.?$/i, 'riskActionInterventionEmailPlanning'],
  [/^instructor intervention required\.?$/i, 'riskActionInstructorIntervention'],
];
const ROLE_KEYS = { STUDENT: 'roleStudent', INSTRUCTOR: 'roleInstructor', ADMIN: 'roleAdmin' };
const DATA_REQUEST_TYPE_KEYS = { ACCESS: 'dataRequestAccess', EXPORT: 'dataRequestExport', CORRECTION: 'dataRequestCorrection', DELETION: 'dataRequestDeletion' };
// Upper-case keys because `enumLabel` upper-cases the value before the lookup.
// These were written lower-case, matching the `event_type` the API actually
// sends, so every single lookup missed and the whole Recent changes block
// rendered "Chưa phân loại" — fifteen distinct events, one meaningless label.
// The translations existed the entire time; only the lookup was wrong.
const CRITICAL_EVENT_KEYS = { USER_STATUS_CHANGED: 'criticalEventUserStatus', USER_ACCESS_CHANGED: 'criticalEventUserAccess', GUARDRAIL_RULE_UPDATED: 'criticalEventGuardrailUpdated', GUARDRAIL_POLICY_ROLLED_BACK: 'criticalEventGuardrailRolledBack', RISK_POLICY_PUBLISHED: 'criticalEventRiskPolicyPublished', RISK_POLICY_ROLLED_BACK: 'criticalEventRiskPolicyRolledBack', ADMIN_SETTINGS_UPDATED: 'criticalEventSettingsUpdated', CURRICULUM_PUBLISHED: 'criticalEventCurriculumPublished', CURRICULUM_ROLLED_BACK: 'criticalEventCurriculumRolledBack', CURRICULUM_ARCHIVED: 'criticalEventCurriculumArchived', DATA_REQUEST_TRANSITIONED: 'criticalEventDataRequestTransitioned', DATA_REQUEST_PURGED: 'criticalEventDataRequestPurged' };
const AUDIT_EVENT_KEYS = {
  ADMIN_SENSITIVE_READ: 'logSensitiveRead',
  COURSE_CREATED: 'logEventCourseCreated',
  COURSE_DELETED: 'logEventCourseDeleted',
  INVITATION_CREATED: 'logEventInvitationCreated',
  INVITATION_REVOKED: 'logEventInvitationRevoked',
  INVITATION_RESENT: 'logEventInvitationResent',
  INVITATION_SCOPE_CHANGED: 'logEventInvitationScopeChanged',
  INVITATION_ACCEPTED: 'logEventInvitationAccepted',
  DATA_REQUEST_CREATED: 'logEventDataRequestCreated',
  DATA_REQUEST_DELETION_PREVIEWED: 'logEventDataRequestDeletionPreviewed',
  ADMIN_COURSE_ADDED: 'logEventAdminCourseAdded',
  ADMIN_COURSE_HIDDEN: 'logEventAdminCourseHidden',
  ADMIN_COURSE_RESTORED: 'logEventAdminCourseRestored',
  ACADEMIC_TERM_UPDATED: 'logEventAcademicTermUpdated',
  ACADEMIC_EXAM_UPDATED: 'logEventAcademicExamUpdated',
  ACADEMIC_EXAM_DELETED: 'logEventAcademicExamDeleted',
};
const RESOURCE_KEYS = {
  USER: 'resourceUser', AI_POLICY: 'resourceAiPolicy',
  SETTING: 'resourceSetting', ADMIN_SETTINGS: 'resourceSetting', CURRICULUM: 'resourceCurriculum',
  DATA_REQUEST: 'resourceDataRequest', PLAN: 'resourcePlan', SESSION: 'resourceSession',
  CHAT: 'resourceChat', REFLECTION: 'resourceReflection', ASSIGNMENT: 'resourceAssignment',
  COURSE: 'resourceCourse', KPI: 'resourceKpi', RISK: 'resourceRisk',
  RISK_CASE: 'resourceRisk',
  INTERVENTION: 'resourceIntervention', SUBMISSION: 'resourceSubmission',
  STUDENT_DOCUMENT: 'resourceStudentDocument', AUDIT: 'resourceAudit',
  INTEGRATION: 'resourceIntegration', SYSTEM_HEALTH: 'resourceSystemHealth',
  DOCUMENT: 'resourceDocument', INVITATION: 'resourceInvitation', RISK_POLICY: 'resourceRiskPolicy',
  GUARDRAIL_RULE: 'resourceGuardrailRule', GUARDRAIL_POLICY: 'resourceGuardrailPolicy',
  INGEST_JOB: 'resourceIngestJob', ACADEMIC_TERM: 'resourceAcademicTerm',
  COURSE_EXAM: 'resourceCourseExam', RISK_SIGNAL: 'resourceRiskSignal',
  GUARDRAIL_EVENT: 'resourceGuardrailEvent',
};
const SUMMARY_SCALAR_FIELDS = new Set([
  'enrollments', 'unresolved_risks', 'reflections', 'conversations', 'messages',
  'weekly_plans', 'self_study_sessions', 'submissions', 'last_message_at',
  'last_active_at', 'total', 'unresolved', 'latest_signal_at', 'open', 'sections',
  'students', 'last_action_at',
]);
const SUMMARY_MAP_FIELDS = {
  by_status: new Set(['PENDING', 'ACTIVE', 'COMPLETED']),
  by_level: new Set(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
};

function enumLabel(t, keys, value) {
  return t(`admin.${keys[String(value || '').toUpperCase()] || 'enumUnknown'}`);
}

export function adminSummaryFieldLabel(t, field) {
  return t(`admin.${SUMMARY_FIELD_KEYS[field] || 'fieldUnknown'}`);
}

export function adminPriorityLabel(t, value) { return enumLabel(t, PRIORITY_KEYS, value); }
export function adminStatusLabel(t, value) { return enumLabel(t, STATUS_KEYS, value); }
export function adminTriggerLabel(t, value) { return enumLabel(t, TRIGGER_KEYS, value); }
export function adminRoleLabel(t, value) { return enumLabel(t, ROLE_KEYS, value); }
export function adminDataRequestTypeLabel(t, value) { return enumLabel(t, DATA_REQUEST_TYPE_KEYS, value); }
export function adminRiskTypeLabel(t, value) {
  return t(`admin.${RISK_TYPE_KEYS[String(value || '').toUpperCase()] || 'riskTypeUnknown'}`);
}
export function adminRecommendedActionLabel(t, value) {
  const raw = String(value || '').trim();
  const match = RECOMMENDED_ACTION_KEYS.find(([pattern]) => pattern.test(raw));
  return t(`admin.${match?.[1] || 'riskActionGeneric'}`);
}
export function adminCriticalChangeEventLabel(t, value) { return enumLabel(t, CRITICAL_EVENT_KEYS, value); }
export function adminAuditEventLabel(t, value) {
  const normalised = String(value || '').toUpperCase();
  return t(`admin.${AUDIT_EVENT_KEYS[normalised] || CRITICAL_EVENT_KEYS[normalised] || 'enumUnknown'}`);
}
export function adminResourceLabel(t, value) { return enumLabel(t, RESOURCE_KEYS, value); }
export function adminAuditDecisionLabel(t, value) {
  return t(`admin.${String(value).toUpperCase() === 'ALLOW' ? 'auditAllow' : String(value).toUpperCase() === 'DENY' ? 'auditDeny' : 'enumUnknown'}`);
}
export function adminSystemStatusLabel(t, value) {
  return t(`admin.${String(value).toUpperCase() === 'HEALTHY' ? 'systemHealthy' : 'systemDegraded'}`);
}

export function adminWorkQueueSummary(t, item) {
  const triggerType = String(item?.trigger_type || '').toUpperCase();
  const summary = String(item?.summary || '').trim();

  if (triggerType === 'RISK_SIGNAL') {
    const match = summary.match(/^([A-Z_]+) risk at ([A-Z_]+) level$/i);
    const key = RISK_TYPE_KEYS[String(match?.[1] || '').toUpperCase()] || 'workQueueRiskGeneric';
    return t(`admin.${key}`);
  }

  if (triggerType === 'GUARDRAIL_EVENT') {
    return t('admin.workQueueGuardrailBlocked');
  }

  if (triggerType === 'DATA_REQUEST') {
    const match = summary.match(/^([A-Z_]+) request is ([A-Z_]+)$/i);
    if (match) return `${adminDataRequestTypeLabel(t, match[1])} · ${adminStatusLabel(t, match[2])}`;
    return t('admin.workQueueDataRequestGeneric');
  }

  if (triggerType === 'INGEST_JOB') {
    const match = summary.match(/^Ingest .+ failed for (.+)$/i);
    return match
      ? t('admin.workQueueIngestFailed').replace('{course}', match[1])
      : t('admin.workQueueIngestGeneric');
  }

  return t('admin.workQueueSummaryFallback');
}

/** Flatten only the aggregate maps a summary promises; nested data is dropped. */
export function safeAdminSummaryEntries(data) {
  return Object.entries(data || {}).flatMap(([key, value]) => {
    if (SUMMARY_SCALAR_FIELDS.has(key) && (value === null || ['string', 'number', 'boolean'].includes(typeof value))) {
      return [{ key, value }];
    }
    const allowedMembers = SUMMARY_MAP_FIELDS[key];
    if (!allowedMembers || !value || Array.isArray(value) || typeof value !== 'object') {
      return [];
    }
    return Object.entries(value)
      .filter(([nestedKey, nestedValue]) => allowedMembers.has(nestedKey.toUpperCase()) && (nestedValue === null || ['string', 'number', 'boolean'].includes(typeof nestedValue)))
      .map(([nestedKey, nestedValue]) => ({ key: `${key}.${nestedKey}`, value: nestedValue }));
  });
}

export function adminSummaryEntryLabel(t, key) {
  const [group, nested] = key.split('.');
  if (!nested) return adminSummaryFieldLabel(t, group);
  if (group === 'by_status') return `${t('admin.fieldByStatus')}: ${adminStatusLabel(t, nested)}`;
  if (group === 'by_level') return `${t('admin.fieldByLevel')}: ${adminPriorityLabel(t, nested)}`;
  return `${t('admin.fieldByType')}: ${adminDataRequestTypeLabel(t, nested)}`;
}
