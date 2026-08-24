/**
 * lib/planning.js — Cursus planning helpers
 * Derives dashboard metrics and next best action from task list.
 */

import { isUrgent } from './dates.js';

/**
 * Computes the 4 weekly momentum metrics from the task list.
 * @param {Array} tasks
 * @returns {{ doneCount, total, progressPct, urgentCount, studyMinutes }}
 */
export function getWeeklyMetrics(tasks) {
  const total = tasks.length;
  const doneCount = tasks.filter(t => t.status === 'done').length;
  const progressPct = total ? Math.round((doneCount / total) * 100) : 0;
  const urgentCount = tasks.filter(t => t.status !== 'done' && isUrgent(t.deadline)).length;

  // Estimate study minutes: sum done + estimate pending (use 45 min default if no estimate)
  const parseMin = (est) => {
    if (!est) return 45;
    const m = est.match(/(\d+)/);
    return m ? parseInt(m[1], 10) : 45;
  };
  const doneMinutes = tasks
    .filter(t => t.status === 'done')
    .reduce((acc, t) => acc + parseMin(t.duration_estimate), 0);
  const pendingMinutes = tasks
    .filter(t => t.status !== 'done')
    .reduce((acc, t) => acc + parseMin(t.duration_estimate), 0);

  return { doneCount, total, progressPct, urgentCount, doneMinutes, pendingMinutes };
}

/**
 * Returns the highest-priority pending task (next best action).
 * Priority: overdue → urgent → pending (by earliest deadline, then by insertion order).
 * @param {Array} tasks
 * @returns {Object|null}
 */
export function getNextBestAction(tasks) {
  const pending = tasks.filter(t => t.status !== 'done');
  if (pending.length === 0) return null;

  // Sort: tasks with a deadline come first, sorted by deadline ascending
  const sorted = [...pending].sort((a, b) => {
    if (a.deadline && b.deadline) return new Date(a.deadline) - new Date(b.deadline);
    if (a.deadline) return -1;
    if (b.deadline) return 1;
    return 0;
  });

  return sorted[0];
}

/**
 * Returns a reason string for why a task was prioritized (mock logic).
 * In production this would come from the AI insight endpoint.
 * @param {Object} task
 * @param {string} lang
 */
export function getPriorityReason(task, lang = 'vi') {
  if (!task) return '';
  if (!task.deadline) {
    return lang === 'vi'
      ? 'Nhiệm vụ chưa có hạn chót — Trợ lý Cursus ưu tiên sớm nhất trong danh sách.'
      : 'No deadline set — Cursus Assistant prioritized this as the earliest in the list.';
  }
  const diff = new Date(task.deadline) - new Date();
  const diffH = Math.floor(diff / 3600000);
  const diffD = Math.floor(diff / 86400000);

  if (diff < 0) {
    return lang === 'vi'
      ? 'Nhiệm vụ đã quá hạn — Trợ lý Cursus ưu tiên hoàn thành ngay.'
      : 'Task is overdue — Cursus Assistant prioritizes immediate completion.';
  }
  if (diffH < 24) {
    return lang === 'vi'
      ? `Hạn chót trong ${diffH} giờ — Trợ lý Cursus ưu tiên để tránh trễ hạn.`
      : `Deadline in ${diffH} hours — Cursus Assistant prioritizes to avoid missing it.`;
  }
  return lang === 'vi'
    ? `Hạn chót còn ${diffD} ngày và có trọng số cao trong Syllabus — Trợ lý Cursus ưu tiên nhiệm vụ này vì nó ảnh hưởng đến điểm tổng kết.`
    : `Deadline in ${diffD} days with high syllabus weight — Cursus Assistant prioritizes this task for its impact on your final grade.`;
}
