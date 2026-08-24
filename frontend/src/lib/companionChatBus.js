/**
 * Tiny cross-component signal so a page (e.g. "Today's plan") can ask the
 * globally-mounted `CompanionChatBubble` to open itself with a proactive
 * reminder, without threading chat-open state through props/route context.
 * No persistence, no backend — just an in-memory pub/sub for one session.
 */

const listeners = new Set();

/** `payload.tasks` — the real open tasks to remind about (already filtered
 * by the caller), each `{ id, title, estimatedMinutes }`. */
export function requestCompanionReminder(payload) {
  listeners.forEach((listener) => listener(payload));
}

export function onCompanionReminderRequest(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}
