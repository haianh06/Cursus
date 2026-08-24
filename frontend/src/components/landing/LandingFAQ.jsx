import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';

const FAQ_KEYS = ['faqPricing', 'faqAccount', 'faqPrivacy', 'faqIntegrity', 'faqSandbox', 'faqLanguage', 'faqIntegration'];

export default function LandingFAQ() {
  const { t } = useLanguage();
  const [openKey, setOpenKey] = useState(FAQ_KEYS[0]);

  return (
    <section id="faq" className="py-24 lg:py-32 px-6 lg:px-10 bg-landing-bg relative z-10">
      <div className="max-w-[880px] mx-auto">
        <LandingReveal className="text-center mb-12">
          <h2 className="landing-section-heading text-2xl md:text-4xl font-display text-landing-text mb-4">
            {t('landing.faqTitle')}
          </h2>
          <p className="text-landing-text-secondary text-base md:text-lg leading-relaxed">
            {t('landing.faqSubtitle')}
          </p>
        </LandingReveal>

        <LandingReveal className="flex flex-col gap-3">
          {FAQ_KEYS.map((key) => {
            const isOpen = openKey === key;
            const panelId = `${key}-panel`;
            const buttonId = `${key}-trigger`;
            return (
              <div
                key={key}
                className="rounded-xl border border-landing-border bg-landing-surface overflow-hidden"
              >
                <h3>
                  <button
                    type="button"
                    id={buttonId}
                    aria-expanded={isOpen}
                    aria-controls={panelId}
                    onClick={() => setOpenKey(isOpen ? null : key)}
                    className="w-full flex items-center justify-between gap-4 text-left px-5 py-4 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent"
                  >
                    <span className="font-semibold text-landing-text text-[15px] md:text-base">
                      {t(`landing.${key}Q`)}
                    </span>
                    <ChevronDown
                      size={18}
                      className={`shrink-0 text-landing-text-muted transition-transform duration-[var(--motion-standard)] ${isOpen ? 'rotate-180' : ''}`}
                      aria-hidden="true"
                    />
                  </button>
                </h3>
                <div
                  id={panelId}
                  role="region"
                  aria-labelledby={buttonId}
                  className={`grid transition-[grid-template-rows] duration-[var(--motion-standard)] ease-[var(--ease-standard)] ${isOpen ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
                >
                  <div className="overflow-hidden">
                    <p className="px-5 pb-4 text-sm md:text-[15px] text-landing-text-secondary leading-relaxed">
                      {t(`landing.${key}A`)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </LandingReveal>
      </div>
    </section>
  );
}
