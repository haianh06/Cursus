import React, { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Coins } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getAdminAiUsage, userFacingApiError } from '../../lib/api';

const WINDOWS = [7, 30, 90];

/** `null` means "not enough data to compute", which is different from `0`.
 * Rendering a dash keeps that distinction visible instead of asserting a zero
 * nobody measured -- same rule the backend follows in ai_usage_service._rate. */
function orDash(value, format) {
  return value === null || value === undefined ? '—' : format(value);
}

const formatInt = (value) => value.toLocaleString();
const formatMs = (value) => `${value.toLocaleString()} ms`;
const formatPercent = (value) => `${(value * 100).toFixed(1)}%`;
/** Costs land far below a cent per call, so two decimals would show $0.00 for
 * everything. Four keeps small numbers readable without implying precision the
 * estimate does not have. */
const formatUsd = (value) => `$${value.toFixed(4)}`;

/** Cost per day as plain inline SVG -- no charting library, because the repo
 * has none and one panel does not justify adding a dependency.
 *
 * Bars rather than a line: with a single day of data a line renders as one
 * unconnected dot and reads as broken, while one bar reads correctly. The
 * series always carries every day in the window, empty ones included, so a
 * three-day gap looks like a gap instead of collapsing shut. */
function DailyCostChart({ series, label, emptyLabel, formatUsd, formatInt }) {
  const values = series.map((row) => row.est_cost_usd ?? 0);
  const peak = Math.max(...values, 0);
  if (peak <= 0) {
    return (
      <p className="rounded-lg border border-line px-4 py-3 text-xs text-fg-muted" role="status">
        {emptyLabel}
      </p>
    );
  }

  const width = 720;
  const height = 120;
  const gap = series.length > 45 ? 1 : 2;
  const slot = width / series.length;
  const barWidth = Math.max(slot - gap, 1);

  return (
    <figure className="rounded-lg border border-line px-4 py-3">
      <figcaption className="mb-2 text-xs text-fg-muted">{label}</figcaption>
      <div className="overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-28 w-full min-w-[320px]"
          role="img"
          aria-label={label}
          preserveAspectRatio="none"
        >
          {series.map((row, index) => {
            const value = row.est_cost_usd ?? 0;
            // Một ngày có gọi nhưng chi phí cực nhỏ vẫn phải nhìn thấy được,
            // nếu không thì "có dùng" và "không dùng" trông giống hệt nhau.
            const barHeight = value > 0 ? Math.max((value / peak) * (height - 8), 2) : 0;
            return (
              <rect
                key={row.date}
                x={index * slot}
                y={height - barHeight}
                width={barWidth}
                height={barHeight}
                className="fill-[var(--accent)]"
              >
                <title>{`${row.date} — ${formatUsd(value)} · ${formatInt(row.calls)}`}</title>
              </rect>
            );
          })}
        </svg>
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-fg-muted">
        <span>{series[0]?.date}</span>
        <span>{formatUsd(peak)}</span>
        <span>{series[series.length - 1]?.date}</span>
      </div>
    </figure>
  );
}

function Stat({ label, value }) {
  return (
    <div className="text-left">
      <p className="text-xs text-fg-muted">{label}</p>
      <p className="font-display text-lg font-semibold text-fg">{value}</p>
    </div>
  );
}

export default function AdminAiUsage() {
  const { t, lang } = useLanguage();
  const [days, setDays] = useState(30);
  const [report, setReport] = useState(null);
  const [error, setError] = useState(null);
  const [requestVersion, setRequestVersion] = useState(0);

  const load = useCallback(async () => {
    setReport(null);
    setError(null);
    try {
      setReport(await getAdminAiUsage(days));
    } catch (err) {
      setError(userFacingApiError(err, lang));
    }
  }, [days, lang]);

  useEffect(() => {
    load();
  }, [load, requestVersion]);

  if (error) {
    return (
      <div className="flex flex-wrap items-center gap-3 text-xs text-danger" role="alert">
        <span className="flex items-center gap-2"><AlertCircle size={14} />{error.message}</span>
        <button
          type="button"
          onClick={() => setRequestVersion((version) => version + 1)}
          className="min-h-11 rounded-lg border border-line px-3 font-semibold text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {t('common.retry')}
        </button>
      </div>
    );
  }

  if (!report) {
    return <p className="text-xs text-fg-secondary" aria-live="polite">{t('admin.loading')}</p>;
  }

  const { totals } = report;

  return (
    <section className="space-y-3 text-left" aria-labelledby="ai-usage-title">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Coins size={16} className="text-accent" />
          <h2 id="ai-usage-title" className="font-display text-base font-semibold text-fg">
            {t('admin.aiUsageTitle')}
          </h2>
        </div>
        <div className="flex gap-1" role="group" aria-label={t('admin.aiUsageTitle')}>
          {WINDOWS.map((window) => (
            <button
              key={window}
              type="button"
              onClick={() => setDays(window)}
              aria-pressed={days === window}
              className={`min-h-11 rounded-lg border px-3 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                days === window
                  ? 'border-accent text-accent'
                  : 'border-line text-fg-secondary'
              }`}
            >
              {t(`admin.aiUsageWindow${window}`)}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-8 gap-y-2 rounded-lg border border-line bg-[var(--bg-elevated)] px-4 py-3">
        <Stat label={t('admin.aiUsageTotalCalls')} value={formatInt(totals.calls)} />
        <Stat
          label={t('admin.aiUsageTotalCost')}
          value={orDash(totals.est_cost_usd, formatUsd)}
        />
        <Stat
          label={t('admin.aiUsageAvgLatency')}
          value={orDash(totals.avg_latency_ms, formatMs)}
        />
        <Stat
          label={t('admin.aiUsageErrorRate')}
          value={orDash(totals.error_rate, formatPercent)}
        />
      </div>

      <DailyCostChart
        series={report.by_day || []}
        label={t('admin.aiUsageChartLabel')}
        emptyLabel={t('admin.aiUsageChartEmpty')}
        formatUsd={formatUsd}
        formatInt={(n) => t('admin.aiUsageChartCalls').replace('{count}', formatInt(n))}
      />

      {report.by_feature.length === 0 ? (
        <p className="rounded-lg border border-line p-4 text-xs leading-relaxed text-fg-secondary" role="status">
          {t('admin.aiUsageEmpty')}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-line">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-line text-fg-muted">
                <th scope="col" className="px-3 py-2 text-left font-semibold">{t('admin.aiUsageColFeature')}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{t('admin.aiUsageColCalls')}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{t('admin.aiUsageColInput')}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{t('admin.aiUsageColOutput')}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{t('admin.aiUsageColLatency')}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{t('admin.aiUsageColErrors')}</th>
                <th scope="col" className="px-3 py-2 text-right font-semibold">{t('admin.aiUsageColCost')}</th>
              </tr>
            </thead>
            <tbody>
              {report.by_feature.map((row) => (
                <tr key={row.feature} className="border-b border-line last:border-b-0">
                  <th scope="row" className="px-3 py-2 text-left font-medium text-fg">
                    {row.feature}
                    <span className="block text-[11px] font-normal text-fg-muted">
                      {row.models.join(', ')}
                    </span>
                  </th>
                  <td className="px-3 py-2 text-right text-fg-secondary">{formatInt(row.calls)}</td>
                  <td className="px-3 py-2 text-right text-fg-secondary">{formatInt(row.input_tokens)}</td>
                  <td className="px-3 py-2 text-right text-fg-secondary">{formatInt(row.output_tokens)}</td>
                  <td className="px-3 py-2 text-right text-fg-secondary">{orDash(row.avg_latency_ms, formatMs)}</td>
                  <td className="px-3 py-2 text-right text-fg-secondary">{orDash(row.error_rate, formatPercent)}</td>
                  <td className="px-3 py-2 text-right text-fg-secondary">
                    {row.est_cost_usd === null
                      ? <span className="text-fg-muted">{t('admin.aiUsageNoPrice')}</span>
                      : formatUsd(row.est_cost_usd)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {report.unattributed_calls > 0 && (
        <p className="text-xs text-fg-muted" role="status">
          {t('admin.aiUsageUnattributed').replace('{count}', formatInt(report.unattributed_calls))}
        </p>
      )}

      <p className="text-xs leading-relaxed text-fg-secondary">
        <strong className="text-fg">{t('admin.methodNoteLabel')}:</strong> {report.method_note}{' '}
        {report.pricing.as_of
          ? t('admin.aiUsagePricingAsOf').replace('{date}', report.pricing.as_of)
          : t('admin.aiUsageNoPricingConfigured')}
      </p>
    </section>
  );
}
