import { useEffect, useMemo, useState } from 'react';
import { Search, BookOpen, X } from 'lucide-react';
import { listSyllabi } from '../lib/api';
import type { SyllabusSummary } from '../types';
import { useLanguage } from '../context/LanguageContext';

export function CommandPalette({
  isOpen,
  onClose,
  onSelectSyllabus,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSelectSyllabus: (code: string) => void;
}) {
  const { t } = useLanguage();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SyllabusSummary[]>([]);

  useEffect(() => {
    if (!isOpen) return;
    setQuery('');
    listSyllabi().then(setResults).catch(() => setResults([]));
  }, [isOpen]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return results;
    return results.filter((r) => `${r.subjectCode} ${r.courseNameEnglish}`.toLowerCase().includes(q));
  }, [results, query]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-start justify-center pt-24 px-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={t('nav.searchTitle')}
        className="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div role="search" className="flex items-center gap-2 px-4 py-3 border-b border-slate-200">
          <Search className="w-4 h-4 text-slate-400 shrink-0" aria-hidden="true" />
          <input
            autoFocus
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('commandPalette.placeholder')}
            aria-label={t('commandPalette.placeholder')}
            className="flex-1 text-sm outline-none"
          />
          <button onClick={onClose} aria-label={t('commandPalette.close')} className="text-slate-400 hover:text-slate-700 transition-colors">
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
        <div className="max-h-80 overflow-y-auto">
          {filtered.length === 0 ? (
            <p className="text-xs text-slate-400 text-center py-8">{t('commandPalette.noResults')}</p>
          ) : (
            filtered.map((r) => (
              <button
                key={r.subjectCode}
                onClick={() => {
                  onSelectSyllabus(r.subjectCode);
                  onClose();
                }}
                className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--accent-soft)] text-left cursor-pointer"
              >
                <BookOpen className="w-4 h-4 text-[var(--accent)] shrink-0" />
                <div className="min-w-0">
                  <span className="font-mono font-bold text-xs text-slate-900 mr-2">{r.subjectCode}</span>
                  <span className="text-xs text-slate-700 truncate">{r.courseNameEnglish}</span>
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
