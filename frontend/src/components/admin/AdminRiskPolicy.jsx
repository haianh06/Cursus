import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, GitCompareArrows, History, RotateCcw } from 'lucide-react';
import ConfirmDialog from '../shared/ConfirmDialog';
import Button from '../shared/Button';
import { useLanguage } from '../../context/LanguageContext';
import {
  getRiskPolicy,
  getRiskPolicyHistory,
  previewRiskPolicy,
  publishRiskPolicy,
  rollbackRiskPolicy,
} from '../../lib/api';

/** Same 6 signals/order as src/services/ai/risk_engine.py RULE_CATALOG.
 * hasThreshold=false for INACTIVE_7_DAYS and SELF_REPORTED_HIGH_STRESS —
 * neither has a tunable comparison value of its own (the first is tied to
 * the fixed 7-day assessment window, the second is a plain equality check
 * on a fixed reflection answer code), only a weight — see risk_engine.py's
 * DEFAULT_SIGNAL_THRESHOLDS comment. */
const SIGNALS = [
  { code: 'OVERDUE_TASKS_2_PLUS', hasThreshold: true, thresholdStep: 1, thresholdMin: 1, thresholdMax: 10 },
  { code: 'COMPLETION_BELOW_40', hasThreshold: true, thresholdStep: 0.05, thresholdMin: 0.05, thresholdMax: 0.95 },
  { code: 'TASK_DEFERRED_2_PLUS', hasThreshold: true, thresholdStep: 1, thresholdMin: 1, thresholdMax: 10 },
  { code: 'DUE_WITHIN_48H_NOT_STARTED', hasThreshold: true, thresholdStep: 1, thresholdMin: 1, thresholdMax: 168 },
  { code: 'INACTIVE_7_DAYS', hasThreshold: false },
  { code: 'SELF_REPORTED_HIGH_STRESS', hasThreshold: false },
];

function toFormState(policy) {
  return {
    signalWeights: { ...policy.signalWeights },
    signalThresholds: { ...policy.signalThresholds },
    watchThreshold: policy.severityBands[1][0],
    needsSupportThreshold: policy.severityBands[2][0],
    reason: '',
  };
}

function toPayload(form) {
  return {
    signalWeights: Object.fromEntries(Object.entries(form.signalWeights).map(([k, v]) => [k, Number(v)])),
    signalThresholds: Object.fromEntries(Object.entries(form.signalThresholds).map(([k, v]) => [k, Number(v)])),
    severityBands: [
      [0, 'normal', 'LOW'],
      [Number(form.watchThreshold), 'watch', 'MEDIUM'],
      [Number(form.needsSupportThreshold), 'needs_support', 'HIGH'],
    ],
  };
}

export default function AdminRiskPolicy() {
  const { t, lang } = useLanguage();
  const [current, setCurrent] = useState(null);
  const [history, setHistory] = useState([]);
  const [form, setForm] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [confirmRollback, setConfirmRollback] = useState(null); // version string or null

  const load = useCallback(() => {
    setError('');
    return Promise.all([getRiskPolicy(), getRiskPolicyHistory()])
      .then(([policy, historyRows]) => {
        setCurrent(policy);
        setHistory(historyRows);
        setForm(toFormState(policy));
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function updateWeight(code, value) {
    setForm((old) => ({ ...old, signalWeights: { ...old.signalWeights, [code]: value } }));
    setPreview(null);
  }

  function updateThreshold(code, value) {
    setForm((old) => ({ ...old, signalThresholds: { ...old.signalThresholds, [code]: value } }));
    setPreview(null);
  }

  function updateBand(key, value) {
    setForm((old) => ({ ...old, [key]: value }));
    setPreview(null);
  }

  const reasonValid = Boolean(form && form.reason.trim().length > 0);
  const bandsValid = Boolean(
    form &&
      Number(form.watchThreshold) >= 1 &&
      Number(form.watchThreshold) < Number(form.needsSupportThreshold) &&
      Number(form.needsSupportThreshold) <= 20,
  );

  function runPreview() {
    setBusy('preview');
    setError('');
    previewRiskPolicy(toPayload(form))
      .then(setPreview)
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  function publish() {
    setBusy('publish');
    setError('');
    publishRiskPolicy({ ...toPayload(form), reason: form.reason.trim() })
      .then(() => {
        setPreview(null);
        return load();
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  function rollback() {
    if (!confirmRollback) return;
    const version = confirmRollback;
    setBusy(`rollback-${version}`);
    setError('');
    rollbackRiskPolicy(version, form.reason.trim() || t('admin.policyRollbackDefaultReason').replace('{version}', version))
      .then(() => {
        setPreview(null);
        setConfirmRollback(null);
        return load();
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  if (!form || !current) {
    return (
      <section className="card p-5 text-xs text-fg-muted">
        {error ? <span className="text-danger">{error}</span> : t('admin.loading')}
      </section>
    );
  }

  return (
    <section className="card p-5 sm:p-6 space-y-5 text-left border-t-2 sm:border-t-[3px]" style={{ borderTopColor: 'var(--gold)' }} aria-labelledby="risk-policy-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <GitCompareArrows size={18} className="text-gold" />
          <h2 id="risk-policy-title" className="text-sm font-bold text-fg">{t('admin.policyTitle')}</h2>
        </div>
        <span className="mono rounded-full bg-gold-soft px-3 py-1 text-xs font-bold text-gold border border-gold/20 shadow-sm">
          {t('admin.policyCurrentVersion')}: {current.policyVersion ?? t('admin.policyNoneYet')}
        </span>
      </div>
      <p className="text-xs leading-relaxed text-fg-secondary">{current.reason}</p>

      {error && (
        <p className="flex items-center gap-2 text-xs text-danger" role="alert">
          <AlertCircle size={14} className="shrink-0" />{error}
        </p>
      )}

      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th scope="col">{t('admin.policyColSignal')}</th>
              <th scope="col">{t('admin.policyColWeight')}</th>
              <th scope="col">{t('admin.policyColThreshold')}</th>
            </tr>
          </thead>
          <tbody>
            {SIGNALS.map(({ code, hasThreshold, thresholdStep, thresholdMin, thresholdMax }) => (
              <tr key={code}>
                <td className="font-semibold text-fg">{t(`admin.signal_${code}`)}</td>
                <td>
                  <input
                    type="number" step={0.5} min={0} max={5}
                    value={form.signalWeights[code]}
                    onChange={(e) => updateWeight(code, e.target.value)}
                    className="input mono text-xs w-20 transition-all focus:ring-2 focus:ring-accent/20 focus:border-accent"
                  />
                </td>
                <td>
                  {hasThreshold ? (
                    <input
                      type="number" step={thresholdStep} min={thresholdMin} max={thresholdMax}
                      value={form.signalThresholds[code]}
                      onChange={(e) => updateThreshold(code, e.target.value)}
                      className="input mono text-xs w-24 transition-all focus:ring-2 focus:ring-accent/20 focus:border-accent"
                    />
                  ) : (
                    <span className="text-fg-muted inline-block py-1.5 px-2 bg-surface-elevated rounded text-[11px] font-medium border border-line/50">{t('admin.policyNoThreshold')}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 mt-2">
        <label className="text-xs font-semibold text-fg group">
          {t('admin.policyWatchThreshold')}
          <input
            type="number" step={1} min={1} max={19}
            value={form.watchThreshold}
            onChange={(e) => updateBand('watchThreshold', e.target.value)}
            className="input mono text-xs mt-2 w-full transition-all focus:ring-2 focus:ring-warning/20 focus:border-warning group-hover:border-line-strong"
          />
        </label>
        <label className="text-xs font-semibold text-fg group">
          {t('admin.policyNeedsSupportThreshold')}
          <input
            type="number" step={1} min={2} max={20}
            value={form.needsSupportThreshold}
            onChange={(e) => updateBand('needsSupportThreshold', e.target.value)}
            className="input mono text-xs mt-2 w-full transition-all focus:ring-2 focus:ring-danger/20 focus:border-danger group-hover:border-line-strong"
          />
        </label>
      </div>
      {!bandsValid && (
        <p className="text-xs font-semibold text-danger" role="alert">{t('admin.policyBandsInvalid')}</p>
      )}

      <label className="block text-xs font-semibold text-fg mt-2">
        {t('admin.policyReason')}
        <textarea
          rows={2}
          value={form.reason}
          onChange={(e) => updateBand('reason', e.target.value)}
          placeholder={t('admin.policyReasonHelp')}
          className="input text-xs mt-2 w-full transition-all focus:ring-2 focus:ring-accent/20 focus:border-accent hover:border-line-strong"
        />
      </label>

      <div className="flex flex-wrap gap-3 mt-4">
        <Button
          variant="outline"
          busy={busy === 'preview'}
          disabled={!bandsValid || Boolean(busy)}
          onClick={runPreview}
          className="font-bold shadow-sm hover:shadow-md"
        >
          {busy === 'preview' ? <RotateCcw size={14} className="inline mr-2 animate-spin" /> : null}
          {busy === 'preview' ? t('admin.loading') : t('admin.policyPreview')}
        </Button>
        <Button
          variant="primary"
          busy={busy === 'publish'}
          disabled={!bandsValid || !reasonValid || !preview || Boolean(busy)}
          onClick={publish}
          className="font-bold shadow-sm hover:shadow-md"
        >
          {busy === 'publish' ? <RotateCcw size={14} className="inline mr-2 animate-spin" /> : null}
          {busy === 'publish' ? t('admin.saving') : t('admin.policyPublish')}
        </Button>
      </div>
      {!preview && bandsValid && (
        <p className="text-[11px] text-fg-muted">{t('admin.policyPreviewRequiredHint')}</p>
      )}

      {preview && (
        <div className="rounded-lg border border-line bg-surface-elevated p-4 text-xs text-fg">
          <p className="font-bold">
            {t('admin.policyAffected')}: {preview.changedCount}/{preview.totalEvaluated}
          </p>
          {preview.changes.length > 0 && (
            <ul className="mt-2 space-y-1 max-h-32 overflow-y-auto">
              {preview.changes.map((c) => (
                <li key={`${c.studentId}-${c.sectionId}`} className="mono text-[11px] text-fg-secondary">
                  {c.studentId}: {c.beforeSeverity} → {c.afterSeverity}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="space-y-3 border-t border-line/60 pt-6 mt-6">
        <h3 className="flex items-center gap-2 text-xs font-bold text-fg">
          <History size={15} className="text-fg-muted" />{t('admin.policyHistory')}
        </h3>
        {history.length === 0 && <p className="text-xs text-fg-muted">{t('admin.policyNoHistory')}</p>}
        {history.map((item) => (
          <div
            key={item.policyVersion}
            className="group flex flex-col gap-3 rounded-[var(--radius-md)] border border-line bg-surface-card hover:bg-surface-elevated hover:border-fg/20 p-4 transition-all duration-200 sm:flex-row sm:items-center sm:justify-between shadow-sm hover:shadow-md"
          >
            <div className="min-w-0">
              <p className="mono text-xs font-bold text-fg">
                v{item.policyVersion}
                {item.policyVersion === current.policyVersion ? (
                  <span className="ml-2 inline-block rounded-md bg-accent-soft px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-accent-text-safe">{t('admin.policyActiveTag')}</span>
                ) : ''}
                {item.rolledBackFrom ? (
                  <span className="ml-2 text-[10px] text-fg-muted italic">· {t('admin.policyRolledBackFromTag').replace('{version}', item.rolledBackFrom)}</span>
                ) : ''}
              </p>
              <p className="mt-2 text-xs text-fg-secondary leading-relaxed">
                <span className="font-medium text-fg">{new Date(item.createdAt).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}</span> — {item.reason}
              </p>
            </div>
            {item.policyVersion !== current.policyVersion && (
              <Button
                variant="outline"
                size="sm"
                busy={busy === `rollback-${item.policyVersion}`}
                disabled={Boolean(busy)}
                onClick={() => setConfirmRollback(item.policyVersion)}
                className="shrink-0 gap-2 font-semibold hover:border-danger hover:text-danger"
              >
                <RotateCcw size={13} className={busy === `rollback-${item.policyVersion}` ? 'animate-spin' : ''} />
                {busy === `rollback-${item.policyVersion}` ? t('admin.saving') : t('admin.policyRollback')}
              </Button>
            )}
          </div>
        ))}
      </div>

      <ConfirmDialog
        open={!!confirmRollback}
        title={t('admin.policyRollbackConfirm').replace('{version}', confirmRollback || '')}
        message={lang === 'vi' ? 'Chính sách này sẽ được áp dụng ngay lập tức.' : 'This policy will be applied immediately.'}
        confirmLabel={t('admin.confirmBtn')}
        cancelLabel={t('admin.cancelBtn')}
        danger
        busy={busy.startsWith('rollback')}
        onConfirm={rollback}
        onCancel={() => setConfirmRollback(null)}
      />
    </section>
  );
}
