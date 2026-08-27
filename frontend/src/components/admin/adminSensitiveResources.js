export const ADMIN_STUDENT_RAW_TABS = Object.freeze([
  { key: 'plans', resources: ['plans', 'tasks', 'progress-events', 'reminders'] },
  { key: 'sessions', resources: ['sessions'] },
  { key: 'coursework', resources: ['assignments', 'submissions'] },
  { key: 'reflection', resources: ['reflections'] },
  { key: 'conversations', resources: ['conversations'] },
  { key: 'risk', resources: ['risk', 'interventions'] },
  { key: 'documents', resources: ['documents'] },
  { key: 'access-history', resources: ['access-history'] },
]);

const RESOURCE_PRESENTATION = Object.freeze({
  plans: {
    title: (item, lang) => `${lang === 'vi' ? 'Tuần' : 'Week'} ${item.weekNumber ?? '—'}`,
    fields: ['studyHoursAllocated', 'goals'],
  },
  tasks: { title: (item) => item.title, fields: ['status', 'priority', 'plannedMinutes', 'actualMinutes'] },
  'progress-events': { title: (item) => item.eventType, fields: ['occurredAt', 'taskId'] },
  reminders: { title: (item) => item.title, fields: ['message', 'channel', 'scheduledTime'] },
  sessions: {
    title: (item) => item.title,
    fields: ['plannedMinutes', 'startedAt', 'scheduledEndAt', 'endedAt', 'actualMinutes', 'pomodorosCompleted', 'status'],
  },
  assignments: { title: (item) => item.title, fields: ['dueDate', 'maxPoints', 'assessmentType'] },
  submissions: { title: (item) => item.assignmentId, fields: ['submittedAt', 'gradingStatus', 'grade', 'isLate'] },
  reflections: {
    title: (item, lang) => `${lang === 'vi' ? 'Phản tư tuần' : 'Reflection week'} ${item.weekNumber ?? '—'}`,
    fields: ['generatedAt', 'content'],
  },
  documents: { title: (item) => item.title, fields: ['version'] },
  risk: { title: (item) => item.riskType, fields: ['riskLevel', 'generatedAt', 'resolvedAt', 'recommendedAction'] },
  interventions: { title: (item) => item.actionTaken, fields: ['status', 'createdAt'] },
  'access-history': { title: (item) => item.resourceType, fields: ['actorUserId', 'resourceId', 'createdAt'] },
});

const FIELD_LABELS = Object.freeze({
  vi: {
    studyHoursAllocated: 'Giờ học phân bổ', goals: 'Mục tiêu', status: 'Trạng thái', priority: 'Ưu tiên',
    plannedMinutes: 'Phút dự kiến', actualMinutes: 'Phút thực tế', occurredAt: 'Thời điểm', taskId: 'Công việc',
    message: 'Nội dung', channel: 'Kênh', scheduledTime: 'Lịch gửi', dueDate: 'Hạn nộp', maxPoints: 'Điểm tối đa',
    assessmentType: 'Loại đánh giá', submittedAt: 'Thời điểm nộp', gradingStatus: 'Chấm điểm', grade: 'Điểm',
    isLate: 'Nộp muộn', generatedAt: 'Thời điểm tạo', content: 'Nội dung', version: 'Phiên bản',
    riskLevel: 'Mức rủi ro', resolvedAt: 'Đã xử lý lúc', recommendedAction: 'Hành động đề xuất',
    createdAt: 'Thời điểm', actorUserId: 'Người truy cập', resourceId: 'Tài nguyên',
    startedAt: 'Bắt đầu', scheduledEndAt: 'Kết thúc dự kiến', endedAt: 'Kết thúc thực tế',
    pomodorosCompleted: 'Pomodoro hoàn thành',
  },
  en: {
    studyHoursAllocated: 'Allocated hours', goals: 'Goals', status: 'Status', priority: 'Priority',
    plannedMinutes: 'Planned minutes', actualMinutes: 'Actual minutes', occurredAt: 'Occurred at', taskId: 'Task',
    message: 'Message', channel: 'Channel', scheduledTime: 'Scheduled time', dueDate: 'Due date', maxPoints: 'Max points',
    assessmentType: 'Assessment type', submittedAt: 'Submitted at', gradingStatus: 'Grading status', grade: 'Grade',
    isLate: 'Late submission', generatedAt: 'Generated at', content: 'Content', version: 'Version',
    riskLevel: 'Risk level', resolvedAt: 'Resolved at', recommendedAction: 'Recommended action',
    createdAt: 'Created at', actorUserId: 'Actor', resourceId: 'Resource',
    startedAt: 'Started at', scheduledEndAt: 'Scheduled end', endedAt: 'Ended at',
    pomodorosCompleted: 'Pomodoros completed',
  },
});

function presentValue(value, lang) {
  if (value === null || value === undefined || value === '') return '—';
  if (typeof value === 'boolean') return value ? (lang === 'vi' ? 'Có' : 'Yes') : (lang === 'vi' ? 'Không' : 'No');
  if (Array.isArray(value)) return value.filter((entry) => ['string', 'number', 'boolean'].includes(typeof entry)).join(' · ') || '—';
  if (['string', 'number'].includes(typeof value)) return String(value);
  return '—';
}

/** Unknown server fields are deliberately omitted until their UI is reviewed. */
export function describeAdminRawItem(resource, item, lang = 'vi') {
  const presentation = RESOURCE_PRESENTATION[resource];
  if (!presentation || !item || typeof item !== 'object' || Array.isArray(item)) return null;
  const labels = FIELD_LABELS[lang] || FIELD_LABELS.en;
  return {
    id: item.id,
    title: presentValue(presentation.title(item, lang), lang),
    rows: presentation.fields.map((field) => ({
      field,
      label: labels[field] || field,
      value: presentValue(item[field], lang),
    })),
  };
}
