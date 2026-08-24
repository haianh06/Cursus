import React from 'react';
import { safeAdminSummaryEntries } from './adminDisplay';

/**
 * A summary block renders the scalar fields the API returns for one section.
 *
 * Nested objects are skipped rather than stringified: a summary is counts and
 * timestamps by contract, so if a raw payload ever appeared in a summary
 * response this component would drop it instead of printing it on screen.
 */
export default function AdminSummaryCard({ title, data, labelFor }) {
  const entries = safeAdminSummaryEntries(data);
  if (!entries.length) return null;

  return (
    <section className="rounded-lg border border-line p-4">
      <h3 className="pb-2 font-display text-sm font-bold text-fg">{title}</h3>
      <dl className="grid grid-cols-2 gap-3 md:grid-cols-3">
        {entries.map(({ key, value }) => (
          <div key={key}>
            <dt className="text-[10px] font-bold uppercase tracking-wide text-fg-secondary">
              {labelFor?.(key)}
            </dt>
            <dd className="mono mt-1 text-sm font-semibold text-fg">
              {value === null || value === '' ? '—' : String(value)}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
