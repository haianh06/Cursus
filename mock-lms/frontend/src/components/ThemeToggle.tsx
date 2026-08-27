import { Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { useLanguage } from '../context/LanguageContext';

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();
  const { t } = useLanguage();
  const isDark = theme === 'dark';

  return (
    <button
      type="button"
      onClick={toggleTheme}
      className="relative w-8 h-8 shrink-0 flex items-center justify-center rounded-[var(--radius-sm)] border border-slate-200 cursor-pointer transition-colors overflow-hidden"
      aria-pressed={isDark}
      aria-label={isDark ? t('nav.themeToLight') : t('nav.themeToDark')}
      title={isDark ? t('nav.themeToLight') : t('nav.themeToDark')}
    >
      <Sun
        size={14}
        aria-hidden="true"
        className="absolute text-amber-500 transition-all duration-300 ease-out"
        style={{
          opacity: isDark ? 0 : 1,
          transform: isDark ? 'scale(0.4) rotate(-70deg)' : 'scale(1) rotate(0deg)',
        }}
      />
      <Moon
        size={14}
        aria-hidden="true"
        className="absolute text-[var(--accent)] transition-all duration-300 ease-out"
        style={{
          opacity: isDark ? 1 : 0,
          transform: isDark ? 'scale(1) rotate(0deg)' : 'scale(0.4) rotate(70deg)',
        }}
      />
    </button>
  );
}
