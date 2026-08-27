import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, AlertTriangle, History, Lock, RotateCcw, ShieldCheck } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  getGuardrailPolicyHistory,
  listGuardrailRules,
  previewGuardrailRule,
  restoreGuardrailDefaults,
  rollbackGuardrailPolicy,
  setGuardrailRule,
} from '../../lib/api';
import ConfirmDialog from '../shared/ConfirmDialog';

const MIN_REASON_LENGTH = 5;

/** Guardrail policy workflow: reason → preview (read-only) → publish.
 * History is immutable; rollback creates a new policy version instead of
 * editing the old snapshot. */
export default function AdminGuardrailRules() {
  const { t, lang } = useLanguage();
  const [rules, setRules] = useState([]);
  const [history, setHistory] = useState([]);
  const [anyDisabled, setAnyDisabled] = useState(false);
  const [reason, setReason] = useState('');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [confirmRollback, setConfirmRollback] = useState(null);
  const [confirmRestore, setConfirmRestore] = useState(false);

  const load = useCallback(() => {
    setError('');
    return Promise.all([listGuardrailRules(), getGuardrailPolicyHistory()])
      .then(([data, versions]) => {
        setRules(data.rules);
        setAnyDisabled(data.any_disabled);
        setHistory(versions);
      })
      .catch((err) => setError(err.message))
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function updateReason(event) {
    setReason(event.target.value);
    setPreview(null);
  }

  function runPreview(rule) {
    if (reason.trim().length < MIN_REASON_LENGTH) {
      setError(t('admin.guardrailReasonInvalid'));
      return;
    }
    setBusy(`preview-${rule.code}`);
    setError('');
    previewGuardrailRule(rule.code, !rule.enabled, reason.trim())
      .then(setPreview)
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  function publishPreview() {
    if (!preview || reason.trim().length < MIN_REASON_LENGTH) return;
    const action = preview.proposed_enabled ? t('admin.guardrailOn') : t('admin.guardrailOff');
    if (!window.confirm(t('admin.guardrailPublishConfirm').replace('{action}', action))) return;
    setBusy('publish');
    setError('');
    setGuardrailRule(preview.code, preview.proposed_enabled, reason.trim())
      .then(() => {
        setPreview(null);
        return load();
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  function restore() {
    if (reason.trim().length < MIN_REASON_LENGTH) {
      setError(t('admin.guardrailReasonInvalid'));
      setConfirmRestore(false);
      return;
    }
    setBusy('restore');
    setError('');
    restoreGuardrailDefaults(reason.trim())
      .then(() => {
        setPreview(null);
        return load();
      })
      .catch((err) => setError(err.message))
      .finally(() => {
        setBusy('');
        setConfirmRestore(false);
      });
  }

  function rollback() {
    if (!confirmRollback || reason.trim().length < MIN_REASON_LENGTH) {
      setError(t('admin.guardrailReasonInvalid'));
      return;
    }
    const version = confirmRollback;
    setBusy(`rollback-${version}`);
    setError('');
    rollbackGuardrailPolicy(version, reason.trim())
      .then(() => {
        setPreview(null);
        setConfirmRollback(null);
        return load();
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  const activeVersion = history.find((item) => item.is_active)?.version || rules[0]?.current_version;
  const reasonValid = reason.trim().length >= MIN_REASON_LENGTH;

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
        <span className="mono rounded-full bg-accent-soft px-3 py-1 text-[11px] font-bold text-accent-text-safe border border-accent/20">
          {t('admin.guardrailCurrentVersion')}: {activeVersion || t('admin.guardrailNoneYet')}
        </span>
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

      <label className="block text-xs font-semibold text-fg">
        {t('admin.guardrailReasonLabel')}
        <textarea rows={2} value={reason} onChange={updateReason} placeholder={t('admin.guardrailReasonHelp')} className="input text-xs mt-2 w-full resize-none" />
      </label>
      {!reasonValid && reason.length > 0 && <p className="text-[11px] text-danger">{t('admin.guardrailReasonInvalid')}</p>}

      {isLoading ? (
        <p className="text-xs text-fg-muted">{t('admin.loading')}</p>
      ) : (
        <ul className="space-y-3 mt-4">
          {rules.map((rule) => (
            <li key={rule.code} className="group flex flex-col gap-3 rounded-xl border border-line bg-surface-card p-4 transition-all duration-200 sm:flex-row sm:items-start sm:justify-between hover:bg-surface-elevated hover:border-accent/30">
              <div className="min-w-0">
                <p className="flex items-center gap-1.5 text-xs font-bold text-fg">
                  {rule.name}
                  {rule.core_locked && <Lock size={11} className="text-fg-muted shrink-0" aria-hidden="true" />}
                </p>
                <p className="mt-1.5 text-xs leading-relaxed text-fg-secondary">{rule.description}</p>
                <p className="mono mt-2.5 inline-block rounded-md bg-surface-elevated px-2 py-1 text-[10px] font-medium text-fg-muted border border-line/50">
                  {t('admin.guardrailPatternCount').replace('{count}', rule.pattern_count)} · {rule.enabled ? t('admin.guardrailOn') : t('admin.guardrailOff')}
                </p>
              </div>
              <button
                type="button"
                disabled={Boolean(busy) || (rule.core_locked && rule.enabled)}
                onClick={() => runPreview(rule)}
                title={rule.core_locked && rule.enabled ? t('admin.guardrailCoreLocked') : undefined}
                className="btn btn-outline shrink-0 min-h-9 px-4 text-xs font-bold cursor-pointer transition-all hover:border-accent hover:text-accent disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {busy === `preview-${rule.code}` ? <RotateCcw size={13} className="inline mr-2 animate-spin" /> : null}
                {t('admin.guardrailPreview')}
              </button>
            </li>
          ))}
        </ul>
      )}

      {preview && (
        <div className="rounded-lg border border-accent/30 bg-accent-soft p-4 text-xs text-fg space-y-2" aria-live="polite">
          <p className="font-bold">{t('admin.guardrailPreviewTitle')}: {preview.code}</p>
          <p>{preview.current_enabled ? t('admin.guardrailOn') : t('admin.guardrailOff')} → <strong>{preview.proposed_enabled ? t('admin.guardrailOn') : t('admin.guardrailOff')}</strong></p>
          <p className="text-fg-secondary">{t('admin.guardrailChangedCodes')}: {preview.changed_codes.join(', ') || t('admin.guardrailNoChanges')}</p>
          <button type="button" disabled={!reasonValid || Boolean(busy)} onClick={publishPreview} className="btn btn-accent min-h-9 px-4 text-xs font-bold disabled:opacity-40">
            {busy === 'publish' ? <RotateCcw size={13} className="inline mr-2 animate-spin" /> : null}
            {busy === 'publish' ? t('admin.saving') : t('admin.guardrailPublish')}
          </button>
        </div>
      )}

      <div className="flex justify-end border-t border-line/60 pt-5">
        <button type="button" disabled={Boolean(busy) || isLoading} onClick={() => setConfirmRestore(true)} className="btn btn-outline flex min-h-9 items-center gap-2 px-3 text-xs font-semibold disabled:opacity-60">
          <RotateCcw size={14} />{t('admin.guardrailRestore')}
        </button>
      </div>

      <div className="space-y-3 border-t border-line/60 pt-6">
        <h3 className="flex items-center gap-2 text-xs font-bold text-fg"><History size={15} className="text-fg-muted" />{t('admin.guardrailHistory')}</h3>
        {history.length === 0 && <p className="text-xs text-fg-muted">{t('admin.guardrailHistoryEmpty')}</p>}
        {history.map((item) => (
          <div key={item.version} className="flex flex-col gap-3 rounded-xl border border-line bg-surface-card p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="mono text-xs font-bold text-fg">
                {item.version}
                {item.is_active && <span className="ml-2 inline-block rounded-md bg-accent-soft px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-accent-text-safe">{t('admin.guardrailActive')}</span>}
                {item.rolled_back_from && <span className="ml-2 text-[10px] text-fg-muted">· {t('admin.guardrailRollbackFrom').replace('{version}', item.rolled_back_from)}</span>}
              </p>
              <p className="mt-1.5 text-xs text-fg-secondary">{new Date(item.created_at).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')} — {item.change_reason || '—'}</p>
            </div>
            {!item.is_active && (
              <button type="button" disabled={Boolean(busy)} onClick={() => setConfirmRollback(item.version)} className="btn btn-outline flex min-h-9 shrink-0 items-center justify-center gap-2 px-4 text-xs font-semibold hover:border-danger hover:text-danger disabled:opacity-40">
                <RotateCcw size={13} />{busy === `rollback-${item.version}` ? t('admin.saving') : t('admin.guardrailRollback')}
              </button>
            )}
          </div>
        ))}
      </div>

      <ConfirmDialog open={confirmRestore} lang={lang} danger busy={busy === 'restore'} title={t('admin.guardrailRestoreConfirm')} message={t('admin.guardrailRestoreMessage')} confirmLabel={t('admin.guardrailRestore')} onCancel={() => setConfirmRestore(false)} onConfirm={restore} />
      <ConfirmDialog open={!!confirmRollback} lang={lang} danger busy={busy.startsWith('rollback-')} title={t('admin.guardrailRollbackConfirm').replace('{version}', confirmRollback || '')} message={t('admin.guardrailRollbackMessage')} confirmLabel={t('admin.guardrailRollback')} onCancel={() => setConfirmRollback(null)} onConfirm={rollback} />
    </section>
  );
}
