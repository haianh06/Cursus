import { AlertTriangle } from 'lucide-react';
import Button from './Button';
import Modal from './Modal';

/**
 * Shared confirm-before-destroy dialog — built on the generic `Modal` shell
 * (focus-trap/ESC/backdrop/restore-focus), so every "not undoable" action
 * across the app (Lecturer intervene/publish/guardrail decisions, Admin
 * delete/restore) goes through one dialog implementation instead of N
 * ad-hoc `window.confirm()` calls or N bespoke modals. Only uses existing
 * tokens (`--color-danger`/`--color-warning`/`--color-accent`) — no new
 * color system.
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
  return (
    <Modal
      open={Boolean(open)}
      onClose={onCancel}
      lang={lang}
      title={
        <span className="inline-flex items-center gap-2">
          <AlertTriangle size={16} className={danger ? 'text-danger' : 'text-warning'} />
          {title}
        </span>
      }
      footer={
        <>
          <Button variant="outline" onClick={onCancel}>
            {cancelLabel ?? (lang === 'vi' ? 'Huỷ' : 'Cancel')}
          </Button>
          <Button variant={danger ? 'danger' : 'primary'} busy={busy} onClick={onConfirm}>
            {busy
              ? lang === 'vi'
                ? 'Đang xử lý…'
                : 'Working…'
              : (confirmLabel ?? (lang === 'vi' ? 'Xác nhận' : 'Confirm'))}
          </Button>
        </>
      }
    >
      <p className="text-[13px] text-fg-secondary leading-relaxed mb-4">{message}</p>
      {children}
    </Modal>
  );
}
