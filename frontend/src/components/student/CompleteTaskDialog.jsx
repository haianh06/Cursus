import React, { useEffect, useRef, useState } from 'react';
import { CheckCircle2, X } from 'lucide-react';

/**
 * mục 13.2: "Khi bấm Hoàn thành, hiện modal hỏi 'Bạn học khoảng bao lâu?'
 * với giá trị gợi ý mặc định = estimate ban đầu, sinh viên tự chỉnh tay nếu
 * khác." No auto-running wall-clock timer (students close the tab mid-task,
 * that would badly skew actual_minutes) -- self-reported, defaulted to the
 * estimate, editable. Same dialog chrome/focus-trap pattern as
 * DeferTaskDialog.jsx.
 */
export default function CompleteTaskDialog({ task, onCancel, onConfirm, busy, lang = 'vi' }) {
  const [minutes, setMinutes] = useState('');
  const panelRef = useRef(null);
  const firstRef = useRef(null);
  const restoreRef = useRef(null);

  useEffect(() => {
    if (!task) return undefined;
    setMinutes(String(task.estimatedMinutes ?? ''));
    restoreRef.current = document.activeElement;
    const focusTimer = setTimeout(() => firstRef.current?.focus(), 0);
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
      clearTimeout(focusTimer);
      document.removeEventListener('keydown', onKeyDown);
      if (restoreRef.current instanceof HTMLElement) restoreRef.current.focus();
    };
  }, [task, onCancel]);

  if (!task) return null;

  const parsed = Number(minutes);
  const valid = minutes.trim() !== '' && Number.isFinite(parsed) && parsed >= 0;

  return (
    <>
      <div className="fixed inset-0 z-[90] bg-black/50 backdrop-blur-sm" onClick={onCancel} aria-hidden="true" />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="complete-dialog-title"
        className="fixed z-[95] left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[calc(100vw-2rem)] max-w-md rounded-2xl border shadow-panel animate-scale-in bg-surface-card border-line"
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-line">
          <div className="flex items-center gap-2 min-w-0">
            <CheckCircle2 size={16} className="text-success" />
            <h2 id="complete-dialog-title" className="font-display text-sm font-bold truncate text-fg">
              {lang === 'vi' ? 'Hoàn thành việc này' : 'Complete this task'}
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
          <p className="text-[13px] font-semibold text-fg">{task.title}</p>

          <div>
            <label htmlFor="complete-minutes" className="text-[11px] font-bold uppercase tracking-widest block mb-1.5 text-fg-muted">
              {lang === 'vi' ? 'Bạn học khoảng bao lâu? (phút)' : 'How long did you spend? (minutes)'}
            </label>
            <input
              ref={firstRef}
              id="complete-minutes"
              type="number"
              min={0}
              step={1}
              inputMode="numeric"
              className="input text-[13px] w-full"
              value={minutes}
              onChange={(event) => setMinutes(event.target.value)}
            />
            <p className="text-[11px] text-fg-muted mt-1.5">
              {lang === 'vi'
                ? `Gợi ý mặc định là thời lượng ước tính ban đầu (${task.estimatedMinutes ?? 0} phút) — sửa lại nếu bạn học lâu/nhanh hơn.`
                : `Defaults to your original estimate (${task.estimatedMinutes ?? 0} min) — adjust if it took more or less time.`}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 px-5 py-4 border-t border-line">
          <button type="button" className="btn btn-outline text-[13px] px-4 min-h-10 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-accent" onClick={onCancel}>
            {lang === 'vi' ? 'Hủy' : 'Cancel'}
          </button>
          <button
            type="button"
            className="btn btn-accent text-[13px] px-4 min-h-10 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed outline-none focus-visible:ring-2 focus-visible:ring-accent"
            disabled={!valid || busy}
            onClick={() => onConfirm(parsed)}
          >
            {busy
              ? lang === 'vi' ? 'Đang lưu…' : 'Saving…'
              : lang === 'vi' ? 'Xác nhận hoàn thành' : 'Confirm complete'}
          </button>
        </div>
      </div>
    </>
  );
}
