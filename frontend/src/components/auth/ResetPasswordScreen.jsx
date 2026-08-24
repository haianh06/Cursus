import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Lock, Eye, EyeOff, Check, ArrowRight } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { resetPassword } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

export default function ResetPasswordScreen() {
  const navigate = useNavigate();
  const { t, lang } = useLanguage();

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [sessionValid, setSessionValid] = useState(true);
  const [mascotState, setMascotState] = useState('idle');
  const [token, setToken] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tokenParam = params.get('token') || '';
    const hasError = params.get('error') || params.get('error_description');
    
    if (hasError || !tokenParam) {
      setSessionValid(false);
      setMascotState('error');
    } else {
      setToken(tokenParam);
      setSessionValid(true);
      setMascotState('idle');
    }
  }, []);

  function validate() {
    const e = {};
    if (password.length < 12) {
      e.password = lang === 'vi' 
        ? 'Mật khẩu phải dài ít nhất 12 ký tự.' 
        : 'Password must be at least 12 characters.';
    }
    if (password !== confirm) e.confirm = t('auth.errConfirm');
    return e;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const validationErrors = validate();
    if (Object.keys(validationErrors).length) {
      setErrors(validationErrors);
      setMascotState('error');
      return;
    }

    setLoading(true);
    setMascotState('loading');
    setErrors({});

    try {
      await resetPassword({ token, newPassword: password });

      setSuccess(true);
      setMascotState('success');
      
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);

    } catch (err) {
      console.error(err);
      setMascotState('error');
      let errMsg = err.message || (lang === 'vi' ? 'Đặt lại mật khẩu thất bại. Vui lòng thử lại.' : 'Reset password failed. Please try again.');
      setErrors({ form: errMsg });
      setLoading(false);
    }
  }

  if (!sessionValid) {
    return (
      <AuthLayout
        title={lang === 'vi' ? 'Liên kết hết hạn' : 'Expired Link'}
        subtitle={lang === 'vi' ? 'Mã xác nhận khôi phục mật khẩu không còn hiệu lực.' : 'Your password recovery link is no longer valid.'}
        mascotState="error"
        cardWidth={430}
      >
        <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 text-center animate-scale-in">
          <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 bg-danger/10 border border-danger/25">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="text-danger">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h2 className="font-display text-lg font-bold text-fg mb-2">
            {lang === 'vi' ? 'Liên kết khôi phục đã hết hạn' : 'Recovery Link Expired'}
          </h2>
          <p className="text-xs text-fg-secondary mb-6 leading-relaxed">
            {lang === 'vi'
              ? 'Yêu cầu khôi phục mật khẩu đã quá hạn 24 giờ hoặc liên kết đã được sử dụng. Vui lòng yêu cầu lại liên kết mới.'
              : 'The password recovery request has expired (24h) or the link has already been used. Please request a new recovery link.'}
          </p>
          <Link to="/forgot-password" className="btn-auth-primary text-sm flex items-center justify-center gap-2">
            {lang === 'vi' ? 'Yêu cầu liên kết mới' : 'Request New Link'}
            <ArrowRight size={16} />
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={t('auth.resetPasswordTitle')}
      subtitle={lang === 'vi' ? 'Nhập mật khẩu mới cho tài khoản Cursus của bạn.' : 'Enter a new password for your Cursus account.'}
      mascotState={mascotState}
      cardWidth={450}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 relative">
        {success ? (
          <div className="text-center py-2 animate-scale-in">
            <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 bg-success-soft border border-success/25">
              <Check size={26} className="text-success" />
            </div>
            <h2 className="font-display text-lg font-bold text-fg mb-2">
              {lang === 'vi' ? 'Đã cập nhật mật khẩu' : 'Password Updated'}
            </h2>
            <p className="text-xs text-fg-secondary mb-6">
              {lang === 'vi'
                ? 'Mật khẩu của bạn đã được thay đổi thành công. Đang chuyển hướng về trang đăng nhập...'
                : 'Your password has been changed successfully. Redirecting to login page...'}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <h2 className="font-display text-xl font-bold text-fg mb-2">
              {lang === 'vi' ? 'Đặt mật khẩu mới' : 'Set New Password'}
            </h2>
            
            {errors.form && (
              <div role="alert" className="p-3 bg-danger/10 border border-danger/20 text-xs font-semibold text-danger rounded-xl mb-4">
                {errors.form}
              </div>
            )}

            {/* New Password field */}
            <div>
              <label htmlFor="reset-password" className="block text-sm font-semibold mb-2 text-fg-secondary">
                {lang === 'vi' ? 'Mật khẩu mới' : 'New Password'}
              </label>
              <div className="relative">
                <input
                  id="reset-password"
                  type={showPass ? 'text' : 'password'}
                  autoComplete="new-password"
                  className="w-full h-[52px] bg-surface border border-line rounded-xl pl-4 pr-11 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                  placeholder={t('auth.passwordPlaceholder')}
                  value={password}
                  disabled={loading}
                  aria-invalid={!!errors.password}
                  aria-describedby={errors.password ? 'reset-password-error' : undefined}
                  onFocus={() => setMascotState('typing-password')}
                  onBlur={() => setMascotState('idle')}
                  onChange={e => { 
                    setPassword(e.target.value); 
                    setErrors(p => ({...p,password:undefined,form:undefined}));
                  }}
                  autoFocus
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-fg-muted hover:text-fg transition-colors outline-none"
                  aria-label={showPass ? t('auth.hidePass') : t('auth.showPass')}
                  onClick={() => setShowPass(v => !v)}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && (
                <p id="reset-password-error" className="text-xs mt-1.5 font-semibold text-danger">
                  {errors.password}
                </p>
              )}
            </div>

            {/* Confirm Password field */}
            <div>
              <label htmlFor="reset-confirm" className="block text-sm font-semibold mb-2 text-fg-secondary">
                {t('auth.regConfirmPasswordLabel')}
              </label>
              <input
                id="reset-confirm"
                type={showPass ? 'text' : 'password'}
                autoComplete="new-password"
                className="w-full h-[52px] bg-surface border border-line rounded-xl px-4 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                placeholder={t('auth.regConfirmPasswordLabel')}
                value={confirm}
                disabled={loading}
                aria-invalid={!!errors.confirm}
                aria-describedby={errors.confirm ? 'reset-confirm-error' : undefined}
                onFocus={() => setMascotState('typing-password')}
                onBlur={() => setMascotState('idle')}
                onChange={e => { 
                  setConfirm(e.target.value); 
                  setErrors(p => ({...p,confirm:undefined,form:undefined}));
                }}
              />
              {errors.confirm && (
                <p id="reset-confirm-error" className="text-xs mt-1.5 font-semibold text-danger">
                  {errors.confirm}
                </p>
              )}
            </div>

            <button
              type="submit"
              className="btn-auth-primary text-sm mt-2"
              disabled={loading}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                  </svg>
                  {t('auth.loadingText')}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  {t('auth.resetPasswordCta')}
                  <ArrowRight size={16} />
                </span>
              )}
            </button>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}
