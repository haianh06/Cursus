import React, { useMemo, useState } from 'react';
import { startOfMonday, toDateInputValue } from '../../lib/api';

const DAY_LABELS_VI = ['Th 2', 'Th 3', 'Th 4', 'Th 5', 'Th 6', 'Th 7', 'CN'];
const DAY_LABELS_EN = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

const WIDTH = 640;
const HEIGHT = 220;
const PAD_LEFT = 30;
const PAD_RIGHT = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 26;
const INNER_W = WIDTH - PAD_LEFT - PAD_RIGHT;
const INNER_H = HEIGHT - PAD_TOP - PAD_BOTTOM;

/** Buckets this week's tasks (scheduledDate = "YYYY-MM-DD") into 7 daily
 * totals of planned (estimatedMinutes) vs actual (actualMinutes) study time,
 * Monday through Sunday of the current calendar week — independent of
 * whether a plan/tasks exist, so the chart always renders 7 days at 0h. */
function buildWeekSeries(tasks, lang) {
  const labels = lang === 'vi' ? DAY_LABELS_VI : DAY_LABELS_EN;
  const monday = startOfMonday();
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday);
    d.setDate(monday.getDate() + i);
    return { key: toDateInputValue(d), label: labels[i] };
  });

  const plannedByDay = Object.fromEntries(days.map((d) => [d.key, 0]));
  const actualByDay = Object.fromEntries(days.map((d) => [d.key, 0]));
  (tasks || []).forEach((task) => {
    if (task.scheduledDate in plannedByDay) {
      plannedByDay[task.scheduledDate] += task.estimatedMinutes || 0;
    }
    if (task.scheduledDate in actualByDay) {
      actualByDay[task.scheduledDate] += task.actualMinutes || 0;
    }
  });

  return days.map((d) => ({
    label: d.label,
    planned: Math.round((plannedByDay[d.key] / 60) * 10) / 10,
    actual: Math.round((actualByDay[d.key] / 60) * 10) / 10,
  }));
}

function pointsFor(series, key, yMax) {
  return series.map((point, i) => {
    const x = PAD_LEFT + (INNER_W * i) / (series.length - 1);
    const y = PAD_TOP + INNER_H * (1 - point[key] / yMax);
    return { x, y, value: point[key] };
  });
}

function toPath(points) {
  return points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
}

export default function WeeklyStudyHoursChart({ tasks, lang }) {
  const [hoverIndex, setHoverIndex] = useState(null);
  const series = useMemo(() => buildWeekSeries(tasks, lang), [tasks, lang]);

  const yMax = Math.max(2, Math.ceil(Math.max(1, ...series.flatMap((s) => [s.planned, s.actual]))));
  const gridValues = [0, yMax / 2, yMax];
  const plannedPoints = pointsFor(series, 'planned', yMax);
  const actualPoints = pointsFor(series, 'actual', yMax);
  const hovered = hoverIndex != null ? series[hoverIndex] : null;

  const t = {
    title: lang === 'vi' ? 'Giờ học mỗi ngày trong tuần' : 'Daily study hours this week',
    planned: lang === 'vi' ? 'Dự kiến' : 'Planned',
    actual: lang === 'vi' ? 'Thực tế' : 'Actual',
    hours: lang === 'vi' ? 'giờ' : 'h',
  };

  return (
    <div className="card p-4">
      <div className="flex items-center gap-4 mb-3 text-[12px]">
        <span className="flex items-center gap-1.5 text-fg-muted">
          <span
            className="inline-block w-3 h-0 border-t-2 border-dashed"
            style={{ borderColor: 'var(--text-muted)' }}
            aria-hidden="true"
          />
          {t.planned}
        </span>
        <span className="flex items-center gap-1.5 text-fg-muted">
          <span
            className="inline-block w-3 h-0.5 rounded-full"
            style={{ background: 'var(--accent)' }}
            aria-hidden="true"
          />
          {t.actual}
        </span>
      </div>

      <div className="relative">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          className="w-full h-auto"
          role="img"
          aria-label={t.title}
        >
          {gridValues.map((v) => {
            const y = PAD_TOP + INNER_H * (1 - v / yMax);
            return (
              <g key={v}>
                <line
                  x1={PAD_LEFT}
                  x2={WIDTH - PAD_RIGHT}
                  y1={y}
                  y2={y}
                  stroke="var(--border-ui)"
                  strokeWidth="1"
                />
                <text x={PAD_LEFT - 6} y={y + 3} textAnchor="end" fontSize="9" fill="var(--text-muted)">
                  {v}
                </text>
              </g>
            );
          })}

          {series.map((point, i) => (
            <text
              key={point.label}
              x={PAD_LEFT + (INNER_W * i) / (series.length - 1)}
              y={HEIGHT - 8}
              textAnchor="middle"
              fontSize="10"
              fill="var(--text-muted)"
            >
              {point.label}
            </text>
          ))}

          <path d={toPath(plannedPoints)} fill="none" stroke="var(--text-muted)" strokeWidth="2" strokeDasharray="4 3" strokeLinecap="round" />
          <path d={toPath(actualPoints)} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

          {plannedPoints.map((p, i) => (
            <circle key={`planned-${i}`} cx={p.x} cy={p.y} r="3" fill="var(--bg-card)" stroke="var(--text-muted)" strokeWidth="1.5" />
          ))}
          {actualPoints.map((p, i) => (
            <circle key={`actual-${i}`} cx={p.x} cy={p.y} r="3.5" fill="var(--accent)" />
          ))}

          {series.map((_, i) => {
            const x = PAD_LEFT + (INNER_W * i) / (series.length - 1);
            const colW = INNER_W / series.length;
            return (
              <rect
                key={`hit-${i}`}
                x={x - colW / 2}
                y={PAD_TOP}
                width={colW}
                height={INNER_H}
                fill="transparent"
                tabIndex={0}
                role="button"
                aria-label={`${series[i].label}: ${t.planned} ${series[i].planned}${t.hours}, ${t.actual} ${series[i].actual}${t.hours}`}
                onMouseEnter={() => setHoverIndex(i)}
                onFocus={() => setHoverIndex(i)}
                onMouseLeave={() => setHoverIndex(null)}
                onBlur={() => setHoverIndex(null)}
                className="outline-none focus-visible:fill-accent-soft"
              />
            );
          })}
        </svg>

        {hovered && (
          <div
            className="absolute top-1 pointer-events-none rounded-lg border border-line bg-surface-card px-2.5 py-1.5 text-[11px] shadow-sm whitespace-nowrap"
            style={{
              left: `${(hoverIndex / (series.length - 1)) * 100}%`,
              transform: hoverIndex === 0 ? 'translateX(0)' : hoverIndex === series.length - 1 ? 'translateX(-100%)' : 'translateX(-50%)',
            }}
          >
            <div className="font-semibold text-fg mb-0.5">{hovered.label}</div>
            <div className="text-fg-muted">{t.planned}: {hovered.planned}{t.hours}</div>
            <div className="text-fg-muted">{t.actual}: {hovered.actual}{t.hours}</div>
          </div>
        )}
      </div>

      <table className="sr-only">
        <caption>{t.title}</caption>
        <thead>
          <tr>
            <th scope="col">{lang === 'vi' ? 'Ngày' : 'Day'}</th>
            <th scope="col">{t.planned}</th>
            <th scope="col">{t.actual}</th>
          </tr>
        </thead>
        <tbody>
          {series.map((point) => (
            <tr key={point.label}>
              <th scope="row">{point.label}</th>
              <td>{point.planned}{t.hours}</td>
              <td>{point.actual}{t.hours}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
