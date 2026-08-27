import { useEffect, useState } from 'react';
import {
  BookOpen, Layers, HelpCircle, Award, Sparkles, ChevronLeft, ChevronRight,
  ExternalLink, RotateCcw,
} from 'lucide-react';
import { getSyllabus, ApiError } from '../lib/api';
import type { SyllabusDetail } from '../types';
import { useLanguage } from '../context/LanguageContext';

type Tab = 'overview' | 'materials' | 'clos' | 'sessions' | 'questions' | 'assessments';

const TAB_DEFS: { key: Tab; labelKey: string; icon: typeof BookOpen }[] = [
  { key: 'overview', labelKey: 'syllabusDetails.tabOverview', icon: BookOpen },
  { key: 'materials', labelKey: 'syllabusDetails.tabMaterials', icon: Layers },
  { key: 'clos', labelKey: 'syllabusDetails.tabClos', icon: Award },
  { key: 'sessions', labelKey: 'syllabusDetails.tabSessions', icon: Sparkles },
  { key: 'questions', labelKey: 'syllabusDetails.tabQuestions', icon: HelpCircle },
  { key: 'assessments', labelKey: 'syllabusDetails.tabAssessments', icon: Award },
];

export function SyllabusDetails({
  code,
  onNavigate,
  onBackToSearch,
}: {
  code: string;
  onNavigate: (path: string) => void;
  onBackToSearch: () => void;
}) {
  const { t } = useLanguage();
  const [syllabus, setSyllabus] = useState<SyllabusDetail | null>(null);
  const [notFound, setNotFound] = useState(false);
  const [tab, setTab] = useState<Tab>('overview');

  useEffect(() => {
    setSyllabus(null);
    setNotFound(false);
    setTab('overview');
    getSyllabus(code)
      .then(setSyllabus)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) setNotFound(true);
      });
  }, [code]);

  if (notFound) {
    return (
      <div className="max-w-2xl mx-auto px-5 py-16 text-center space-y-3">
        <p className="text-sm text-slate-600">{t('syllabusDetails.notFoundPrefix')} <strong className="font-mono">{code}</strong> {t('syllabusDetails.notFoundSuffix')}</p>
        <button onClick={onBackToSearch} className="text-[var(--accent)] hover:underline text-xs font-semibold">&larr; {t('syllabusDetails.backToSearch')}</button>
      </div>
    );
  }
  if (!syllabus) return <div className="max-w-4xl mx-auto px-5 py-16 text-center text-sm text-slate-400">{t('app.loading')}</div>;

  const { metadata } = syllabus;

  return (
    <div className="w-full bg-slate-50/50 min-h-screen py-6 px-4 sm:px-6">
      <div className="w-full max-w-[1200px] mx-auto space-y-5">
        {/* Global Breadcrumbs (App.tsx) already has a "Tra Cứu Đề Cương"
            crumb pointing back here -- no duplicate back-link needed. */}
        <div className="card p-6 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="border border-[var(--accent)] text-[var(--accent)] font-mono font-bold text-xs px-2 py-0.5 rounded-[var(--radius-sm)]">{metadata.subjectCode}</span>
            <h1 className="text-lg sm:text-xl font-extrabold text-slate-900">{metadata.courseNameEnglish}</h1>
            {metadata.isApproved && <span className="badge badge-success border border-[#15803d]/20 px-1.5 py-0.5 rounded-[var(--radius-sm)]">{t('syllabusDetails.approvedBadge')}</span>}
          </div>
          <p className="text-xs text-slate-500">{metadata.syllabusName}</p>
        </div>

        <div className="tabs-underline">
          {TAB_DEFS.map(({ key, labelKey, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              aria-selected={tab === key}
              className="tab-underline-item"
            >
              <Icon className="w-3.5 h-3.5" /> {t(labelKey)}
            </button>
          ))}
        </div>

        <div className="card p-6">
          {tab === 'overview' && <OverviewTab syllabus={syllabus} onNavigate={onNavigate} />}
          {tab === 'materials' && <MaterialsTab materials={syllabus.materials} />}
          {tab === 'clos' && <CLOsTab clos={syllabus.clos} />}
          {tab === 'sessions' && <SessionsTab sessions={syllabus.sessions} />}
          {tab === 'questions' && <QuestionsTab questions={syllabus.questions} />}
          {tab === 'assessments' && <AssessmentsTab assessments={syllabus.assessments} />}
        </div>
      </div>
    </div>
  );
}

function OverviewTab({ syllabus, onNavigate }: { syllabus: SyllabusDetail; onNavigate: (path: string) => void }) {
  const { t } = useLanguage();
  const { metadata } = syllabus;
  return (
    <div className="space-y-5 text-xs">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Spec label={t('syllabusDetails.creditsLabel')} value={String(metadata.noCredit)} />
        <Spec label={t('syllabusDetails.degreeLevelLabel')} value={metadata.degreeLevel} />
        <Spec label={t('syllabusDetails.scoringScaleLabel')} value={`/${metadata.scoringScale}`} />
        <Spec label={t('syllabusDetails.decisionNoLabel')} value={metadata.decisionNo} mono />
      </div>
      <div>
        <h3 className="font-bold text-slate-800 mb-1.5">{t('syllabusDetails.teachingMethodHeading')}</h3>
        <p className="text-slate-600 leading-relaxed">{metadata.learningTeachingMethod}</p>
      </div>
      <div>
        <h3 className="font-bold text-slate-800 mb-1.5">{t('syllabusDetails.timeAllocationHeading')}</h3>
        <p className="text-slate-600 leading-relaxed">{metadata.timeAllocation}</p>
      </div>
      <div>
        <h3 className="font-bold text-slate-800 mb-1.5">{t('syllabusDetails.prerequisiteHeading')}</h3>
        <button
          onClick={() => onNavigate(`/courses/learning-path?code=${metadata.subjectCode}`)}
          className="text-[var(--accent)] font-bold text-xs hover:underline cursor-pointer"
        >
          {metadata.preRequisite || t('syllabusDetails.none')}
        </button>
      </div>
      <div>
        <h3 className="font-bold text-slate-800 mb-1.5">{t('syllabusDetails.descriptionHeading')}</h3>
        <p className="text-slate-600 leading-relaxed whitespace-pre-line">{metadata.description}</p>
      </div>
      {metadata.studentTasks && (
        <div>
          <h3 className="font-bold text-slate-800 mb-1.5">{t('syllabusDetails.studentTasksHeading')}</h3>
          <p className="text-slate-600 leading-relaxed">{metadata.studentTasks}</p>
        </div>
      )}
      {metadata.tools && (
        <div>
          <h3 className="font-bold text-slate-800 mb-1.5">{t('syllabusDetails.toolsHeading')}</h3>
          <p className="text-slate-600 leading-relaxed">{metadata.tools}</p>
        </div>
      )}
    </div>
  );
}

function Spec({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-[var(--radius-sm)] p-3">
      <span className="text-slate-500 block text-[11px] mb-1">{label}</span>
      <strong className={`text-slate-900 text-sm ${mono ? 'mono' : ''}`}>{value}</strong>
    </div>
  );
}

function MaterialsTab({ materials }: { materials: SyllabusDetail['materials'] }) {
  const { t } = useLanguage();
  if (materials.length === 0) return <EmptyState label={t('syllabusDetails.materialsEmpty')} />;
  return (
    <div className="space-y-2.5">
      {materials.map((m) => (
        <div key={m.no} className="flex items-start gap-3 p-3.5 border border-slate-200 rounded-[var(--radius-sm)]">
          <span className="w-6 h-6 rounded-[var(--radius-sm)] bg-slate-100 font-bold flex items-center justify-center text-slate-600 text-[11px] shrink-0">{m.no}</span>
          <div className="flex-1 min-w-0 text-xs">
            <div className="flex flex-wrap items-center gap-1.5">
              <strong className="text-slate-900">{m.description}</strong>
              {m.isMain && <span className="badge badge-accent border border-[var(--accent)]/20 px-1 py-0.5 rounded text-[10px]">{t('syllabusDetails.materialMainBadge')}</span>}
            </div>
            {m.author && <p className="text-slate-500 mt-0.5">{m.author} {m.publisher && `· ${m.publisher}`} {m.publishedDate && `· ${m.publishedDate}`}</p>}
            {m.note && <p className="text-slate-400 mt-0.5 italic">{m.note}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

function CLOsTab({ clos }: { clos: SyllabusDetail['clos'] }) {
  const { t } = useLanguage();
  if (clos.length === 0) return <EmptyState label={t('syllabusDetails.closEmpty')} />;
  return (
    <div className="space-y-2.5">
      {clos.map((c) => (
        <div key={c.no} className="flex items-start gap-3 p-3.5 border border-slate-200 rounded-[var(--radius-sm)]">
          <span className="text-[11px] mono font-bold border border-slate-200 bg-slate-50 text-slate-700 px-2 py-0.5 rounded shrink-0">{c.cloName}</span>
          <p className="text-xs text-slate-700 leading-relaxed">{c.details}</p>
        </div>
      ))}
    </div>
  );
}

function SessionsTab({ sessions }: { sessions: SyllabusDetail['sessions'] }) {
  const { t } = useLanguage();
  const [keyword, setKeyword] = useState('');
  if (sessions.length === 0) return <EmptyState label={t('syllabusDetails.sessionsEmpty')} />;
  const filtered = keyword.trim()
    ? sessions.filter((s) => s.topic.toLowerCase().includes(keyword.toLowerCase()))
    : sessions;
  return (
    <div className="space-y-3">
      <input
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        placeholder={t('syllabusDetails.sessionsFilterPlaceholder')}
        className="w-full max-w-xs bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 text-xs outline-none focus:bg-white focus:border-[var(--accent)]"
      />
      <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
        {filtered.map((s) => (
          <details key={s.sessionNo} className="border border-slate-200 rounded-[var(--radius-sm)] group">
            <summary className="flex items-center gap-3 p-3 cursor-pointer list-none bg-slate-50/50 hover:bg-slate-50 transition-colors">
              <span className="w-8 h-8 rounded-[var(--radius-sm)] bg-white border border-slate-200 font-bold flex items-center justify-center text-slate-700 text-xs shrink-0">{s.sessionNo}</span>
              <span className="flex-1 text-xs font-semibold text-slate-800 whitespace-pre-line group-hover:text-[var(--accent)] transition-colors">{s.topic}</span>
              <span className="text-[10px] border border-slate-200 bg-white text-slate-600 font-bold px-1.5 py-0.5 rounded">{s.type}</span>
            </summary>
            <div className="px-3 pb-3 pl-14 text-[11px] text-slate-600 space-y-1.5">
              <p><strong className="text-slate-700">{t('syllabusDetails.loLabel')}</strong> {s.lo}</p>
              {s.studentTasks && <p className="whitespace-pre-line"><strong className="text-slate-700">{t('syllabusDetails.tasksLabel')}</strong> {s.studentTasks}</p>}
              {s.urls && (
                <a href={s.urls} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline inline-flex items-center gap-1">
                  {t('syllabusDetails.referenceLink')} <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

function QuestionsTab({ questions }: { questions: SyllabusDetail['questions'] }) {
  const { t } = useLanguage();
  const [practiceMode, setPracticeMode] = useState(false);
  const [idx, setIdx] = useState(0);

  if (questions.length === 0) return <EmptyState label={t('syllabusDetails.questionsEmpty')} />;

  if (!practiceMode) {
    return (
      <div className="space-y-3">
        <button onClick={() => { setPracticeMode(true); setIdx(0); }} className="bg-amber-500 hover:bg-amber-600 text-white text-xs font-bold px-4 py-2 rounded-xl flex items-center gap-1.5 cursor-pointer">
          <Sparkles className="w-3.5 h-3.5" /> {t('syllabusDetails.practiceModeBtn')} ({questions.length} {t('syllabusDetails.questionsUnit')})
        </button>
        <div className="space-y-2">
          {questions.map((q) => (
            <div key={q.no} className="p-3 border border-slate-200 rounded-xl text-xs flex items-start gap-2.5">
              <span className="font-mono font-bold text-slate-400 shrink-0">#{q.no}</span>
              <span className="text-slate-700">{q.question}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const q = questions[idx];
  return (
    <div className="max-w-xl mx-auto space-y-4">
      <div className="flex items-center justify-between text-xs">
        <button onClick={() => setPracticeMode(false)} className="text-slate-500 hover:text-slate-800 flex items-center gap-1"><RotateCcw className="w-3.5 h-3.5" /> {t('syllabusDetails.exitBtn')}</button>
        <span className="font-bold text-slate-600">{idx + 1} / {questions.length}</span>
      </div>
      <div className="bg-amber-50 border-2 border-amber-300 rounded-2xl p-8 text-center min-h-[160px] flex items-center justify-center">
        <p className="text-sm font-semibold text-slate-800">{q.question}</p>
      </div>
      <div className="flex items-center justify-between">
        <button disabled={idx === 0} onClick={() => setIdx((i) => Math.max(0, i - 1))} className="p-2 rounded-lg border border-slate-200 disabled:opacity-30 cursor-pointer">
          <ChevronLeft className="w-4 h-4" />
        </button>
        <button disabled={idx === questions.length - 1} onClick={() => setIdx((i) => Math.min(questions.length - 1, i + 1))} className="p-2 rounded-lg border border-slate-200 disabled:opacity-30 cursor-pointer">
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

function AssessmentsTab({ assessments }: { assessments: SyllabusDetail['assessments'] }) {
  const { t } = useLanguage();
  if (assessments.length === 0) return <EmptyState label={t('syllabusDetails.assessmentsEmpty')} />;
  const totalWeight = assessments.reduce((sum, a) => sum + a.weight, 0);
  return (
    <div className="space-y-3">
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>{t('syllabusDetails.tableCategory')}</th><th className="text-center">{t('syllabusDetails.tableWeight')}</th><th>{t('syllabusDetails.tableClo')}</th><th>{t('syllabusDetails.tableCompletionCriteria')}</th><th>{t('syllabusDetails.tableDuration')}</th>
            </tr>
          </thead>
          <tbody>
            {assessments.map((a) => (
              <tr key={a.no}>
                <td><strong className="text-slate-900 block">{a.category}</strong><span className="text-[11px] text-slate-500">{a.type}</span></td>
                <td className="text-center font-bold mono text-slate-900">{a.weight}%</td>
                <td className="mono text-[11px] text-slate-600">{a.clo || '—'}</td>
                <td className="text-slate-600">{a.completionCriteria}</td>
                <td className="text-slate-600">{a.duration}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-slate-200 bg-slate-50">
              <td className="font-bold text-slate-900">{t('syllabusDetails.total')}</td>
              <td className="text-center font-extrabold text-[var(--accent)] mono">{totalWeight}%</td>
              <td colSpan={3} />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

function EmptyState({ label }: { label: string }) {
  return <p className="text-xs text-slate-400 text-center py-10">{label}</p>;
}
