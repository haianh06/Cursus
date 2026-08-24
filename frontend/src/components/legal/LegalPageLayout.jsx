import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingLogoMark from '../landing/LandingLogoMark';

/**
 * Shared shell for standalone legal pages (Privacy Policy, Terms of
 * Service). Deliberately NOT the full LandingNavbar/LandingFooter: those
 * are built for in-page anchor scrolling on "/" and would silently no-op
 * here. A minimal header (logo + back-to-home) is the common pattern for
 * legal pages anyway.
 */
export default function LegalPageLayout({ title, updatedAtLabel, children }) {
  const { lang } = useLanguage();

  return (
    <div className="landing-page-scope font-sans min-h-screen flex flex-col bg-landing-bg text-landing-text">
      <header className="border-b border-landing-border">
        <div className="max-w-[760px] mx-auto px-6 lg:px-0 h-[72px] flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent rounded">
            <LandingLogoMark size={26} />
            <span className="landing-wordmark text-landing-text">Cursus</span>
          </Link>
          <Link
            to="/"
            className="flex items-center gap-1.5 text-sm font-medium text-landing-text-secondary hover:text-landing-text transition-colors"
          >
            <ArrowLeft size={15} />
            {lang === 'vi' ? 'Về trang chủ' : 'Back to home'}
          </Link>
        </div>
      </header>

      <main className="flex-1 max-w-[760px] w-full mx-auto px-6 lg:px-0 py-14 lg:py-20">
        <h1 className="font-display text-3xl md:text-4xl font-bold text-landing-text mb-2 tracking-tight">
          {title}
        </h1>
        <p className="text-sm text-landing-text-muted mb-10">{updatedAtLabel}</p>
        <div className="legal-content text-landing-text-secondary text-[15px] leading-relaxed space-y-8">
          {children}
        </div>
      </main>

      <footer className="border-t border-landing-border py-8">
        <div className="max-w-[760px] mx-auto px-6 lg:px-0 flex flex-wrap items-center justify-between gap-3 text-xs text-landing-text-muted">
          <span>&copy; {new Date().getFullYear()} Cursus.</span>
          <div className="flex items-center gap-5">
            <Link to="/privacy" className="hover:text-landing-text transition-colors">
              {lang === 'vi' ? 'Chính sách bảo mật' : 'Privacy Policy'}
            </Link>
            <Link to="/terms" className="hover:text-landing-text transition-colors">
              {lang === 'vi' ? 'Điều khoản dịch vụ' : 'Terms of Service'}
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
