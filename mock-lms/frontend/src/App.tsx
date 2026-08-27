import { useCallback, useEffect, useState } from 'react';
import { Navbar } from './components/Navbar';
import { Breadcrumbs, type BreadcrumbItem } from './components/Breadcrumbs';
import { CommandPalette } from './components/CommandPalette';
import { FeaturesHub } from './screens/FeaturesHub';
import { CurriculumView } from './screens/CurriculumView';
import { LearningPathView } from './screens/LearningPathView';
import { SyllabusSearch } from './screens/SyllabusSearch';
import { SyllabusDetails } from './screens/SyllabusDetails';
import { AssignmentsScreen } from './screens/AssignmentsScreen';
import { AssignmentDetailScreen } from './screens/AssignmentDetailScreen';
import { ApiError, getIdentity } from './lib/api';
import type { Identity } from './types';
import { useLanguage } from './context/LanguageContext';

type Route =
  | { view: 'hub' }
  | { view: 'curriculum' }
  | { view: 'learning-path'; code: string }
  | { view: 'search' }
  | { view: 'syllabus'; code: string }
  | { view: 'assignments' }
  | { view: 'assignment-detail'; code: string };

function parseRoute(pathname: string, search: string): Route {
  const params = new URLSearchParams(search);
  const syllabusMatch = pathname.match(/^\/courses\/syllabus\/([^/]+)\/?$/);
  if (syllabusMatch) return { view: 'syllabus', code: decodeURIComponent(syllabusMatch[1]) };

  const assignmentMatch = pathname.match(/^\/courses\/assignments\/([^/]+)\/?$/);
  if (assignmentMatch) return { view: 'assignment-detail', code: decodeURIComponent(assignmentMatch[1]) };

  if (pathname === '/courses/assignments') return { view: 'assignments' };
  if (pathname === '/courses/curriculum') return { view: 'curriculum' };
  if (pathname === '/courses/learning-path') return { view: 'learning-path', code: params.get('code') || 'CSI106' };
  if (pathname === '/courses/search') return { view: 'search' };
  return { view: 'hub' };
}

export function App() {
  const { t } = useLanguage();
  const [route, setRoute] = useState<Route>(() => parseRoute(window.location.pathname, window.location.search));
  const [identity, setIdentity] = useState<Identity | null>(null);
  // Stores a translation key (re-rendered through t() below), not the
  // translated string itself, so switching language mid-error updates it.
  const [identityError, setIdentityError] = useState<{ key: string; redirecting: boolean } | null>(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  useEffect(() => {
    getIdentity()
      .then(setIdentity)
      .catch((err) => {
        // A 401 here already triggered a real top-level navigation to
        // /sso/refresh (see lib/api.ts) -- showing the raw "session_expired"
        // message would just flash an error box right before the browser
        // navigates away, so show a friendly in-flight message instead.
        if (err instanceof ApiError && err.status === 401) {
          setIdentityError({ key: 'app.sessionExpired', redirecting: true });
          return;
        }
        setIdentityError({ key: 'app.identityLoadError', redirecting: false });
      });
  }, []);

  const navigate = useCallback((path: string) => {
    window.history.pushState(null, '', path);
    const url = new URL(path, window.location.origin);
    setRoute(parseRoute(url.pathname, url.search));
  }, []);

  useEffect(() => {
    const onPopState = () => setRoute(parseRoute(window.location.pathname, window.location.search));
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const goHome = useCallback(() => navigate('/courses'), [navigate]);
  const openSyllabus = useCallback((code: string) => navigate(`/courses/syllabus/${encodeURIComponent(code)}`), [navigate]);

  const breadcrumbFor = (): BreadcrumbItem[] => {
    switch (route.view) {
      case 'curriculum':
        return [{ label: t('breadcrumb.curriculum'), active: true }];
      case 'learning-path':
        return [{ label: t('breadcrumb.learningPath'), active: true }];
      case 'search':
        return [{ label: t('breadcrumb.search'), active: true }];
      case 'syllabus':
        return [
          { label: t('breadcrumb.search'), onClick: () => navigate('/courses/search') },
          { label: route.code, active: true },
        ];
      case 'assignments':
        return [{ label: t('breadcrumb.assignments'), active: true }];
      case 'assignment-detail':
        return [
          { label: t('breadcrumb.assignments'), onClick: () => navigate('/courses/assignments') },
          { label: route.code, active: true },
        ];
      default:
        return [];
    }
  };

  if (identityError) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center px-4">
        <div
          className={
            identityError.redirecting
              ? 'text-slate-500 text-sm text-center'
              : 'bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-5 max-w-md text-center'
          }
        >
          {t(identityError.key)}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar identity={identity} onGoHome={goHome} onNavigate={navigate} onOpenCommandPalette={() => setIsCommandPaletteOpen(true)} />
      {route.view !== 'hub' && <Breadcrumbs items={breadcrumbFor()} onHome={goHome} />}

      {!identity ? (
        <div className="max-w-5xl mx-auto px-5 py-16 text-center text-sm text-slate-400">{t('app.loading')}</div>
      ) : (
        <RouteView route={route} identity={identity} onNavigate={navigate} onOpenSyllabus={openSyllabus} />
      )}

      <CommandPalette isOpen={isCommandPaletteOpen} onClose={() => setIsCommandPaletteOpen(false)} onSelectSyllabus={openSyllabus} />
    </div>
  );
}

function RouteView({
  route,
  identity,
  onNavigate,
  onOpenSyllabus,
}: {
  route: Route;
  identity: Identity;
  onNavigate: (path: string) => void;
  onOpenSyllabus: (code: string) => void;
}) {
  switch (route.view) {
    case 'hub':
      return <FeaturesHub identity={identity} onNavigate={onNavigate} />;
    case 'curriculum':
      return <CurriculumView onSelectSubject={onOpenSyllabus} />;
    case 'learning-path':
      return <LearningPathView initialSubjectCode={route.code} onSelectSubject={onOpenSyllabus} />;
    case 'search':
      return <SyllabusSearch onSelectSyllabus={onOpenSyllabus} />;
    case 'syllabus':
      return (
        <SyllabusDetails
          code={route.code}
          onNavigate={onNavigate}
          onBackToSearch={() => onNavigate('/courses/search')}
        />
      );
    case 'assignments':
      return <AssignmentsScreen onNavigate={onNavigate} />;
    case 'assignment-detail':
      return <AssignmentDetailScreen code={route.code} identity={identity} />;
  }
}
