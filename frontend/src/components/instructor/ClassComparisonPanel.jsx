import React, { useCallback, useEffect, useState } from 'react';
import { Columns3 } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { getClassComparison, userFacingApiError } from '../../lib/api';

/** B3 — so sanh tat ca cac lop GV dang day cung luc, thay vi chi xem duoc 1
 *  lop/gop het tai 1 thoi diem nhu bo loc F9 tren dashboard. An han neu GV
 *  chi day dung 1 lop — "so sanh" khong co y nghia gi voi 1 dong duy nhat. */
export default function ClassComparisonPanel() {
  const { t, lang } = useLanguage();
  const [classes, setClasses] = useState([]);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  const load = useCallback(async () => {
    setIsLoading(true);
    setError('');
    try {
      setClasses(await getClassComparison());
    } catch (err) {
      setError(userFacingApiError(err, lang).message || t('instructor.compareError'));
    } finally {
      setIsLoading(false);
    }
  }, [lang, t]);

  useEffect(() => {
    load();
  }, [load]);

  if (isLoading || classes.length < 2) return null;

  return (
    <div className="card p-6 space-y-4 text-left">
      <div className="flex items-center justify-between border-b border-line pb-3">
        <h2 className="text-base font-black text-fg flex items-center gap-2 font-serif-heading">
          <Columns3 className="w-5 h-5 text-accent" />
          <span>{t('instructor.compareTitle')}</span>
        </h2>
      </div>
      <p className="text-xs text-slate-600 dark:text-slate-400 font-medium -mt-2">{t('instructor.compareHint')}</p>
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800/60 rounded-[var(--radius-md)] flex items-start gap-2" role="alert">
          <span className="text-[11px] font-bold text-red-900 dark:text-red-300">{error}</span>
        </div>
      )}
      {/* Nhieu lop thi cuon doc rieng trong bang, tieu de cot dinh lai (sticky)
          de van biet dang xem cot nao khi da cuon xuong duoi. */}
      <div className="overflow-x-auto max-h-[24rem] overflow-y-auto rounded-[var(--radius-md)] border border-line">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left text-xs font-black text-slate-600 dark:text-slate-400 border-b border-line">
              <th className="sticky top-0 bg-surface-elevated py-2 pr-3 pl-3">{t('instructor.compareColClass')}</th>
              <th className="sticky top-0 bg-surface-elevated py-2 px-3 text-right">{t('instructor.compareColSize')}</th>
              <th className="sticky top-0 bg-surface-elevated py-2 px-3 text-right">{t('instructor.compareColHighRisk')}</th>
              <th className="sticky top-0 bg-surface-elevated py-2 px-3 text-right">{t('instructor.compareColOpen')}</th>
              <th className="sticky top-0 bg-surface-elevated py-2 px-3 text-right">{t('instructor.compareColOverdue')}</th>
              <th className="sticky top-0 bg-surface-elevated py-2 pl-3 pr-3 text-right">{t('instructor.compareColCompletion')}</th>
            </tr>
          </thead>
          <tbody>
            {classes.map((row) => (
              <tr key={row.courseId} className="border-b border-line last:border-0">
                <td className="py-2.5 pr-3 pl-3">
                  <span className="font-mono-code text-xs font-black text-accent">{row.code}</span>
                  {row.name && <span className="block text-xs text-slate-500 dark:text-slate-400 truncate max-w-[220px]">{row.name}</span>}
                </td>
                <td className="py-2.5 px-3 text-right text-fg font-medium">{row.classSize}</td>
                <td className={`py-2.5 px-3 text-right font-black ${row.highRiskCount > 0 ? 'text-danger dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}>
                  {row.highRiskCount}
                </td>
                <td className="py-2.5 px-3 text-right text-fg font-medium">{row.totalActiveWarnings}</td>
                <td className={`py-2.5 px-3 text-right font-black ${row.overdueCount > 0 ? 'text-danger dark:text-red-400' : 'text-slate-500 dark:text-slate-400'}`}>
                  {row.overdueCount}
                </td>
                <td className="py-2.5 pl-3 pr-3 text-right text-fg font-medium">
                  {row.latestWeekCompletion == null ? '—' : `${row.latestWeekCompletion}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
