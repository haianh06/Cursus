import { useLanguage } from '../context/LanguageContext';

const OPTIONS = ['vi', 'en'] as const;

export function LanguageToggle() {
  const { lang, setLang } = useLanguage();
  const activeIndex = OPTIONS.indexOf(lang);

  return (
    <div
      role="radiogroup"
      aria-label={lang === 'vi' ? 'Chọn ngôn ngữ' : 'Select language'}
      className="relative inline-flex items-center p-0.5 rounded-[var(--radius-sm)] border border-slate-200"
    >
      <span
        aria-hidden="true"
        className="absolute top-0.5 bottom-0.5 left-0.5 w-7 rounded-[4px] transition-transform duration-200 ease-out"
        style={{ background: 'var(--accent)', transform: `translateX(${activeIndex * 28}px)` }}
      />
      {OPTIONS.map((code) => {
        const isActive = lang === code;
        return (
          <button
            key={code}
            type="button"
            role="radio"
            aria-checked={isActive}
            onClick={() => setLang(code)}
            className={`relative z-10 h-7 w-7 rounded-[4px] text-[10px] font-bold uppercase tracking-wide transition-colors cursor-pointer ${
              isActive ? 'text-white' : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            {code}
          </button>
        );
      })}
    </div>
  );
}
