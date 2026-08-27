import { useEffect, useState } from 'react';
import { ArrowRight, Search } from 'lucide-react';
import { listSyllabi } from '../lib/api';
import type { SyllabusSummary } from '../types';
import { useLanguage } from '../context/LanguageContext';

// Source syllabi mix "None"/"Không" (Vietnamese "none") and multi-line
// numbered text ("1. EXE201\n2. Pass on-the-job training\n...") in the same
// free-text field -- collapsing newlines to " · " keeps numbered conditions
// readable on one line instead of the raw \n rendering as an odd double
// space, and normalizing every "no prerequisite" spelling to one em dash
// instead of literally showing "Không  None" side by side.
const NO_PREREQ_VALUES = new Set(['none', 'không', 'n/a', '']);
function formatPrerequisite(raw: string): string | null {
  const cleaned = raw.replace(/\s*\n\s*/g, ' · ').trim();
  if (NO_PREREQ_VALUES.has(cleaned.toLowerCase())) return null;
  // "Không\nNone" -> "Không · None" after the replace above -- still just
  // means "none" in both languages, not two different conditions.
  if (/^(không|none)\s*·\s*(không|none)$/i.test(cleaned)) return null;
  return cleaned;
}

export function SyllabusSearch({
  onSelectSyllabus,
}: {
  onSelectSyllabus: (code: string) => void;
}) {
  const { t } = useLanguage();
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState<SyllabusSummary[] | null>(null);

  useEffect(() => {
    const handle = setTimeout(() => {
      listSyllabi(keyword).then(setResults).catch(() => setResults([]));
    }, 200);
    return () => clearTimeout(handle);
  }, [keyword]);

  return (
    <div className="w-full bg-slate-50/50 min-h-screen py-6 px-4 sm:px-6">
      <div className="w-full max-w-[1440px] mx-auto space-y-6">
        <div className="card p-6 space-y-4">
          {/* Global Breadcrumbs (App.tsx) already provides the way back to
              EduSync -- search is the primary interaction on this screen,
              so it leads instead of a duplicate back-link. */}
          <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight flex items-center space-x-2">
            <Search className="w-6 h-6 text-slate-500" /><span>{t('syllabusSearch.heading')}</span>
          </h1>

          <div className="relative max-w-md">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              autoFocus
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder={t('syllabusSearch.searchPlaceholder')}
              className="w-full bg-slate-50 border border-slate-300 rounded-xl pl-9 pr-3 py-2 text-xs font-semibold text-slate-900 outline-none focus:bg-white focus:border-[var(--accent)]"
            />
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="bg-slate-900 text-white px-6 py-3 flex items-center justify-between">
            <span className="font-extrabold text-xs tracking-wider uppercase">
              {t('syllabusSearch.resultsLabel')} ({results?.length ?? 0} {t('syllabusSearch.resultsUnit')})
            </span>
          </div>
          {results === null ? (
            <p className="text-xs text-slate-400 text-center py-10">{t('syllabusSearch.searching')}</p>
          ) : results.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-10">{t('syllabusSearch.noResults')}</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="w-28">{t('syllabusSearch.tableCode')}</th>
                    <th>{t('syllabusSearch.tableName')}</th>
                    <th className="text-center w-20">{t('syllabusSearch.tableCredit')}</th>
                    <th>{t('syllabusSearch.tableMethod')}</th>
                    <th>{t('syllabusSearch.tablePrerequisite')}</th>
                    <th className="text-right w-24">{t('syllabusSearch.tableDetail')}</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((item) => (
                    <tr key={item.subjectCode} className="group cursor-pointer" onClick={() => onSelectSyllabus(item.subjectCode)}>
                      <td><span className="mono font-bold text-slate-900 group-hover:text-[var(--accent)] transition-colors">{item.subjectCode}</span></td>
                      <td>
                        <strong className="text-slate-900 block font-bold group-hover:text-[var(--accent)] transition-colors">{item.courseNameEnglish}</strong>
                        <span className="text-[11px] text-slate-500 line-clamp-1">{item.cloCount} CLO &bull; {item.sessionCount} buổi &bull; {item.questionCount} câu hỏi</span>
                      </td>
                      <td className="text-center font-bold text-slate-700 mono">{item.noCredit}</td>
                      <td><span className="badge badge-neutral">{item.learningTeachingMethod.split(',')[0]}</span></td>
                      <td className="mono text-slate-700 max-w-[220px]">
                        {(() => {
                          const prereq = item.preRequisite ? formatPrerequisite(item.preRequisite) : null;
                          return prereq ? (
                            <span className="text-slate-700 font-bold line-clamp-2" title={prereq}>{prereq}</span>
                          ) : (
                            <span className="text-slate-400 text-[11px]">&mdash;</span>
                          );
                        })()}
                      </td>
                      <td className="text-right">
                        <button onClick={(e) => { e.stopPropagation(); onSelectSyllabus(item.subjectCode); }} className="text-slate-500 hover:text-[var(--accent)] font-semibold text-[11px] flex items-center justify-end gap-1 w-full cursor-pointer transition-colors">
                          <span>{t('syllabusSearch.openLabel')}</span><ArrowRight className="w-3 h-3" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
