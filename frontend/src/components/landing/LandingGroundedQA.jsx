import React, { useState } from 'react';
import { Quote, FileText, AlertTriangle, ChevronDown } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';

/**
 * Deliberately fixed graphite section — does NOT follow the light/dark
 * theme toggle. It's one visual "beat" in the page's rhythm (light → dark →
 * light), not a themed surface, so its colors reference the --landing-fixed-*
 * tokens (index.css :root) instead of the theme-flipping --landing-* ones —
 * those are pinned once, globally, to the same values this section always
 * used, so they can't quietly drift out of sync with the real dark palette
 * the way a hand-copied hex literal did before (this section's muted-text
 * color was still #858B84, a shade retired for failing an axe-core contrast
 * check well before this fix — --landing-fixed-text-muted carries the
 * corrected #959B94 instead). The "verified citation" teal was also its own
 * bespoke #58BDB6, matching neither --accent nor --landing-accent — that's
 * consolidated into --brand-blue now, since "verified citation" is exactly
 * what --landing-accent (now an alias of brand-blue) already exists for. */
export default function LandingGroundedQA() {
  const { t, lang } = useLanguage();
  const [excerptOpen, setExcerptOpen] = useState(false);

  return (
    <section
      id="grounded"
      className="py-20 lg:py-28 px-6 lg:px-10 relative z-10 overflow-hidden"
      style={{ backgroundColor: 'var(--landing-fixed-surface-muted)' }}
    >
      <div className="max-w-[1280px] mx-auto grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        <LandingReveal className="text-left">
          <span className="text-xs font-medium mb-3 block" style={{ color: 'var(--landing-fixed-text-muted)' }}>
            {t('landing.groundedLabel')}
          </span>
          <h2 className="landing-section-heading text-2xl md:text-4xl font-display mb-6" style={{ color: 'var(--landing-fixed-text)' }}>
            {t('landing.howTitle')}
          </h2>
          <p className="text-base md:text-lg leading-relaxed mb-4" style={{ color: 'var(--landing-fixed-text-secondary)' }}>
            {t('landing.howDesc1')}
          </p>
          <p className="text-base md:text-lg leading-relaxed" style={{ color: 'var(--landing-fixed-text-secondary)' }}>
            {t('landing.howDesc2')}
          </p>
        </LandingReveal>

        <LandingReveal className="flex flex-col gap-4">
          <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: 'var(--landing-fixed-text-muted)' }}>
            {t('landing.howExampleLabel')}
          </span>

          <div className="p-4 rounded-xl border" style={{ backgroundColor: 'var(--landing-fixed-surface)', borderColor: 'var(--landing-fixed-border)' }}>
            <p className="text-sm font-medium" style={{ color: 'var(--landing-fixed-text)' }}>"{t('landing.presetPassQuestion')}"</p>
          </div>

          <div className="pl-5 border-l-2 space-y-3 relative" style={{ borderColor: 'var(--brand-blue)' }}>
            <div
              className="absolute -left-[17px] top-1 rounded-full border w-8 h-8 flex items-center justify-center"
              style={{ backgroundColor: 'var(--landing-fixed-surface)', borderColor: 'var(--landing-fixed-border)', color: 'var(--brand-blue)' }}
            >
              <Quote size={14} />
            </div>
            <p className="text-sm leading-relaxed mt-1" style={{ color: 'var(--landing-fixed-text-secondary)' }}>
              {t('landing.presetPassAnswer')}
            </p>

            {/* Citation — a real, keyboard-focusable control (not a static
                chip), expands to the document name + a short excerpt */}
            <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'rgba(36,104,201,0.25)' }}>
              <button
                type="button"
                onClick={() => setExcerptOpen((v) => !v)}
                aria-expanded={excerptOpen}
                className="w-full flex items-center justify-between gap-2 px-3 py-2 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1"
                style={{ backgroundColor: 'var(--brand-blue-soft)', color: 'var(--brand-blue-text-dark)' }}
              >
                <span className="flex items-center gap-2">
                  <FileText size={14} /> {t('landing.presetPassSource')}
                </span>
                <ChevronDown size={14} className={`transition-transform duration-200 ${excerptOpen ? 'rotate-180' : ''}`} />
              </button>
              {excerptOpen && (
                <div className="px-3 py-2.5 text-xs leading-relaxed border-t" style={{ backgroundColor: 'var(--landing-fixed-surface)', borderColor: 'rgba(36,104,201,0.2)', color: 'var(--landing-fixed-text-secondary)' }}>
                  <span className="font-semibold" style={{ color: 'var(--landing-fixed-text)' }}>
                    {lang === 'vi' ? 'Trích đoạn: ' : 'Excerpt: '}
                  </span>
                  “Final Exam ≥ 4.0, Course Average ≥ 5.0/10 — Section 3.1”
                </div>
              )}
            </div>
          </div>

          <div className="mt-1 pt-4 border-t flex items-start gap-2.5" style={{ borderColor: 'var(--landing-fixed-border)' }}>
            <AlertTriangle size={15} className="shrink-0 mt-0.5" style={{ color: 'var(--landing-fixed-warning)' }} />
            <p className="text-xs leading-relaxed" style={{ color: 'var(--landing-fixed-text-muted)' }}>
              <span className="font-semibold" style={{ color: 'var(--landing-fixed-text-secondary)' }}>{t('landing.howFallbackLead')}</span>{' '}
              {t('landing.unsupportedAnswer')}
            </p>
          </div>
        </LandingReveal>
      </div>
    </section>
  );
}
