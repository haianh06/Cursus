import React, { useRef } from 'react';
import { useLanguage } from '../../context/LanguageContext';

const OPTIONS = ['vi', 'en'];

/**
 * Segmented control with a single sliding thumb (transform: translateX
 * only, never a layout-affecting width/left change) — both segments are
 * always the same fixed size, so the control's total footprint never
 * changes between locales. The thumb is filled with the neutral text
 * color, matching the primary CTA treatment; no teal here — teal is
 * reserved for tiny signal/verified marks elsewhere on the page, not UI
 * chrome. Implemented as an ARIA radiogroup so Tab lands once on the
 * checked option and ArrowLeft/ArrowRight move the roving selection,
 * per the WAI-ARIA radio-group pattern.
 */
export default function LanguageToggle({ className = '' }) {
  const { lang, setLang } = useLanguage();
  const groupRef = useRef(null);
  const activeIndex = OPTIONS.indexOf(lang);

  const handleKeyDown = (e) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
    e.preventDefault();
    const dir = e.key === 'ArrowRight' ? 1 : -1;
    const nextIndex = (activeIndex + dir + OPTIONS.length) % OPTIONS.length;
    setLang(OPTIONS[nextIndex]);
    groupRef.current?.querySelectorAll('button')[nextIndex]?.focus();
  };

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label={lang === 'vi' ? 'Chọn ngôn ngữ' : 'Select language'}
      onKeyDown={handleKeyDown}
      className={`relative inline-flex items-center p-0.5 rounded-lg border border-landing-border bg-landing-surface ${className}`}
    >
      <span
        aria-hidden="true"
        className="absolute top-0.5 bottom-0.5 left-0.5 w-[38px] rounded-[7px] bg-landing-text transition-transform duration-[var(--motion-ui)] ease-[var(--ease-standard)]"
        style={{ transform: `translateX(${activeIndex * 38}px)` }}
      />
      {OPTIONS.map((code) => {
        const isActive = lang === code;
        return (
          <button
            key={code}
            type="button"
            role="radio"
            aria-checked={isActive}
            tabIndex={isActive ? 0 : -1}
            onClick={() => setLang(code)}
            className={`relative z-10 px-2.5 h-9 w-[38px] rounded-[7px] text-xs font-semibold uppercase tracking-wide transition-colors cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
              isActive ? 'text-landing-bg' : 'text-landing-text-muted hover:text-landing-text'
            }`}
          >
            {code}
          </button>
        );
      })}
    </div>
  );
}
