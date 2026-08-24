import React, { useEffect, useRef } from 'react';
import { AlertTriangle, X } from 'lucide-react';

/**
 * Shared confirm-before-destroy dialog — reuses the exact focus-trap/ESC/
 * restore-focus pattern already proven in `student/DeferTaskDialog.jsx`,
 * generalized so every "not undoable" action across the app (Lecturer
 * intervene/publish/guardrail decisions, Admin delete/restore) goes through
 * one component instead of N ad-hoc `window.confirm()` calls or N bespoke
 * modals. Only uses existing tokens (`--color-danger`/`--color-warning`/
 * `--color-accent`) — no new color system.
 *
 * `open` is the thing being confirmed (any truthy value, typically an id or
 * a small object) — passing `null`/`undefined` hides the dialog, mirroring
 * `DeferTaskDialog`'s `task` prop contract.
 */
export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
  lang = 'vi',
  children,
}) {
  const panelRef = useRef(null);
  const firstRef = useRef(null);
  const restoreRef = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    restoreRef.current = document.activeElement;
    firstRef.current?.focus();
    const selector =
      'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onCancel();
        return;
      }
      if (event.key !== 'Tab' || !panelRef.current) return;
      const items = Array.from(panelRef.current.querySelectorAll(selector));
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      if (restoreRef.current instanceof HTMLElement) restoreRef.current.focus();
    };
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm" onClick={onCancel} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-md rounded-2xl border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-line">
          <div className="flex items-center gap-2 min-w-0">
            <AlertTriangle size={16} className={danger ? 'text-danger' : 'text-warning'} />
            <h2 id="confirm-dialog-title" className="font-display text-sm font-bold truncate text-fg">
              {title}
            </h2>
          </div>
          <button
            type="button"
            className="btn-ghost w-10 h-10 inline-flex items-center justify-center rounded-lg cursor-pointer text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={onCancel}
            aria-label={lang === 'vi' ? 'Đóng' : 'Close'}
          >
            <X size={15} />
          </button>
        </div>

        <div className="p-5 text-left">
          <p id="confirm-dialog-message" className="text-[13px] text-fg-secondary leading-relaxed mb-4">
            {message}
          </p>
          {children}
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-line">
          <button
            ref={firstRef}
            type="button"
            className="btn btn-outline text-[13px] px-4 min-h-10 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent"
            onClick={onCancel}
          >
            {cancelLabel ?? (lang === 'vi' ? 'Huỷ' : 'Cancel')}
          </button>
          <button
            type="button"
            className={`btn text-[13px] px-4 min-h-10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent ${
              danger ? 'text-danger border border-danger bg-danger-soft hover:opacity-90' : 'btn-accent'
            }`}
            disabled={busy}
            onClick={onConfirm}
          >
            {busy
              ? lang === 'vi'
                ? 'Đang xử lý…'
                : 'Working…'
              : (confirmLabel ?? (lang === 'vi' ? 'Xác nhận' : 'Confirm'))}
          </button>
        </div>
      </div>
    </>
  );
}
