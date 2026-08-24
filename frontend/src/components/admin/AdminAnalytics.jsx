import React, { useEffect, useState } from 'react';
import { AlertCircle, BarChart3, FileText, TrendingUp, Users } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminAnalytics, getAdminKpi } from '../../lib/api';

const TREND_BAR_TRACK_PX = 96;
const MAX_WEEKS_SHOWN = 12;

function MetricCard({ icon, label, value, accent }) {
  return (
    <div className="card p-5" style={accent ? { borderTop: '3px solid var(--accent)' } : undefined}>
      <p className="mono text-[9px] font-bold uppercase tracking-widest text-fg-muted mb-2 flex items-center gap-1.5">
        {icon} {label}
      </p>
      <span
        className={`mono text-3xl font-bold ${accent ? 'text-accent-text-safe' : 'text-fg-secondary'}`}
        aria-label={`${label}: ${value}`}
      >
        {value}
      </span>
    </div>
  );
}

/** mục 6.5 expanded Analytics: grows the single with_cursus/baseline KPI
 * widget (still fetched here too, for one cohesive dashboard) into total
 * documents, system-wide at-risk student count, and a weekly risk-signal
 * trend -- GET /admin/analytics (src/api/admin.py), backed by
 * AdminReadService.get_analytics(). */
export default function AdminAnalytics() {
  const { t } = useLanguage();
  const [kpi, setKpi] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    setError('');
    Promise.all([getAdminKpi(), getAdminAnalytics()])
      .then(([kpiData, analyticsData]) => {
        setKpi(kpiData);
        setAnalytics(analyticsData);
      })
      .catch((err) => setError(err.message || String(err)));
  }, []);

  if (error) {
    return (
      <section className="card p-5 text-xs text-danger flex items-center gap-2" role="alert">
        <AlertCircle size={14} className="shrink-0" />{error}
      </section>
    );
  }
  if (!kpi || !analytics) {
    return <section className="card p-5 text-xs text-fg-muted">{t('admin.loading')}</section>;
  }

  const trend = analytics.weekly_risk_trend.slice(-MAX_WEEKS_SHOWN);
  const maxCount = Math.max(1, ...trend.map((point) => point.count));

  return (
    <div className="flex flex-col gap-4 text-left">
      <h2 className="sr-only">{t('admin.analyticsTabLabel')}</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          icon={<TrendingUp size={15} className="text-gold" />}
          label={t('admin.withCursus')}
          value={`${Math.round(kpi.with_cursus_overall * 100)}%`}
          accent
        />
        <MetricCard
          icon={<TrendingUp size={15} className="text-fg-muted" />}
          label={t('admin.baseline')}
          value={`${Math.round(kpi.baseline_overall * 100)}%`}
        />
        <MetricCard
          icon={<FileText size={15} className="text-accent" />}
          label={t('admin.analyticsTotalDocuments')}
          value={analytics.total_documents}
        />
        <MetricCard
          icon={<Users size={15} className="text-danger" />}
          label={t('admin.analyticsAtRiskCount')}
          value={analytics.at_risk_student_count}
        />
      </div>

      <section className="card p-5 sm:p-6 space-y-4" aria-labelledby="analytics-trend-title">
        <h2 id="analytics-trend-title" className="text-sm font-bold text-fg flex items-center gap-2">
          <BarChart3 size={16} className="text-accent" /> {t('admin.analyticsTrendTitle')}
        </h2>
        <p className="text-[11px] text-fg-muted">{t('admin.analyticsTrendHint')}</p>
        {trend.length === 0 ? (
          <p className="text-xs text-fg-muted">{t('admin.analyticsTrendEmpty')}</p>
        ) : (
          <div className="flex items-end gap-2 overflow-x-auto">
            {trend.map((point) => (
              <div key={point.week} className="flex-1 flex flex-col items-center gap-1.5 min-w-[36px]">
                <span className="text-[10px] font-bold text-fg-secondary mono">{point.count}</span>
                <div className="w-full flex items-end" style={{ height: `${TREND_BAR_TRACK_PX}px` }}>
                  <div
                    className="w-full rounded-t-md bg-accent"
                    style={{ height: `${Math.max(4, Math.round((point.count / maxCount) * TREND_BAR_TRACK_PX))}px` }}
                    role="img"
                    aria-label={`${t('admin.analyticsTrendWeekLabel')} ${point.week}: ${point.count}`}
                  />
                </div>
                <span className="text-[9px] text-fg-muted whitespace-nowrap">
                  {t('admin.analyticsTrendWeekLabel')} {point.week}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
