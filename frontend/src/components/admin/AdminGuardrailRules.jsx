import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, Lock, RotateCcw, ShieldCheck } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getGuardrailRules, restoreGuardrailDefaults, setGuardrailRuleEnabled } from '../../lib/api';
import ConfirmDialog from '../shared/ConfirmDialog';

/** mục 6.5 "Chính sách AI" — danh sách rule/pattern guardrail, bật/tắt qua UI.
 * Không sửa được nội dung pattern/regex ở đây (đúng spec — sửa pattern vẫn
 * phải qua code). Backend hiện tại (`/admin/guardrail-rules`) không yêu cầu
 * lý do khi toggle — khác bản tham khảo origin/main, không thêm field đó vào
 * đây vì API thật không nhận nó. */
export default function AdminGuardrailRules() {
  const { t, lang } = useLanguage();
  const [rules, setRules] = useState([]);
  const [anyDisabled, setAnyDisabled] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [confirmRestore, setConfirmRestore] = useState(false);
  const [confirmToggle, setConfirmToggle] = useState(null); // { rule, reason }

  const load = useCallback(() => {
    setError('');
    return getGuardrailRules()
      .then((data) => {
        setRules(data.rules);
        setAnyDisabled(data.any_disabled);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function executeToggle() {
    if (!confirmToggle) return;
    const { rule, reason } = confirmToggle;
    if (reason.trim().length < 5) {
      alert(lang === 'vi' ? 'Lý do phải dài ít nhất 5 ký tự.' : 'Reason must be at least 5 characters.');
      return;
    }
    
    setConfirmToggle(null);
    setBusy(rule.code);
    setError('');
    setGuardrailRuleEnabled(rule.code, !rule.enabled, reason)
      .then((data) => setAnyDisabled(data.any_disabled))
      .then(load)
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  function toggle(rule) {
    if (rule.core_locked && rule.enabled) return;
    setConfirmToggle({ rule, reason: '' });
  }

  function restore() {
    setBusy('ALL');
    setError('');
    restoreGuardrailDefaults()
      .then(load)
      .catch((err) => setError(err.message))
      .finally(() => {
        setBusy('');
        setConfirmRestore(false);
      });
  }

  return (
    <section className="card p-5 sm:p-6 space-y-5 text-left border-t-2 sm:border-t-[3px]" style={{ borderTopColor: 'var(--accent)' }} aria-labelledby="guardrail-title">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <ShieldCheck size={18} className="text-accent" />
            <h2 id="guardrail-title" className="text-sm font-bold text-fg">{t('admin.guardrailTitle')}</h2>
          </div>
          <p className="text-xs leading-relaxed text-fg-secondary">{t('admin.guardrailPatternNote')}</p>
        </div>
        <button
          type="button"
          disabled={Boolean(busy) || isLoading}
          onClick={() => setConfirmRestore(true)}
          className="btn btn-outline flex shrink-0 min-h-9 items-center justify-center gap-2 px-3 text-xs font-semibold cursor-pointer transition-all hover:bg-surface-elevated hover:border-accent/40 disabled:opacity-60"
        >
          <RotateCcw size={14} className={busy === 'ALL' ? 'animate-spin' : ''} />
          {busy === 'ALL' ? t('admin.saving') : t('admin.guardrailRestore')}
        </button>
      </div>

      {anyDisabled && (
        <p className="flex items-center gap-2 rounded-lg border border-warning/40 bg-warning-soft p-3 text-xs text-fg">
          <AlertTriangle size={15} className="text-warning shrink-0" />{t('admin.guardrailDisabledWarning')}
        </p>
      )}
      {error && (
        <p className="flex items-center gap-2 text-xs text-danger" role="alert">
          <AlertCircle size={14} className="shrink-0" />{error}
        </p>
      )}

      {isLoading ? (
        <p className="text-xs text-fg-muted">{t('admin.loading')}</p>
      ) : (
        <ul className="space-y-3 mt-4">
          {rules.map((rule) => (
            <li
              key={rule.code}
              className="group flex flex-col gap-3 rounded-xl border border-line bg-surface-card hover:bg-surface-elevated hover:border-accent/30 p-4 transition-all duration-200 sm:flex-row sm:items-start sm:justify-between"
            >
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-xs font-bold text-fg group-hover:text-accent transition-colors">
                  {rule.name}
                  {rule.core_locked && (
                    <Lock size={11} className="text-fg-muted shrink-0" aria-hidden="true" />
                  )}
                </p>
                <p className="mt-1.5 text-xs leading-relaxed text-fg-secondary">{rule.description}</p>
                <p className="mono mt-2.5 inline-block rounded-md bg-surface-elevated px-2 py-1 text-[10px] font-medium text-fg-muted border border-line/50">
                  {t('admin.guardrailPatternCount').replace('{count}', rule.pattern_count)}
                </p>
                {rule.core_locked && (
                  <p className="mt-1.5 flex items-center gap-1 text-[10px] font-medium text-fg-muted">
                    <Lock size={10} className="shrink-0" aria-hidden="true" />
                    {t('admin.guardrailCoreLocked')}
                  </p>
                )}
              </div>
              <button
                type="button"
                disabled={Boolean(busy) || (rule.core_locked && rule.enabled)}
                onClick={() => toggle(rule)}
                title={rule.core_locked && rule.enabled ? t('admin.guardrailCoreLocked') : undefined}
                className={`btn shrink-0 min-h-9 px-4 text-xs font-bold cursor-pointer transition-all duration-200 disabled:opacity-60 disabled:cursor-not-allowed ${
                  rule.enabled
                    ? 'bg-success-soft text-success border border-success/30 hover:bg-success hover:text-white'
                    : 'btn-outline hover:border-fg hover:text-fg'
                }`}
              >
                {busy === rule.code ? t('admin.saving') : rule.enabled ? t('admin.guardrailOn') : t('admin.guardrailOff')}
              </button>
            </li>
          ))}
        </ul>
      )}

      <ConfirmDialog
        open={confirmRestore}
        lang={lang}
        danger
        busy={busy === 'ALL'}
        title={lang === 'vi' ? 'Khôi phục rule guardrail về mặc định?' : 'Restore guardrail rules to defaults?'}
        message={
          lang === 'vi'
            ? 'Mọi tuỳ chỉnh bật/tắt rule hiện tại sẽ mất.'
            : 'All current rule on/off customizations will be lost.'
        }
        confirmLabel={lang === 'vi' ? 'Khôi phục mặc định' : 'Restore defaults'}
        onCancel={() => setConfirmRestore(false)}
        onConfirm={restore}
      />

      <ConfirmDialog
        open={!!confirmToggle}
        title={lang === 'vi' ? (confirmToggle?.rule?.enabled ? 'Tắt quy tắc này?' : 'Bật quy tắc này?') : (confirmToggle?.rule?.enabled ? 'Disable rule?' : 'Enable rule?')}
        message={lang === 'vi' ? 'Hành động này sẽ được ghi vào nhật ký hệ thống.' : 'This action will be recorded in the system audit log.'}
        confirmLabel={t('admin.confirmBtn')}
        cancelLabel={t('admin.cancelBtn')}
        danger={confirmToggle?.rule?.enabled}
        onConfirm={executeToggle}
        onCancel={() => setConfirmToggle(null)}
      >
        {confirmToggle && (
          <div className="mt-2">
            <label className="block text-xs font-bold text-fg-secondary mb-1">
              {lang === 'vi' ? 'Lý do thay đổi' : 'Reason for change'} <span className="text-danger">*</span>
            </label>
            <textarea
              className="input text-xs w-full resize-none h-20"
              placeholder={lang === 'vi' ? 'Nhập lý do (ít nhất 5 ký tự)...' : 'Enter reason (min 5 chars)...'}
              value={confirmToggle.reason}
              onChange={(e) => setConfirmToggle(prev => ({ ...prev, reason: e.target.value }))}
              autoFocus
            />
          </div>
        )}
      </ConfirmDialog>
    </section>
  );
}
