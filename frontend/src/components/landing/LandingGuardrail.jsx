import React from 'react';
import { MessageCircle, Search, Ban, MessagesSquare } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';

export default function LandingGuardrail() {
  const { t } = useLanguage();

  const flow = [
    { icon: MessageCircle, labelKey: 'integrityStepRequest' },
    { icon: Search, labelKey: 'integrityStepDetect' },
    { icon: Ban, labelKey: 'integrityStepRefuse', isBlocked: true },
    { icon: MessagesSquare, labelKey: 'integrityStepRedirect' }
  ];

  return (
    <section id="academic-integrity" className="py-24 lg:py-32 px-6 lg:px-10 bg-landing-surface-muted border-y border-landing-border relative z-10">
      <div className="max-w-[1280px] mx-auto grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
        <LandingReveal className="text-left">
          <span className="text-xs font-medium text-landing-text-muted mb-3 block">
            {t('landing.integrityLabel')}
          </span>
          <h2 className="landing-section-heading text-2xl md:text-4xl font-display text-landing-text mb-6">
            {t('landing.integrityTitle')}
          </h2>
          <p className="text-landing-text-secondary text-base md:text-lg leading-relaxed">
            {t('landing.integrityDesc')}
          </p>
        </LandingReveal>

        <LandingReveal className="flex flex-col gap-5">
          {/* Decision flow — coral appears only on the refusal step, nowhere else */}
          {/* flex-nowrap + horizontal scroll (not flex-wrap) so the chip/arrow
              sequence is always a single row at a given viewport — VI/EN
              label-length differences change the row's total scrollable
              width, never which chips wrap to a new line relative to their
              connecting arrows. */}
          <div className="flex items-center gap-1.5 flex-nowrap overflow-x-auto pb-1 -mx-1 px-1">
            {flow.map((step, i) => {
              const Icon = step.icon;
              return (
                <React.Fragment key={step.labelKey}>
                  <div
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium whitespace-nowrap shrink-0 ${
                      step.isBlocked
                        ? 'border-landing-danger/30 bg-landing-danger-soft text-landing-danger'
                        : 'border-landing-border bg-landing-surface text-landing-text-secondary'
                    }`}
                  >
                    <Icon size={14} className="shrink-0" />
                    {t(`landing.${step.labelKey}`)}
                  </div>
                  {i < flow.length - 1 && (
                    <span className="text-landing-text-muted text-xs shrink-0" aria-hidden="true">→</span>
                  )}
                </React.Fragment>
              );
            })}
          </div>

          <div className="bg-landing-surface p-4 rounded-xl border border-landing-border">
            <p className="text-sm font-medium text-landing-text">"{t('landing.presetGuardrailQuestion')}"</p>
          </div>

          <div className="pl-5 border-l-2 border-landing-border">
            <p className="text-sm text-landing-text-secondary leading-relaxed">
              {t('landing.presetGuardrailAnswer')}
            </p>
          </div>
        </LandingReveal>
      </div>
    </section>
  );
}
