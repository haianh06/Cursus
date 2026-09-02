import React, { useCallback, useEffect, useState } from 'react';
import { BarChart3 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminAnalyticsSummary, userFacingApiError } from '../../lib/api';
import ErrorState from '../shared/ErrorState';

export default function AdminAnalytics() {
  const { t, lang } = useLanguage();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [requestVersion, setRequestVersion] = useState(0);

  const load = useCallback(async () => {
    setSummary(null);
    setError(null);
    try {
      setSummary(await getAdminAnalyticsSummary());
    } catch (err) {
      setError(userFacingApiError(err, lang));
    }
  }, [lang]);

  useEffect(() => {
    load();
  }, [load, requestVersion]);

  if (error) {
    return (
      <ErrorState
        title={t('admin.regionError')}
        description={error.message}
        onRetry={() => setRequestVersion((version) => version + 1)}
        retryLabel={t('common.retry')}
      />
    );
  }

  if (!summary) {
    return <p className="text-xs text-fg-secondary" aria-live="polite">{t('admin.loading')}</p>;
  }

  return (
    <section className="space-y-3 text-left" aria-labelledby="analytics-title">
      <div className="flex items-center gap-2">
        <BarChart3 size={16} className="text-accent" />
        <h2 id="analytics-title" className="font-display text-base font-semibold text-fg">{t('admin.analyticsTitle')}</h2>
      </div>

      <div className="flex flex-wrap items-center gap-x-8 gap-y-2 rounded-lg border border-line bg-[var(--bg-elevated)] px-4 py-3">
        <Stat label={t('admin.analyticsCourses')} value={`${summary.ingested_courses}/${summary.total_courses}`} />
        <Stat label={t('admin.analyticsDocuments')} value={summary.total_documents} />
        <Stat label={t('admin.analyticsChunks')} value={summary.total_chunks} />
        <Stat label={t('admin.analyticsRisk')} value={summary.at_risk_students} />
      </div>

      {summary.measurement_status === 'not_measured' && (
        <div className="rounded-lg border border-line p-4" role="status">
          <h3 className="text-sm font-bold text-fg">{t('admin.analyticsNotMeasuredTitle')}</h3>
          <p className="mt-1 text-xs leading-relaxed text-fg-secondary">
            {t('admin.analyticsNotMeasuredDescription')}
          </p>
        </div>
      )}

      <p className="text-xs leading-relaxed text-fg-secondary">
        <strong className="text-fg">{t('admin.methodNoteLabel')}:</strong> {summary.method_note}
      </p>
    </section>
  );
}

function Stat({ label, value }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="text-[11px] text-fg-secondary">{label}</span>
      <span className="mono text-lg font-bold text-fg">{value}</span>
    </div>
  );
}
