/**
 * lib/dates.js — Cursus date helpers
 * Extracted from StudentHome.jsx; shared across student module.
 */

/**
 * Returns true if deadline is within the next 48 hours.
 */
export function isUrgent(deadline) {
  if (!deadline) return false;
  const diff = new Date(deadline) - new Date();
  return diff > 0 && diff < 48 * 3600 * 1000;
}

/**
 * Returns true if deadline is today.
 */
export function isToday(deadline) {
  if (!deadline) return false;
  const d = new Date(deadline);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate();
}

/**
 * Returns true if deadline is tomorrow.
 */
export function isTomorrow(deadline) {
  if (!deadline) return false;
  const d = new Date(deadline);
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return d.getFullYear() === tomorrow.getFullYear() &&
    d.getMonth() === tomorrow.getMonth() &&
    d.getDate() === tomorrow.getDate();
}

/**
 * Returns true if deadline is within the next 7 days (excluding today/tomorrow).
 */
export function isThisWeek(deadline) {
  if (!deadline) return false;
  const diff = new Date(deadline) - new Date();
  return diff > 0 && diff < 7 * 24 * 3600 * 1000 && !isToday(deadline) && !isTomorrow(deadline);
}

/**
 * Groups tasks by deadline bucket: today, tomorrow, thisWeek, later.
 * Only includes tasks with a deadline that are not done.
 */
export function groupDeadlines(tasks) {
  const groups = { today: [], tomorrow: [], thisWeek: [], later: [] };
  tasks
    .filter(t => t.deadline && t.status !== 'done')
    .sort((a, b) => new Date(a.deadline) - new Date(b.deadline))
    .forEach(t => {
      if (isToday(t.deadline)) groups.today.push(t);
      else if (isTomorrow(t.deadline)) groups.tomorrow.push(t);
      else if (isThisWeek(t.deadline)) groups.thisWeek.push(t);
      else groups.later.push(t);
    });
  return groups;
}

/**
 * Returns the greeting segment based on current hour (Vietnamese).
 */
export function getTimeOfDay(lang = 'vi') {
  const hour = new Date().getHours();
  if (lang === 'vi') {
    if (hour < 12) return 'buổi sáng';
    if (hour < 18) return 'buổi chiều';
    return 'buổi tối';
  }
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
}

/**
 * Formats a deadline date to a short human-readable string.
 * e.g. "Hôm nay 23:59" or "12/08/2026"
 */
export function formatDeadline(deadline, lang = 'vi') {
  if (!deadline) return '';
  const d = new Date(deadline);
  const now = new Date();
  const diffMs = d - now;
  const diffH = Math.floor(diffMs / 3600000);
  const diffD = Math.floor(diffMs / 86400000);

  if (diffMs < 0) {
    return lang === 'vi' ? 'Đã quá hạn' : 'Overdue';
  }
  if (diffH < 24) {
    if (lang === 'vi') return `Hôm nay ${d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
    return `Today ${d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
  }
  if (diffD === 1) {
    if (lang === 'vi') return `Ngày mai ${d.toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
    return `Tomorrow ${d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}`;
  }
  if (lang === 'vi') return `Còn ${diffD} ngày`;
  return `In ${diffD} days`;
}
