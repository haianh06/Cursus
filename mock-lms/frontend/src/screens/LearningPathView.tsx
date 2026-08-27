import { useEffect, useState } from 'react';
import { BookOpen, GitFork, Sparkles } from 'lucide-react';
import { listPrerequisites } from '../lib/api';
import type { PrerequisiteNode } from '../types';
import { useLanguage } from '../context/LanguageContext';

export function LearningPathView({
  initialSubjectCode,
  onSelectSubject,
}: {
  initialSubjectCode: string;
  onSelectSubject: (code: string) => void;
}) {
  const { t } = useLanguage();
  const [nodes, setNodes] = useState<Record<string, PrerequisiteNode>>({});
  const [selectedCode, setSelectedCode] = useState(initialSubjectCode);

  useEffect(() => {
    listPrerequisites().then((list) => {
      const map = Object.fromEntries(list.map((n) => [n.code, n]));
      setNodes(map);
      if (!map[selectedCode] && list.length > 0) setSelectedCode(list[0].code);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const nodeList = Object.values(nodes);
  const activeNode = nodes[selectedCode];

  if (nodeList.length === 0) return <div className="max-w-4xl mx-auto px-5 py-16 text-center text-sm text-slate-400">{t('app.loading')}</div>;
  if (!activeNode) return null;

  const lookup = (code: string): PrerequisiteNode =>
    nodes[code] || { code, name: code, semester: 0, credits: 3, prerequisites: [], isPrerequisiteOf: [], category: 'Foundation' };
  const prerequisitesList = activeNode.prerequisites.map(lookup);
  const successorsList = activeNode.isPrerequisiteOf.map(lookup);

  return (
    <div className="w-full bg-slate-50/50 min-h-screen py-6 px-4 sm:px-6">
      <div className="w-full max-w-[1440px] mx-auto space-y-6">
        <div className="card p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 pb-3">
            <div>
              {/* Global Breadcrumbs (App.tsx) already provides the way back
                  to EduSync -- no per-screen duplicate. */}
              <h1 className="text-xl sm:text-2xl font-extrabold text-slate-900 tracking-tight flex items-center space-x-2">
                <GitFork className="w-6 h-6 text-[var(--accent)]" />
                <span>{t('learningPath.heading')}</span>
              </h1>
            </div>
            <div className="flex items-center space-x-2 text-xs">
              <label className="text-slate-700 font-bold">{t('learningPath.subjectSelectLabel')}</label>
              <select value={selectedCode} onChange={(e) => setSelectedCode(e.target.value)} className="border border-slate-300 rounded-xl px-3 py-1.5 text-xs bg-white outline-none font-bold text-slate-800 cursor-pointer">
                {nodeList.map((n) => <option key={n.code} value={n.code}>{n.code} - {n.name}</option>)}
              </select>
            </div>
          </div>

          <div className="bg-[var(--accent-soft)] border border-[var(--accent)]/20 p-5 rounded-xl flex flex-wrap items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="bg-[var(--accent)] text-white font-mono font-extrabold text-xs px-2.5 py-0.5 rounded">{activeNode.code}</span>
                <h2 className="text-base sm:text-lg font-extrabold text-slate-900">{activeNode.name}</h2>
                <span className="text-xs text-slate-500 font-medium">({t('learningPath.semesterWord')} {activeNode.semester} &bull; {activeNode.credits} {t('learningPath.creditsWord')} &bull; {t('learningPath.categoryWord')} {activeNode.category})</span>
              </div>
            </div>
            <button onClick={() => onSelectSubject(activeNode.code)} className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2 rounded-xl cursor-pointer transition-all flex items-center space-x-1.5">
              <BookOpen className="w-3.5 h-3.5" /><span>{t('learningPath.openSyllabusBtn')} {activeNode.code} &rarr;</span>
            </button>
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h2 className="font-extrabold text-slate-900 text-sm uppercase tracking-wide flex items-center space-x-2 border-b border-slate-100 pb-3">
            <Sparkles className="w-4 h-4 text-[var(--accent)]" /><span>{t('learningPath.stagesHeading')}</span>
          </h2>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
            <PathColumn title={t('learningPath.col1Title')} items={prerequisitesList} tone="blue" emptyLabel={t('learningPath.col1Empty')} onSelect={setSelectedCode} note={t('learningPath.col1Note')} subjectsUnit={t('learningPath.subjectsUnit')} semesterShort={t('learningPath.tableSemesterShort')} />

            <div className="bg-[var(--accent-soft)] border-2 border-[var(--accent)]/50 rounded-2xl p-5 flex flex-col justify-between shadow-md relative space-y-4">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#1B57A8] text-white text-[10px] uppercase font-bold tracking-wider px-3 py-0.5 rounded-full">{t('learningPath.activeBadge')}</div>
              <div className="text-center pt-2 space-y-3">
                <div className="w-14 h-14 rounded-2xl bg-[var(--accent)] text-white font-mono font-extrabold text-base flex items-center justify-center mx-auto">{activeNode.code}</div>
                <div>
                  <h3 className="font-extrabold text-slate-900 text-base">{activeNode.name}</h3>
                  <span className="text-xs text-slate-600 font-medium">{t('learningPath.semesterWord')} {activeNode.semester} &bull; {activeNode.credits} {t('learningPath.creditsWord')}</span>
                </div>
              </div>
              <button onClick={() => onSelectSubject(activeNode.code)} className="w-full bg-slate-900 hover:bg-slate-800 text-white text-xs font-bold py-2.5 px-4 rounded-xl cursor-pointer transition-all flex items-center justify-center space-x-1.5">
                <BookOpen className="w-3.5 h-3.5" /><span>{t('learningPath.viewSyllabusBtn')} &rarr;</span>
              </button>
            </div>

            <PathColumn title={t('learningPath.col3Title')} items={successorsList} tone="emerald" emptyLabel={t('learningPath.col3Empty')} onSelect={setSelectedCode} note={t('learningPath.col3Note')} subjectsUnit={t('learningPath.subjectsUnit')} semesterShort={t('learningPath.tableSemesterShort')} />
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h3 className="font-extrabold text-slate-900 text-sm uppercase tracking-wide border-b border-slate-100 pb-3">{t('learningPath.summaryHeading')}</h3>
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>{t('learningPath.tableCode')}</th><th>{t('learningPath.tableName')}</th><th className="text-center">{t('learningPath.tableSemesterShort')}</th><th className="text-center">{t('learningPath.tableCreditShort')}</th>
                  <th>{t('learningPath.tablePrerequisite')}</th><th>{t('learningPath.tableUnlocks')}</th>
                </tr>
              </thead>
              <tbody>
                {nodeList.map((node) => (
                  <tr key={node.code} onClick={() => setSelectedCode(node.code)} className={`cursor-pointer group ${node.code === activeNode.code ? 'bg-[var(--accent-soft)]' : ''}`}>
                    <td><span className="mono font-bold text-slate-900 group-hover:text-[var(--accent)] transition-colors">{node.code}</span></td>
                    <td className="font-bold text-slate-900 group-hover:text-[var(--accent)] transition-colors">{node.name}</td>
                    <td className="text-center font-bold mono text-slate-800">{t('learningPath.tableSemesterShort')} {node.semester}</td>
                    <td className="text-center font-bold mono text-slate-800">{node.credits}</td>
                    <td className="mono text-slate-700">
                      {node.prerequisites.length > 0 ? node.prerequisites.map((p) => <span key={p} className="badge badge-neutral mr-2">{p}</span>) : <span className="text-slate-400 text-[11px]">&mdash;</span>}
                    </td>
                    <td className="mono text-slate-700">
                      {node.isPrerequisiteOf.length > 0 ? node.isPrerequisiteOf.map((s) => <span key={s} className="badge badge-success mr-2">{s}</span>) : <span className="text-slate-400 text-[11px]">&mdash;</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

function PathColumn({
  title, items, tone, emptyLabel, onSelect, note, subjectsUnit, semesterShort,
}: {
  title: string; items: PrerequisiteNode[]; tone: 'blue' | 'emerald'; emptyLabel: string; onSelect: (code: string) => void; note: string; subjectsUnit: string; semesterShort: string;
}) {
  const toneCls = tone === 'blue'
    ? { wrap: 'bg-blue-50/50 border-blue-200', headBorder: 'border-blue-200', headText: 'text-blue-900', badge: 'bg-blue-200 text-blue-900', item: 'border-blue-200 hover:border-blue-500', itemText: 'text-blue-900 group-hover:text-blue-600', chip: 'bg-blue-100 text-blue-800', footer: 'text-blue-700 bg-blue-100/60' }
    : { wrap: 'bg-emerald-50/50 border-emerald-200', headBorder: 'border-emerald-200', headText: 'text-emerald-900', badge: 'bg-emerald-200 text-emerald-900', item: 'border-emerald-200 hover:border-emerald-500', itemText: 'text-emerald-900 group-hover:text-emerald-600', chip: 'bg-emerald-100 text-emerald-800', footer: 'text-emerald-700 bg-emerald-100/60' };

  return (
    <div className={`${toneCls.wrap} border rounded-[var(--radius-sm)] p-5 flex flex-col justify-between space-y-4`}>
      <div>
        <div className={`flex items-center justify-between mb-3 border-b ${toneCls.headBorder} pb-2`}>
          <span className={`font-extrabold text-xs ${toneCls.headText}`}>{title}</span>
          <span className={`${toneCls.badge} font-mono text-[10px] font-bold px-2 py-0.5 rounded-full`}>{items.length} {subjectsUnit}</span>
        </div>
        {items.length === 0 ? (
          <div className="p-6 bg-white border border-slate-100 rounded-xl text-center text-xs text-slate-500">{emptyLabel}</div>
        ) : (
          <div className="space-y-2">
            {items.map((item) => (
              <div key={item.code} onClick={() => onSelect(item.code)} className={`bg-white border ${toneCls.item} p-3 rounded-xl flex items-center justify-between cursor-pointer transition-all group`}>
                <div>
                  <span className={`font-mono font-bold block text-xs ${toneCls.itemText}`}>{item.code}</span>
                  <span className="text-[11px] text-slate-600 line-clamp-1">{item.name}</span>
                </div>
                <span className={`text-[10px] ${toneCls.chip} font-bold px-2 py-0.5 rounded-full`}>{semesterShort} {item.semester}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className={`text-[11px] font-medium ${toneCls.footer} p-2.5 rounded-xl text-center`}>{note}</div>
    </div>
  );
}
