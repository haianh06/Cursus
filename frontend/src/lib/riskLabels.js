/**
 * Shared label/format helpers for risk & guardrail case UI (instructor
 * pages). Kept as plain functions (not locale JSON) since the source sets
 * are small and backend-defined (see src/services/ai/risk_engine.py::_risk_type
 * and migrations/versions/20260813_guardrail_rules.py seed rows).
 */

const RISK_TYPE_LABELS_VI = {
  LATE_SUBMISSION: 'Nộp bài trễ',
  WEEKLY_GOAL_FAILURE: 'Không đạt mục tiêu tuần',
  ACADEMIC_DECLINE: 'Sa sút học tập',
  ABANDONMENT: 'Ngừng hoạt động',
  SELF_REPORTED_HELP_REQUEST: 'Sinh viên tự yêu cầu hỗ trợ',
  SELF_REPORTED_HIGH_STRESS: 'Tự báo cáo căng thẳng cao trong Phản tư',
};

const RISK_TYPE_LABELS_EN = {
  LATE_SUBMISSION: 'Late submission',
  WEEKLY_GOAL_FAILURE: 'Missed weekly goal',
  ACADEMIC_DECLINE: 'Academic decline',
  ABANDONMENT: 'Inactive / abandoned',
  SELF_REPORTED_HELP_REQUEST: 'Student self-reported',
  SELF_REPORTED_HIGH_STRESS: 'Self-reported high stress in Reflection',
};

const BLOCK_REASON_LABELS_VI = {
  HOMEWORK_VI: 'Yêu cầu giải bài tập (tiếng Việt)',
  HOMEWORK_EN: 'Yêu cầu giải bài tập (tiếng Anh)',
  FULL_CODE: 'Yêu cầu code hoàn chỉnh',
};

const BLOCK_REASON_LABELS_EN = {
  HOMEWORK_VI: 'Asked to solve homework (Vietnamese)',
  HOMEWORK_EN: 'Asked to solve homework (English)',
  FULL_CODE: 'Asked for full working code',
};

/** `t` is the i18n lookup from useLanguage(); falls back to the built-in
 * Vietnamese labels above if the key isn't in locale JSON yet. */
export function riskLevelLabel(t, level) {
  const normalized = (level || '').toUpperCase();
  if (normalized === 'HIGH') return t('instructor.riskHigh') || 'Rủi ro Cao';
  if (normalized === 'MEDIUM') return t('instructor.riskMedium') || 'Rủi ro Trung bình';
  return t('instructor.riskLow') || 'An toàn';
}

export function riskTypeLabel(t, type, lang = 'vi') {
  const key = String(type || '').toUpperCase();
  const table = lang === 'en' ? RISK_TYPE_LABELS_EN : RISK_TYPE_LABELS_VI;
  return table[key] || key || (lang === 'en' ? 'Unknown' : 'Không xác định');
}

export function blockReasonLabel(t, reason, lang = 'vi') {
  const key = String(reason || '').toUpperCase();
  const table = lang === 'en' ? BLOCK_REASON_LABELS_EN : BLOCK_REASON_LABELS_VI;
  return table[key] || key || (lang === 'en' ? 'Blocked question' : 'Câu hỏi bị chặn');
}

export function isHighRisk(level) {
  return String(level || '').toUpperCase() === 'HIGH';
}

/** Relative-ish absolute timestamp for case lists — `iso` may be null while
 * a case is still loading. */
export function formatDetectedAt(iso, lang = 'vi') {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleString(lang === 'en' ? 'en-US' : 'vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
