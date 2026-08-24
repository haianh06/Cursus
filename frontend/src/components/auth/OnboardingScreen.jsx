import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, BookOpen, GraduationCap, Check, ArrowRight, Shield } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { supabase } from '../../lib/supabaseClient';
import { googleLogin } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

const MAJORS = [
  { value: 'Software Engineering', label: 'Kỹ thuật Phần mềm (Software Engineering)' },
  { value: 'Artificial Intelligence', label: 'Trí tuệ Nhân tạo (Artificial Intelligence)' },
  { value: 'Information Assurance', label: 'An toàn Thông tin (Information Assurance)' },
  { value: 'Information Systems', label: 'Hệ thống Thông tin (Information Systems)' }
];

export default function OnboardingScreen() {
  const navigate = useNavigate();
  const { t, lang } = useLanguage();

  const [user, setUser] = useState(null);
  const [name, setName] = useState('');
  const [studentId, setStudentId] = useState('');
  const [major, setMajor] = useState(MAJORS[0].value);
  // Role is never client-settable here; Teacher/Admin access is granted by
  // an administrator out of band, never through this form. Note: Google
  // sign-in now only authenticates an already-invited account (backend
  // rejects unknown emails, see src/api/auth.py google_login) — this
  // profile-completion step only ever runs for a user who was invited and
  // already has a role assigned server-side.
  const role = 'student';

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [mascotState, setMascotState] = useState('idle');

  useEffect(() => {
    let cancelled = false;
    let syncStarted = false;

    const runGoogleSync = async (authUser) => {
      if (syncStarted) return;
      syncStarted = true;
      try {
        setLoading(true);
        setMascotState('loading');

        const fullName = authUser.user_metadata?.name || authUser.user_metadata?.full_name || authUser.email.split('@')[0];
        const data = await googleLogin({
          email: authUser.email,
          fullName,
          googleId: authUser.id
        });

        setSuccess(true);
        setMascotState('success');

        // Clear Supabase session so we only rely on FastAPI httpOnly cookie session
        await supabase.auth.signOut();

        setTimeout(() => {
          const role = (data.user?.role || 'student').toLowerCase();
          navigate(`/${role}`, { replace: true });
          window.location.reload();
        }, 1000);

      } catch (err) {
        console.error(err);
        setErrorMsg(err.message || 'Google synchronization failed.');
        setMascotState('error');
        setLoading(false);
      }
    };

    // Right after the Google OAuth redirect lands here, supabase-js may still be
    // exchanging the ?code= in the URL for a session (async, not instant). Calling
    // getUser() once immediately can race that exchange and see "no user" even
    // though sign-in actually succeeded — kicking the user straight back to
    // /login with no visible error. Listening for onAuthStateChange (which fires
    // once the exchange completes) instead of a single getUser() check avoids
    // that race.
    const { data: authListener } = supabase.auth.onAuthStateChange((event, session) => {
      if (cancelled) return;
      if (session?.user) {
        runGoogleSync(session.user);
      }
    });

    // Fallback: if a session already exists (e.g. user reloaded this exact page),
    // onAuthStateChange won't fire again — check directly too.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (cancelled || session?.user) return;
      // Give the URL-based session exchange a moment before giving up — only
      // bail to /login if still no session after a short grace period.
      setTimeout(() => {
        if (cancelled) return;
        supabase.auth.getSession().then(({ data: { session: retrySession } }) => {
          if (cancelled) return;
          if (!retrySession?.user) {
            navigate('/login', { replace: true });
          }
        });
      }, 2000);
    });

    return () => {
      cancelled = true;
      authListener?.subscription?.unsubscribe();
    };
  }, [navigate]);

  const handleOnboarding = async (e) => {
    e.preventDefault();
    if (!name.trim() || loading) return;

    setLoading(true);
    setMascotState('loading');
    setErrorMsg('');

    try {
      const profilePayload = {
        id: user.id,
        name: name,
        role: role
      };

      const { error: profileError } = await supabase
        .from('profiles')
        .upsert(profilePayload);

      if (profileError) throw profileError;

      const { error: authError } = await supabase.auth.updateUser({
        data: {
          name: name,
          role: role,
          student_id: role === 'student' ? studentId : undefined,
          major: role === 'student' ? major : undefined,
          onboarded: true
        }
      });

      if (authError) throw authError;

      setSuccess(true);
      setMascotState('success');

      setTimeout(() => {
        navigate(`/${role}`, { replace: true });
        window.location.reload();
      }, 1000);

    } catch (err) {
      console.error(err);
      setMascotState('error');
      setErrorMsg(err.message || (lang === 'vi' ? 'Thiết lập thất bại. Vui lòng thử lại.' : 'Setup failed. Please try again.'));
      setLoading(false);
    }
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-surface flex flex-col items-center justify-center gap-3">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin text-brand-blue"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/></svg>
        <span className="text-xs text-fg-muted font-semibold font-mono">LOADING ONBOARDING...</span>
      </div>
    );
  }

  return (
    <AuthLayout
      title={t('auth.onboardingTitle')}
      subtitle={t('auth.onboardingDesc')}
      mascotState={mascotState}
      cardWidth={480}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 relative">
        <form onSubmit={handleOnboarding} className="space-y-5" noValidate>
          
          <h2 className="font-display text-xl font-bold text-fg mb-2">
            {lang === 'vi' ? 'Thiết lập hồ sơ' : 'Complete Profile'}
          </h2>

          {errorMsg && (
            <div role="alert" className="p-3 bg-danger/10 border border-danger/20 text-xs font-semibold text-danger rounded-xl mb-4">
              {errorMsg}
            </div>
          )}

          {/* Full name input */}
          <div>
            <label htmlFor="onboard-name" className="block text-sm font-semibold mb-2 text-fg-secondary">
              {t('auth.regNameLabel')}
            </label>
            <div className="relative">
              <User size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                id="onboard-name"
                type="text"
                required
                className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-4 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                placeholder={t('auth.regNamePlaceholder')}
                value={name}
                disabled={loading}
                onFocus={() => setMascotState('typing-email')}
                onBlur={() => setMascotState('idle')}
                onChange={e => setName(e.target.value)}
              />
            </div>
          </div>

          {/* Major Selection */}
          <div>
            <label htmlFor="onboard-major" className="block text-sm font-semibold mb-2 text-fg-secondary">
              {t('auth.onboardingMajor')}
            </label>
            <div className="relative">
              <GraduationCap size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
              <select
                id="onboard-major"
                className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-4 text-sm text-fg outline-none cursor-pointer appearance-none"
                style={{ colorScheme: 'dark' }}
                value={major}
                disabled={loading}
                onChange={e => setMajor(e.target.value)}
              >
                {MAJORS.map(m => (
                  <option key={m.value} value={m.value} className="bg-surface-card text-fg">
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Student ID input */}
          <div>
            <label htmlFor="onboard-id" className="block text-sm font-semibold mb-2 text-fg-secondary">
              {t('auth.onboardingStudentId')}
            </label>
            <div className="relative">
              <BookOpen size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-fg-muted" />
              <input
                id="onboard-id"
                type="text"
                className="w-full h-[52px] bg-surface border border-line rounded-xl pl-11 pr-4 text-sm text-fg placeholder-fg-muted outline-none input-auth-field"
                placeholder="e.g. SE180123"
                value={studentId}
                disabled={loading}
                onFocus={() => setMascotState('typing-email')}
                onBlur={() => setMascotState('idle')}
                onChange={e => setStudentId(e.target.value.toUpperCase())}
              />
            </div>
          </div>

          {/* Teacher/Admin access is never self-serve — informational only, no
              form field, no client-settable role. Matches AcceptInviteScreen. */}
          <div className="flex items-start gap-2.5 p-3.5 rounded-xl bg-surface border border-line">
            <Shield size={14} className="text-fg-muted shrink-0 mt-0.5" />
            <p className="text-[11px] text-fg-muted leading-relaxed">
              {lang === 'vi'
                ? 'Là Giảng viên hoặc Quản trị viên? Quyền truy cập được quản trị viên hệ thống cấp riêng, không qua form này.'
                : 'Are you a Teacher or Admin? That access is granted separately by a system administrator, not through this form.'}
            </p>
          </div>

          <button
            type="submit"
            className="btn-auth-primary text-sm mt-4"
            disabled={loading}
          >
            {success ? (
              <span className="flex items-center gap-2">
                <Check size={18} className="text-white" />
                {lang === 'vi' ? 'Thiết lập thành công!' : 'Profile Setup Complete!'}
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
                {lang === 'vi' ? 'Bắt đầu học tập' : 'Get Started'}
                <ArrowRight size={16} />
              </span>
            )}
          </button>
        </form>
      </div>
    </AuthLayout>
  );
}
