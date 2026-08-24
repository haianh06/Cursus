import React from 'react';
import { MessageSquareQuote, BarChart3, ShieldCheck, BookOpen } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';

// Weekly completion bars for the "evidence" cell — deliberately not the same
// numbers as anywhere else on the page; this is a compact illustrative
// mockup, not a data source.
const EVIDENCE_BARS = [40, 65, 55, 82, 70, 91];

export default function LandingFeatureBento() {
  const { t } = useLanguage();

  return (
    <section className="py-20 lg:py-28 px-6 lg:px-10 bg-landing-bg relative z-10">
      <div className="max-w-[1280px] mx-auto">
        <LandingReveal className="max-w-2xl mb-12 lg:mb-14">
          <span className="text-xs font-medium text-landing-text-muted mb-3 block">
            {t('landing.bentoKicker')}
          </span>
          <h2 className="landing-section-heading text-2xl md:text-4xl font-display text-landing-text">
            {t('landing.bentoTitle')}
          </h2>
        </LandingReveal>

        <LandingReveal>
          <div className="bento-grid">
            {/* Grounded Q&A — the central claim, full-width cell */}
            <div className="bento-cell bento-cell--qa border border-landing-border bg-landing-surface-muted lg:flex-row lg:items-center lg:gap-10">
              <div className="lg:flex-1">
                <div className="w-10 h-10 rounded-xl bg-landing-accent-soft flex items-center justify-center mb-4">
                  <MessageSquareQuote size={19} className="text-landing-accent" />
                </div>
                <h3 className="text-lg font-semibold text-landing-text mb-2">{t('landing.bentoQaTitle')}</h3>
                <p className="text-sm text-landing-text-secondary leading-relaxed max-w-sm">{t('landing.bentoQaDesc')}</p>
              </div>

              <div className="mt-6 lg:mt-0 lg:flex-1 lg:max-w-md w-full rounded-xl border border-landing-border bg-landing-surface p-4 flex flex-col gap-2.5">
                <div className="self-end max-w-[85%] rounded-2xl rounded-br-sm bg-landing-cta text-landing-cta-fg text-sm px-3.5 py-2.5">
                  {t('landing.bentoQaMsgUser')}
                </div>
                <div className="self-start max-w-[90%] rounded-2xl rounded-bl-sm border border-landing-border bg-landing-surface-elevated text-landing-text text-sm px-3.5 py-2.5">
                  {t('landing.bentoQaMsgAssistant')}
                  <div className="mt-2 pt-2 border-t border-landing-border flex items-center gap-1.5 text-[11px] font-semibold text-landing-accent">
                    <BookOpen size={12} className="shrink-0" />
                    <span>{t('landing.bentoQaCitation')}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Instructor evidence — mini bar chart */}
            <div className="bento-cell bento-cell--evidence border border-landing-border bg-landing-surface-muted">
              <div className="w-10 h-10 rounded-xl bg-landing-accent-soft flex items-center justify-center mb-4">
                <BarChart3 size={19} className="text-landing-accent" />
              </div>
              <h3 className="text-lg font-semibold text-landing-text mb-2">{t('landing.bentoEvidenceTitle')}</h3>
              <p className="text-sm text-landing-text-secondary leading-relaxed mb-6">{t('landing.bentoEvidenceDesc')}</p>

              <div className="mt-auto">
                <div className="flex items-end gap-2 h-24">
                  {EVIDENCE_BARS.map((h, i) => (
                    <div key={i} className="flex-1 rounded-t-md bg-landing-accent/70" style={{ height: `${h}%` }} />
                  ))}
                </div>
                <p className="mt-2.5 text-[11px] font-medium text-landing-text-muted">{t('landing.bentoEvidenceLegend')}</p>
              </div>
            </div>

            {/* Academic guardrail — shield with soft glow */}
            <div className="bento-cell bento-cell--guardrail border border-landing-border bg-landing-surface-muted items-start relative overflow-hidden">
              <div
                className="absolute -top-8 -right-8 w-32 h-32 rounded-full pointer-events-none"
                style={{ background: 'radial-gradient(circle, var(--landing-accent-soft) 0%, transparent 70%)' }}
                aria-hidden="true"
              />
              <div className="w-10 h-10 rounded-xl bg-landing-accent-soft flex items-center justify-center mb-4 relative">
                <ShieldCheck size={19} className="text-landing-accent" />
              </div>
              <h3 className="text-lg font-semibold text-landing-text mb-2 relative">{t('landing.bentoGuardrailTitle')}</h3>
              <p className="text-sm text-landing-text-secondary leading-relaxed relative">{t('landing.bentoGuardrailDesc')}</p>
            </div>
          </div>
        </LandingReveal>
      </div>
    </section>
  );
}
