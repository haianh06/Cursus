import { useEffect, useId, useRef } from 'react';
import { X } from 'lucide-react';

/**
 * Canonical modal shell — the focus-trap/ESC/backdrop/restore-focus
 * mechanics were already proven in ConfirmDialog.jsx (itself generalized
 * from student/DeferTaskDialog.jsx); this pulls that logic out into a
 * reusable shell so every popup across the app shares one implementation
 * instead of drifting into N slightly-different hand-rolled dialogs.
 * `rounded-[var(--radius-lg)]` on purpose, not a bare `rounded-2xl` — under
 * Tailwind v4 that utility resolves to Tailwind's own built-in radius scale,
 * not this app's --radius-lg token (see index.css's own note on this), so
 * every ad hoc `rounded-2xl` modal was silently a slightly different corner
 * radius than the design system's actual --radius-lg value.
 *
 * `open` is a boolean; pass `title` for the header, `footer` for the action
 * row (typically one or two <Button>s), and normal children for the body.
 */
export default function Modal({ open, onClose, title, footer, children, lang = 'vi' }) {
  const panelRef = useRef(null);
  const firstRef = useRef(null);
  const restoreRef = useRef(null);
  const titleId = useId();

  useEffect(() => {
    if (!open) return undefined;
    restoreRef.current = document.activeElement;
    firstRef.current?.focus();
    const selector =
      'a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])';
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose?.();
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
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-md rounded-[var(--radius-lg)] border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        {title && (
          <div className="flex items-center justify-between px-5 py-4 border-b border-line">
            <h2 id={titleId} className="font-display text-sm font-bold truncate text-fg">
              {title}
            </h2>
            <button
              ref={firstRef}
              type="button"
              className="btn-ghost w-10 h-10 inline-flex items-center justify-center rounded-[var(--radius-sm)] cursor-pointer text-fg-muted hover:text-fg transition-colors outline-none focus-visible:ring-2 focus-visible:ring-accent"
              onClick={onClose}
              aria-label={lang === 'vi' ? 'Đóng' : 'Close'}
            >
              <X size={15} />
            </button>
          </div>
        )}

        <div className="p-5 text-left">{children}</div>

        {footer && <div className="flex justify-end gap-2 px-5 py-4 border-t border-line">{footer}</div>}
      </div>
    </>
  );
}
