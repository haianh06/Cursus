import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Sun, Moon } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { useTheme } from '../../context/ThemeContext';
import LoginLanguageSelect from './LoginLanguageSelect';
import LandingLogoMark from '../landing/LandingLogoMark';

/**
 * Khung dung chung cho cac man auth phu (Forgot/Reset Password), theo dung
 * phong cach moi cua LoginScreen (clp-* / cursus-login.css) — nhung khac
 * LoginScreen o 2 diem, theo yeu cau rieng 30/08:
 *   1. Logo header dung CHU "C" khoi cu (LandingLogoMark, giong AuthLayout
 *      va Landing Page) — KHONG dung logo lockup con Curi
 *      (CursusLogo/BrandAsset) ma LoginScreen/DemoSelectRoleScreen dang dung.
 *   2. Khong co 3 the Plan/Do/Reflect — khong lien quan ngu canh quen/dat
 *      lai mat khau, nen bo hang do, chi giu illustration + tieu de.
 *
 * Minh hoa Curi (mascot) o cot trai + goc card van duoc giu — do la
 * illustration trang tri, khac voi logo o header.
 *
 * KHONG dung cho /email-verification, /request-access, /onboarding,
 * /accept-invite — cac man do van dung AuthLayout nguyen ven (chua co yeu
 * cau doi UI).
 */
export default function AuthCardLayout({
  heroTitle,
  heroSub,
  heroImg = '/brand/login-curi-study-hero.png',
  children,
}) {
  const { t, lang } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const vi = lang === 'vi';
  const isDark = theme === 'dark';

  const backLink = (extraClass) => (
    <Link to="/" className={`clp-back${extraClass ? ` ${extraClass}` : ''}`}>
      <ArrowLeft size={20} strokeWidth={2} aria-hidden="true" />
      {t('auth.backToHome')}
    </Link>
  );

  return (
    <div className="cursus-login-page">
      <div className="clp-bg" aria-hidden="true" />

      <div className="clp-shell">
        <header className="clp-header">
          <Link to="/" className="clp-logo clp-logo-old" aria-label={vi ? 'Cursus — về trang chủ' : 'Cursus — back to home'}>
            <LandingLogoMark size={32} strokeClassName="clp-logomark-stroke" dotClassName="clp-logomark-dot" />
            <span className="clp-logo-old__text">Cursus</span>
          </Link>

          <div className="clp-header__controls">
            <LoginLanguageSelect />
            <button
              type="button"
              className="clp-theme"
              onClick={toggleTheme}
              aria-pressed={isDark}
              aria-label={isDark ? t('landing.themeToggleToLight') : t('landing.themeToggleToDark')}
              title={isDark ? t('landing.themeToggleToLight') : t('landing.themeToggleToDark')}
            >
              {isDark
                ? <Moon size={22} strokeWidth={1.9} aria-hidden="true" />
                : <Sun size={22} strokeWidth={1.9} aria-hidden="true" />}
            </button>
          </div>
        </header>

        <main className="clp-main">
          <section className="clp-brand">
            {backLink('clp-back--outside')}

            <div className="clp-hero">
              <img src={heroImg} alt="" aria-hidden="true" className="clp-hero__img" draggable="false" />
            </div>

            <h1 className="clp-heading">{heroTitle}</h1>
            {heroSub && <p className="clp-sub">{heroSub}</p>}
          </section>

          <section className="clp-card">
            <div className="clp-peek" aria-hidden="true">
              <img src="/brand/login-curi-peek.png" alt="" aria-hidden="true" className="clp-peek__img" draggable="false" />
            </div>

            {backLink()}

            {children}
          </section>
        </main>
      </div>
    </div>
  );
}
