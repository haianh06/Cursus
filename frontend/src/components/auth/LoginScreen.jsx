import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, ArrowLeft, ArrowRight } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { login } from '../../lib/authClient';
import { useLanguage } from '../../context/LanguageContext';

function isValidEmail(e) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e); 
}

export default function LoginScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const { t, lang } = useLanguage();

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
  const [mascotState, setMascotState] = useState('idle');

  // Parse redirect target
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
    setMascotState('success');

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
    const e = validate();
    if (Object.keys(e).length) {
      setErrors(e);
      setMascotState('error');
      return;
    }

    setLoading(true);
    setMascotState('loading');
    setErrors({});

    try {
      const data = await login({ email, password, rememberMe: true });
      onLoginSuccess(data);
    } catch (err) {
      console.error(err);
      setMascotState('error');
      
      let errMsg = err.message || t('auth.invalidCredentialsError');
      
      if (err.message && err.message.toLowerCase().includes('rate limit')) {
        errMsg = lang === 'vi' 
          ? 'Quá nhiều yêu cầu đăng nhập. Vui lòng thử lại sau.'
          : 'Too many login requests. Please try again later.';
      }
      
      setErrors({ form: errMsg });
      setLoading(false);
    }
  }


  return (
    <AuthLayout
      title={t('auth.loginHeading')}
      subtitle={t('auth.loginDesc')}
      mascotState={mascotState}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 relative">

        {/* Back to Homepage Link */}
        <div className="mb-6">
          <Link to="/" className="link-auth-secondary hover:underline group text-fg-secondary">
            <ArrowLeft size={16} className="icon-arrow" />
            {t('auth.backToHome')}
          </Link>
        </div>

        {errors.form && (
          <div role="alert" aria-live="assertive" className="p-3.5 rounded-xl bg-danger/10 border border-danger/20 text-sm font-semibold text-danger mb-4 animate-scale-in">
            {errors.form}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {/* Email input field */}
          <div>
            <label htmlFor="login-email" className="block text-sm font-semibold mb-2 text-fg-secondary">
              Email
            </label>
            <div className="relative">
              <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                id="login-email"
                type="email"
                autoComplete="username"
                autoFocus
                className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-4 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                placeholder={t('auth.emailPlaceholder')}
                value={email}
                disabled={loading}
                aria-invalid={!!errors.email}
                aria-describedby={errors.email ? 'login-email-error' : undefined}
                onFocus={() => setMascotState('typing-email')}
                onBlur={() => setMascotState('idle')}
                onChange={e => { 
                  setEmail(e.target.value); 
                  setErrors(p => ({...p,email:undefined,form:undefined})); 
                  if (mascotState !== 'typing-email') setMascotState('typing-email');
                }}
              />
            </div>
            {errors.email && (
              <p id="login-email-error" className="text-sm mt-1.5 font-semibold text-danger">
                {errors.email}
              </p>
            )}
          </div>

          {/* Password input field */}
          <div>
            <div className="flex justify-between items-center mb-2">
              <label htmlFor="login-password" className="block text-sm font-semibold text-fg-secondary">
                {t('auth.passwordLabel')}
              </label>
              <Link to="/forgot-password" className="text-xs font-semibold text-fg-secondary hover:text-brand-blue dark:hover:text-brand-blue-text-dark transition-colors">
                {t('auth.forgotPassword')}
              </Link>
            </div>
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                id="login-password"
                type={showPass ? 'text' : 'password'}
                autoComplete="current-password"
                className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-11 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                placeholder={t('auth.passwordPlaceholder')}
                value={password}
                disabled={loading}
                aria-invalid={!!errors.password}
                aria-describedby={errors.password ? 'login-password-error' : undefined}
                onFocus={() => setMascotState('typing-password')}
                onBlur={() => setMascotState('idle')}
                onChange={e => { 
                  setPassword(e.target.value); 
                  setErrors(p => ({...p,password:undefined,form:undefined})); 
                  if (mascotState !== 'typing-password') setMascotState('typing-password');
                }}
              />
              <button 
                type="button" 
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-fg-muted hover:text-fg transition-colors outline-none rounded"
                aria-label={showPass ? t('auth.hidePass') : t('auth.showPass')}
                onClick={() => setShowPass(v=>!v)}
              >
                {showPass ? <EyeOff size={16}/> : <Eye size={16}/>}
              </button>
            </div>
            {errors.password && (
              <p id="login-password-error" className="text-sm mt-1.5 font-semibold text-danger">
                {errors.password}
              </p>
            )}
          </div>

          {/* Primary Action CTA */}
          <button
            id="login-submit"
            type="submit"
            className="btn-auth-primary btn-brand-cta mt-2"
            disabled={loading}
            style={{ width: '100%' }}
          >
            {success ? (
              <span className="flex items-center gap-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" className="text-white">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                {lang === 'vi' ? 'Đăng nhập thành công' : 'Signed In'}
              </span>
            ) : loading ? (
              <span className="flex items-center gap-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                </svg>
                {t('auth.loadingText')}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                {t('auth.loginCta')}
                <ArrowRight size={16} className="icon-arrow" />
              </span>
            )}
          </button>
        </form>

        {/* No public registration — try the sandbox, or request org access */}
        <div className="pt-4 mt-4 border-t border-line text-center space-y-2">
          <Link
            to="/demo/select-role"
            className="block text-sm font-semibold text-fg-secondary hover:text-brand-blue dark:hover:text-brand-blue-text-dark transition-colors"
          >
            {t('auth.newAccountLink')}
          </Link>
          <Link to="/request-access" className="text-xs text-fg-muted hover:text-brand-blue dark:hover:text-brand-blue-text-dark transition-colors">
            {t('auth.staffAccountNote')}
          </Link>
        </div>

      </div>
    </AuthLayout>
  );
}
