import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, CheckCircle2, Settings } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminSettings, updateAdminSettings } from '../../lib/api';

/** mục 6.5 "Cấu hình" — bật/tắt chế độ demo, bật/tắt tự động cảnh báo nguy
 * cơ, học kỳ mặc định. Backend (`/admin/settings`) đã xong từ trước; tab
 * này trước 22/08 hoàn toàn không tồn tại ở frontend dù mục 6.5 liệt kê
 * như đã có (đọc chi tiết ở docs/AUDIT_0_HIENTRANG.md mục 4.6). */
export default function AdminSettingsPanel() {
  const { t } = useLanguage();
  const [settings, setSettings] = useState(null);
  const [draftSemester, setDraftSemester] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const load = useCallback(() => {
    setError('');
    return getAdminSettings()
      .then((data) => {
        setSettings(data);
        setDraftSemester(data.defaultSemester);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function toggle(field) {
    setBusy(true);
    setError('');
    setSaved(false);
    updateAdminSettings({ [field]: !settings[field] })
      .then((data) => {
        setSettings(data);
        setSaved(true);
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  }

  function saveSemester(event) {
    event.preventDefault();
    if (!draftSemester.trim() || draftSemester === settings.defaultSemester) return;
    setBusy(true);
    setError('');
    setSaved(false);
    updateAdminSettings({ defaultSemester: draftSemester.trim() })
      .then((data) => {
        setSettings(data);
        setSaved(true);
      })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false));
  }

  if (loading) {
    return <p className="text-xs text-fg-muted">{t('admin.loading')}</p>;
  }

  return (
    <section className="card p-5 sm:p-6 space-y-5 text-left border-t-2 sm:border-t-[3px]" style={{ borderTopColor: 'var(--accent)' }} aria-labelledby="admin-settings-title">
      <div className="flex items-center gap-2 mb-1.5">
        <Settings size={18} className="text-accent" />
        <h2 id="admin-settings-title" className="text-sm font-bold text-fg">{t('admin.settingsTitle')}</h2>
      </div>

      {error && (
        <p className="flex items-center gap-2 text-xs text-danger" role="alert">
          <AlertCircle size={14} className="shrink-0" />{error}
        </p>
      )}
      {saved && !error && (
        <p className="flex items-center gap-2 text-xs text-success">
          <CheckCircle2 size={14} className="shrink-0" />{t('admin.settingsSaved')}
        </p>
      )}

      <div className="space-y-3">
        <label className="flex items-center justify-between gap-4 rounded-xl border border-line bg-surface-card p-4">
          <div className="min-w-0">
            <p className="text-xs font-bold text-fg">{t('admin.demoModeLabel')}</p>
            <p className="mt-1 text-[11px] text-fg-secondary leading-relaxed">{t('admin.demoModeDesc')}</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={settings.demoModeEnabled}
            disabled={busy}
            onClick={() => toggle('demoModeEnabled')}
            className={`shrink-0 relative h-6 w-11 rounded-full transition-colors cursor-pointer disabled:opacity-60 ${settings.demoModeEnabled ? 'bg-accent' : 'bg-surface-elevated border border-line'}`}
          >
            <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${settings.demoModeEnabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
        </label>

        <label className="flex items-center justify-between gap-4 rounded-xl border border-line bg-surface-card p-4">
          <div className="min-w-0">
            <p className="text-xs font-bold text-fg">{t('admin.autoRiskAlertsLabel')}</p>
            <p className="mt-1 text-[11px] text-fg-secondary leading-relaxed">{t('admin.autoRiskAlertsDesc')}</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={settings.autoRiskAlertsEnabled}
            disabled={busy}
            onClick={() => toggle('autoRiskAlertsEnabled')}
            className={`shrink-0 relative h-6 w-11 rounded-full transition-colors cursor-pointer disabled:opacity-60 ${settings.autoRiskAlertsEnabled ? 'bg-accent' : 'bg-surface-elevated border border-line'}`}
          >
            <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform ${settings.autoRiskAlertsEnabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
          </button>
        </label>

        <form onSubmit={saveSemester} className="rounded-xl border border-line bg-surface-card p-4 space-y-2.5">
          <label htmlFor="default-semester" className="text-xs font-bold text-fg block">{t('admin.defaultSemesterLabel')}</label>
          <p className="text-[11px] text-fg-secondary leading-relaxed">{t('admin.defaultSemesterDesc')}</p>
          <div className="flex items-center gap-2 pt-1">
            <input
              id="default-semester"
              type="text"
              className="input text-xs flex-1"
              value={draftSemester}
              maxLength={50}
              onChange={(event) => setDraftSemester(event.target.value)}
            />
            <button
              type="submit"
              disabled={busy || !draftSemester.trim() || draftSemester === settings.defaultSemester}
              className="btn btn-accent text-xs px-4 py-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {busy ? t('admin.saving') : t('admin.saveBtn')}
            </button>
          </div>
        </form>
      </div>
    </section>
  );
}
