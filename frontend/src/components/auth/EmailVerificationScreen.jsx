import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate, Link } from 'react-router-dom';
import { Mail, RefreshCw, Edit2, Check, ArrowLeft, ArrowRight } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { verifyEmail, resendEmailVerification, changeEmail } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

export default function EmailVerificationScreen({ user, onLogout }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { t, lang } = useLanguage();

  const query = new URLSearchParams(location.search);
  const initialEmail = query.get('email') || (user && user.email) || '';

  const [email, setEmail] = useState(initialEmail);

  useEffect(() => {
    if (user && user.email && !email) {
      setEmail(user.email);
    }
  }, [user, email]);
  const [maskedEmail, setMaskedEmail] = useState('');
  const [editingEmail, setEditingEmail] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [mascotState, setMascotState] = useState('idle');

  useEffect(() => {
    if (!email) return;
    const parts = email.split('@');
    if (parts.length < 2) {
      setMaskedEmail(email);
      return;
    }
    const name = parts[0];
    const domain = parts[1];
    if (name.length <= 3) {
      setMaskedEmail(`${name.charAt(0)}***@${domain}`);
    } else {
      setMaskedEmail(`${name.substring(0, 2)}***${name.charAt(name.length - 1)}@${domain}`);
    }
  }, [email]);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = setTimeout(() => setCountdown(countdown - 1), 1000);
    return () => clearTimeout(timer);
  }, [countdown]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');
    
    if (token) {
      setLoading(true);
      setMascotState('loading');
      setErrorMsg('');
      setSuccessMsg('');
      
      verifyEmail({ token })
        .then(() => {
          setSuccessMsg(lang === 'vi' ? 'Xác thực email thành công! Đang chuyển hướng...' : 'Email verified successfully! Redirecting...');
          setMascotState('success');
          setTimeout(() => {
            navigate('/onboarding', { replace: true });
            window.location.reload();
          }, 2000);
        })
        .catch((err) => {
          console.error(err);
          setErrorMsg(err.message || (lang === 'vi' ? 'Xác thực email thất bại hoặc liên kết đã hết hạn.' : 'Email verification failed or link has expired.'));
          setMascotState('error');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [navigate, lang]);

  const handleResend = async () => {
    if (countdown > 0 || loading) return;
    setLoading(true);
    setMascotState('loading');
    setErrorMsg('');
    setSuccessMsg('');

    try {
      await resendEmailVerification({ email });

      setSuccessMsg(lang === 'vi' ? 'Đã gửi lại email xác nhận thành công.' : 'Verification email resent successfully.');
      setCountdown(60);
      setMascotState('success');
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || (lang === 'vi' ? 'Không thể gửi lại email. Vui lòng thử lại sau.' : 'Failed to resend email. Please try again.'));
      setMascotState('error');
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateEmail = async (e) => {
    e.preventDefault();
    if (!newEmail || loading) return;
    setLoading(true);
    setMascotState('loading');
    setErrorMsg('');
    setSuccessMsg('');

    try {
      await changeEmail({ email: newEmail });
      setEmail(newEmail);
      setEditingEmail(false);
      setSuccessMsg(lang === 'vi' ? 'Đã đổi email xác thực thành công. Vui lòng kiểm tra hộp thư mới.' : 'Email changed successfully. Please check your new inbox.');
      setMascotState('success');
      setCountdown(60);
    } catch (err) {
      console.error(err);
      setErrorMsg(err.message || (lang === 'vi' ? 'Không thể đổi email. Vui lòng thử lại sau.' : 'Failed to change email. Please try again.'));
      setMascotState('error');
    } finally {
      setLoading(false);
    }
  };

  const handleBackToLogin = async (e) => {
    e.preventDefault();
    if (onLogout) {
      await onLogout();
    }
    navigate('/login', { replace: true });
  };

  return (
    <AuthLayout
      title={t('auth.verificationTitle')}
      subtitle={t('auth.verificationDesc')}
      mascotState={mascotState}
      cardWidth={450}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 relative">
        <div className="text-center space-y-5">
          
          {/* Inbox Graphic Icon */}
          <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto bg-brand-blue-soft border border-brand-blue/20">
            <Mail size={28} className="text-brand-blue animate-pulse" />
          </div>

          <h2 className="font-display text-xl font-bold text-fg">
            {lang === 'vi' ? 'Kiểm tra hộp thư' : 'Check your inbox'}
          </h2>

          <p className="text-sm text-fg-secondary leading-relaxed">
            {lang === 'vi'
              ? 'Chúng tôi đã gửi một liên kết xác nhận tài khoản tới địa chỉ:'
              : 'We have sent an authentication link to the address:'}
            <br />
            <strong className="text-fg mt-1.5 block text-base bg-surface py-1.5 px-3 rounded-lg border border-line inline-block font-mono">
              {maskedEmail || email || 'đang tải...'}
            </strong>
          </p>

          {successMsg && (
            <div role="alert" className="p-3 bg-success-soft border border-success/20 text-xs font-semibold text-success rounded-xl animate-scale-in">
              {successMsg}
            </div>
          )}

          {errorMsg && (
            <div role="alert" className="p-3 bg-danger/10 border border-danger/20 text-xs font-semibold text-danger rounded-xl animate-scale-in">
              {errorMsg}
            </div>
          )}

          <div className="space-y-3.5 pt-4 border-t border-line">
            
            {/* Countdown / Resend Action Button */}
            <button
              type="button"
              onClick={handleResend}
              disabled={countdown > 0 || loading}
              className="btn-auth-primary text-sm flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                  </svg>
                  {t('auth.loadingText')}
                </>
              ) : countdown > 0 ? (
                <>
                  <RefreshCw size={16} className="spin text-fg-muted" />
                  {t('auth.verificationResendCountdown', { seconds: countdown })}
                </>
              ) : (
                <>
                  <RefreshCw size={16} />
                  {t('auth.verificationResendBtn')}
                </>
              )}
            </button>

            {/* Email Edit / Type Correction Action */}
            {!editingEmail ? (
              <button
                type="button"
                onClick={() => { setEditingEmail(true); setNewEmail(email); }}
                className="w-full py-2.5 rounded-xl border border-line bg-surface hover:bg-surface-elevated text-fg font-bold text-xs flex items-center justify-center gap-2.5 transition-all select-none cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-brand-blue"
              >
                <Edit2 size={13} />
                {t('auth.verificationChangeEmailBtn')}
              </button>
            ) : (
              <form onSubmit={handleUpdateEmail} className="p-4 rounded-xl bg-surface border border-line space-y-3 text-left animate-scale-in">
                <label htmlFor="change-email-input" className="block text-xs font-bold text-fg-secondary">
                  {lang === 'vi' ? 'Nhập email chính xác' : 'Enter correct email'}
                </label>
                <div className="flex gap-2">
                  <input
                    id="change-email-input"
                    type="email"
                    required
                    className="flex-1 h-9 bg-surface-card border border-line rounded-lg px-3 text-xs text-fg placeholder-fg-muted outline-none"
                    placeholder="example@university.edu.vn"
                    value={newEmail}
                    onChange={e => setNewEmail(e.target.value)}
                  />
                  <button
                    type="submit"
                    className="px-3 bg-brand-blue hover:bg-brand-blue-hover text-white font-bold rounded-lg text-xs transition-colors cursor-pointer"
                  >
                    {lang === 'vi' ? 'Lưu' : 'Save'}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={() => setEditingEmail(false)}
                  className="text-[10px] text-fg-muted underline hover:text-fg transition-colors"
                >
                  {lang === 'vi' ? 'Hủy bỏ' : 'Cancel'}
                </button>
              </form>
            )}

            <div className="pt-2">
              <button
                type="button"
                onClick={handleBackToLogin}
                className="link-auth-secondary text-xs hover:underline inline-flex items-center gap-1.5 group text-fg-secondary cursor-pointer bg-transparent border-none outline-none p-0"
              >
                <ArrowLeft size={14} className="icon-arrow" />
                {lang === 'vi' ? 'Quay lại đăng nhập' : 'Back to Login'}
              </button>
            </div>

          </div>

        </div>
      </div>
    </AuthLayout>
  );
}
