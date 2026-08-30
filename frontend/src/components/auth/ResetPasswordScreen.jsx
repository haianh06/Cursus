import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Lock, Eye, EyeOff, Check, ArrowRight } from 'lucide-react';
import AuthCardLayout from './AuthCardLayout';
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
  const [token, setToken] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const tokenParam = params.get('token') || '';
    const hasError = params.get('error') || params.get('error_description');

    if (hasError || !tokenParam) {
      setSessionValid(false);
    } else {
      setToken(tokenParam);
      setSessionValid(true);
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
      return;
    }

    setLoading(true);
    setErrors({});

    try {
      await resetPassword({ token, newPassword: password });
      setSuccess(true);
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 2000);
    } catch (err) {
      console.error(err);
      const errMsg = err.message || (lang === 'vi' ? 'Đặt lại mật khẩu thất bại. Vui lòng thử lại.' : 'Reset password failed. Please try again.');
      setErrors({ form: errMsg });
      setLoading(false);
    }
  }

  if (!sessionValid) {
    return (
      <AuthCardLayout
        heroTitle={lang === 'vi' ? 'Liên kết đã hết hạn' : 'Link expired'}
        heroSub={lang === 'vi'
          ? 'Mã xác nhận khôi phục mật khẩu không còn hiệu lực — yêu cầu một liên kết mới để tiếp tục.'
          : 'Your password recovery link is no longer valid — request a new one to continue.'}
      >
        <div className="text-center" style={{ padding: '8px 0' }}>
          <div className="clp-successicon clp-successicon--error">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <h2 className="clp-cardheading">
            {lang === 'vi' ? 'Liên kết khôi phục đã hết hạn' : 'Recovery link expired'}
          </h2>
          <p className="clp-cardsub">
            {lang === 'vi'
              ? 'Yêu cầu khôi phục mật khẩu đã quá hạn 24 giờ hoặc liên kết đã được sử dụng. Vui lòng yêu cầu lại liên kết mới.'
              : 'The password recovery request has expired (24h) or the link has already been used. Please request a new recovery link.'}
          </p>
          <Link to="/forgot-password" className="clp-submit" style={{ textDecoration: 'none', marginTop: 28 }}>
            {lang === 'vi' ? 'Yêu cầu liên kết mới' : 'Request new link'}
            <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
          </Link>
        </div>
      </AuthCardLayout>
    );
  }

  return (
    <AuthCardLayout
      heroTitle={lang === 'vi' ? 'Đặt lại mật khẩu mới' : 'Set your new password'}
      heroSub={lang === 'vi'
        ? 'Chọn một mật khẩu mới, đủ mạnh để bảo vệ tài khoản Cursus của bạn.'
        : 'Choose a new, strong password to keep your Cursus account secure.'}
    >
      {success ? (
        <div className="text-center" style={{ padding: '8px 0' }}>
          <div className="clp-successicon">
            <Check size={26} strokeWidth={2.5} aria-hidden="true" />
          </div>
          <h2 className="clp-cardheading">
            {lang === 'vi' ? 'Đã cập nhật mật khẩu' : 'Password updated'}
          </h2>
          <p className="clp-cardsub">
            {lang === 'vi'
              ? 'Mật khẩu của bạn đã được thay đổi thành công. Đang chuyển hướng về trang đăng nhập...'
              : 'Your password has been changed successfully. Redirecting to the login page...'}
          </p>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="clp-form" noValidate>
          <h2 className="clp-cardheading">
            {lang === 'vi' ? 'Đặt mật khẩu mới' : 'Set new password'}
          </h2>

          {errors.form && (
            <div role="alert" className="clp-alert" style={{ marginBottom: 18 }}>{errors.form}</div>
          )}

          <div className="clp-field">
            <label htmlFor="reset-password" className="clp-label">
              {lang === 'vi' ? 'Mật khẩu mới' : 'New password'}
            </label>
            <div className="clp-inputwrap">
              <span className="clp-inputicon"><Lock size={18} strokeWidth={2} aria-hidden="true" /></span>
              <input
                id="reset-password"
                type={showPass ? 'text' : 'password'}
                autoComplete="new-password"
                className="clp-input clp-input--pw"
                placeholder={t('auth.passwordPlaceholder')}
                value={password}
                disabled={loading}
                aria-invalid={!!errors.password}
                aria-describedby={errors.password ? 'reset-password-error' : undefined}
                onChange={(e) => { setPassword(e.target.value); setErrors((p) => ({ ...p, password: undefined, form: undefined })); }}
                autoFocus
              />
              <button
                type="button"
                className="clp-eye"
                aria-label={showPass ? t('auth.hidePass') : t('auth.showPass')}
                onClick={() => setShowPass((v) => !v)}
              >
                {showPass ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}
              </button>
            </div>
            {errors.password && <p id="reset-password-error" className="clp-fielderr">{errors.password}</p>}
          </div>

          <div className="clp-field">
            <label htmlFor="reset-confirm" className="clp-label">{t('auth.regConfirmPasswordLabel')}</label>
            <div className="clp-inputwrap">
              <span className="clp-inputicon"><Lock size={18} strokeWidth={2} aria-hidden="true" /></span>
              <input
                id="reset-confirm"
                type={showPass ? 'text' : 'password'}
                autoComplete="new-password"
                className="clp-input"
                placeholder={t('auth.regConfirmPasswordLabel')}
                value={confirm}
                disabled={loading}
                aria-invalid={!!errors.confirm}
                aria-describedby={errors.confirm ? 'reset-confirm-error' : undefined}
                onChange={(e) => { setConfirm(e.target.value); setErrors((p) => ({ ...p, confirm: undefined, form: undefined })); }}
              />
            </div>
            {errors.confirm && <p id="reset-confirm-error" className="clp-fielderr">{errors.confirm}</p>}
          </div>

          <button type="submit" className="clp-submit" disabled={loading}>
            {loading ? (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                </svg>
                {t('auth.loadingText')}
              </>
            ) : (
              <>
                {t('auth.resetPasswordCta')}
                <ArrowRight size={18} strokeWidth={2} aria-hidden="true" />
              </>
            )}
          </button>
        </form>
      )}
    </AuthCardLayout>
  );
}
