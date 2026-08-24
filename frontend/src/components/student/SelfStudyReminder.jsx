import { useEffect, useRef } from 'react';
import { getUpcomingSelfStudy } from '../../lib/api';
import { notify, notificationPermission } from '../../lib/notifications';

const POLL_MS = 60_000;

/**
 * Global, invisible poller: fires an in-tab browser Notification once per
 * self-study block, the moment its 10-minute reminder window opens
 * (REMINDER_LEAD in src/services/self_study_service.py — the backend, not
 * this component, owns "10 minutes before"). No-ops silently if the user
 * never granted Notification permission (see Settings screen toggle) —
 * this only works while the tab/app is open, by design (no service worker).
 */
export default function SelfStudyReminder() {
  const notifiedRef = useRef(new Set());

  useEffect(() => {
    let cancelled = false;

    const tick = async () => {
      if (notificationPermission() !== 'granted') return;
      let items;
      try {
        items = await getUpcomingSelfStudy();
      } catch {
        return;
      }
      if (cancelled) return;
      for (const item of items || []) {
        if (!item.canStart || notifiedRef.current.has(item.blockId)) continue;
        notifiedRef.current.add(item.blockId);
        const n = notify('Sắp đến giờ tự học', {
          body: `${item.title} · bắt đầu lúc ${item.start.slice(11, 16)}`,
          tag: `self-study-${item.blockId}`,
        });
        if (n) n.onclick = () => window.focus();
      }
    };

    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return null;
}
