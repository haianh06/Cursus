import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, LogIn } from 'lucide-react';
import LandingLogoMark from '../landing/LandingLogoMark';
import ThemeToggle from '../shared/ThemeToggle';
import LanguageToggle from '../shared/LanguageToggle';
import { useLanguage } from '../../context/LanguageContext';

/**
 * Header cua man Chon vai tro, dung theo anh tham chieu: ben trai la logo
 * va nut quay lai; ben phai la VI|EN, nut doi che do va nut dang nhap dang
 * the noi. Moi thu tren cung mot duong tam doc, khong phan tu nao duoc
 * xuong dong.
 *
 * Logo (30/08, phien ban 2): dung LandingLogoMark ("C" khoi) + chu "Cursus"
 * — DUNG Y HET logo Landing Page (xem LandingNavbar.jsx) — thay vi
 * CursusLogo (anh lockup Curi) dung truoc do. Yeu cau rieng: logo header
 * phai giong Landing Page tren moi man.
 */
export default function CursusAuthHeader({ showBackLink = false, showLoginLink = false }) {
  const { lang } = useLanguage();
  const vi = lang === 'vi';

  return (
    <header className="cb-header">
      <div className="cb-header__left">
        <Link
          to="/"
          className="cb-logo cb-logo-old"
          aria-label={vi ? 'Cursus — về trang chủ' : 'Cursus — back to home'}
        >
          <LandingLogoMark size={30} strokeClassName="cb-logomark-stroke" dotClassName="cb-logomark-dot" />
          <span className="cb-logo-old__text">Cursus</span>
        </Link>
        {showBackLink && (
          <Link to="/" className="cb-backlink">
            <ArrowLeft size={19} strokeWidth={1.9} aria-hidden="true" />
            {vi ? 'Về trang chủ' : 'Back to home'}
          </Link>
        )}
      </div>

      <div className="cb-header__right">
        <div className="cb-toggles">
          <LanguageToggle />
          <ThemeToggle />
        </div>
        {showLoginLink && (
          <Link to="/login" className="cb-header-login">
            <LogIn size={18} strokeWidth={1.9} aria-hidden="true" />
            {vi ? 'Đã có tài khoản? Đăng nhập' : 'Have an account? Sign in'}
          </Link>
        )}
      </div>
    </header>
  );
}
