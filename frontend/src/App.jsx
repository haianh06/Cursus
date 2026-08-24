import React, { useState, useEffect, Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import {
  BookOpen, RotateCcw, BarChart2,
  LogOut, Sun, Moon, Globe, Menu, X, Bell, Search, ChevronDown,
  Sparkles, GraduationCap, LayoutDashboard, CheckSquare, FlaskConical, Target,
  MessageCircle, CalendarRange, NotebookPen, ExternalLink, CalendarClock, FileCheck2, ShieldAlert, Mail, ClipboardCheck, ShieldQuestion
} from 'lucide-react';
import { useTheme } from './context/ThemeContext';
import { useLanguage } from './context/LanguageContext';
import CursusMascot from './components/shared/CursusMascot';
import { CursusProvider, useCursus } from './context/CursusContext';
import { ROLE_LABEL, ROLE_DESC, DEFAULT_ROUTE } from './constants/roles';
import { getMe, logout as apiLogout, setAuthFailureHandler } from './lib/authClient';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Screens — LandingPage stays a static import: it's the public "/" route
// and must render with zero Suspense delay for anonymous visitors. Every
// auth screen below it is lazy: none of them are ever needed by a landing
// page visitor, so they no longer belong in the same JS chunk (previously
// they all shipped eagerly alongside the landing page bundle).
import LandingPage from './components/shared/LandingPage';
import CuriChatLauncher from './components/shared/CuriChatLauncher';
import SelfStudyReminder from './components/student/SelfStudyReminder';

const LoginScreen = lazy(() => import('./components/auth/LoginScreen'));
const AcceptInviteScreen = lazy(() => import('./components/auth/AcceptInviteScreen'));
const RequestAccessScreen = lazy(() => import('./components/auth/RequestAccessScreen'));
const DemoSelectRoleScreen = lazy(() => import('./components/auth/DemoSelectRoleScreen'));
const ForgotPasswordScreen = lazy(() => import('./components/auth/ForgotPasswordScreen'));
const ResetPasswordScreen = lazy(() => import('./components/auth/ResetPasswordScreen'));
const EmailVerificationScreen = lazy(() => import('./components/auth/EmailVerificationScreen'));
const OnboardingScreen = lazy(() => import('./components/auth/OnboardingScreen'));
const SettingsScreen = lazy(() => import('./components/shared/SettingsScreen'));
const NotFoundPage = lazy(() => import('./components/shared/NotFoundPage'));
const PrivacyPolicyScreen = lazy(() => import('./components/legal/PrivacyPolicyScreen'));
const TermsOfServiceScreen = lazy(() => import('./components/legal/TermsOfServiceScreen'));

import { Gate2Provider } from './context/Gate2Context';
// Also statically imported by ProtectedRoute.jsx (which is itself eager),
// so lazy-loading it here would be a no-op split — kept as a normal import
// to match what actually ends up in the bundle.
import UnauthorizedPage from './components/shared/UnauthorizedPage';
import Skeleton from './components/shared/Skeleton';

// Role dashboards are code-split per role so a Student session never
// downloads Instructor/Admin JS (and vice versa) — previously all three
// shipped in the same bundle as the landing page.
const StudentHome = lazy(() => import('./components/student/StudentHome'));
const StudentPlanner = lazy(() => import('./components/student/StudentPlanner'));
const StudentReflection = lazy(() => import('./components/student/StudentReflection'));
const InstructorHome = lazy(() => import('./components/instructor/InstructorHome'));
const InstructorRiskPage = lazy(() => import('./components/instructor/InstructorRiskPage'));
const InstructorStudentProfile = lazy(() => import('./components/instructor/InstructorStudentProfile'));
const InstructorQuizManager = lazy(() => import('./components/instructor/InstructorQuizManager'));
const InstructorClassActivityPanel = lazy(() => import('./components/instructor/InstructorClassActivityPanel'));
const InstructorDigestPage = lazy(() => import('./components/instructor/InstructorDigestPage'));
const AssignmentSubmissionsPanel = lazy(() => import('./components/instructor/AssignmentSubmissionsPanel'));
const GuardrailReviewQueue = lazy(() => import('./components/GuardrailReviewQueue'));

import AdminNavigation from './components/admin/AdminNavigation';

const AdminConsole = lazy(() => import('./components/admin/AdminConsole'));
const AdminStudent360 = lazy(() => import('./components/admin/AdminStudent360'));
const AdminInstructor360 = lazy(() => import('./components/admin/AdminInstructor360'));
// Additive student surface (semester setup, practice sets, companion chat) —
// wired to the new backend endpoints in semester.py / practice.py /
// companion.py. Kept as separate routes, never a gate in front of the
// existing Gate2 demo flow above.
const SemesterSetupWizard = lazy(() => import('./components/student/SemesterSetupWizard'));
const StudentPractice = lazy(() => import('./components/student/StudentPractice'));
const StudentCompanionPage = lazy(() => import('./components/student/CourseCompanionChat'));
// Second, independent plan-generation flow (timetable/lecture sessions, not
// assignments) — coexists with Gate2's PlanBuilder, never wired into it.
const LecturePlanPanel = lazy(() => import('./components/student/LecturePlanPanel'));
// Self-Study Pomodoro: day-focused checklist + timer runner for one timetable
// block (src/services/academic/self_study_service.py). Timetable.jsx already
// links to both of these; they just weren't routed yet.
const TodayPlanScreen = lazy(() => import('./components/student/TodayPlanScreen'));
const SelfStudySession = lazy(() => import('./components/student/SelfStudySession'));
const StudentQuizzes = lazy(() => import('./components/student/StudentQuizzes'));

function RoutePageFallback() {
  return (
    <div className="flex flex-col gap-4 p-6">
      <Skeleton className="h-14 w-full rounded-xl" />
      <Skeleton className="h-24 w-full rounded-2xl" />
      <Skeleton className="h-64 w-full rounded-2xl" />
    </div>
  );
}

// State system components
import OfflineBanner from './components/shared/OfflineBanner';
import SeoManager from './components/shared/SeoManager';
import LandingLogoMark from './components/landing/LandingLogoMark';
import ApiErrorScreen, { ConnectionBanner } from './components/shared/ApiErrorScreen';
import { FatalErrorScreen } from './components/shared/FatalErrorScreen';
import ScrollToTop from './components/shared/ScrollToTop';


/* ── SIDEBAR ── */
function Sidebar({ user, onLogout, open, setOpen, activeSection }) {
  const { theme, toggleTheme } = useTheme();
  const { t, lang, toggleLang } = useLanguage();
  const location = useLocation();
  const navigate = useNavigate();

  const handleItemClick = (path, sectionId) => {
    setOpen(false);
    navigate(path);

    // Scroll to section if specified
    if (sectionId) {
      setTimeout(() => {
        const el = document.getElementById(sectionId);
        if (el) {
          el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 150);
    }
  };

  const handleLogout = async () => {
    setOpen(false);
    await onLogout();
    navigate(user.isDemo ? '/request-access' : '/login', { replace: true });
  };

  return (
    <>
      {/* Mobile backdrop */}
      {open && (
        <div className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setOpen(false)} />
      )}

      <aside className={`
        fixed top-0 left-0 z-30 h-full flex flex-col sidebar
        transition-transform duration-300 ease-out
        ${open ? 'translate-x-0' : '-translate-x-full'}
        lg:relative lg:translate-x-0 lg:z-auto
      `} style={{ width: 220 }}>

        {/* Brand Logo — same LandingLogoMark used everywhere else in the app
            (landing, auth, error screen). The sidebar itself is always dark
            navy regardless of the app's light/dark theme (--sidebar-bg), so
            the mark's colors are fixed here rather than theme-token-driven. */}
        <div className="flex items-center gap-2.5 px-4 py-4 border-b" style={{ borderColor: 'var(--sidebar-border)' }}>
          <span className="shrink-0 transition-transform duration-300 hover:scale-110">
            <LandingLogoMark size={22} strokeClassName="text-white" dotClassName="fill-brand-blue" />
          </span>
          <span className="font-display font-black text-sm text-white tracking-tight">Cursus</span>
          <button className="btn-ghost ml-auto p-1 lg:hidden text-slate-400" onClick={() => setOpen(false)}
            aria-label="Đóng menu">
            <X size={15} />
          </button>
        </div>

        {/* Selector Role Box (Dropdown look alike) */}
        <div className="px-3 py-3 border-b" style={{ borderColor: 'var(--sidebar-border)' }}>
          <div className="flex items-center justify-between p-2.5 rounded-[var(--radius-md)] bg-white/[0.04] border border-white/10 text-left transition-colors duration-200 hover:bg-white/[0.07] hover:border-white/15">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-white truncate">
                <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: 'var(--brand-blue-text-dark)' }} aria-hidden="true" />
                <span className="truncate">{user.name} ({(ROLE_LABEL[lang] || ROLE_LABEL.vi)[user.role]})</span>
              </div>
              <div className="text-[10px] text-slate-400 truncate mt-0.5 pl-3">
                {(ROLE_DESC[lang] || ROLE_DESC.vi)[user.role]}
              </div>
            </div>
            <ChevronDown size={12} className="text-sidebar-text shrink-0 ml-1.5" />
          </div>
        </div>

        {/* Sidebar Nav Items — only the current role's own pages are shown */}
        <nav className="flex-1 px-2 py-3 space-y-1 overflow-y-auto">
          <p className="px-2 pb-1 text-[9px] font-bold uppercase tracking-widest text-sidebar-text">
            {lang === 'vi' ? 'Không gian làm việc' : 'Workspace'}
          </p>

          {user.role === 'student' && (
            <>
              {/* 1. Dashboard */}
              <button
                aria-current={((location.pathname === '/student' || location.pathname === '/student/') && activeSection === 'top') ? 'page' : undefined}
                className={`nav-item w-full text-left ${((location.pathname === '/student' || location.pathname === '/student/') && activeSection === 'top') ? 'active' : ''}`}
                onClick={() => handleItemClick('/student', 'top')}
              >
                <LayoutDashboard size={15} />
                <span>{t('nav.overview')}</span>
              </button>

              {/* 2. Weekly planner (Plan step) */}
              <button
                aria-current={location.pathname === '/student/planner' ? 'page' : undefined}
                className={`nav-item w-full text-left ${location.pathname === '/student/planner' ? 'active' : ''}`}
                onClick={() => handleItemClick('/student/planner')}
              >
                <Target size={15} />
                <span>{t('nav.weeklyPlan')}</span>
              </button>

              {/* Semester setup + lecture plan are reachable via deep link only
                  (onboarding step 2, LecturePlanPanel's own "Sửa học kỳ" link) —
                  matches a46db63, which never gave these a sidebar entry. */}

              {/* 3. Today's Plan (Do step) — real day view + checklist
                  (src/services/academic/self_study_service.py), not just a
                  scroll-anchor on the dashboard. */}
              <button
                aria-current={location.pathname === '/student/today' ? 'page' : undefined}
                className={`nav-item w-full text-left ${location.pathname === '/student/today' ? 'active' : ''}`}
                onClick={() => handleItemClick('/student/today')}
              >
                <CheckSquare size={15} />
                <span>{t('nav.todayPlan')}</span>
              </button>

              {/* 3. Phản tư */}
              <button
                aria-current={location.pathname === '/student/reflection' ? 'page' : undefined}
                className={`nav-item w-full text-left ${location.pathname === '/student/reflection' ? 'active' : ''}`}
                onClick={() => handleItemClick('/student/reflection')}
              >
                <RotateCcw size={15} />
                <span>{t('nav.reflection')}</span>
              </button>

              {/* 4. Practice sets */}
              <button
                aria-current={location.pathname === '/student/practice' ? 'page' : undefined}
                className={`nav-item w-full text-left ${location.pathname === '/student/practice' ? 'active' : ''}`}
                onClick={() => handleItemClick('/student/practice')}
              >
                <FlaskConical size={15} />
                <span>{t('nav.practice')}</span>
              </button>

              {/* Companion chat has no sidebar entry in a46db63 — it's the
                  floating CompanionChatBubble on every student page, not a
                  standalone route. Quizzes (post-a46db63 feature) also has no
                  sidebar entry, per explicit request to match a46db63's exact
                  5-item sidebar — the /student/quizzes route still works via
                  deep link, only the nav button is removed. */}
            </>
          )}

          {user.role === 'instructor' && (
            <>
              <button
                className={`nav-item w-full text-left ${location.pathname === '/instructor' ? 'active' : ''}`}
                onClick={() => handleItemClick('/instructor')}
              >
                <BarChart2 size={15} />
                <span>{t('nav.instructorHome')}</span>
              </button>
              <button
                className={`nav-item w-full text-left ${location.pathname === '/instructor/risks' ? 'active' : ''}`}
                onClick={() => handleItemClick('/instructor/risks')}
              >
                <ShieldAlert size={15} />
                <span>Rủi ro & Cảnh báo</span>
              </button>
              <button
                className={`nav-item w-full text-left ${location.pathname === '/instructor/activities' ? 'active' : ''}`}
                onClick={() => handleItemClick('/instructor/activities')}
              >
                <CalendarClock size={15} />
                <span>Hoạt động lớp</span>
              </button>
              <button
                className={`nav-item w-full text-left ${location.pathname === '/instructor/quizzes' ? 'active' : ''}`}
                onClick={() => handleItemClick('/instructor/quizzes')}
              >
                <BookOpen size={15} />
                <span>Quản lý Quiz</span>
              </button>
              <button
                className={`nav-item w-full text-left ${location.pathname === '/instructor/submissions' ? 'active' : ''}`}
                onClick={() => handleItemClick('/instructor/submissions')}
              >
                <FileCheck2 size={15} />
                <span>Bài tập nộp</span>
              </button>
              <button
                className={`nav-item w-full text-left ${location.pathname === '/instructor/digest' ? 'active' : ''}`}
                onClick={() => handleItemClick('/instructor/digest')}
              >
                <Mail size={15} />
                <span>Digest</span>
              </button>
              <button
                className={`nav-item w-full text-left ${location.pathname === '/instructor/guardrail-reviews' ? 'active' : ''}`}
                onClick={() => handleItemClick('/instructor/guardrail-reviews')}
              >
                <ShieldQuestion size={15} />
                <span>Xét duyệt Guardrail</span>
              </button>
            </>
          )}

          {user.role === 'admin' && (
            <AdminNavigation onNavigate={() => setOpen(false)} />
          )}
        </nav>

        {/* Bottom controls */}
        <div className="px-2 py-3 border-t space-y-0.5" style={{ borderColor: 'var(--sidebar-border)' }}>
          <button id="theme-toggle" className="nav-item w-full" onClick={toggleTheme}>
            {theme === 'dark' ? <Sun size={14}/> : <Moon size={14}/>}
            <span>{theme === 'dark' ? (lang === 'vi' ? 'Chế độ sáng' : 'Light mode') : (lang === 'vi' ? 'Chế độ tối' : 'Dark mode')}</span>
          </button>
          <button id="lang-toggle" className="nav-item w-full justify-between" onClick={toggleLang}>
            <div className="flex items-center gap-3">
              <Globe size={14}/>
              <span>{lang === 'vi' ? 'Ngôn ngữ' : 'Language'}</span>
            </div>
            <div className="flex gap-1 text-[9px] font-bold">
              <span className={`px-1 rounded ${lang === 'vi' ? 'bg-accent-cta text-white' : 'text-sidebar-text'}`}>VI</span>
              <span className={`px-1 rounded ${lang === 'en' ? 'bg-accent-cta text-white' : 'text-sidebar-text'}`}>EN</span>
            </div>
          </button>
          <button id="logout-btn" className="nav-item w-full text-red-400 hover:text-red-300" onClick={handleLogout}>
            <LogOut size={14}/>
            <span>{lang === 'vi' ? 'Đăng xuất' : 'Sign out'}</span>
          </button>
        </div>
      </aside>
    </>
  );
}

/* ── NOTIFICATIONS ── */
function NotificationsBell({ lang }) {
  const { notifications, markNotificationRead, markAllNotificationsRead } = useCursus();
  const [open, setOpen] = useState(false);
  const ref = React.useRef(null);
  const unread = notifications.filter((n) => !n.read).length;

  useEffect(() => {
    if (!open) return undefined;
    const onOutside = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onEsc = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onOutside);
    document.addEventListener('keydown', onEsc);
    return () => {
      document.removeEventListener('mousedown', onOutside);
      document.removeEventListener('keydown', onEsc);
    };
  }, [open]);

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        className="btn-ghost p-2 rounded-lg text-slate-500 dark:text-slate-400 relative cursor-pointer"
        onClick={() => setOpen((v) => !v)}
        aria-label={lang === 'vi' ? 'Thông báo' : 'Notifications'}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Bell size={16} />
        {unread > 0 && (
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-red-500 ring-2 ring-surface-card" aria-hidden="true" />
        )}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label={lang === 'vi' ? 'Danh sách thông báo' : 'Notifications list'}
          className="absolute right-0 top-full mt-2 w-80 max-w-[calc(100vw-2rem)] max-h-96 overflow-y-auto rounded-[var(--radius-md)] bg-surface-card border border-line shadow-elevation-2 animate-scale-in z-50 text-left"
        >
          <div className="flex items-center justify-between px-4 py-3 border-b border-line sticky top-0 bg-surface-card">
            <span className="text-xs font-bold text-fg">{lang === 'vi' ? 'Thông báo' : 'Notifications'}</span>
            {unread > 0 && (
              <button type="button" className="text-[10px] font-bold text-accent-text-safe cursor-pointer" onClick={markAllNotificationsRead}>
                {lang === 'vi' ? 'Đánh dấu đã đọc tất cả' : 'Mark all read'}
              </button>
            )}
          </div>
          {notifications.length === 0 ? (
            <p className="text-xs text-fg-muted text-center py-6">{lang === 'vi' ? 'Không có thông báo nào' : 'No notifications'}</p>
          ) : (
            <div className="divide-y divide-line">
              {notifications.map((n) => (
                <button
                  type="button"
                  key={n.id}
                  onClick={() => markNotificationRead(n.id)}
                  className={`w-full text-left px-4 py-3 text-xs hover:bg-surface-elevated cursor-pointer transition-colors flex items-start gap-2 ${n.read ? 'text-fg-muted' : 'text-fg font-semibold'}`}
                >
                  {!n.read && <span className="w-1.5 h-1.5 rounded-full bg-accent mt-1 shrink-0" aria-hidden="true" />}
                  <span className={n.read ? 'ml-3.5' : ''}>
                    <span className="block">{n.title}</span>
                    <span className="mono text-[10px] text-fg-muted mt-0.5 block">
                      {new Date(n.timestamp).toLocaleString(lang === 'vi' ? 'vi-VN' : 'en-US', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── TOPBAR ── */
function Topbar({ user, setSidebarOpen }) {
  const { theme, toggleTheme } = useTheme();
  const { t, lang, toggleLang } = useLanguage();
  const navigate = useNavigate();
  return (
    <header className="h-14 flex items-center gap-3 px-4 border-b border-line shrink-0 bg-surface-card">
      <button className="btn-ghost lg:hidden p-1 rounded-md" onClick={() => setSidebarOpen(true)}>
        <Menu size={18} className="text-fg-secondary" />
      </button>

      {/* Semester indicator */}
      <div className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" aria-hidden="true" />
        <span className="text-xs font-semibold text-fg-secondary">
          {t('common.semesterInfo')}
        </span>
      </div>

      {/* EduSync (hệ thống môn học ngoài, đóng vai Canvas -- mục 6.6, tên nội
          bộ vẫn là "Mock LMS" trong code/docs, không hiện ra UI) — mở tab
          mới, tự đăng nhập qua SSO danh tính Cursus (ADR-020), không cần
          nhập tài khoản gì thêm. Hiện cho cả 3 role vì Topbar dùng chung 1
          component. */}
      <a
        href={`${import.meta.env.VITE_MOCK_LMS_URL || 'http://localhost:9000'}/courses`}
        target="_blank"
        rel="noopener noreferrer"
        className="btn-ghost hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-fg-secondary hover:text-fg"
        title={lang === 'vi' ? 'Mở hệ thống môn học ngoài (EduSync) ở tab mới' : 'Open the external course platform (EduSync) in a new tab'}
      >
        <ExternalLink size={13} />
        EduSync
      </a>

      <div className="flex-1" />

      {/* Search box — disabled until functional */}
      <div className="relative hidden md:block w-56">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-fg-muted" />
        <input
          type="text"
          className="input pr-8 py-1.5 text-xs bg-surface"
          // `.input` (index.css) sets its own shorthand `padding`, which wins
          // over the `pl-9` Tailwind utility under this Tailwind v4 cascade
          // — collapsing left padding back to 14px against a search icon
          // that needs ~36px of clearance, so the icon sat on top of the
          // placeholder text. Inline style has the specificity to actually
          // win instead of silently losing to `.input` again.
          style={{ paddingLeft: '2.25rem' }}
          placeholder={t('common.searchPlaceholder')}
          disabled
          aria-label={t('common.searchPlaceholder')}
        />
      </div>

      {/* Notifications */}
      <NotificationsBell lang={lang} />

      {/* Theme toggle */}
      <button className="btn-ghost p-2 rounded-lg text-fg-muted" onClick={toggleTheme} aria-label={theme === 'dark' ? 'Chuyển sang giao diện sáng' : 'Chuyển sang giao diện tối'}>
        {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
      </button>

      {/* Language toggle (consolidated, topbar only for students — sidebar keeps for all roles) */}
      <button className="btn-ghost p-1.5 rounded-lg flex items-center gap-1 text-xs" onClick={toggleLang} aria-label={lang === 'vi' ? 'Switch to English' : 'Chuyển sang tiếng Việt'}>
        <span className={`px-1.5 py-0.5 rounded font-bold ${lang === 'vi' ? 'bg-accent-cta text-white' : 'text-fg-muted'}`}>VI</span>
        <span className={`px-1.5 py-0.5 rounded font-bold ${lang === 'en' ? 'bg-accent-cta text-white' : 'text-fg-muted'}`}>EN</span>
      </button>

      {/* Profile / settings */}
      <button
        type="button"
        className="btn-ghost p-1.5 rounded-lg flex items-center gap-2 cursor-pointer"
        onClick={() => navigate(`/${user.role}/settings`)}
        aria-label={lang === 'vi' ? 'Hồ sơ và cài đặt' : 'Profile and settings'}
      >
        <span className="w-7 h-7 rounded-full bg-accent-soft text-accent-text-safe flex items-center justify-center text-[11px] font-bold shrink-0 select-none">
          {user.name?.trim()?.[0]?.toUpperCase() || '?'}
        </span>
        <span className="hidden lg:block text-xs font-semibold text-fg-secondary max-w-[100px] truncate">{user.name}</span>
      </button>
    </header>
  );
}

/* ── DEMO MODE BANNER ── */
/* ── APP SHELL ── */
function InstructorRoutes({ user }) {
  return (
    <Routes>
      <Route path="/" element={<InstructorHome user={user}/>} />
      <Route path="students/:studentId" element={<InstructorStudentProfile />} />
      <Route path="digest" element={<InstructorDigestPage />} />
      <Route path="risks" element={<InstructorRiskPage />} />
      <Route path="activities" element={<InstructorClassActivityPanel />} />
      <Route path="quizzes" element={<InstructorQuizManager />} />
      <Route path="submissions" element={<AssignmentSubmissionsPanel />} />
      <Route path="guardrail-reviews" element={<GuardrailReviewQueue />} />
      <Route path="*" element={<NotFoundPage/>}/>
    </Routes>
  );
}

function AppShell({ user, onLogout, onUserUpdate }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('top');
  const mainRef = React.useRef(null);

  React.useEffect(() => {
    const mainEl = mainRef.current;
    if (!mainEl || user.role !== 'student') return;

    const sections = ['top', 'weekly-plan-section', 'qa-section'];
    
    const observerOptions = {
      root: mainEl,
      rootMargin: '-50px 0px -50% 0px',
      threshold: 0,
    };

    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setActiveSection(entry.target.id);
        }
      });
    }, observerOptions);

    sections.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    const handleScroll = () => {
      if (mainEl.scrollTop < 50) {
        setActiveSection('top');
      }
    };
    mainEl.addEventListener('scroll', handleScroll);

    return () => {
      observer.disconnect();
      mainEl.removeEventListener('scroll', handleScroll);
    };
  }, [user.role]);

  // The student slice reads/writes one canonical state (Gate2Provider →
  // real backend). Other roles don't need it, so it is not mounted for them.
  const withStudentState = (node) =>
    user.role === 'student' ? <Gate2Provider>{node}</Gate2Provider> : node;

  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      {user.role === 'student' && <SelfStudyReminder />}
      <Sidebar
        user={user}
        onLogout={onLogout}
        open={sidebarOpen}
        setOpen={setSidebarOpen}
        activeSection={activeSection}
      />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar user={user} setSidebarOpen={setSidebarOpen} />
        <main ref={mainRef} className="flex-1 overflow-y-auto bg-surface bg-grid">
          {withStudentState(
          <Suspense fallback={<RoutePageFallback />}>
          {user.role === 'admin' ? (
            // AdminConsole owns everything else under /admin/* through its
            // own nested <Routes> (overview, people, courses, ... -- see
            // AdminConsole.jsx). A literal "settings" segment has to be
            // declared here, ahead of the "/*" splat, because AdminConsole
            // separately owns "org-settings" (org-wide config) at that same
            // depth -- v6 ranks a static segment above a splat regardless
            // of declaration order, so this always resolves to the
            // account-level Settings screen, never AdminConsole's tab.
            <Routes>
              <Route path="settings" element={<SettingsScreen user={user} onLogout={onLogout}/>} />
              <Route path="students/:studentId" element={<AdminStudent360 user={user}/>} />
              <Route path="instructors/:instructorId" element={<AdminInstructor360 user={user}/>} />
              <Route path="/*" element={<AdminConsole user={user}/>} />
            </Routes>
          ) : user.role === 'instructor' ? (
            // InstructorRoutes owns everything else under /instructor/*
            // through its own nested <Routes> (risks, quizzes, digest, ...).
            <Routes>
              <Route path="settings" element={<SettingsScreen user={user} onLogout={onLogout}/>} />
              <Route path="/*" element={<InstructorRoutes user={user}/>} />
            </Routes>
          ) : (
            <Routes>
              <Route path="/"           element={<StudentHome user={user}/>} />
              <Route path="settings"    element={<SettingsScreen user={user} onLogout={onLogout}/>} />
              <Route path="planner"     element={<StudentPlanner user={user}/>} />
              <Route path="reflection"  element={<StudentReflection user={user}/>} />
              <Route path="practice"        element={<StudentPractice user={user}/>} />
              <Route path="companion"       element={<StudentCompanionPage user={user}/>} />
              <Route path="semester-setup"  element={<SemesterSetupWizard user={user}/>} />
              <Route path="lecture-plan"    element={<LecturePlanPanel user={user}/>} />
              <Route path="quizzes"         element={<StudentQuizzes />} />
              <Route path="today"           element={<TodayPlanScreen user={user}/>} />
              <Route path="self-study/:blockId" element={<SelfStudySession user={user}/>} />
              <Route path="*"            element={<NotFoundPage/>}/>
            </Routes>
          )}
          </Suspense>,
          )}
        </main>
      </div>
    </div>
  );
}

/* Browsers default `history.scrollRestoration` to "auto", which replays the
   scroll offset from the last visit on every reload — on a long page like
   the landing page this makes a plain refresh look like it "jumps" to a
   random section instead of opening at the top. We take manual control:
   reload/first load with no #hash always starts at the top; a real deep
   link (e.g. "/#playground") still scrolls to that section. */
if (typeof window !== 'undefined' && 'scrollRestoration' in window.history) {
  window.history.scrollRestoration = 'manual';
}

function ScrollManager() {
  const { pathname, hash } = useLocation();
  const isFirstRun = React.useRef(true);

  useEffect(() => {
    // A hard reload (or the very first paint) always opens at the top —
    // full stop. A `#hash` still sitting in the address bar from a nav
    // click 2 reloads ago should not silently jump the page back down;
    // that's exactly the confusing behavior being fixed here. Strip it so
    // the URL matches what's actually on screen.
    if (isFirstRun.current) {
      isFirstRun.current = false;
      window.scrollTo(0, 0);
      if (hash) {
        window.history.replaceState(null, '', pathname + window.location.search);
      }
      return;
    }

    if (hash) {
      // In-app nav click while already on the page — this one legitimately
      // means "scroll me to this section".
      const id = hash.slice(1);
      const scrollToTarget = () => document.getElementById(id)?.scrollIntoView({ block: 'start' });
      const timers = [0, 60, 200, 500].map((delay) => setTimeout(scrollToTarget, delay));
      return () => timers.forEach(clearTimeout);
    }
    window.scrollTo(0, 0);
  }, [pathname, hash]);

  return null;
}

/* Already-signed-in visitor landing on a public/auth-only route (/, /login,
   /register, /forgot-password) — bounce to the right next step instead of
   letting them see that screen again. */
function AuthedElsewhereRedirect({ user }) {
  if (!user.email_confirmed) return <Navigate to="/email-verification" replace />;
  if (!user.onboarded) return <Navigate to="/onboarding" replace />;
  return <Navigate to={DEFAULT_ROUTE[user.role]} replace />;
}

/* ── ROOT ── */
export default function App() {
  const { theme } = useTheme();
  const [user, setUser] = useState(null);
  // Explicit auth states: initializing -> unauthenticated | authenticated |
  // email_unverified | error. (`authenticating` lives in LoginScreen's own
  // `loading`; `session_expired` is handled via the auth-failure handler
  // below, which redirects straight to /login; `unauthorized` is a per-route
  // render in ProtectedRoute, not a global state.)
  const [authStatus, setAuthStatus] = useState('initializing');
  const [loading, setLoading] = useState(true);
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [mascotLoadState, setMascotLoadState] = useState('thinking');

  const runSessionProbe = React.useCallback(() => {
    setAuthStatus('initializing');
    return getMe()
      .then((profile) => {
        const nextUser = {
          id: profile.id,
          name: profile.full_name,
          email: profile.email,
          role: profile.role.toLowerCase(), // Ensure lowercase role for client router
          onboarded: profile.onboarded,
          major: profile.major || null,
          studentCode: profile.student_code || null,
          email_confirmed: profile.is_email_verified,
          isDemo: Boolean(profile.is_demo),
          organizationName: profile.organization_name || null,
          preferences: profile.preferences || {},
        };
        setUser(nextUser);
        setAuthStatus(nextUser.email_confirmed ? 'authenticated' : 'email_unverified');
      })
      .catch((err) => {
        setUser(null);
        if (err?.status === 401) {
          setAuthStatus('unauthenticated');
        } else {
          // Network/5xx — distinct from "not logged in" so the UI can offer
          // a retry instead of silently dropping the visitor to the landing page.
          console.warn('Auth check failed:', err);
          setAuthStatus('error');
        }
      });
  }, []);

  // Force logout + redirect to /login on any 401/403 from an authenticated
  // call elsewhere in the app (session expired mid-use). The bootstrap probe
  // above suppresses this handler (`suppressAuthHandler`), so a guest never
  // trips it on first load.
  useEffect(() => {
    setAuthFailureHandler(() => {
      setUser(null);
      setAuthStatus('session_expired');
      const returnTo = encodeURIComponent(window.location.pathname + window.location.search);
      window.location.assign(`/login?returnTo=${returnTo}&reason=session_expired`);
    });
    return () => setAuthFailureHandler(null);
  }, []);

  useEffect(() => {
    // Sync font and font-size settings from local storage
    const savedFontVal = localStorage.getItem('cursus_font_val');
    if (savedFontVal) {
      document.documentElement.style.setProperty('--font-family-custom', savedFontVal);
    }
    const savedFontSizeVal = localStorage.getItem('cursus_font_size_val');
    if (savedFontSizeVal) {
      document.documentElement.style.setProperty('--font-size-adjust', savedFontSizeVal);
    }

    // Get current active session from FastAPI backend
    runSessionProbe().finally(() => {
        // Trigger loading completion states
        setMascotLoadState('celebrate');
        setTimeout(() => {
          setIsFadingOut(true);
          setTimeout(() => {
            setLoading(false);
          }, 300); // 300ms fade-out duration
        }, 320); // wait 320ms for happy blink / chest pulse complete sequence
      });
  }, [runSessionProbe]);

  const logout = async () => {
    try {
      await apiLogout();
    } catch (e) {
      console.error("Logout request failed:", e);
    } finally {
      setUser(null);
    }
  };

  // The public landing page must render instantly for anonymous visitors —
  // it doesn't need to wait on the session probe below. `user` starts out
  // `null`, so LandingPage already renders under the hood while `loading`
  // is true; only the branded overlay was hiding it. Session-gated routes
  // (dashboards, auth screens) still show the overlay so they don't flash
  // the wrong screen before redirecting.
  const isPublicLandingRoute = window.location.pathname === '/';

  return (
    <FatalErrorScreen>
      <CursusProvider user={user}>
        <BrowserRouter>
          <ScrollManager />
          <SeoManager />
          {/* Global network connectivity watcher — always mounted */}
          <OfflineBanner />
          {loading && !isPublicLandingRoute && (
          <div
            id="cursus-loader-overlay"
            className={`fixed inset-0 z-[100] flex flex-col items-center justify-center bg-surface transition-all duration-350 ease-out ${
              isFadingOut ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100'
            }`}
          >
            {/* Circular Bubble Container */}
            <div className="relative flex items-center justify-center w-[200px] h-[200px] md:w-[260px] md:h-[260px]">

              {/* Asymmetric Floating Learning Icon 1: Book (hidden on small mobile screens) */}
              <div className="absolute -top-4 left-1/4 curi-icon-float-1-anim hidden sm:flex w-8.5 h-8.5 items-center justify-center bg-surface-card rounded-[var(--radius-sm)] border border-line shadow-elevation-1">
                <BookOpen size={16} className="text-accent" />
              </div>

              {/* Asymmetric Floating Learning Icon 2: Graduation Cap */}
              <div className="absolute -bottom-2 right-6 curi-icon-float-2-anim hidden sm:flex w-8.5 h-8.5 items-center justify-center bg-surface-card rounded-[var(--radius-sm)] border border-line shadow-elevation-1">
                <GraduationCap size={16} className="text-gold" />
              </div>

              {/* Asymmetric Floating Learning Icon 3: Sparkles */}
              <div className="absolute top-12 -left-6 curi-icon-float-3-anim hidden sm:flex w-8.5 h-8.5 items-center justify-center bg-surface-card rounded-[var(--radius-sm)] border border-line shadow-elevation-1">
                <Sparkles size={14} className="text-gold fill-gold/80" />
              </div>

              {/* Borderless, soft feathered circular bubble (radial gradient driven) —
                  navy-blue "sky" glow, same rgba(20,49,92,…) used behind the mascot
                  everywhere else (chat launcher, auth screens) so every appearance
                  of the mascot reads as one consistent character, not a different
                  accent color depending on which screen happens to render it
                  (this one used to be amber, unrelated to the mascot's own colors). */}
              <div
                className="w-[185px] h-[185px] md:w-[240px] md:h-[240px] rounded-full flex flex-col items-center justify-center relative"
                style={{
                  background: theme === 'dark'
                    ? 'radial-gradient(circle at 30% 20%, rgba(26,27,31,0.95) 0%, rgba(20,49,92,0.22) 50%, rgba(148,163,184,0.06) 100%)'
                    : 'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.95) 0%, rgba(20,49,92,0.14) 50%, rgba(148,163,184,0.08) 100%)'
                }}
              >
                {/* Subtle soft shadow underneath the mascot */}
                <div className="absolute bottom-[24px] md:bottom-[32px] w-[70px] h-[7px] md:w-[96px] md:h-[9px] bg-black/10 dark:bg-black/25 rounded-full blur-[2.5px]" />

                {/* Mascot (size w-130px mobile, w-170px desktop) */}
                <div className="curi-float-slow-anim curi-breath-anim z-10 flex items-center justify-center w-[130px] h-[130px] md:w-[170px] md:h-[170px]">
                  <CursusMascot size="100%" className="w-full h-full" state={mascotLoadState} />
                </div>
              </div>
            </div>

            {/* Typography Description */}
            <h1 className="font-display font-bold text-[20px] text-fg mt-6 tracking-tight px-4 text-center">
              Trợ lý Cursus đang chuẩn bị không gian học tập
            </h1>
            <p className="font-sans text-[15px] text-fg-muted mt-2 px-6 text-center leading-relaxed max-w-[340px]" style={{ lineHeight: '1.6' }}>
              Đang tải kế hoạch, học liệu và tiến độ của bạn...
            </p>

            {/* Brand-accent loading dots (teal / gold / teal-hover) */}
            <div className="flex items-center gap-1.5 mt-4 justify-center">
              <span className="w-2.5 h-2.5 rounded-full bg-accent animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-2.5 h-2.5 rounded-full bg-gold animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-2.5 h-2.5 rounded-full bg-[var(--accent-hover)] animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
          )}
          <Suspense fallback={null}>
          <Routes>

            {/* Landing page — always renders; ConnectionBanner overlays on API error */}
            <Route path="/" element={
              user ? (
                <AuthedElsewhereRedirect user={user} />
              ) : (
                <>
                  {authStatus === 'error' && (
                    <ConnectionBanner onRetry={runSessionProbe} />
                  )}
                  <LandingPage />
                </>
              )
            }/>

            {/* Non-landing routes: show full-page ApiErrorScreen when server is down.
                ScrollManager + OfflineBanner already run, so no router-bypass needed. */}
            <Route path="/login" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : user ? <AuthedElsewhereRedirect user={user} /> : <LoginScreen />
            }/>

            <Route path="/accept-invite" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : user ? <AuthedElsewhereRedirect user={user} /> : <AcceptInviteScreen />
            }/>

            <Route path="/request-access" element={<RequestAccessScreen />} />

            <Route path="/privacy" element={<PrivacyPolicyScreen />} />
            <Route path="/terms" element={<TermsOfServiceScreen />} />

            <Route path="/demo/select-role" element={<DemoSelectRoleScreen />} />

            <Route path="/forgot-password" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : user ? <AuthedElsewhereRedirect user={user} /> : <ForgotPasswordScreen />
            }/>

            <Route path="/reset-password" element={<ResetPasswordScreen />} />

            <Route path="/email-verification" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : user ? (
                user.email_confirmed ? <Navigate to="/onboarding" replace /> :
                <EmailVerificationScreen user={user} onLogout={logout} />
              ) : <Navigate to="/login" replace />
            } />

            {/* Onboarding step — reachable with NO backend session yet: this is the
                page that creates the first backend session for a brand-new Google
                sign-in (via OnboardingScreen's own googleLogin() call using the
                Supabase client-side session). Gating this route on `user` (backend
                session) would make it unreachable on that exact first visit. */}
            <Route path="/onboarding" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : (
                user && user.onboarded ? <Navigate to={DEFAULT_ROUTE[user.role]} replace /> :
                user && !user.email_confirmed ? <Navigate to="/email-verification" replace /> :
                <OnboardingScreen />
              )
            }/>

            {/* Protected dashboards */}
            <Route path="/student/*" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : (
                <ProtectedRoute authStatus={authStatus} user={user} allowedRoles={['student']}>
                  <AppShell user={user} onLogout={logout} />
                </ProtectedRoute>
              )
            }/>

            <Route path="/instructor/*" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : (
                <ProtectedRoute authStatus={authStatus} user={user} allowedRoles={['instructor']}>
                  <AppShell user={user} onLogout={logout} />
                </ProtectedRoute>
              )
            }/>

            <Route path="/admin/*" element={
              authStatus === 'error' ? (
                <ApiErrorScreen onRetry={runSessionProbe} context="dashboard" />
              ) : (
                <ProtectedRoute authStatus={authStatus} user={user} allowedRoles={['admin']}>
                  <AppShell user={user} onLogout={logout} />
                </ProtectedRoute>
              )
            }/>

            {/* Direct-link safety net for role-mismatch redirects elsewhere in the app */}
            <Route path="/unauthorized" element={<UnauthorizedPage role={user?.role} />} />

            <Route path="*" element={<NotFoundPage/>}/>
          </Routes>
          </Suspense>
          <ScrollToTop />
          <CuriChatLauncher />
        </BrowserRouter>
      </CursusProvider>
    </FatalErrorScreen>
  );
}
