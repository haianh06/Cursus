import React from 'react';
import { FileText, Quote, UserCheck } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';

const ITEMS = [
  { icon: FileText, key: 'productTruthItem1' },
  { icon: Quote, key: 'productTruthItem2', verified: true },
  { icon: UserCheck, key: 'productTruthItem3' }
];

export default function LandingTrustStrip() {
  const { t } = useLanguage();

  return (
    <section id="proof-strip" className="py-14 lg:py-16 px-6 lg:px-10 border-y border-landing-border bg-landing-surface-muted relative z-10">
      <LandingReveal className="max-w-[1000px] mx-auto grid sm:grid-cols-3 gap-6 sm:gap-10">
        {ITEMS.map(({ icon: Icon, key, verified }) => (
          <div key={key} className="flex items-start gap-3">
            <Icon size={18} className={`shrink-0 mt-0.5 ${verified ? 'text-landing-accent' : 'text-landing-text-muted'}`} />
            <p className="text-sm font-medium text-landing-text-secondary leading-relaxed">
              {t(`landing.${key}`)}
            </p>
          </div>
        ))}
      </LandingReveal>
    </section>
  );
}
