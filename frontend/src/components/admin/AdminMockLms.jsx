import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, GitCompareArrows, History, RotateCcw } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import {
  getMockLmsSyncHistory,
  previewMockLmsSync,
  publishMockLmsSync,
  rollbackMockLmsSync,
} from '../../lib/api';

export default function AdminMockLms() {
  const { t, lang } = useLanguage();
  const [history, setHistory] = useState([]);
  const [preview, setPreview] = useState(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(() => {
    setError('');
    return getMockLmsSyncHistory()
      .then(setHistory)
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const current = history[0] || null;
  const reasonValid = reason.trim().length > 0;

  function runPreview() {
    setBusy('preview');
    setError('');
    previewMockLmsSync()
      .then(setPreview)
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  function publish() {
    setBusy('publish');
    setError('');
    publishMockLmsSync(reason.trim())
      .then(() => {
        setPreview(null);
        setReason('');
        return load();
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  function rollback(version) {
    if (!window.confirm(t('admin.mockLmsRollbackConfirm').replace('{version}', version))) return;
    setBusy(`rollback-${version}`);
    setError('');
    rollbackMockLmsSync(version, reason.trim() || t('admin.mockLmsRollbackDefaultReason').replace('{version}', version))
      .then(() => {
        setPreview(null);
        return load();
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(''));
  }

  return (
    <section className="card p-5 sm:p-6 space-y-5 text-left border-t-2 sm:border-t-[3px]" style={{ borderTopColor: 'var(--gold)' }} aria-labelledby="mock-lms-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <GitCompareArrows size={18} className="text-gold" />
          <h2 id="mock-lms-title" className="text-sm font-bold text-fg">{t('admin.mockLmsTitle')}</h2>
        </div>
        <span className="mono rounded-full bg-gold-soft px-3 py-1 text-xs font-bold text-gold border border-gold/20 shadow-sm">
          {t('admin.mockLmsCurrentVersion')}: {current ? `v${current.syncVersion}` : t('admin.mockLmsNoneYet')}
        </span>
      </div>
      <p className="text-xs leading-relaxed text-fg-secondary">{t('admin.mockLmsIntro')}</p>

      {error && (
        <p className="flex items-center gap-2 text-xs text-danger" role="alert">
          <AlertCircle size={14} className="shrink-0" />{error}
        </p>
      )}

      <label className="block text-xs font-semibold text-fg mt-2">
        {t('admin.mockLmsReason')}
        <textarea
          rows={2}
          value={reason}
          onChange={(e) => { setReason(e.target.value); setPreview(null); }}
          placeholder={t('admin.mockLmsReasonHelp')}
          className="input text-xs mt-2 w-full transition-all focus:ring-2 focus:ring-accent/20 focus:border-accent hover:border-line-strong"
        />
      </label>

      <div className="flex flex-wrap gap-3 mt-2">
        <button
          type="button"
          disabled={Boolean(busy)}
          onClick={runPreview}
          className="btn btn-outline min-h-10 px-5 text-xs font-bold cursor-pointer transition-all hover:bg-surface-elevated hover:text-fg disabled:opacity-40"
        >
          {busy === 'preview' ? <RotateCcw size={14} className="inline mr-2 animate-spin" /> : null}
          {busy === 'preview' ? t('admin.loading') : t('admin.mockLmsPreview')}
        </button>
        <button
          type="button"
          disabled={!reasonValid || !preview || Boolean(busy)}
          onClick={publish}
          className="btn btn-accent min-h-10 px-6 text-xs font-bold cursor-pointer transition-all shadow-sm hover:shadow-md disabled:opacity-40"
        >
          {busy === 'publish' ? <RotateCcw size={14} className="inline mr-2 animate-spin" /> : null}
          {busy === 'publish' ? t('admin.saving') : t('admin.mockLmsPublish')}
        </button>
      </div>
      {!preview && (
        <p className="text-[11px] text-fg-muted">{t('admin.mockLmsPreviewRequiredHint')}</p>
      )}

      {preview && (
        <div className="rounded-lg border border-line bg-surface-elevated p-4 text-xs text-fg">
          <p className="font-bold">
            {t('admin.mockLmsAffected')}: {t('admin.mockLmsChangeCount').replace('{changed}', preview.changedCount).replace('{total}', preview.totalEvaluated)}
          </p>
          {preview.changes.length === 0 ? (
            <p className="mt-2 text-fg-muted">{t('admin.mockLmsNoChanges')}</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-left mono text-[11px]">
                <thead>
                  <tr className="border-b border-line text-fg-muted uppercase tracking-widest text-[9px]">
                    <th className="py-1.5 pr-3">{t('admin.mockLmsColCourse')}</th>
                    <th className="py-1.5 pr-3">{t('admin.mockLmsColAssignment')}</th>
                    <th className="py-1.5 pr-3">{t('admin.mockLmsColBefore')}</th>
                    <th className="py-1.5 pr-3">{t('admin.mockLmsColAfter')}</th>
                    <th className="py-1.5">{t('admin.mockLmsColSource')}</th>
                  </tr>
                </thead>
                <tbody className="max-h-40">
                  {preview.changes.map((c) => (
                    <tr key={`${c.courseCode}-${c.assignmentId}`} className="border-b border-line/50">
                      <td className="py-1.5 pr-3 font-bold">{c.courseCode}</td>
                      <td className="py-1.5 pr-3">{c.assignmentName}</td>
                      <td className="py-1.5 pr-3 text-fg-muted">{c.before || '—'}</td>
                      <td className="py-1.5 pr-3 text-accent">{c.after}</td>
                      <td className="py-1.5 text-fg-secondary">{c.winningTierLabel}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      <div className="space-y-3 border-t border-line/60 pt-6 mt-6">
        <h3 className="flex items-center gap-2 text-xs font-bold text-fg">
          <History size={15} className="text-fg-muted" />{t('admin.mockLmsHistory')}
        </h3>
        {history.length === 0 && <p className="text-xs text-fg-muted">{t('admin.mockLmsNoHistory')}</p>}
        {history.map((item) => (
          <div
            key={item.syncVersion}
            className="group flex flex-col gap-3 rounded-xl border border-line bg-surface-card hover:bg-surface-elevated hover:border-fg/20 p-4 transition-all duration-200 sm:flex-row sm:items-center sm:justify-between shadow-sm hover:shadow-md"
          >
            <div className="min-w-0">
              <p className="mono text-xs font-bold text-fg">
                v{item.syncVersion}
                {item.syncVersion === current?.syncVersion ? (
                  <span className="ml-2 inline-block rounded-md bg-accent-soft px-1.5 py-0.5 text-[9px] uppercase tracking-wider text-accent-text-safe">{t('admin.mockLmsActiveTag')}</span>
                ) : ''}
                {item.rolledBackFrom ? (
                  <span className="ml-2 text-[10px] text-fg-muted italic">· {t('admin.mockLmsRolledBackFromTag').replace('{version}', item.rolledBackFrom)}</span>
                ) : ''}
              </p>
              <p className="mt-2 text-xs text-fg-secondary leading-relaxed">
                <span className="font-medium text-fg">{new Date(item.createdAt).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US')}</span> — {item.reason} ({item.payload.length})
              </p>
            </div>
            {item.syncVersion !== current?.syncVersion && (
              <button
                type="button"
                disabled={Boolean(busy)}
                onClick={() => rollback(item.syncVersion)}
                className="btn btn-outline flex min-h-9 shrink-0 items-center justify-center gap-2 px-4 text-xs font-semibold cursor-pointer transition-all hover:border-danger hover:text-danger disabled:opacity-40"
              >
                <RotateCcw size={13} className={busy === `rollback-${item.syncVersion}` ? 'animate-spin' : ''} />
                {busy === `rollback-${item.syncVersion}` ? t('admin.saving') : t('admin.mockLmsRollback')}
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
