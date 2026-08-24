/**
 * Thin wrapper around the browser Notification API — in-tab/in-app only
 * (fires while this tab is open; no service worker / push infra). Never
 * throws: every call site can fire-and-forget.
 */

export function notificationsSupported() {
  return typeof window !== 'undefined' && 'Notification' in window;
}

export function notificationPermission() {
  return notificationsSupported() ? Notification.permission : 'unsupported';
}

export async function requestNotificationPermission() {
  if (!notificationsSupported()) return 'unsupported';
  if (Notification.permission !== 'default') return Notification.permission;
  try {
    return await Notification.requestPermission();
  } catch {
    return Notification.permission;
  }
}

/** No-op (not an error) unless permission is already granted — callers
 * should request permission once, up front, from a real user gesture. */
export function notify(title, options = {}) {
  if (!notificationsSupported() || Notification.permission !== 'granted') return null;
  try {
    return new Notification(title, options);
  } catch {
    return null;
  }
}

/* ── Pomodoro phase-change chime ──────────────────────────────────────────
 * Synthesized tones (Web Audio API) — no audio file to host/bundle, and it
 * doesn't need Notification permission. Browsers block audio until a real
 * user gesture happens on the page; by the time a phase actually changes
 * the student has already clicked "Start studying", so this is safe. */
let audioCtx = null;

function getAudioContext() {
  if (typeof window === 'undefined') return null;
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!audioCtx) audioCtx = new Ctx();
  if (audioCtx.state === 'suspended') audioCtx.resume().catch(() => {});
  return audioCtx;
}

function playTone(ctx, { frequency, startAt, duration, gain = 0.15 }) {
  const oscillator = ctx.createOscillator();
  const gainNode = ctx.createGain();
  oscillator.type = 'sine';
  oscillator.frequency.value = frequency;
  gainNode.gain.setValueAtTime(0, startAt);
  gainNode.gain.linearRampToValueAtTime(gain, startAt + 0.02);
  gainNode.gain.linearRampToValueAtTime(0, startAt + duration);
  oscillator.connect(gainNode).connect(ctx.destination);
  oscillator.start(startAt);
  oscillator.stop(startAt + duration + 0.02);
}

/** `kind`: 'break' (work → break, a lower single tone), 'work' (break →
 * work, a higher single tone), or 'complete' (session finished, a short
 * ascending two-note chime). Never throws — best-effort only. */
export function playPomodoroChime(kind) {
  try {
    const ctx = getAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    if (kind === 'complete') {
      playTone(ctx, { frequency: 523.25, startAt: now, duration: 0.18 });
      playTone(ctx, { frequency: 783.99, startAt: now + 0.16, duration: 0.28 });
    } else if (kind === 'break') {
      playTone(ctx, { frequency: 440, startAt: now, duration: 0.3 });
    } else {
      playTone(ctx, { frequency: 659.25, startAt: now, duration: 0.22 });
    }
  } catch {
    /* best-effort only */
  }
}
