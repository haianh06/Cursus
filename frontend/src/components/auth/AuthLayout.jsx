import React from 'react';
import { Link } from 'react-router-dom';
import Mascot from '../shared/CursusMascot';
import { useLanguage } from '../../context/LanguageContext';
import { useTheme } from '../../context/ThemeContext';
import LandingLogoMark from '../landing/LandingLogoMark';
import ThemeToggle from '../shared/ThemeToggle';
import LanguageToggle from '../shared/LanguageToggle';

/**
 * Shared split-screen layout for /login, /register, /forgot-password, /onboarding.
 * Left: brand, interactive robot mascot Cursus Assistant, and verified benefits copy.
 * Right: the auth card passed in as children.
 */
export default function AuthLayout({ title, subtitle, children, cardWidth = 460, mascotState = 'idle' }) {
  const { lang } = useLanguage();
  const { theme } = useTheme();
 
  // Standard benefits copy as per request with matching semantic tag classes.
  // Label text is --text-secondary, not --plan/--do/--reflect directly: at
  // this weight/size (9px bold), all three tokens' own hues measured
  // 3.18-4.09:1 against this tinted chip background — under the 4.5:1 text
  // bar (they're tuned for the app's normal, larger badge/icon uses, which
  // this tiny all-caps tag isn't). The tint + border alone still keep each
  // tag visually distinct; only the letters themselves needed a safe color.
  const benefits = [
    { label: 'PLAN', colorClass: 'bg-plan/10 text-fg-secondary border-plan/20', text: lang === 'vi' ? 'Lập kế hoạch tuần từ syllabus và deadline.' : 'Plan your study week directly from the syllabus and deadlines.' },
    { label: 'DO', colorClass: 'bg-do/10 text-fg-secondary border-do/20', text: lang === 'vi' ? 'Nhận câu trả lời có trích nguồn học liệu.' : 'Get answers verified by course material citations.' },
    { label: 'REFLECT', colorClass: 'bg-reflect/10 text-fg-secondary border-reflect/20', text: lang === 'vi' ? 'Theo dõi tiến độ và cải thiện sau mỗi tuần.' : 'Track your progress and improve week by week.' }
  ];
 
  return (
    <div className="min-h-screen flex items-stretch justify-center bg-surface text-fg transition-colors duration-300 relative overflow-hidden font-sans select-none">

      {/* The visible page title below lives inside the "hidden lg:flex" brand
          panel, so it disappears from the DOM entirely under 1024px (Chrome
          collapses `display:none` subtrees out of the accessibility tree) --
          every screen through this layout had zero <h1> on mobile. This
          sr-only copy is the ONE real heading, always present; the panel's
          copy below is demoted to a <p> so there's still just one <h1> in
          the tree, not two competing ones for screen-reader heading nav. */}
      <h1 className="sr-only">{title}</h1>

      {/* ── DOT MATRIX BACKGROUND — flat, no blur (blob glow retired) ── */}
      <div className="absolute inset-0 opacity-[0.03] bg-grid pointer-events-none" />

      {/* Language/theme switching is a core, always-available affordance on
          the landing page and every authenticated dashboard screen — but
          was missing here, leaving /login, /onboarding, /accept-invite,
          /forgot-password, /reset-password, /email-verification and
          /request-access as dead ends for a visitor who lands there first
          (e.g. from a bookmarked/shared link) in the "wrong" language or
          theme. `ThemeToggle`/`LanguageToggle` read their colors from the
          `--landing-*` custom properties, which only exist inside
          `.landing-page-scope` — scoping just this wrapper reuses that
          already-tuned, contrast-verified styling instead of forking the
          components for a second token set. */}
      <div className="landing-page-scope absolute top-5 right-5 lg:top-6 lg:right-6 z-20 flex items-center gap-2">
        <LanguageToggle />
        <ThemeToggle />
      </div>

      {/* Main Container constrained to max 1280px */}
      <div className="max-w-[1280px] w-full mx-auto flex items-stretch relative z-10">
        
        {/* ── LEFT SIDEBAR: Cursus Brand & Mascot Info ── */}
        <div
          className="relative hidden lg:flex flex-col justify-between flex-1 px-16 py-12 overflow-hidden border-r border-line"
        >
          {/* Logo pinned top-left, links back to home "/" */}
          <Link to="/" className="inline-flex items-center gap-3 outline-none group focus-visible:ring-2 focus-visible:ring-brand-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--bg-app)] rounded-lg p-1 w-max">
            <span className="transition-transform duration-300 group-hover:scale-105">
              <LandingLogoMark size={36} strokeClassName="text-fg" dotClassName="fill-accent" />
            </span>
            <div className="text-left flex items-center gap-2.5">
              <span className="logo-text-custom text-fg tracking-tight">Cursus</span>
            </div>
          </Link>
 
          {/* Interactive Mascot & Slogans */}
          <div className="flex flex-col gap-6 max-w-md my-auto">
            {/* Same navy "sky" glow as the chat launcher and the boot loader
                (rgba(20,49,92,…)) — this screen previously had no glow behind
                the mascot at all, which was the actual source of "why does
                it look different on every page": not a wrong color, a missing
                one. */}
            <div
              className="shrink-0 origin-center w-[150px] h-[150px] rounded-full flex items-center justify-center"
              style={{
                background: theme === 'dark'
                  ? 'radial-gradient(circle at 30% 20%, rgba(26,27,31,0.95) 0%, rgba(20,49,92,0.22) 50%, rgba(148,163,184,0.06) 100%)'
                  : 'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.95) 0%, rgba(20,49,92,0.14) 50%, rgba(148,163,184,0.08) 100%)'
              }}
            >
              <div className="w-[130px] h-[130px]">
                <Mascot size={130} state={mascotState} />
              </div>
            </div>

            <div className="space-y-4 pt-2">
              {/* Decorative duplicate of the real <h1> above (sr-only, always
                  in the DOM) -- kept as a <p> so this desktop-only panel
                  doesn't add a second real heading to the page. */}
              <p aria-hidden="true" className="font-display text-[32px] font-bold leading-[1.25] text-metallic tracking-tight">
                {title}
              </p>
              {subtitle && (
                <p className="text-base leading-[1.6] text-fg-secondary font-semibold">{subtitle}</p>
              )}
            </div>
 
            {/* Structured Product Benefits */}
            <div className="space-y-4 pt-2 border-t border-line">
              {benefits.map(({ label, colorClass, text }) => (
                <div key={label} className="flex items-start gap-4">
                  <span className={`mono text-[9px] font-bold px-2 py-0.5 rounded border uppercase tracking-widest mt-0.5 ${colorClass}`}>
                    {label}
                  </span>
                  <span className="text-sm font-semibold text-fg-secondary leading-normal">{text}</span>
                </div>
              ))}
            </div>
          </div>
 
          {/* Static Footer */}
          <div className="mono text-[10px] text-fg-muted">
            Cursus · 2026
          </div>
        </div>

        {/* ── RIGHT COLUMN: Form Card Panel ── */}
        <div className="flex-1 flex flex-col items-center justify-center p-6 lg:p-12 min-w-0">
          <div className="w-full animate-scale-in" style={{ maxWidth: cardWidth }}>

            {/* Mobile-only brand logo mark */}
            <div className="flex lg:hidden items-center justify-center gap-2.5 mb-8">
              <LandingLogoMark size={28} strokeClassName="text-fg" dotClassName="fill-accent" />
              <span className="font-display font-black text-xl text-fg tracking-tight">Cursus</span>
            </div>

            {/* Form Slot */}
            {children}
          </div>
        </div>

      </div>
    </div>
  );
}
