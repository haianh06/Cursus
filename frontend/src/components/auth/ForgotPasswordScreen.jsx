import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, Send, Check } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { forgotPassword } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

export default function ForgotPasswordScreen() {
  const { t, lang } = useLanguage();
  
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [mascotState, setMascotState] = useState('idle');

  async function handleSubmit(e) {
    e.preventDefault();
    if (!isValidEmail(email)) {
      setError(t('auth.errEmail'));
      setMascotState('error');
      return;
    }
    setError('');
    setLoading(true);
    setMascotState('loading');
    
    try {
      await forgotPassword({ email });
      setSent(true);
      setMascotState('success');
    } catch (err) {
      console.error(err);
      setError(err.message || (lang === 'vi' 
        ? 'Không thể gửi yêu cầu khôi phục. Vui lòng thử lại.' 
        : 'Failed to send recovery request. Please try again.'));
      setMascotState('error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout
      title={lang === 'vi' ? 'Khôi phục mật khẩu' : 'Recover password'}
      subtitle={lang === 'vi' ? 'Trợ lý Cursus sẽ giúp bạn đặt lại mật khẩu một cách an toàn.' : 'Cursus Assistant will help you securely reset your password.'}
      mascotState={mascotState}
      cardWidth={430}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 relative">
        {sent ? (
          <div className="text-center py-2 animate-scale-in">
            <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4 bg-success-soft border border-success/25">
              <Check size={26} className="text-success" />
            </div>
            <h2 className="font-display text-lg font-bold text-fg mb-2">
              {lang === 'vi' ? 'Email hướng dẫn đã gửi' : 'Instructions Sent'}
            </h2>
            <p className="text-xs text-fg-secondary mb-6 leading-relaxed">
              {lang === 'vi'
                ? `Yêu cầu đặt lại mật khẩu đã được xử lý. Nếu tài khoản tồn tại, một liên kết khôi phục sẽ được gửi tới ${email}. Vui lòng kiểm tra hộp thư.`
                : `A reset link has been processed. If the account exists, an email has been sent to ${email} with instructions.`}
            </p>
            <Link to="/login" className="btn-auth-primary text-sm flex items-center justify-center gap-2">
              <ArrowLeft size={16} />
              {lang === 'vi' ? 'Quay lại đăng nhập' : 'Back to Login'}
            </Link>
          </div>
        ) : (
          <>
            <div className="mb-6">
              <Link to="/login" className="link-auth-secondary hover:underline group text-fg-secondary">
                <ArrowLeft size={16} className="icon-arrow" />
                {lang === 'vi' ? 'Quay lại đăng nhập' : 'Back to Login'}
              </Link>
            </div>

            <h2 className="font-display text-xl font-bold text-fg mb-2">
              {t('auth.forgotPassword')}
            </h2>
            <p className="text-xs text-fg-secondary mb-6 leading-relaxed">
              {lang === 'vi'
                ? 'Nhập email của bạn và chúng tôi sẽ gửi hướng dẫn để đặt lại mật khẩu.'
                : 'Enter your email address and we will send instructions to reset your password.'}
            </p>

            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <div>
                <label htmlFor="forgot-email" className="block text-sm font-semibold mb-2 text-fg-secondary">
                  Email
                </label>
                <div className="relative">
                  <Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
                  <input
                    id="forgot-email"
                    type="email"
                    className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-4 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                    placeholder="ten.msv@truong.edu.vn"
                    value={email}
                    disabled={loading}
                    aria-invalid={!!error}
                    onFocus={() => setMascotState('typing-email')}
                    onBlur={() => setMascotState('idle')}
                    onChange={e => { 
                      setEmail(e.target.value); 
                      setError(''); 
                      if (mascotState !== 'typing-email') setMascotState('typing-email');
                    }}
                    autoFocus
                  />
                </div>
                {error && <p className="text-xs mt-1.5 font-semibold text-danger">{error}</p>}
              </div>

              <button
                id="forgot-submit"
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
                    <Send size={16} />
                    {lang === 'vi' ? 'Gửi liên kết khôi phục' : 'Send Recovery Link'}
                  </span>
                )}
              </button>
            </form>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
