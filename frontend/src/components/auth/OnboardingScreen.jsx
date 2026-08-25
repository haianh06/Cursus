import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check } from 'lucide-react';
import AuthLayout from './AuthLayout';
import { supabase } from '../../lib/supabaseClient';
import { googleLogin } from '../../lib/api';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Route: `/onboarding`. Despite the name, this is no longer a student
 * setup flow (profile completion + class-schedule declaration were both
 * removed — schedules are now assigned by an admin, not declared by the
 * student). What's left is purely mechanical: finish exchanging a
 * just-completed Google OAuth redirect for a real FastAPI session, then
 * bounce straight to the dashboard. A user with an existing session never
 * lands here at all (see the `user.onboarded` guard in App.jsx, always true
 * now) — this only ever renders mid Google-sign-in.
 */
export default function OnboardingScreen() {
  const navigate = useNavigate();
  const { lang } = useLanguage();

  const [errorMsg, setErrorMsg] = useState('');
  const [mascotState, setMascotState] = useState('loading');

  useEffect(() => {
    let cancelled = false;
    let syncStarted = false;

    const runGoogleSync = async (authUser) => {
      if (syncStarted) return;
      syncStarted = true;
      try {
        const fullName = authUser.user_metadata?.name || authUser.user_metadata?.full_name || authUser.email.split('@')[0];
        const data = await googleLogin({
          email: authUser.email,
          fullName,
          googleId: authUser.id,
        });

        setMascotState('success');

        // Clear Supabase session so we only rely on FastAPI httpOnly cookie session
        await supabase.auth.signOut();

        setTimeout(() => {
          const role = (data.user?.role || 'student').toLowerCase();
          navigate(`/${role}`, { replace: true });
          window.location.reload();
        }, 800);
      } catch (err) {
        console.error(err);
        setErrorMsg(err.message || 'Google synchronization failed.');
        setMascotState('error');
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

  return (
    <AuthLayout
      title={lang === 'vi' ? 'Đang đăng nhập…' : 'Signing you in…'}
      subtitle={lang === 'vi' ? 'Đang hoàn tất đăng nhập bằng Google.' : 'Finishing your Google sign-in.'}
      mascotState={mascotState}
      cardWidth={420}
    >
      <div className="p-8 rounded-[var(--radius-lg)] border border-line bg-surface-card shadow-elevation-3 flex flex-col items-center gap-3 text-center">
        {errorMsg ? (
          <div role="alert" className="p-3 bg-danger/10 border border-danger/20 text-xs font-semibold text-danger rounded-xl">
            {errorMsg}
          </div>
        ) : mascotState === 'success' ? (
          <span className="flex items-center gap-2 text-sm font-semibold text-fg">
            <Check size={18} className="text-success" />
            {lang === 'vi' ? 'Đăng nhập thành công!' : 'Signed in!'}
          </span>
        ) : (
          <>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" className="spin text-brand-blue">
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
            </svg>
            <span className="text-xs text-fg-muted font-semibold font-mono">
              {lang === 'vi' ? 'ĐANG ĐỒNG BỘ...' : 'SYNCING...'}
            </span>
          </>
        )}
      </div>
    </AuthLayout>
  );
}
