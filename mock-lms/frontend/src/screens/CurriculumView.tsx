import { useEffect, useState } from 'react';
import { ArrowRight, Filter, Layers } from 'lucide-react';
import { getCurriculumProgram, listCurriculumPrograms } from '../lib/api';
import type { CurriculumProgramDetail, CurriculumProgramSummary, SubjectCategory } from '../types';
import { useLanguage } from '../context/LanguageContext';

const CATEGORY_STYLE: Record<SubjectCategory, string> = {
  Foundation: 'badge badge-neutral',
  Core: 'badge badge-accent',
  Specialized: 'badge badge-success',
  Elective: 'badge badge-warning',
  Capstone: 'badge badge-accent',
  'Soft Skills': 'badge badge-neutral',
};

export function CurriculumView({
  onSelectSubject,
}: {
  onSelectSubject: (code: string) => void;
}) {
  const { t } = useLanguage();
  const [programs, setPrograms] = useState<CurriculumProgramSummary[]>([]);
  const [programCode, setProgramCode] = useState('BIT_SE_K20D_K21A');
  const [program, setProgram] = useState<CurriculumProgramDetail | null>(null);
  const [selectedSemester, setSelectedSemester] = useState<number | 'all'>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [error, setError] = useState(false);

  useEffect(() => {
    listCurriculumPrograms().then(setPrograms).catch(() => setPrograms([]));
  }, []);

  useEffect(() => {
    setProgram(null);
    setError(false);
    getCurriculumProgram(programCode)
      .then(setProgram)
      .catch(() => setError(true));
  }, [programCode]);

  if (error) return <div className="max-w-4xl mx-auto px-5 py-10 text-sm text-red-600">{t('curriculum.loadError')}</div>;
  if (!program) return <div className="max-w-4xl mx-auto px-5 py-16 text-center text-sm text-slate-400">{t('app.loading')}</div>;

  const filteredSemesters = program.semesters
    .filter((sem) => selectedSemester === 'all' || sem.semesterNo === selectedSemester)
    .map((sem) => ({
      ...sem,
      subjects: sem.subjects.filter((sub) => categoryFilter === 'all' || sub.category === categoryFilter),
    }))
    .filter((sem) => sem.subjects.length > 0);

  return (
    <div className="w-full bg-slate-50/50 min-h-screen py-6 px-4 sm:px-6">
      <div className="w-full max-w-[1440px] mx-auto space-y-6">
        <div className="card p-6 space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              {/* No inline "back to dashboard" here -- the global
                  Breadcrumbs strip (App.tsx) already gives every non-hub
                  screen a clickable "EduSync" home link; duplicating that
                  as a second, differently-styled back button per screen
                  was redundant navigation, not two real options. */}
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight flex items-center space-x-2">
                  <Layers className="w-6 h-6 text-slate-500" />
                  <span>{t('curriculum.heading')}</span>
                </h1>
                <span className="mono text-xs font-bold px-2 py-0.5 border border-[var(--accent)] text-[var(--accent)] rounded-[var(--radius-sm)]">{program.code}</span>
              </div>
            </div>

            <div className="flex items-center space-x-2 text-xs">
              <label className="text-slate-600 font-semibold">{t('curriculum.majorLabel')}</label>
              <select
                value={programCode}
                onChange={(e) => setProgramCode(e.target.value)}
                className="border border-slate-300 rounded-xl px-3 py-1.5 text-xs bg-white outline-none font-bold text-slate-800 cursor-pointer"
              >
                {programs.map((p) => (
                  <option key={p.code} value={p.code}>{p.name} ({p.code})</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs bg-slate-50 p-4 rounded-[var(--radius-sm)] border border-slate-200">
            <div><span className="text-slate-500 block text-[11px]">{t('curriculum.programNameLabel')}</span><strong className="text-slate-900 font-bold text-sm">{program.name}</strong></div>
            <div><span className="text-slate-500 block text-[11px]">{t('curriculum.facultyYearLabel')}</span><span className="text-slate-800 font-semibold">{program.faculty} ({program.effectiveYear})</span></div>
            <div><span className="text-slate-500 block text-[11px]">{t('curriculum.decisionNoLabel')}</span><span className="text-slate-900 mono font-semibold">{program.decisionNo}</span></div>
            <div><span className="text-slate-500 block text-[11px]">{t('curriculum.totalCreditsLabel')}</span><strong className="text-[var(--accent)] text-sm font-extrabold">{program.totalCredits} {t('curriculum.creditsWord')}</strong></div>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed bg-slate-50 p-3.5 rounded-[var(--radius-sm)] border border-slate-200">{program.description}</p>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-100 text-xs">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="font-bold text-slate-700 mr-1 flex items-center space-x-1"><Filter className="w-3.5 h-3.5 text-slate-500" /><span>{t('curriculum.semesterFilterLabel')}</span></span>
              <button onClick={() => setSelectedSemester('all')} className={`px-3 py-1.5 rounded-[var(--radius-sm)] font-bold cursor-pointer transition-colors ${selectedSemester === 'all' ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'}`}>
                {t('curriculum.allSemesters')} ({program.semesters.length} {t('curriculum.semestersUnit')})
              </button>
              {program.semesters.map((s) => (
                <button key={s.semesterNo} onClick={() => setSelectedSemester(s.semesterNo)} className={`px-2.5 py-1.5 rounded-[var(--radius-sm)] font-bold cursor-pointer transition-colors ${selectedSemester === s.semesterNo ? 'bg-[var(--accent)] text-white' : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'}`}>
                  {t('curriculum.semesterShort')} {s.semesterNo}
                </button>
              ))}
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="font-semibold text-slate-600">{t('curriculum.categoryFilterLabel')}</span>
              <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="border border-slate-300 rounded-lg px-2.5 py-1 text-xs bg-white outline-none font-bold text-slate-800 cursor-pointer">
                <option value="all">{t('curriculum.allCategories')}</option>
                {Object.keys(CATEGORY_STYLE).map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {filteredSemesters.map((sem) => {
            const semTotalCredits = sem.subjects.reduce((sum, s) => sum + s.credits, 0);
            return (
              <div key={sem.semesterNo} className="card overflow-hidden">
                <div className="bg-slate-50 text-slate-800 px-4 py-3 flex flex-wrap items-center justify-between gap-2 border-b border-slate-200">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-sm tracking-wide">{t('curriculum.semesterHeadingPrefix')} {sem.semesterNo}: {sem.title.toUpperCase()}</span>
                    <span className="text-xs text-slate-500">({sem.subjects.length} {t('curriculum.subjectsUnit')})</span>
                  </div>
                  <span className="text-[11px] mono font-bold text-slate-500 border border-slate-200 bg-white px-2 py-0.5 rounded-[var(--radius-sm)]">
                    {t('curriculum.semesterTotalLabel')} {semTotalCredits} {t('curriculum.creditsShort')}
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th className="w-28">{t('curriculum.tableCode')}</th>
                        <th>{t('curriculum.tableName')}</th>
                        <th className="text-center w-20">{t('curriculum.creditsShort')}</th>
                        <th className="w-32">{t('curriculum.tableCategory')}</th>
                        <th>{t('curriculum.tablePrerequisite')}</th>
                        <th className="text-right w-24">{t('curriculum.tableSyllabus')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sem.subjects.map((sub) => (
                        <tr key={sub.code} className="group">
                          <td><span className="mono font-bold text-slate-900">{sub.code}</span></td>
                          <td><strong className="text-slate-900 font-medium group-hover:text-[var(--accent)] transition-colors">{sub.name}</strong></td>
                          <td className="text-center font-bold text-slate-700 mono">{sub.credits}</td>
                          <td><span className={CATEGORY_STYLE[sub.category] ?? 'badge badge-neutral'}>{sub.category}</span></td>
                          <td className="mono text-slate-700">
                            {sub.prerequisite && sub.prerequisite !== 'None' ? (
                              <span className="text-slate-700 font-bold">{sub.prerequisite}</span>
                            ) : <span className="text-slate-400 text-[11px]">&mdash;</span>}
                          </td>
                          <td className="text-right">
                            <button onClick={() => onSelectSubject(sub.code)} className="text-slate-500 hover:text-[var(--accent)] font-semibold text-[11px] flex items-center justify-end gap-1 w-full cursor-pointer transition-colors">
                              <span>{t('curriculum.openLabel')}</span><ArrowRight className="w-3 h-3" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
