import React from 'react';
import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import { useLanguage } from '../../context/LanguageContext';

export default function ThemeToggle({ className = '' }) {
  const { theme, toggleTheme } = useTheme();
  const { t } = useLanguage();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className={`relative w-10 h-10 shrink-0 flex items-center justify-center rounded-lg border border-landing-border bg-landing-surface hover:bg-landing-surface-elevated hover:border-landing-border-hover transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent overflow-hidden ${className}`}
      aria-pressed={isDark}
      aria-label={isDark ? t('landing.themeToggleToLight') : t('landing.themeToggleToDark')}
      title={isDark ? t('landing.themeToggleToLight') : t('landing.themeToggleToDark')}
    >
      {/* Sun and Moon are both always mounted and crossfade in place
          (opacity + transform only) so switching theme never remounts an
          icon or shifts the button's fixed 40x40 footprint. */}
      <Sun
        size={16}
        aria-hidden="true"
        className="landing-theme-icon absolute text-landing-text-secondary transition-all duration-[var(--motion-emphasized)] ease-[var(--ease-emphasized)]"
        style={{
          opacity: isDark ? 0 : 1,
          transform: isDark ? 'scale(0.4) rotate(-70deg)' : 'scale(1) rotate(0deg)',
          filter: isDark ? 'none' : 'drop-shadow(0 0 3px rgba(217, 160, 82, 0.35))'
        }}
      />
      <Moon
        size={16}
        aria-hidden="true"
        className="landing-theme-icon absolute text-landing-text-secondary transition-all duration-[var(--motion-emphasized)] ease-[var(--ease-emphasized)]"
        style={{
          opacity: isDark ? 1 : 0,
          transform: isDark ? 'scale(1) rotate(0deg)' : 'scale(0.4) rotate(70deg)',
          // rgba(36,104,201,…) = --brand-blue's own RGB (was rgba(96,165,250,…),
          // the old dark-mode --landing-accent value, retired in the
          // 18/08/2026 brand-blue consolidation).
          filter: isDark ? 'drop-shadow(0 0 3px rgba(36, 104, 201, 0.35))' : 'none'
        }}
      />
    </button>
  );
}
