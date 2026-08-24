import React from 'react';
import { Link } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';

export default function NotFoundPage() {
  const { t } = useLanguage();

  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center bg-surface">
      <div className="mono text-8xl font-bold mb-4 select-none text-line-strong">
        404
      </div>
      <h1 className="text-2xl font-semibold mb-3 text-fg">
        {t('states.notFoundTitle')}
      </h1>
      <p className="text-sm mb-6 max-w-sm text-fg-secondary">
        {t('states.notFoundDesc')}
      </p>
      <Link to="/" className="btn btn-accent px-6 py-3 cursor-pointer">
        {t('states.notFoundCta')}
      </Link>
    </div>
  );
}
