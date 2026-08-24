import React, { useState } from 'react';
import { AlertTriangle, ArrowRight, ShieldCheck, TrendingDown, Check } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';

export default function LandingLecturerHITL() {
  const { t } = useLanguage();
  const tm = (key) => t(`landing.trustMock.${key}`);
  const [intervened, setIntervened] = useState(false);

  return (
    <section id="for-instructors" className="py-20 lg:py-28 px-6 lg:px-10 bg-landing-bg relative z-10">
      <div className="max-w-[1280px] mx-auto">
        <LandingReveal className="max-w-2xl mb-12 lg:mb-14">
          <span className="text-xs font-medium text-landing-text-muted mb-3 block">
            {t('landing.lecturerLabel')}
          </span>
          <h2 className="landing-section-heading text-2xl md:text-4xl font-display text-landing-text mb-4">
            {t('landing.lecturerTitle')}
          </h2>
          <p className="text-landing-text-secondary text-base md:text-lg leading-relaxed">
            {t('landing.lecturerDesc')}
          </p>
        </LandingReveal>

        <LandingReveal className="flex flex-col lg:flex-row items-stretch gap-4 lg:gap-3 max-w-4xl">
          {/* Left: the learning signal */}
          <div className="flex-1 rounded-xl border border-landing-border bg-landing-surface p-5">
            <div className="text-[11px] font-medium text-landing-text-muted uppercase tracking-wide mb-4">
              {tm('studentId')}
            </div>
            <div className="space-y-2.5 mb-4">
              <div className="flex justify-between items-center text-sm">
                <span className="text-landing-text-secondary">{tm('missedCheckins')}</span>
                <span className="font-semibold text-landing-text">{tm('missedCheckinsValue')}</span>
              </div>
              <div className="flex justify-between items-center text-sm">
                <span className="text-landing-text-secondary">{tm('assignment2')}</span>
                <span className="font-semibold text-landing-danger">{tm('notStarted')}</span>
              </div>
              <div className="flex items-center gap-1.5 text-sm text-landing-danger">
                <TrendingDown size={14} />
                {t('landing.lecturerCompletionTrend')}
              </div>
            </div>
            <p className="text-xs text-landing-text-muted leading-relaxed pt-3 border-t border-landing-border">
              {t('landing.lecturerSignalReason')}
            </p>
          </div>

          {/* Connector */}
          <div className="flex lg:flex-col items-center justify-center shrink-0 py-2 lg:py-0 lg:px-2">
            <ArrowRight size={18} className="text-landing-text-muted rotate-90 lg:rotate-0" />
          </div>

          {/* Right: lecturer review */}
          <div className="flex-1 rounded-xl border border-landing-border bg-landing-surface p-5">
            <div className="flex items-center justify-between mb-4">
              <span className="text-[11px] font-medium text-landing-text-muted uppercase tracking-wide">
                {tm('instructorDashboard')}
              </span>
              <span className="flex items-center gap-1.5 text-[11px] font-semibold text-landing-warning bg-landing-warning-soft px-2 py-1 rounded-md">
                <AlertTriangle size={12} /> {tm('needsReview')}
              </span>
            </div>
            <p className="text-sm text-landing-text-secondary leading-relaxed mb-4">
              {tm('highRisk')}
            </p>
            <button
              onClick={() => setIntervened(true)}
              disabled={intervened}
              className={`w-full py-2.5 border text-sm font-semibold rounded-lg transition-colors flex items-center justify-center gap-2 ${
                intervened
                  ? 'bg-landing-success-soft border-landing-success/30 text-landing-success cursor-default'
                  : 'bg-landing-surface-elevated border-landing-border hover:border-landing-border-hover text-landing-text'
              }`}
            >
              {intervened ? <Check size={14} /> : <ShieldCheck size={14} />}
              {intervened ? t('landing.lecturerIntervened') : tm('reviewIntervene')}
            </button>
          </div>
        </LandingReveal>

        <LandingReveal className="max-w-4xl mt-6 text-sm font-medium text-landing-text-secondary flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-landing-text-muted shrink-0" />
          {t('landing.lecturerStatement')}
        </LandingReveal>
      </div>
    </section>
  );
}
