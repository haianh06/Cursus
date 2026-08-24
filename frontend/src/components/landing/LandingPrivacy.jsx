import React from 'react';
import { CheckCircle2, UserCog, Lock } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';

const ITEMS = [
  { icon: CheckCircle2, key: 'trustCompactItem1' },
  { icon: UserCog, key: 'trustCompactItem2' },
  { icon: Lock, key: 'trustCompactItem3' }
];

export default function LandingPrivacy() {
  const { t } = useLanguage();

  return (
    <section id="privacy" className="py-14 lg:py-16 px-6 lg:px-10 border-y border-landing-border bg-landing-surface-muted relative z-10">
      <LandingReveal className="max-w-[1000px] mx-auto grid sm:grid-cols-3 gap-6 sm:gap-10">
        {ITEMS.map(({ icon: Icon, key }) => (
          <div key={key} className="flex items-start gap-3">
            <Icon size={18} className="text-landing-text-muted shrink-0 mt-0.5" />
            <p className="text-sm font-medium text-landing-text-secondary leading-relaxed">
              {t(`landing.${key}`)}
            </p>
          </div>
        ))}
      </LandingReveal>
    </section>
  );
}
