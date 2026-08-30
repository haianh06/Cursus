import { useState } from 'react';
import { Search, Menu, X, ArrowLeft } from 'lucide-react';
import type { Identity } from '../types';
import { useLanguage } from '../context/LanguageContext';
import { ThemeToggle } from './ThemeToggle';
import { LanguageToggle } from './LanguageToggle';
import { EduSyncMark } from './EduSyncMark';
import { UserMenu } from './UserMenu';
import { handleBackToCursusClick } from '../lib/backToCursus';

// FLM/EduSync is opened from Cursus in a new tab (frontend/src/App.jsx's
// EduSync Topbar link, target="_blank"), so the browser Back button has no
// history to go to -- without this link, closing the tab was the only way
// out. Points at the same origin Cursus's own SSO handoff already knows
// about (src/config.py's cursus_frontend_url), read via env with the same
// fallback-to-localhost pattern Cursus uses for VITE_MOCK_LMS_URL.
const CURSUS_URL = import.meta.env.VITE_CURSUS_URL || 'http://localhost:5173';

export function Navbar({
  identity,
  onGoHome,
  onNavigate,
  onOpenCommandPalette,
}: {
  identity: Identity | null;
  onGoHome: () => void;
  onNavigate: (path: string) => void;
  onOpenCommandPalette: () => void;
}) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { t } = useLanguage();

  const ROLE_LABEL: Record<Identity['role'], string> = {
    STUDENT: t('nav.roleStudent'),
    INSTRUCTOR: t('nav.roleInstructor'),
    ADMIN: t('nav.roleAdmin'),
  };

  const NAV_LINKS = [
    { label: t('nav.linkCurriculum'), path: '/courses/curriculum' },
    { label: t('nav.linkPrerequisites'), path: '/courses/learning-path' },
    // Syllabus search also owns the syllabus detail route, so a detail page
    // still shows this item as active instead of nothing being highlighted.
    { label: t('nav.linkSyllabus'), path: '/courses/search', matchPrefixes: ['/courses/search', '/courses/syllabus'] },
    { label: t('nav.linkAssignments'), path: '/courses/assignments' },
  ];

  // App.tsx re-renders Navbar on every route change (it's a prop of the
  // page, not a route param itself), so reading the URL directly here
  // rather than threading the current route down as a prop stays in sync
  // for free -- one fewer prop to wire through App.tsx.
  const currentPath = window.location.pathname;
  const isActive = (link: (typeof NAV_LINKS)[number]) =>
    (link.matchPrefixes ?? [link.path]).some((prefix) => currentPath.startsWith(prefix));

  return (
    <header className="w-full bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="w-full max-w-[1440px] mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0">
          <button onClick={onGoHome} className="flex items-center gap-2 cursor-pointer shrink-0">
            <EduSyncMark size={24} />
            <span className="font-bold text-sm text-slate-900 tracking-tight whitespace-nowrap">{t('nav.brand')}</span>
          </button>

          <a
            href={CURSUS_URL}
            onClick={(e) => handleBackToCursusClick(e, CURSUS_URL)}
            title={t('nav.backToCursusTitle')}
            className="hidden sm:flex items-center gap-2 shrink-0 whitespace-nowrap text-xs font-semibold text-slate-500 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            {t('nav.backToCursus')}
          </a>

          <nav
            aria-label={t('nav.mainNavAriaLabel')}
            className="hidden xl:flex items-center gap-1 border-l border-slate-200 pl-4 text-sm font-medium text-slate-600 min-w-0"
          >
            {NAV_LINKS.map((link) => {
              const active = isActive(link);
              return (
                <button
                  key={link.path}
                  onClick={() => onNavigate(link.path)}
                  aria-current={active ? 'page' : undefined}
                  className={`px-3 py-2 rounded-[var(--radius-sm)] whitespace-nowrap shrink-0 transition-colors cursor-pointer ${
                    active ? 'text-[var(--accent)] bg-[var(--accent-soft)]' : 'hover:text-slate-900 hover:bg-slate-100'
                  }`}
                >
                  {link.label}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onOpenCommandPalette}
            aria-haspopup="dialog"
            aria-label={t('nav.searchTitle')}
            className="hidden sm:flex items-center gap-2 shrink-0 whitespace-nowrap text-slate-500 hover:text-slate-800 hover:bg-slate-100 px-3 py-2 rounded-[var(--radius-sm)] border border-slate-200 text-xs cursor-pointer transition-colors"
          >
            <Search className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            <span className="hidden xl:inline">{t('nav.searchPlaceholder')}</span>
            <kbd className="mono text-slate-400 text-[10px] px-1 py-0.5 rounded border border-slate-200 shrink-0" aria-hidden="true">Ctrl K</kbd>
          </button>

          <div className="hidden sm:flex items-center gap-2 pl-3 border-l border-slate-200 shrink-0">
            <LanguageToggle />
            <ThemeToggle />
          </div>

          {identity && <UserMenu identity={identity} roleLabel={ROLE_LABEL[identity.role]} cursusUrl={CURSUS_URL} />}

          <button
            onClick={() => setIsMobileMenuOpen((v) => !v)}
            aria-expanded={isMobileMenuOpen}
            aria-controls="mobile-nav-panel"
            aria-label={isMobileMenuOpen ? t('nav.closeMobileMenu') : t('nav.openMobileMenu')}
            className="xl:hidden shrink-0 text-slate-600 p-2 rounded-[var(--radius-sm)] border border-slate-200 transition-colors hover:bg-slate-100"
          >
            {isMobileMenuOpen ? <X className="w-4 h-4" aria-hidden="true" /> : <Menu className="w-4 h-4" aria-hidden="true" />}
          </button>
        </div>
      </div>

      {isMobileMenuOpen && (
        <nav
          id="mobile-nav-panel"
          aria-label={t('nav.mobileMenuAriaLabel')}
          className="xl:hidden bg-white border-t border-slate-200 px-4 py-2 space-y-1"
        >
          <a
            href={CURSUS_URL}
            onClick={(e) => handleBackToCursusClick(e, CURSUS_URL)}
            className="flex items-center gap-2 px-3 py-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 rounded-[var(--radius-sm)] transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" aria-hidden="true" />
            {t('nav.backToCursus')}
          </a>
          {NAV_LINKS.map((link) => {
            const active = isActive(link);
            return (
              <button
                key={link.path}
                onClick={() => {
                  onNavigate(link.path);
                  setIsMobileMenuOpen(false);
                }}
                aria-current={active ? 'page' : undefined}
                className={`w-full text-left px-3 py-2 text-xs font-medium rounded-[var(--radius-sm)] transition-colors ${
                  active ? 'text-[var(--accent)] bg-[var(--accent-soft)]' : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                {link.label}
              </button>
            );
          })}
          <div className="flex items-center gap-2 pt-2 mt-1 border-t border-slate-200">
            <LanguageToggle />
            <ThemeToggle />
          </div>
        </nav>
      )}
    </header>
  );
}
