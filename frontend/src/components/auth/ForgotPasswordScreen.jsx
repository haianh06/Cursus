import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Mail, ArrowLeft, Send, Check } from 'lucide-react';
import AuthCardLayout from './AuthCardLayout';
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

  async function handleSubmit(e) {
    e.preventDefault();
    if (!isValidEmail(email)) {
      setError(t('auth.errEmail'));
      return;
    }
    setError('');
    setLoading(true);

    try {
      await forgotPassword({ email });
      setSent(true);
    } catch (err) {
      console.error(err);
      setError(err.message || (lang === 'vi'
        ? 'Không thể gửi yêu cầu khôi phục. Vui lòng thử lại.'
        : 'Failed to send recovery request. Please try again.'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthCardLayout
      heroTitle={lang === 'vi' ? 'Khôi phục mật khẩu của bạn' : 'Recover your password'}
      heroSub={lang === 'vi'
        ? 'Nhập email đã đăng ký, Cursus sẽ gửi liên kết để bạn đặt lại mật khẩu một cách an toàn.'
        : 'Enter your registered email and Cursus will send a link to securely reset your password.'}
    >
      {sent ? (
        <div className="text-center" style={{ padding: '8px 0' }}>
          <div className="clp-successicon">
            <Check size={26} strokeWidth={2.5} aria-hidden="true" />
          </div>
          <h2 className="clp-cardheading">
            {lang === 'vi' ? 'Email hướng dẫn đã gửi' : 'Instructions sent'}
          </h2>
          <p className="clp-cardsub">
            {lang === 'vi'
              ? `Yêu cầu đặt lại mật khẩu đã được xử lý. Nếu tài khoản tồn tại, một liên kết khôi phục sẽ được gửi tới ${email}. Vui lòng kiểm tra hộp thư.`
              : `A reset link has been processed. If the account exists, an email has been sent to ${email} with instructions.`}
          </p>
          <Link to="/login" className="clp-submit" style={{ textDecoration: 'none', marginTop: 28 }}>
            <ArrowLeft size={18} strokeWidth={2} aria-hidden="true" />
            {lang === 'vi' ? 'Quay lại đăng nhập' : 'Back to login'}
          </Link>
        </div>
      ) : (
        <>
          <h2 className="clp-cardheading">{t('auth.forgotPassword')}</h2>
          <p className="clp-cardsub">
            {lang === 'vi'
              ? 'Nhập email của bạn và chúng tôi sẽ gửi hướng dẫn để đặt lại mật khẩu.'
              : 'Enter your email address and we will send instructions to reset your password.'}
          </p>

          <form onSubmit={handleSubmit} className="clp-form" noValidate>
            <div className="clp-field">
              <label htmlFor="forgot-email" className="clp-label">Email</label>
              <div className="clp-inputwrap">
                <span className="clp-inputicon"><Mail size={18} strokeWidth={2} aria-hidden="true" /></span>
                <input
                  id="forgot-email"
                  type="email"
                  className="clp-input"
                  placeholder="ten.msv@truong.edu.vn"
                  value={email}
                  disabled={loading}
                  aria-invalid={!!error}
                  onChange={(e) => { setEmail(e.target.value); setError(''); }}
                  autoFocus
                />
              </div>
              {error && <p className="clp-fielderr">{error}</p>}
            </div>

            <button id="forgot-submit" type="submit" className="clp-submit" disabled={loading}>
              {loading ? (
                <>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                  </svg>
                  {t('auth.loadingText')}
                </>
              ) : (
                <>
                  <Send size={18} strokeWidth={2} aria-hidden="true" />
                  {lang === 'vi' ? 'Gửi liên kết khôi phục' : 'Send recovery link'}
                </>
              )}
            </button>
          </form>
        </>
      )}
    </AuthCardLayout>
  );
}
