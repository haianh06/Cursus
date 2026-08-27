import { useEffect, useRef, useState } from 'react';
import { ChevronDown, ArrowLeft } from 'lucide-react';
import type { Identity } from '../types';
import { useLanguage } from '../context/LanguageContext';

function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase();
}

// Replaces the old inline "name / role" row, which truncated long role
// labels (e.g. "Phòng Đào Tạo / Ban Học Vụ") with no way to read the full
// text. A dropdown shows the full name + role with no truncation, and an
// avatar (initials on a brand-colored disc) instead of just plain text
// gives the button something to click that isn't "the whole sentence".
export function UserMenu({ identity, roleLabel, cursusUrl }: { identity: Identity; roleLabel: string; cursusUrl: string }) {
  const { t } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setIsOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [isOpen]);

  return (
    <div ref={rootRef} className="relative pl-3 border-l border-slate-200 shrink-0">
      <button
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-label={t('nav.userMenuAriaLabel')}
        className="flex items-center gap-2 h-8 pl-1 pr-2 rounded-[var(--radius-sm)] hover:bg-slate-100 transition-colors cursor-pointer"
      >
        <span
          aria-hidden="true"
          className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold text-white shrink-0"
          style={{ background: 'var(--accent)' }}
        >
          {initialsOf(identity.name)}
        </span>
        <span className="hidden lg:inline text-xs font-semibold text-slate-800 whitespace-nowrap">{identity.name}</span>
        <ChevronDown className={`w-3 h-3 text-slate-400 shrink-0 transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`} aria-hidden="true" />
      </button>

      {isOpen && (
        <div
          role="menu"
          aria-label={t('nav.userMenuAriaLabel')}
          className="dropdown-pop absolute right-0 top-full mt-2 w-64 bg-white border border-slate-200 rounded-[var(--radius-md)] shadow-lg py-1 z-50 origin-top-right"
        >
          <div className="px-3 py-2 border-b border-slate-100">
            <p className="text-sm font-semibold text-slate-900 truncate">{identity.name}</p>
            <p className="text-xs text-slate-500 mt-0.5">{roleLabel}</p>
          </div>
          <a
            href={cursusUrl}
            role="menuitem"
            className="flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            {t('nav.backToCursus')}
          </a>
        </div>
      )}
    </div>
  );
}
