import React, { useEffect, useRef, useState } from 'react';
import { CalendarClock, X } from 'lucide-react';

/**
 * Blueprint §3.1: "Khi defer bắt buộc chọn lý do ngắn."
 *
 * The confirm button stays disabled until a reason code is chosen, and the
 * backend rejects a reason-less defer anyway — the dialog is the friendly
 * half of a rule that is enforced server-side.
 */
export default function DeferTaskDialog({ task, reasons, onCancel, onConfirm, busy, lang = 'vi' }) {
  const [reasonCode, setReasonCode] = useState('');
  const [note, setNote] = useState('');
  const panelRef = useRef(null);
  const firstRef = useRef(null);
  const restoreRef = useRef(null);

  useEffect(() => {
    if (!task) return undefined;
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
      // Keep Tab inside the dialog — same trap as SourceDrawer/AlertDrawer.
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
  }, [task, onCancel]);

  if (!task) return null;

  const list = reasons?.length
    ? reasons
    : [{ code: 'underestimated_time', label: 'Ước tính thiếu thời gian' }];

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm" onClick={onCancel} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="defer-dialog-title"
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-md rounded-2xl border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-line">
          <div className="flex items-center gap-2 min-w-0">
            <CalendarClock size={16} className="text-warning" />
            <h2
              id="defer-dialog-title"
              className="font-display text-sm font-bold truncate text-fg"
            >
              {lang === 'vi' ? 'Dời việc này' : 'Defer this task'}
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

        <div className="p-5 space-y-4 text-left">
          <p className="text-[13px] font-semibold text-fg">
            {task.title}
          </p>

          <fieldset>
            <legend className="text-[11px] font-bold uppercase tracking-widest mb-2 text-fg-muted">
              {lang === 'vi' ? 'Lý do dời (bắt buộc)' : 'Reason (required)'}
            </legend>
            <div className="space-y-1.5">
              {list.map((reason, index) => (
                <label
                  key={reason.code}
                  className={`flex items-center gap-2.5 px-3 min-h-11 rounded-xl border cursor-pointer transition-colors duration-200 focus-within:ring-2 focus-within:ring-accent ${
                    reasonCode === reason.code
                      ? 'border-accent bg-accent-soft'
                      : 'border-line bg-surface-elevated hover:border-line-strong'
                  }`}
                >
                  <input
                    ref={index === 0 ? firstRef : undefined}
                    type="radio"
                    name="defer-reason"
                    value={reason.code}
                    checked={reasonCode === reason.code}
                    onChange={() => setReasonCode(reason.code)}
                    className="accent-[var(--accent)] w-4 h-4 shrink-0 outline-none"
                  />
                  <span className="text-[13px] text-fg">
                    {reason.label}
                  </span>
                </label>
              ))}
            </div>
          </fieldset>

          <div>
            <label
              htmlFor="defer-note"
              className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted"
            >
              {lang === 'vi' ? 'Ghi chú thêm (không bắt buộc)' : 'Note (optional)'}
            </label>
            <textarea
              id="defer-note"
              rows={2}
              className="textarea text-[13px] w-full"
              maxLength={500}
              value={note}
              onChange={(event) => setNote(event.target.value)}
              placeholder={
                lang === 'vi' ? 'VD: cần hỏi nhóm trước khi làm tiếp.' : 'e.g. need to ask my group first.'
              }
            />
          </div>

          <p className="text-[11px] text-fg-muted">
            {lang === 'vi'
              ? 'Lý do này chỉ dùng để gợi ý điều chỉnh kế hoạch của bạn ở bước phản tư. Giảng viên không xem nội dung ghi chú.'
              : 'This reason only informs your own reflection. Lecturers do not see the note text.'}
          </p>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-line">
          <button type="button" className="btn btn-outline text-[13px] px-4 min-h-10 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent" onClick={onCancel}>
            {lang === 'vi' ? 'Hủy' : 'Cancel'}
          </button>
          <button
            type="button"
            className="btn btn-accent text-[13px] px-4 min-h-10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent"
            disabled={!reasonCode || busy}
            onClick={() => onConfirm(reasonCode, note.trim() || null)}
          >
            {busy
              ? lang === 'vi'
                ? 'Đang lưu…'
                : 'Saving…'
              : lang === 'vi'
                ? 'Xác nhận dời'
                : 'Confirm defer'}
          </button>
        </div>
      </div>
    </>
  );
}
