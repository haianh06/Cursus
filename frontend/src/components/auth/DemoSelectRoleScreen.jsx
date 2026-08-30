import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, GraduationCap, Users, ShieldCheck, Sparkles } from 'lucide-react';
import { startDemoSession } from '../../lib/authClient';
import { useLanguage } from '../../context/LanguageContext';
import ThemeToggle from '../shared/ThemeToggle';
import LanguageToggle from '../shared/LanguageToggle';

const ROLE_CARDS = [
  {
    role: 'student',
    icon: GraduationCap,
    titleVi: 'Sinh viên', titleEn: 'Student',
    descVi: 'Kế hoạch học tập theo tuần, hỏi đáp có trích nguồn học liệu, theo dõi tiến độ.',
    descEn: 'Weekly study plans, cited course Q&A, progress tracking.',
  },
  {
    role: 'instructor',
    icon: Users,
    titleVi: 'Giảng viên', titleEn: 'Teacher',
    descVi: 'Giám sát lớp học, cảnh báo sinh viên nguy cơ, duyệt can thiệp cơ chế an toàn học thuật.',
    descEn: 'Class oversight, at-risk student alerts, guardrail review.',
  },
  {
    role: 'admin',
    icon: ShieldCheck,
    titleVi: 'Quản trị viên', titleEn: 'Admin',
    descVi: 'Quản lý curriculum, mời tài khoản, theo dõi KPI toàn trường.',
    descEn: 'Curriculum management, invites, school-wide KPIs.',
  },
];

/**
 * Public, no-account entry point. Each card starts a real short-lived
 * session (POST /auth/demo-session) scoped to the isolated "Cursus Sandbox
 * University" organization — never production data.
 */
export default function DemoSelectRoleScreen() {
  const navigate = useNavigate();
  const { lang } = useLanguage();
  const [loadingRole, setLoadingRole] = useState(null);
  const [error, setError] = useState('');

  async function enterDemo(role) {
    setLoadingRole(role);
    setError('');
    try {
      await startDemoSession(role);
      navigate(`/${role}`, { replace: true });
      window.location.reload();
    } catch (err) {
      setError(err.message || (lang === 'vi' ? 'Không thể bắt đầu trải nghiệm sandbox. Vui lòng thử lại.' : 'Could not start the sandbox trial. Please try again.'));
      setLoadingRole(null);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center bg-surface text-fg relative overflow-hidden font-sans">
      <div className="absolute inset-0 opacity-[0.03] bg-grid pointer-events-none" />

      <div className="relative z-10 w-full max-w-5xl px-6 py-12 flex flex-col items-center">
        <div className="w-full flex items-center justify-between mb-10">
          <Link to="/" className="link-auth-secondary hover:underline group text-fg-secondary text-sm">
            <ArrowLeft size={16} className="icon-arrow" />
            {lang === 'vi' ? 'Về trang chủ' : 'Back to home'}
          </Link>
          <div className="flex items-center gap-4">
            {/* Same gap as AuthLayout: this is a public, no-account entry
                point a visitor can land on directly, so it needs the same
                always-available language/theme switch the landing page and
                every authenticated screen offer — scoped to
                `.landing-page-scope` because that's where the toggles'
                `--landing-*` color tokens are defined. */}
            <div className="landing-page-scope flex items-center gap-2">
              <LanguageToggle />
              <ThemeToggle />
            </div>
            <Link to="/login" className="text-sm font-semibold text-fg-secondary hover:text-brand-blue dark:hover:text-brand-blue-text-dark transition-colors">
              {lang === 'vi' ? 'Đã có tài khoản? Đăng nhập' : 'Have an account? Sign in'}
            </Link>
          </div>
        </div>

        <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase bg-brand-blue-soft text-brand-blue dark:text-brand-blue-text-dark border border-brand-blue/20 mb-5">
          <Sparkles size={10} /> {lang === 'vi' ? 'Sandbox — dữ liệu giả lập' : 'Sandbox — synthetic data'}
        </span>
        <h1 className="font-display text-3xl md:text-4xl font-bold text-center text-fg mb-3 tracking-tight">
          {lang === 'vi' ? 'Chọn vai trò để trải nghiệm' : 'Pick a role to explore'}
        </h1>
        <p className="text-fg-secondary text-center max-w-lg mb-10">
          {lang === 'vi'
            ? 'Không cần tạo tài khoản. Bạn sẽ vào "Cursus Sandbox University" — một tổ chức mẫu tách biệt hoàn toàn khỏi dữ liệu thật.'
            : 'No account needed. You\'ll enter "Cursus Sandbox University" — a sample organization fully isolated from real data.'}
        </p>

        {error && (
          <div role="alert" className="mb-6 p-3.5 rounded-xl bg-danger/10 border border-danger/20 text-sm font-semibold text-danger">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full">
          {ROLE_CARDS.map(({ role, icon: Icon, titleVi, titleEn, descVi, descEn }) => (
            <button
              key={role}
              type="button"
              disabled={loadingRole !== null}
              onClick={() => enterDemo(role)}
              className="group text-left p-6 rounded-[var(--radius-lg)] border border-line bg-surface-card hover:shadow-elevation-1 hover:border-brand-blue/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer flex flex-col gap-4"
            >
              <div className="w-12 h-12 rounded-xl bg-brand-blue-soft text-brand-blue flex items-center justify-center">
                <Icon size={22} />
              </div>
              <div>
                <h2 className="font-display text-lg font-bold text-fg mb-1.5">
                  {lang === 'vi' ? titleVi : titleEn}
                </h2>
                <p className="text-sm text-fg-secondary leading-relaxed">
                  {lang === 'vi' ? descVi : descEn}
                </p>
              </div>
              {/* This pill is the card's actual call-to-action ("go" prompt) —
                  uses the shared brand-CTA blue (same token pair as
                  landing/login: bg + white text together, not the blue as a
                  bare text color). Using it as plain colored text instead of
                  a filled pill measured 3.44:1 against this card's dark-theme
                  surface (needs 4.5:1) — the token was verified for the
                  bg+white-text PAIRING, not as a foreground color against a
                  variable, theme-dependent surface. The badge above and this
                  card's icon chip/hover border intentionally keep --accent:
                  they're uniform decorative chrome, not the action trigger,
                  so out of scope here. */}
              <span
                className="mt-auto inline-flex items-center gap-1.5 text-sm font-bold px-3 py-1.5 rounded-full w-fit"
                style={{ backgroundColor: 'var(--landing-cta-bg)', color: 'var(--landing-cta-text)' }}
              >
                {loadingRole === role ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                  </svg>
                ) : (
                  <>
                    {lang === 'vi' ? `Khám phá vai trò ${titleVi}` : `Explore as ${titleEn}`}
                    <ArrowRight size={15} className="transition-transform group-hover:translate-x-0.5" />
                  </>
                )}
              </span>
            </button>
          ))}
        </div>

        <p className="text-xs text-fg-muted text-center mt-10 max-w-md">
          {lang === 'vi'
            ? 'Đại diện trường học, giảng viên hoặc nhà đầu tư? '
            : 'Represent a school, teach, or invest? '}
          <Link to="/request-access" className="font-semibold text-brand-blue dark:text-brand-blue-text-dark hover:underline">
            {lang === 'vi' ? 'Yêu cầu triển khai cho tổ chức của bạn' : 'Request institutional access'}
          </Link>
        </p>
      </div>
    </div>
  );
}
