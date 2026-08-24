import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ArrowRight, Mail, Phone, MapPin } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingLogoMark from './LandingLogoMark';

// Placeholder contact details — swap for the real institution/company
// details once available. Kept centralized here so there's exactly one
// place to update when real contact info is ready. Deliberately NOT tied to
// any real institution's name/campus (18/08/2026) — the organizing
// committee's brief only ever specified a generic "University X", never a
// real named school, and Cursus has no affiliation with the one this used
// to name.
const CONTACT_EMAIL = 'contact@cursus.edu.vn';
const CONTACT_PHONE = '+84 24 7300 5588';
const CONTACT_ADDRESS = {
  vi: 'Hà Nội, Việt Nam',
  en: 'Hanoi, Vietnam',
};

export default function LandingFooter() {
  const navigate = useNavigate();
  const { t, lang } = useLanguage();

  return (
    <>
      {/* FINAL CTA — the story's closing beat: a continuation-line motif
          (reflect → next plan, the loop closing) instead of a generic
          gradient box. Monochrome, one restrained Cursus Assistant glow, no teal fill. */}
      <section className="py-16 lg:py-20 px-6 lg:px-10 z-10 relative bg-landing-bg overflow-hidden">
        <div className="max-w-[1024px] mx-auto rounded-3xl bg-landing-surface-inverse px-8 py-14 md:py-16 text-center flex flex-col items-center relative overflow-hidden z-10">
          <div
            className="pointer-events-none absolute -top-20 left-1/2 -translate-x-1/2 w-[380px] h-[180px] rounded-full opacity-50"
            style={{ background: 'radial-gradient(closest-side, var(--landing-accent-glow), transparent)' }}
            aria-hidden="true"
          />

          {/* Continuation line: reflect (left dot) → next plan (right, teal).
              bg-landing-text-inverse/NN, not a hardcoded rgba(245,245,242,…):
              this card's background is --landing-surface-inverse, which
              flips (dark in light mode, light in dark mode) — a fixed
              off-white was invisible against the now-light card in dark
              mode (axe measured 1.02:1 contrast on the paragraph below). */}
          <div className="flex items-center gap-2 mb-6 relative" aria-hidden="true">
            <span className="w-1.5 h-1.5 rounded-full bg-landing-text-inverse/35" />
            <span className="w-10 h-px bg-landing-text-inverse/20" />
            <span className="w-2 h-2 rounded-full bg-landing-accent" />
          </div>

          <h2 className="landing-section-heading text-2xl md:text-4xl font-display text-landing-text-inverse mb-4 relative">
            {t('landing.ctaTitle')}
          </h2>
          <p className="text-base md:text-lg max-w-xl mx-auto mb-8 leading-relaxed relative text-landing-text-inverse/85">
            {t('landing.ctaBody')}
          </p>

          <div className="flex flex-wrap items-center justify-center gap-4 relative">
            <button
              onClick={() => navigate('/demo/select-role')}
              className="px-7 py-3.5 bg-landing-cta text-landing-cta-fg hover:bg-landing-cta-hover text-base font-semibold rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent focus-visible:ring-offset-2 flex items-center gap-2"
            >
              {t('landing.ctaPrimary')} <ArrowRight size={17} />
            </button>
            <a
              href="#how-it-works"
              className="px-7 py-3.5 border text-base font-medium rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent"
              style={{ borderColor: 'color-mix(in srgb, var(--landing-text-inverse) 25%, transparent)', color: 'var(--landing-text-inverse)' }}
            >
              {t('landing.ctaSecondary')}
            </a>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-landing-border px-6 lg:px-10 py-14 z-10 relative bg-landing-surface">
        <div className="max-w-[1280px] mx-auto grid grid-cols-1 md:grid-cols-[auto_1fr_auto] gap-10 md:gap-8 mb-10">
          <div className="flex items-center gap-2.5">
            <LandingLogoMark size={22} />
            <span className="font-display font-semibold text-lg text-landing-text tracking-tight">Cursus</span>
          </div>

          <nav className="flex flex-wrap items-start md:items-center gap-x-8 gap-y-3 text-sm font-medium text-landing-text-secondary md:justify-center">
            <a href="#product" className="hover:text-landing-text transition-colors">{t('landing.navProduct')}</a>
            <a href="#how-it-works" className="hover:text-landing-text transition-colors">{t('landing.navWorkflow')}</a>
            <a href="#academic-integrity" className="hover:text-landing-text transition-colors">{t('landing.navGuardrail')}</a>
            <a href="#for-instructors" className="hover:text-landing-text transition-colors">{t('landing.navLecturer')}</a>
            <a href="#try-it" className="hover:text-landing-text transition-colors">{t('landing.navSandbox')}</a>
          </nav>

          {/* Contact column — placeholder details (see CONTACT_* constants
              above) until real institution contact info is supplied. */}
          <div className="flex flex-col gap-2 text-xs text-landing-text-secondary md:items-end md:text-right">
            <span className="text-[11px] font-semibold uppercase tracking-wide text-landing-text-muted mb-0.5">
              {lang === 'vi' ? 'Liên hệ' : 'Contact'}
            </span>
            <a href={`mailto:${CONTACT_EMAIL}`} className="flex items-center gap-1.5 md:flex-row-reverse hover:text-landing-text transition-colors">
              <Mail size={13} className="shrink-0" aria-hidden="true" />
              {CONTACT_EMAIL}
            </a>
            <a href={`tel:${CONTACT_PHONE.replace(/\s+/g, '')}`} className="flex items-center gap-1.5 md:flex-row-reverse hover:text-landing-text transition-colors">
              <Phone size={13} className="shrink-0" aria-hidden="true" />
              {CONTACT_PHONE}
            </a>
            <span className="flex items-start gap-1.5 md:flex-row-reverse max-w-[220px]">
              <MapPin size={13} className="shrink-0 mt-0.5" aria-hidden="true" />
              {lang === 'vi' ? CONTACT_ADDRESS.vi : CONTACT_ADDRESS.en}
            </span>
          </div>
        </div>

        <div className="max-w-[1280px] mx-auto pt-6 border-t border-landing-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4 text-xs text-landing-text-muted">
          <span>&copy; {new Date().getFullYear()} Cursus. Built by Neural Forge.</span>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
            <Link to="/privacy" className="hover:text-landing-text transition-colors">
              {lang === 'vi' ? 'Chính sách bảo mật' : 'Privacy Policy'}
            </Link>
            <Link to="/terms" className="hover:text-landing-text transition-colors">
              {lang === 'vi' ? 'Điều khoản dịch vụ' : 'Terms of Service'}
            </Link>
            <Link to="/request-access" className="hover:text-landing-text transition-colors">
              {lang === 'vi' ? 'Liên hệ / Triển khai cho trường' : 'Contact / Institutional access'}
            </Link>
          </div>
        </div>
      </footer>
    </>
  );
}
