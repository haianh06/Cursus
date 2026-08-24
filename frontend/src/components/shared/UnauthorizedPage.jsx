import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { ROLE_LABEL, DEFAULT_ROUTE } from '../../constants/roles';

/**
 * Shown when a signed-in user's role doesn't match the route they tried to
 * reach (e.g. a student opening an /instructor/* link). Explicit page
 * instead of a silent redirect, so the "why did the URL change" question
 * never comes up.
 */
export default function UnauthorizedPage({ role }) {
  const { lang } = useLanguage();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center bg-surface">
      <div className="w-14 h-14 rounded-full bg-danger-soft flex items-center justify-center mb-5">
        <ShieldAlert size={26} className="text-danger" />
      </div>
      <h1 className="text-2xl font-semibold mb-3 text-fg">
        {lang === 'vi' ? 'Bạn không có quyền truy cập trang này' : "You don't have access to this page"}
      </h1>
      <p className="text-sm mb-6 max-w-sm text-fg-secondary">
        {lang === 'vi'
          ? `Trang này dành cho vai trò khác với tài khoản ${role ? ROLE_LABEL.vi[role] : ''} của bạn.`
          : `This page is for a different role than your ${role ? ROLE_LABEL.en[role] : ''} account.`}
      </p>
      <button
        type="button"
        onClick={() => navigate(role ? DEFAULT_ROUTE[role] : '/', { replace: true })}
        className="btn btn-accent px-6 py-3 cursor-pointer"
      >
        {lang === 'vi' ? 'Về trang của tôi' : 'Back to my dashboard'}
      </button>
    </div>
  );
}
