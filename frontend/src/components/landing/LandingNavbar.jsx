import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import ThemeToggle from '../shared/ThemeToggle';
import LanguageToggle from '../shared/LanguageToggle';
import LandingLogoMark from './LandingLogoMark';

const NAV_LINKS = [
  // minWidth = ceil(max(vi, en) rendered width at 14px/550) + ~6px buffer, so the
  // link's own box never shrinks when the shorter-language label swaps in — that's
  // what keeps the centered nav block (and therefore the whole bar) from re-centering
  // on VI <-> EN toggle. Measured with Playwright against the live rendered nav.
  { id: 'home', labelKey: 'landing.navHome', minWidth: 68 },
  { id: 'product', labelKey: 'landing.navProduct', minWidth: 70 },
  { id: 'how-it-works', labelKey: 'landing.navWorkflow', minWidth: 108 },
  { id: 'for-instructors', labelKey: 'landing.navLecturer', minWidth: 138 },
  { id: 'academic-integrity', labelKey: 'landing.navGuardrail', minWidth: 126 },
  { id: 'try-it', labelKey: 'landing.navSandbox', minWidth: 82 }
];

export default function LandingNavbar({ activeSection, handleNavClick }) {
  const navigate = useNavigate();
  const { t, lang } = useLanguage();
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const mobileMenuButtonRef = useRef(null);
  const mobileMenuPanelRef = useRef(null);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 10);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    if (!mobileMenuOpen) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileMenuOpen]);

  useEffect(() => {
    if (!mobileMenuOpen) return undefined;

    const panel = mobileMenuPanelRef.current;
    const focusable = panel
      ? Array.from(panel.querySelectorAll('a[href], button:not([disabled])'))
      : [];
    (focusable[0] || panel)?.focus();

    const handleKeydown = (e) => {
      if (e.key === 'Escape') {
        setMobileMenuOpen(false);
        mobileMenuButtonRef.current?.focus();
        return;
      }
      if (e.key !== 'Tab' || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    window.addEventListener('keydown', handleKeydown);
    return () => {
      window.removeEventListener('keydown', handleKeydown);
      mobileMenuButtonRef.current?.focus();
    };
  }, [mobileMenuOpen]);

  const handleLogoClick = (e) => {
    if (window.location.pathname === '/') {
      // Same destination as the Home nav link — reuse its handler so
      // history/scroll/reduced-motion behavior stays identical.
      handleNavClick(e, 'home');
    } else {
      e.preventDefault();
      navigate('/');
    }
  };

  return (
    <header
      className={`fixed top-0 inset-x-0 h-[72px] z-50 transition-[background-color,border-color] duration-[var(--motion-emphasized)] ease-[var(--ease-emphasized)] ${
        isScrolled
          ? 'bg-landing-surface-muted/95 backdrop-blur-md border-b border-black/[0.06] dark:border-white/[0.08]'
          : 'bg-transparent border-transparent'
      }`}
      role="banner"
    >
      {!isScrolled && (
        // The day hero video is bright, and the Hero's own scrim only darkens the left
        // side (fading to fully transparent on the right) — so the forced-white nav text
        // above measured ~1.3:1 contrast (need 4.5:1) wherever it sat over that faded-out
        // right two-thirds, in light theme specifically. This scrim is independent of the
        // Hero's, spans the full navbar width evenly, and holds ~0.94 opacity through the
        // full 72px header height — pixel-sampled >=6:1 against every nav label even over
        // the video's brightest hotspots (window/lamp), with headroom because a playing
        // video's brightness isn't static frame to frame — before fading into the hero.
        <div
          className="absolute inset-x-0 top-0 h-[160px] z-0 pointer-events-none"
          style={{ background: 'linear-gradient(to bottom, rgba(0,0,0,0.94) 0px, rgba(0,0,0,0.94) 72px, rgba(0,0,0,0) 160px)' }}
          aria-hidden="true"
        />
      )}
      {/* The "transparent bar over the dark hero video" text/surface override is scoped to
          this row only — NOT the <header> itself — because the mobile menu panel below is a
          sibling of this row. It always renders a solid, theme-correct surface, so it must
          always resolve --landing-text/--landing-surface from the real light/dark theme
          instead of inheriting this always-white override (that was the light-mode
          "white text on white panel" unreadable-contrast bug). */}
      <div
        className="relative z-10 w-full max-w-[1440px] mx-auto grid grid-cols-2 min-[1400px]:grid-cols-[auto_1fr_auto] gap-x-4 min-[1400px]:gap-x-6 items-center px-6 min-[1400px]:px-8 h-full"
        style={!isScrolled ? {
          '--landing-text': '#ffffff',
          '--landing-text-secondary': 'rgba(255, 255, 255, 0.85)',
          '--landing-text-muted': 'rgba(255, 255, 255, 0.65)',
          // LanguageToggle pairs bg-landing-text (its sliding thumb) with
          // text-landing-bg (the active option's label) so the label always
          // reads against the thumb. --landing-text flips to white right above,
          // so --landing-bg must flip to black here too, or that label — still
          // its theme value (near-white in light mode) — winds up near-white on
          // the now-white thumb (axe-core measured 1.09:1, the "VI/EN nearly
          // invisible" report).
          '--landing-bg': '#000000',
          '--landing-surface': 'rgba(0, 0, 0, 0.15)',
          '--landing-surface-elevated': 'rgba(0, 0, 0, 0.3)',
          '--landing-surface-inverse': '#ffffff',
          '--landing-text-inverse': '#000000',
          '--landing-border': 'rgba(255, 255, 255, 0.15)',
          '--landing-border-hover': 'rgba(255, 255, 255, 0.3)',
        } : {}}
      >
        <div className="flex justify-start">
          <a
            href="/"
            onClick={handleLogoClick}
            className="landing-logo-link flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent rounded"
            aria-label={lang === 'vi' ? 'Cursus — về trang chủ' : 'Cursus — go to homepage'}
          >
            <LandingLogoMark size={28} />
            <span className="landing-wordmark text-landing-text">Cursus</span>
          </a>
        </div>

        <nav className="hidden min-[1400px]:flex items-center gap-5 justify-center" role="navigation" aria-label={lang === 'vi' ? 'Điều hướng chính' : 'Main navigation'}>
          {NAV_LINKS.map((link) => {
            const isActive = activeSection === link.id;
            return (
              <a
                key={link.id}
                href={`#${link.id}`}
                onClick={(e) => handleNavClick(e, link.id)}
                aria-current={isActive ? 'page' : undefined}
                style={{ minWidth: `${link.minWidth}px` }}
                className={`landing-nav-link relative inline-flex justify-center pb-1 transition-colors rounded leading-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent after:content-[''] after:absolute after:left-0 after:right-0 after:-bottom-1 after:h-[2px] after:rounded-full after:transition-colors after:duration-[var(--motion-ui)] active:scale-[0.98] ${
                  isActive
                    ? 'text-landing-text font-semibold after:bg-landing-text'
                    : 'text-landing-text-secondary font-medium hover:text-landing-text after:bg-transparent'
                }`}
              >
                {t(link.labelKey)}
              </a>
            );
          })}
        </nav>

        <div className="flex items-center justify-end gap-2 min-[1400px]:gap-2.5">
          <div className="hidden min-[1400px]:flex items-center gap-1.5">
            <LanguageToggle />
            <ThemeToggle />
          </div>
          <button
            onClick={() => navigate('/login')}
            className="hidden min-[1400px]:inline-flex shrink-0 items-center justify-center whitespace-nowrap min-w-[104px] h-[42px] px-3 rounded-lg text-sm font-medium text-landing-text-secondary hover:text-landing-text hover:bg-landing-surface-elevated transition-colors active:scale-[0.98] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent"
          >
            {t('landing.loginBtn')}
          </button>
          <button
            onClick={() => navigate('/demo/select-role')}
            className="shrink-0 inline-flex items-center justify-center whitespace-nowrap h-[42px] min-w-[168px] bg-landing-cta text-landing-cta-fg hover:bg-landing-cta-hover hover:shadow-landing-sm text-sm font-semibold px-3.5 rounded-lg transition-[background-color,box-shadow,transform] active:scale-[0.98] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent focus-visible:ring-offset-2"
          >
            {t('landing.startFreeBtn')}
          </button>
          <button
            ref={mobileMenuButtonRef}
            onClick={() => setMobileMenuOpen((v) => !v)}
            className="min-[1400px]:hidden w-10 h-10 flex items-center justify-center rounded-lg text-landing-text-secondary hover:bg-landing-surface-elevated transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent"
            aria-label={mobileMenuOpen ? t('landing.menuCloseLabel') : t('landing.menuOpenLabel')}
            aria-expanded={mobileMenuOpen}
            aria-controls="landing-mobile-menu"
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {mobileMenuOpen && (
        <>
          <div
            className="min-[1400px]:hidden fixed inset-x-0 top-[72px] bottom-0 z-40 bg-black/40 backdrop-blur-sm"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          <div
            id="landing-mobile-menu"
            ref={mobileMenuPanelRef}
            role="dialog"
            aria-modal="true"
            aria-label={lang === 'vi' ? 'Menu di động' : 'Mobile navigation'}
            tabIndex={-1}
            className="min-[1400px]:hidden absolute top-full left-0 right-0 z-40 max-h-[calc(100vh-72px)] overflow-y-auto bg-landing-surface/98 backdrop-blur-xl border-b border-landing-border shadow-landing-lg"
          >
            <nav className="flex flex-col p-4 gap-1">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.id}
                  href={`#${link.id}`}
                  onClick={(e) => {
                    handleNavClick(e, link.id);
                    setMobileMenuOpen(false);
                  }}
                  className={`px-3 py-3 rounded-lg block transition-colors ${
                    activeSection === link.id
                      ? 'text-landing-text font-semibold bg-landing-surface-muted'
                      : 'text-landing-text-secondary font-medium hover:bg-landing-surface-elevated hover:text-landing-text'
                  }`}
                >
                  {t(link.labelKey)}
                </a>
              ))}
              <a
                href="/login"
                onClick={(e) => { e.preventDefault(); setMobileMenuOpen(false); navigate('/login'); }}
                className="px-3 py-3 rounded-lg block font-medium text-landing-text-secondary hover:bg-landing-surface-elevated hover:text-landing-text transition-colors mt-2 border-t border-landing-border"
              >
                {t('landing.loginBtn')}
              </a>
              <div className="flex items-center justify-between px-3 pt-4 mt-2">
                <LanguageToggle />
                <ThemeToggle />
              </div>
            </nav>
          </div>
        </>
      )}
    </header>
  );
}
