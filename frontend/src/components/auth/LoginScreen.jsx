import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Mail, Lock, Eye, EyeOff, ArrowLeft, Sun, Moon, Target, ListChecks, RefreshCcw,
} from 'lucide-react';
import { login } from '../../lib/authClient';
import { useLanguage } from '../../context/LanguageContext';
import { useTheme } from '../../context/ThemeContext';
import LoginLanguageSelect from './LoginLanguageSelect';

function isValidEmail(e) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e);
}

/** Dung ba the, dung thu tu, moi the mot accent — khong bao gio the thu tu. */
const STAGES = [
  { key: 'plan', Icon: Target, name: 'auth.stagePlanName', l1: 'auth.stagePlanL1', l2: 'auth.stagePlanL2' },
  { key: 'do', Icon: ListChecks, name: 'auth.stageDoName', l1: 'auth.stageDoL1', l2: 'auth.stageDoL2' },
  { key: 'reflect', Icon: RefreshCcw, name: 'auth.stageReflectName', l1: 'auth.stageReflectL1', l2: 'auth.stageReflectL2' },
];

/**
 * Man dang nhap, dung lai theo screenshot tham chieu o 1672x941.
 *
 * KHONG dung AuthLayout nua: AuthLayout la mot split 1280px voi the 460px,
 * khong the tao ra card 709px canh mot illustration 660px ma khong viet lai
 * — ma viet lai no se keo theo /register, /forgot-password,
 * /reset-password, /onboarding, /accept-invite va /request-access. Cac man
 * do giu AuthLayout nguyen ven.
 *
 * Toan bo phan xac thuc ben duoi duoc giu y nguyen: validate, lam sach
 * `returnTo`, thong bao het phien, thong bao rate limit, va login() goi
 * POST /auth/login voi credentials: 'include' (phien bang cookie HttpOnly,
 * khong bao gio luu JWT vao localStorage). Day la ban dung lai giao dien,
 * khong phai thay doi cach dang nhap hoat dong.
 */
export default function LoginScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t, lang } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const vi = lang === 'vi';
  const isDark = theme === 'dark';

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [errors, setErrors] = useState(() => {
    const q = new URLSearchParams(location.search);
    if (q.get('reason') === 'session_expired') {
      return {
        form: lang === 'vi'
          ? 'Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.'
          : 'Your session has expired. Please sign in again.',
      };
    }
    return {};
  });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const query = new URLSearchParams(location.search);
  const returnToParam = query.get('returnTo') || '';

  const getSafeRedirect = (url) => {
    if (!url) return '';
    let decoded = '';
    try {
      decoded = decodeURIComponent(url);
    } catch (e) {
      decoded = url;
    }
    if (
      decoded.startsWith('/') &&
      !decoded.startsWith('//') &&
      !decoded.startsWith('/\\') &&
      !/^(https?:|javascript:|data:|file:)/i.test(decoded)
    ) {
      return decoded;
    }
    return '';
  };

  const safeRedirectPath = getSafeRedirect(returnToParam);

  function validate() {
    const e = {};
    if (!isValidEmail(email)) e.email = t('auth.errEmail');
    if (password.length < 6) e.password = t('auth.errPassword');
    return e;
  }

  function onLoginSuccess(data) {
    setSuccess(true);
    setTimeout(() => {
      if (safeRedirectPath) {
        navigate(safeRedirectPath, { replace: true });
        window.location.reload();
      } else {
        const role = (data.user?.role || 'student').toLowerCase();
        navigate(`/${role}`, { replace: true });
        window.location.reload();
      }
    }, 1000);
  }

  async function handleSubmit(ev) {
    ev.preventDefault();
    // Chan gui lap: dang gui hoac da thanh cong thi bo qua.
    if (loading || success) return;

    const e = validate();
    if (Object.keys(e).length) {
      setErrors(e);
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      const data = await login({ email, password, rememberMe: true });
      onLoginSuccess(data);
    } catch (err) {
      console.error(err);
      let errMsg = err.message || t('auth.invalidCredentialsError');
      if (err.message && err.message.toLowerCase().includes('rate limit')) {
        errMsg = vi
          ? 'Quá nhiều yêu cầu đăng nhập. Vui lòng thử lại sau.'
          : 'Too many login requests. Please try again later.';
      }
      setErrors({ form: errMsg });
      setLoading(false);
    }
  }

  const backLink = (extraClass) => (
    <Link to="/" className={`clp-back${extraClass ? ` ${extraClass}` : ''}`}>
      <ArrowLeft size={20} strokeWidth={2} aria-hidden="true" />
      {t('auth.backToHome')}
    </Link>
  );

  return (
    <div className="cursus-login-page">
      {/* Glow teal + luoi cham: thuan trang tri, nam duoi cung, khong nhan chuot. */}
      <div className="clp-bg" aria-hidden="true" />

      <div className="clp-shell">
        <header className="clp-header">
          <Link to="/" className="clp-logo" aria-label={vi ? 'Cursus — về trang chủ' : 'Cursus — back to home'}>
            <img
              src="/brand/cursus-logo-horizontal.png"
              alt="Cursus · Plan · Do · Reflect"
              className="clp-logo__img"
              draggable="false"
            />
          </Link>

          <div className="clp-header__controls">
            <LoginLanguageSelect />
            <button
              type="button"
              className="clp-theme"
              onClick={toggleTheme}
              aria-pressed={isDark}
              aria-label={isDark ? t('landing.themeToggleToLight') : t('landing.themeToggleToDark')}
              title={isDark ? t('landing.themeToggleToLight') : t('landing.themeToggleToDark')}
            >
              {isDark
                ? <Moon size={22} strokeWidth={1.9} aria-hidden="true" />
                : <Sun size={22} strokeWidth={1.9} aria-hidden="true" />}
            </button>
          </div>
        </header>

        <main className="clp-main">
          {/* ── Cot trai: cau chuyen thuong hieu ── */}
          <section className="clp-brand">
            {/* Reference co HAI nut quay lai (mot ngoai, mot trong card) va do
                la chu dich. Ban ngoai bi an duoi 1200px de mobile chi con mot. */}
            {backLink('clp-back--outside')}

            <div className="clp-hero">
              <img
                src="/brand/login-curi-study-hero.png"
                alt=""
                aria-hidden="true"
                className="clp-hero__img"
                draggable="false"
              />
            </div>

            <h1 className="clp-heading">
              {t('auth.loginHeroLine1')}
              <br />
              {t('auth.loginHeroLine2')}
            </h1>

            <p className="clp-sub">{t('auth.loginHeroDesc')}</p>

            <div className="clp-stages">
              {STAGES.map(({ key, Icon, name, l1, l2 }) => (
                <div key={key} className={`clp-stage clp-stage--${key}`}>
                  <span className="clp-stage__icon">
                    <Icon size={20} strokeWidth={2} aria-hidden="true" />
                  </span>
                  <span style={{ minWidth: 0 }}>
                    <span className="clp-stage__name">{t(name)}</span>
                    <span className="clp-stage__text">{t(l1)}<br />{t(l2)}</span>
                  </span>
                </div>
              ))}
            </div>
          </section>

          {/* ── Cot phai: card dang nhap ── */}
          <section className="clp-card">
            {/* Curi tho dau — trang tri thuan tuy, duoi noi dung, click xuyen qua. */}
            <div className="clp-peek" aria-hidden="true">
              <img
                src="/brand/login-curi-peek.png"
                alt=""
                aria-hidden="true"
                className="clp-peek__img"
                draggable="false"
              />
            </div>

            {backLink()}

            <div aria-live="polite">
              {errors.form && !success && (
                <div role="alert" className="clp-alert">{errors.form}</div>
              )}
              {success && (
                <div className="clp-alert clp-alert--ok">
                  {vi ? 'Đăng nhập thành công. Đang chuyển bạn vào Cursus…' : 'Signed in. Taking you into Cursus…'}
                </div>
              )}
            </div>

            {/* Google OAuth chua duoc noi trong ban trien khai nay (cau hinh
                Supabase free tier). Hien o trang thai vo hieu mot cach trung
                thuc thay vi mot nut bam duoc ma luon bao loi — cai do doc ra
                nhu mot bug chu khong phai mot tinh nang chua lam. */}
            <button
              type="button"
              disabled
              aria-disabled="true"
              className="clp-google"
              title={t('auth.googleLoginComingSoon')}
            >
              <span className="clp-google__icon" aria-hidden="true">
                <svg width="27" height="27" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
                </svg>
              </span>
              <span className="clp-google__body">
                <span className="clp-google__label">{t('auth.loginGoogleCta')}</span>
                <span className="clp-google__soon">{t('auth.googleLoginComingSoon')}</span>
              </span>
            </button>

            <div className="clp-divider">
              <span>{t('auth.orEmail')}</span>
            </div>

            <form className="clp-form" onSubmit={handleSubmit} noValidate>
              <div className="clp-field">
                <label htmlFor="login-email" className="clp-label">Email</label>
                <div className="clp-inputwrap">
                  <span className="clp-inputicon" aria-hidden="true">
                    <Mail size={21} strokeWidth={1.9} />
                  </span>
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="email"
                    className="clp-input"
                    placeholder={t('auth.loginEmailPlaceholder')}
                    value={email}
                    disabled={loading || success}
                    aria-invalid={errors.email ? 'true' : undefined}
                    aria-describedby={errors.email ? 'login-email-error' : undefined}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      setErrors((p) => ({ ...p, email: undefined, form: undefined }));
                    }}
                  />
                </div>
                {errors.email && <p id="login-email-error" className="clp-fielderr">{errors.email}</p>}
              </div>

              <div className="clp-field">
                <label htmlFor="login-password" className="clp-label">{t('auth.passwordLabel')}</label>
                <div className="clp-inputwrap">
                  <span className="clp-inputicon" aria-hidden="true">
                    <Lock size={21} strokeWidth={1.9} />
                  </span>
                  <input
                    id="login-password"
                    type={showPass ? 'text' : 'password'}
                    autoComplete="current-password"
                    className="clp-input clp-input--pw"
                    placeholder={t('auth.loginPasswordPlaceholder')}
                    value={password}
                    disabled={loading || success}
                    aria-invalid={errors.password ? 'true' : undefined}
                    aria-describedby={errors.password ? 'login-password-error' : undefined}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      setErrors((p) => ({ ...p, password: undefined, form: undefined }));
                    }}
                  />
                  {/* type="button" la bat buoc: mot <button> khong co type nam
                      trong <form> mac dinh la submit, tuc bam con mat se gui form. */}
                  <button
                    type="button"
                    className="clp-eye"
                    aria-label={showPass ? t('auth.hidePass') : t('auth.showPass')}
                    aria-pressed={showPass}
                    onClick={() => setShowPass((v) => !v)}
                  >
                    {showPass ? <EyeOff size={21} strokeWidth={1.9} /> : <Eye size={21} strokeWidth={1.9} />}
                  </button>
                </div>
                {errors.password && <p id="login-password-error" className="clp-fielderr">{errors.password}</p>}
              </div>

              <div className="clp-forgotrow">
                <Link to="/forgot-password" className="clp-forgot">{t('auth.forgotPassword')}</Link>
              </div>

              <button
                id="login-submit"
                type="submit"
                className={`clp-submit${success ? ' clp-submit--ok' : ''}`}
                disabled={loading || success}
              >
                {success ? (
                  <>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" aria-hidden="true">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    {vi ? 'Đăng nhập thành công' : 'Signed in'}
                  </>
                ) : loading ? (
                  <>
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="clp-spin" aria-hidden="true">
                      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                    </svg>
                    {t('auth.loadingText')}
                  </>
                ) : (
                  t('auth.loginCta')
                )}
              </button>
            </form>

            {/* Thong tin, khong phai CTA canh tranh: khong nut to, nam duoi
                mot duong ke mo. */}
            <div className="clp-sandbox">
              <span className="clp-sandbox__icon" aria-hidden="true">
                <img src="/brand/curi-neutral-icon.png" alt="" aria-hidden="true" className="clp-sandbox__img" draggable="false" />
              </span>
              <p className="clp-sandbox__text">
                {t('auth.sandboxNoteLead')}
                <Link to="/demo/select-role">{t('auth.sandboxNoteLink')}</Link>
                {t('auth.sandboxNoteTail')}
              </p>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
