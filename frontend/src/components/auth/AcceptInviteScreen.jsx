import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff, ArrowLeft, ArrowRight, Check, ShieldCheck, Building2 } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { register, getInviteDetails } from '../../lib/authClient';
import { useLanguage } from '../../context/LanguageContext';
import { ROLE_LABEL } from '../../constants/roles';

function strengthScore(p) {
  if (!p) return 0;
  let s = 0;
  if (p.length >= 8) s++;
  if (/[A-Z]/.test(p)) s++;
  if (/[0-9]/.test(p)) s++;
  if (/[^A-Za-z0-9]/.test(p)) s++;
  return s;
}

// Weak→strong password-meter ramp. Endpoints anchor to the real semantic
// tokens (was '#ef4444'/'#059669' — the strong end was an exact, undeclared
// duplicate of --success); the 3 middle steps are this meter's own
// intentional gradient, not a duplicate of anything else.
const S_COLORS = ['var(--danger)', '#f87171', '#fb923c', '#10b981', 'var(--success)'];

/**
 * Replaces public self-registration. Cursus is provisioned per
 * organization — the only way in is an admin-issued invite link
 * (?token=...). Email, full name, and role are all read-only here,
 * sourced from the invite record; this screen only ever collects a
 * password. No token in the URL -> no form, just a redirect to
 * /request-access.
 */
export default function AcceptInviteScreen() {
  const navigate = useNavigate();
  const location = useLocation();
  const { lang } = useLanguage();

  const token = new URLSearchParams(location.search).get('token') || '';

  const [status, setStatus] = useState(token ? 'loading' : 'no-token'); // loading | valid | invalid | no-token
  const [invite, setInvite] = useState(null);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [mascotState, setMascotState] = useState('idle');

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    getInviteDetails(token)
      .then((data) => {
        if (cancelled) return;
        setInvite(data);
        setStatus('valid');
      })
      .catch(() => {
        if (cancelled) return;
        setStatus('invalid');
      });
    return () => { cancelled = true; };
  }, [token]);

  const strength = strengthScore(password);
  const S_LABELS = lang === 'vi'
    ? ['Rất yếu', 'Yếu', 'Trung bình', 'Mạnh', 'Rất mạnh']
    : ['Very weak', 'Weak', 'Medium', 'Strong', 'Very strong'];

  function validate() {
    const e = {};
    if (password.length < 12) e.password = lang === 'vi' ? 'Tối thiểu 12 ký tự.' : 'Minimum 12 characters.';
    if (password !== confirm) e.confirm = lang === 'vi' ? 'Mật khẩu không khớp.' : 'Passwords do not match.';
    return e;
  }

  async function handleSubmit(ev) {
    ev.preventDefault();
    const e = validate();
    if (Object.keys(e).length) {
      setErrors(e);
      setMascotState('error');
      return;
    }

    setSubmitting(true);
    setMascotState('loading');
    setErrors({});

    try {
      await register({
        email: invite.email,
        password,
        fullName: invite.full_name,
        inviteToken: token,
      });
      setSuccess(true);
      setMascotState('success');
      setTimeout(() => {
        navigate('/login', { replace: true });
      }, 1500);
    } catch (err) {
      setMascotState('error');
      setErrors({ form: err.message || (lang === 'vi' ? 'Không thể kích hoạt tài khoản. Vui lòng thử lại.' : 'Could not activate account. Please try again.') });
      setSubmitting(false);
    }
  }

  if (status === 'no-token') {
    return (
      <AuthLayout
        title={lang === 'vi' ? 'Cần lời mời từ tổ chức' : 'You need an invitation'}
        subtitle={lang === 'vi'
          ? 'Cursus không mở đăng ký công khai. Tài khoản do trường của bạn cấp.'
          : 'Cursus has no public sign-up. Accounts are issued by your institution.'}
        mascotState="idle"
      >
        <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 text-center space-y-5">
          <div className="w-14 h-14 rounded-full bg-brand-blue-soft text-brand-blue flex items-center justify-center mx-auto">
            <Building2 size={26} />
          </div>
          <p className="text-sm text-fg-secondary leading-relaxed">
            {lang === 'vi'
              ? 'Sinh viên được nhập/đồng bộ, giảng viên được quản trị viên mời, quản trị viên được cấp khi khởi tạo tổ chức. Nếu trường của bạn chưa dùng Cursus, hãy gửi yêu cầu bên dưới.'
              : 'Students are imported/synced, teachers are invited by an admin, admins are provisioned when an organization is set up. If your school isn’t on Cursus yet, send a request below.'}
          </p>
          <Link to="/request-access" className="btn-auth-primary inline-flex">
            {lang === 'vi' ? 'Yêu cầu quyền truy cập cho tổ chức' : 'Request institutional access'}
          </Link>
          <div className="pt-2">
            <Link to="/login" className="link-auth-secondary text-sm hover:underline inline-flex items-center gap-1.5 text-fg-secondary">
              <ArrowLeft size={14} className="icon-arrow" />
              {lang === 'vi' ? 'Quay lại đăng nhập' : 'Back to login'}
            </Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  if (status === 'loading') {
    return (
      <AuthLayout title={lang === 'vi' ? 'Đang kiểm tra lời mời...' : 'Checking invitation...'} mascotState="loading">
        <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 text-center text-sm text-fg-muted">
          {lang === 'vi' ? 'Vui lòng đợi trong giây lát.' : 'Please wait a moment.'}
        </div>
      </AuthLayout>
    );
  }

  if (status === 'invalid') {
    return (
      <AuthLayout
        title={lang === 'vi' ? 'Lời mời không hợp lệ hoặc đã hết hạn' : 'Invalid or expired invitation'}
        mascotState="error"
      >
        <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 text-center space-y-5">
          <p className="text-sm text-fg-secondary">
            {lang === 'vi'
              ? 'Liên kết này đã được dùng, hết hạn, hoặc không còn hiệu lực. Liên hệ quản trị viên của bạn để được gửi lời mời mới.'
              : 'This link has been used, expired, or is no longer valid. Ask your admin to send a new invite.'}
          </p>
          <Link to="/login" className="btn-auth-primary inline-flex">
            {lang === 'vi' ? 'Quay lại đăng nhập' : 'Back to login'}
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title={lang === 'vi' ? 'Kích hoạt tài khoản' : 'Activate your account'}
      subtitle={lang === 'vi' ? `Bạn được ${invite.organization_name} mời tham gia Cursus.` : `${invite.organization_name} invited you to Cursus.`}
      mascotState={mascotState}
      cardWidth={480}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 relative">
        <div className="mb-6">
          <Link to="/" className="link-auth-secondary hover:underline group text-fg-secondary">
            <ArrowLeft size={16} className="icon-arrow" />
            {lang === 'vi' ? 'Về trang chủ' : 'Back to home'}
          </Link>
        </div>

        {/* Read-only invite summary — email/role/org come from the server, never editable here */}
        <div className="mb-6 p-4 rounded-xl bg-surface border border-line space-y-2.5">
          <div className="flex items-center gap-2.5 text-sm">
            <Mail size={15} className="text-fg-muted shrink-0" />
            <span className="font-semibold text-fg">{invite.email}</span>
          </div>
          <div className="flex items-center gap-2.5 text-sm">
            <ShieldCheck size={15} className="text-fg-muted shrink-0" />
            <span className="text-fg-secondary">
              {(ROLE_LABEL[lang] || ROLE_LABEL.vi)[String(invite.role || '').toLowerCase()]} · {invite.organization_name}
            </span>
          </div>
        </div>

        {errors.form && (
          <div role="alert" aria-live="assertive" className="p-3.5 rounded-xl bg-danger/10 border border-danger/20 text-sm font-semibold text-danger mb-4 animate-scale-in">
            {errors.form}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <div>
            <label htmlFor="invite-password" className="block text-sm font-semibold mb-2 text-fg-secondary">
              {lang === 'vi' ? 'Đặt mật khẩu' : 'Set a password'}
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                id="invite-password"
                type={showPass ? 'text' : 'password'}
                autoComplete="new-password"
                autoFocus
                className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-11 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                value={password}
                disabled={submitting}
                aria-invalid={!!errors.password}
                onChange={(e) => { setPassword(e.target.value); setErrors((p) => ({ ...p, password: undefined, form: undefined })); }}
              />
              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 text-fg-muted hover:text-fg transition-colors outline-none rounded"
                onClick={() => setShowPass((v) => !v)}
                aria-label={showPass ? (lang === 'vi' ? 'Ẩn mật khẩu' : 'Hide password') : (lang === 'vi' ? 'Hiện mật khẩu' : 'Show password')}
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {password && (
              <div className="mt-3 space-y-1.5">
                <div className="flex justify-between items-center text-[11px] font-bold">
                  <span className="text-fg-muted">{lang === 'vi' ? 'Độ mạnh mật khẩu' : 'Password strength'}</span>
                  <span style={{ color: S_COLORS[strength] }}>{S_LABELS[strength]}</span>
                </div>
                <div className="flex gap-1 h-1.5">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="flex-1 rounded-full transition-all duration-300"
                      style={{ background: i < strength ? S_COLORS[strength] : 'var(--border-ui)' }} />
                  ))}
                </div>
              </div>
            )}
            {errors.password && <p className="text-sm mt-1.5 font-semibold text-danger">{errors.password}</p>}
          </div>

          <div>
            <label htmlFor="invite-confirm" className="block text-sm font-semibold mb-2 text-fg-secondary">
              {lang === 'vi' ? 'Xác nhận mật khẩu' : 'Confirm password'}
            </label>
            <div className="relative">
              <Lock size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                id="invite-confirm"
                type={showPass ? 'text' : 'password'}
                autoComplete="new-password"
                className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-4 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                value={confirm}
                disabled={submitting}
                aria-invalid={!!errors.confirm}
                onChange={(e) => { setConfirm(e.target.value); setErrors((p) => ({ ...p, confirm: undefined, form: undefined })); }}
              />
            </div>
            {errors.confirm && <p className="text-sm mt-1.5 font-semibold text-danger">{errors.confirm}</p>}
          </div>

          <button type="submit" className="btn-auth-primary mt-2" disabled={submitting} style={{ width: '100%' }}>
            {success ? (
              <span className="flex items-center gap-2">
                <Check size={18} className="text-white" />
                {lang === 'vi' ? 'Kích hoạt thành công' : 'Account activated'}
              </span>
            ) : submitting ? (
              <span className="flex items-center gap-2">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin">
                  <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
                </svg>
                {lang === 'vi' ? 'Đang xử lý...' : 'Working...'}
              </span>
            ) : (
              <span className="flex items-center gap-2">
                {lang === 'vi' ? 'Kích hoạt & đăng nhập' : 'Activate & continue'}
                <ArrowRight size={16} className="icon-arrow" />
              </span>
            )}
          </button>
        </form>
      </div>
    </AuthLayout>
  );
}
