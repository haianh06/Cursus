import React, { useEffect, useRef, useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import { BookOpen, ListChecks, PlayCircle, MessageSquareQuote, RotateCcw, CalendarClock, Check, FileText, Sparkles, User, UserCheck } from 'lucide-react';
import LandingReveal from './LandingReveal';

const STEPS = [
  {
    key: 'step1', icon: BookOpen, titleKey: 'workflowStep1Title', descKey: 'workflowStep1Desc'
  },
  {
    key: 'step2', icon: ListChecks, titleKey: 'workflowStep2Title', descKey: 'workflowStep2Desc'
  },
  {
    key: 'step3', icon: PlayCircle, titleKey: 'workflowStep3Title', descKey: 'workflowStep3Desc'
  },
  {
    key: 'step4', icon: MessageSquareQuote, titleKey: 'workflowStep4Title', descKey: 'workflowStep4Desc'
  },
  {
    key: 'step5', icon: RotateCcw, titleKey: 'workflowStep5Title', descKey: 'workflowStep5Desc'
  },
  {
    key: 'step6', icon: CalendarClock, titleKey: 'workflowStep6Title', descKey: 'workflowStep6Desc'
  }
];

const MockupStep1 = ({ lang }) => (
  <div className="flex flex-col gap-3.5 w-full max-w-sm mx-auto lg:max-w-none">
    <div className="p-4 rounded-xl border border-landing-border bg-landing-surface shadow-sm flex items-center gap-4">
      <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0 border border-blue-500/20">
        <FileText size={20} className="text-blue-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-landing-text truncate">SSA101_Syllabus_FA26.pdf</p>
        <div className="flex items-center justify-between mt-2.5 mb-1.5">
          <span className="text-[10px] font-medium text-landing-text-muted">{lang === 'vi' ? 'Đang phân tích cấu trúc...' : 'Parsing structure...'}</span>
          <span className="text-[10px] font-bold text-blue-500">85%</span>
        </div>
        <div className="w-full bg-landing-border h-1.5 rounded-full overflow-hidden">
          <div className="w-[85%] bg-blue-500 h-full rounded-full relative">
            <div className="absolute inset-0 bg-white/20 animate-pulse"></div>
          </div>
        </div>
      </div>
    </div>
    <div className="flex items-center gap-2.5 mt-0.5 flex-wrap">
      <span className="px-3 py-1.5 rounded-lg bg-landing-accent-soft border border-landing-accent/20 text-[11px] font-semibold text-landing-accent flex items-center gap-1.5 shadow-sm">
        <Sparkles size={13}/> {lang === 'vi' ? '3 Deadlines' : '3 deadlines'}
      </span>
      <span className="px-3 py-1.5 rounded-lg bg-landing-surface-elevated border border-landing-border text-[11px] font-medium text-landing-text-secondary shadow-sm">
        Rubric
      </span>
    </div>
  </div>
);

const MockupStep2 = ({ lang }) => (
  <div className="flex flex-col gap-3 w-full max-w-sm mx-auto lg:max-w-none">
    <div className="flex items-center justify-between px-1 mb-1.5">
      <span className="text-[10px] font-bold text-landing-text-muted uppercase tracking-wider">{lang === 'vi' ? 'Kế hoạch Tuần 3' : 'Week 3 Plan'}</span>
      <span className="text-[11px] font-medium text-landing-text-muted bg-landing-surface-elevated px-2.5 py-0.5 rounded-full border border-landing-border">{lang === 'vi' ? '7h / 12h rảnh' : '7h / 12h free'}</span>
    </div>
    <div className="w-full flex gap-1 h-2 rounded-full overflow-hidden bg-landing-surface-elevated border border-landing-border mb-2.5">
      <div className="w-[20%] bg-landing-accent"></div>
      <div className="w-[25%] bg-landing-accent"></div>
      <div className="w-[15%] bg-landing-accent"></div>
      <div className="w-[40%] bg-transparent"></div>
    </div>
    <div className="p-3.5 rounded-xl border border-landing-border bg-landing-surface shadow-sm">
      <div className="flex items-center gap-3">
        <div className="w-4 h-4 rounded-full border-[1.5px] border-landing-border-hover flex items-center justify-center shrink-0"></div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-landing-text truncate">{lang === 'vi' ? 'Đọc rubric bài tập' : 'Read the grading rubric'}</p>
        </div>
        <span className="text-[11px] font-mono text-landing-text-muted bg-landing-surface-elevated px-1.5 py-0.5 rounded">45m</span>
      </div>
    </div>
    <div className="p-3.5 rounded-xl border border-landing-border bg-landing-surface shadow-sm opacity-60">
      <div className="flex items-center gap-3">
        <div className="w-4 h-4 rounded-full border-[1.5px] border-landing-border-hover flex items-center justify-center shrink-0"></div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-landing-text truncate">{lang === 'vi' ? 'Tìm hiểu Functional Req.' : 'Review functional requirements'}</p>
        </div>
        <span className="text-[11px] font-mono text-landing-text-muted bg-landing-surface-elevated px-1.5 py-0.5 rounded">1h20m</span>
      </div>
    </div>
  </div>
);

const MockupStep3 = ({ lang }) => (
  <div className="flex flex-col gap-3 w-full max-w-sm mx-auto lg:max-w-none">
    <div className="p-3.5 rounded-xl border border-landing-border bg-landing-surface-elevated/50">
      <div className="flex items-center gap-3">
        <div className="w-4 h-4 rounded-full bg-landing-accent/20 flex items-center justify-center shrink-0">
          <Check size={10} className="text-landing-accent" strokeWidth={3} />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-landing-text-muted truncate line-through">{lang === 'vi' ? 'Đọc rubric bài tập' : 'Read the grading rubric'}</p>
        </div>
      </div>
    </div>
    <div className="p-4 rounded-xl border border-landing-accent/30 bg-landing-accent-soft shadow-sm relative overflow-hidden">
      <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-landing-accent rounded-l-xl"></div>
      <div className="flex items-center gap-3.5 pl-1">
        <div className="w-5 h-5 rounded-full border-2 border-landing-accent/30 flex items-center justify-center shrink-0 relative">
          <div className="absolute inset-[-2px] rounded-full border-2 border-landing-accent/20 border-t-landing-accent animate-spin"></div>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold text-landing-text truncate">{lang === 'vi' ? 'Tìm hiểu Functional Req.' : 'Review functional requirements'}</p>
          <p className="text-[11px] text-landing-accent font-medium mt-1">{lang === 'vi' ? 'Đang thực hiện • 1h20m' : 'In progress • 1h20m'}</p>
        </div>
      </div>
    </div>
  </div>
);

const MockupStep4 = ({ lang }) => (
  <div className="flex flex-col gap-4 w-full max-w-sm mx-auto lg:max-w-none">
    <div className="flex items-end gap-2.5 self-end max-w-[90%]">
      <div className="px-4 py-3 bg-landing-surface-elevated rounded-2xl rounded-tr-sm border border-landing-border shadow-sm">
        <p className="text-[13px] text-landing-text">{lang === 'vi' ? 'Rubric yêu cầu vẽ mấy sơ đồ vậy?' : 'How many diagrams does the rubric ask for?'}</p>
      </div>
      <div className="w-6 h-6 rounded-full bg-landing-surface border border-landing-border shrink-0 flex items-center justify-center text-[9px] font-bold text-landing-text-muted uppercase">{lang === 'vi' ? 'SV' : 'ST'}</div>
    </div>
    <div className="flex items-start gap-2.5 max-w-[95%]">
      <div className="w-6 h-6 rounded-full bg-landing-accent/10 shrink-0 flex items-center justify-center text-landing-accent mt-1 border border-landing-accent/20">
        <Sparkles size={11} />
      </div>
      <div className="flex flex-col gap-2.5">
        <div className="px-4 py-3 bg-landing-accent-soft/50 rounded-2xl rounded-tl-sm border border-landing-accent/20 shadow-sm">
          <p className="text-[13px] text-landing-text leading-relaxed">
            {lang === 'vi' ? (
              <>Bạn cần vẽ 3 sơ đồ: <strong>Use Case</strong>, <strong>Activity</strong> và <strong>Class Diagram</strong>.</>
            ) : (
              <>You need 3 diagrams: <strong>Use Case</strong>, <strong>Activity</strong>, and <strong>Class Diagram</strong>.</>
            )}
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-landing-border bg-landing-surface shadow-sm w-fit group cursor-pointer hover:border-landing-accent/40 transition-colors">
          <FileText size={13} className="text-landing-accent" />
          <span className="text-[11px] font-medium text-landing-text-secondary group-hover:text-landing-text transition-colors">Syllabus SSA101 — Overview</span>
        </div>
      </div>
    </div>
  </div>
);

const MockupStep5 = ({ lang }) => (
  <div className="flex flex-col gap-4 w-full max-w-sm mx-auto lg:max-w-none">
    <div className="p-5 rounded-xl border border-landing-border bg-landing-surface shadow-md relative overflow-hidden">
      <div className="absolute top-0 right-0 w-32 h-32 bg-landing-accent/10 rounded-full blur-2xl -mr-10 -mt-10 pointer-events-none"></div>
      <div className="flex items-center justify-between mb-5 relative z-10">
        <p className="text-[11px] font-bold text-landing-text uppercase tracking-widest">{lang === 'vi' ? 'Tổng kết Tuần 3' : 'Week 3 Summary'}</p>
        <span className="px-2.5 py-1 rounded-md bg-green-500/10 text-green-600 text-[9px] font-bold uppercase tracking-wider border border-green-500/20 shadow-sm">{lang === 'vi' ? 'Hoàn thành' : 'Completed'}</span>
      </div>
      <div className="grid grid-cols-3 gap-3 relative z-10">
        <div className="bg-landing-surface-elevated p-3 rounded-xl border border-landing-border text-center">
          <p className="text-[9px] text-landing-text-muted uppercase tracking-widest mb-1.5 font-semibold">{lang === 'vi' ? 'Kế hoạch' : 'Planned'}</p>
          <p className="text-lg font-mono font-bold text-landing-text">{lang === 'vi' ? '7h00' : '7h00m'}</p>
        </div>
        <div className="bg-landing-surface-elevated p-3 rounded-xl border border-landing-border text-center">
          <p className="text-[9px] text-landing-text-muted uppercase tracking-widest mb-1.5 font-semibold">{lang === 'vi' ? 'Thực tế' : 'Actual'}</p>
          <p className="text-lg font-mono font-bold text-landing-text">{lang === 'vi' ? '6h30' : '6h30m'}</p>
        </div>
        <div className="bg-landing-accent-soft p-3 rounded-xl border border-landing-accent/30 text-center shadow-sm relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-landing-accent/10 to-transparent pointer-events-none"></div>
          <p className="text-[9px] text-landing-accent-hover uppercase tracking-widest mb-1.5 font-bold relative z-10">{lang === 'vi' ? 'Hiệu suất' : 'Efficiency'}</p>
          <p className="text-lg font-mono font-bold text-landing-accent relative z-10">93%</p>
        </div>
      </div>
    </div>
  </div>
);

const MockupStep6 = ({ lang }) => (
  <div className="flex flex-col gap-4 w-full max-w-sm mx-auto lg:max-w-none">
    <div className="grid grid-cols-2 gap-4 h-full">
      {/* Student side */}
      <div className="flex flex-col gap-2.5 h-full">
        <div className="flex items-center gap-1.5 mb-1.5">
          <User size={12} className="text-landing-text-muted"/>
          <span className="text-[9px] font-bold uppercase text-landing-text-muted tracking-widest">{lang === 'vi' ? 'Sinh viên' : 'Student'}</span>
        </div>
        <div className="p-4 rounded-xl border border-landing-accent/30 bg-landing-accent-soft/80 shadow-sm h-full flex flex-col justify-center">
          <p className="text-[11px] font-bold text-landing-text mb-2 uppercase tracking-wide">{lang === 'vi' ? 'Kế hoạch Tuần 4' : 'Week 4 Plan'}</p>
          <p className="text-[12px] text-landing-text-secondary leading-relaxed">{lang === 'vi' ? 'Sẵn sàng với 8 task mới dựa trên dữ liệu tuần trước.' : 'Ready with 8 new tasks based on last week’s data.'}</p>
        </div>
      </div>
      {/* Instructor side */}
      <div className="flex flex-col gap-2.5 h-full">
        <div className="flex items-center gap-1.5 mb-1.5">
          <UserCheck size={12} className="text-landing-text-muted"/>
          <span className="text-[9px] font-bold uppercase text-landing-text-muted tracking-widest">{lang === 'vi' ? 'Giảng viên' : 'Instructor'}</span>
        </div>
        <div className="p-4 rounded-xl border border-landing-border bg-landing-surface shadow-sm relative overflow-hidden h-full flex flex-col justify-center">
          <div className="absolute top-0 right-0 p-3">
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
            </span>
          </div>
          <p className="text-[11px] font-bold text-landing-text mb-2 uppercase tracking-wide">Dashboard</p>
          <p className="text-[12px] text-landing-text-secondary leading-relaxed"><span className="font-medium text-landing-text">Nguyễn Minh:</span> {lang === 'vi' ? 'Đã trở lại nhịp học ổn định (93%).' : 'Back to a steady study rhythm (93%).'}</p>
        </div>
      </div>
    </div>
  </div>
);

const WorkflowMockup = ({ stepKey, lang }) => {
  switch (stepKey) {
    case 'step1': return <MockupStep1 lang={lang} />;
    case 'step2': return <MockupStep2 lang={lang} />;
    case 'step3': return <MockupStep3 lang={lang} />;
    case 'step4': return <MockupStep4 lang={lang} />;
    case 'step5': return <MockupStep5 lang={lang} />;
    case 'step6': return <MockupStep6 lang={lang} />;
    default: return null;
  }
};

export default function LandingWorkflow() {
  const { t, lang } = useLanguage();
  const [activeIndex, setActiveIndex] = useState(0);
  const stepRefs = useRef([]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const idx = stepRefs.current.indexOf(entry.target);
            if (idx !== -1) setActiveIndex(idx);
          }
        });
      },
      { rootMargin: '-40% 0px -40% 0px', threshold: 0 }
    );
    stepRefs.current.forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const active = STEPS[activeIndex];
  const ActiveIcon = active.icon;

  return (
    <section id="how-it-works" className="py-20 lg:py-28 px-6 lg:px-10 bg-landing-bg relative z-10 bg-grid">
      <div className="max-w-[1280px] mx-auto">
        <LandingReveal className="max-w-2xl mb-12 lg:mb-14">
          <span className="inline-flex items-center gap-2 text-xs font-semibold tracking-wide uppercase text-landing-accent-hover mb-3">
            <span className="w-1.5 h-1.5 rounded-full bg-landing-accent" aria-hidden="true" />
            {t('landing.workflowKicker')}
          </span>
          <h2 className="landing-section-heading text-2xl md:text-4xl font-display text-landing-text mb-4">
            {t('landing.workflowTitle')}
          </h2>
          <p className="text-landing-text-secondary text-base md:text-lg leading-relaxed">
            {t('landing.workflowDesc')}
          </p>
        </LandingReveal>

        <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_minmax(0,560px)] lg:gap-16">
          <ol className="lg:order-1 relative list-none m-0 p-0" aria-label={t('landing.workflowTitle')}>
            {/* Track + fill: a static line read as "phẳng" — this now grows
                with activeIndex so the rail visibly fills as the reader
                scrolls, matching the sticky preview's progress dots on the
                right instead of just sitting there as a fixed rule. */}
            <div className="absolute left-[15px] top-1 bottom-1 w-px bg-landing-border hidden sm:block overflow-hidden" aria-hidden="true">
              <div
                className="landing-progress-fill w-full bg-landing-accent transition-[height] duration-500 ease-out"
                style={{ height: `${(activeIndex / Math.max(STEPS.length - 1, 1)) * 100}%` }}
              />
            </div>
            {STEPS.map((step, i) => {
              const Icon = step.icon;
              const isActive = i === activeIndex;
              const isDone = i < activeIndex;
              return (
                <li
                  key={step.key}
                  ref={(el) => { stepRefs.current[i] = el; }}
                  // lg:min-h-[*vh] gives each step enough scroll runway for
                  // the sticky preview opposite it to stay pinned in sync —
                  // without it, the steps list (a few hundred px of short
                  // text blocks) was shorter than the sticky card's own
                  // travel range, so the card detached and scrolled off
                  // partway through, leaving steps 4-6 with a blank right
                  // column. vh scales with viewport, so the runway stays
                  // proportionally sufficient on any screen size. Desktop
                  // (lg) only — mobile has no sticky panel to feed. Kept
                  // moderate (not the first pass's 55vh/38vh) — enough
                  // runway without the text reading as lost in blank space.
                  className="relative flex gap-4 py-6 sm:py-8 first:pt-0 last:pb-0 lg:min-h-[36vh] lg:items-center lg:py-0 lg:last:min-h-[24vh]"
                >
                  <div
                    className={`relative z-10 shrink-0 w-8 h-8 rounded-full border flex items-center justify-center transition-all duration-300 ${
                      isActive
                        ? 'border-landing-accent bg-landing-accent-soft scale-110 shadow-[0_0_0_4px_var(--landing-accent-glow)]'
                        : isDone
                          ? 'border-landing-border-hover bg-landing-surface-muted'
                          : 'border-landing-border bg-landing-surface'
                    }`}
                  >
                    <Icon size={15} aria-hidden="true" className={isActive ? 'text-landing-accent' : isDone ? 'text-landing-text-secondary' : 'text-landing-text-muted'} />
                  </div>
                  {/* De-emphasis for inactive steps is expressed with color
                      tokens, not opacity — axe-core flagged the previous
                      opacity-50 wrapper because it blends every child's
                      text color toward the background, dropping even the
                      near-black heading to ~3.3:1 (fails WCAG AA's 4.5:1).
                      Every token used below already clears 4.5:1 at full
                      opacity, so hierarchy comes from color choice alone.
                      The card padding/border below is identical whether
                      active or not (only border/bg color toggles) — sizing
                      it off `isActive` would grow the box exactly when the
                      IntersectionObserver flips state mid-scroll, shifting
                      every step below it (a layout-shift/CLS regression). */}
                  <div
                    className={`flex-1 transition-colors duration-500 lg:-mx-5 lg:rounded-2xl lg:border lg:px-5 lg:py-4 ${
                      isActive ? 'lg:border-landing-border lg:bg-landing-surface-elevated lg:shadow-landing-sm' : 'lg:border-transparent lg:bg-transparent'
                    }`}
                  >
                    <div className="text-xs font-medium text-landing-text-muted mb-1.5">
                      {i + 1}/{STEPS.length}
                    </div>
                    <h3 className={`text-lg sm:text-xl lg:text-2xl font-semibold mb-1.5 transition-colors duration-300 ${isActive ? 'text-landing-text' : 'text-landing-text-secondary'}`}>
                      {t(`landing.${step.titleKey}`)}
                    </h3>
                    <p className="text-sm sm:text-base lg:text-lg text-landing-text-secondary leading-relaxed max-w-md lg:max-w-lg">
                      {t(`landing.${step.descKey}`)}
                    </p>
                  </div>
                </li>
              );
            })}
          </ol>

          {/* Sticky product surface — falls back to a plain static block on
              mobile (no position:sticky there; STEPS text above already
              reads as six compact stacked scenes without this panel). */}
          <div className="lg:order-2 hidden lg:block">
            <div className="sticky top-[110px]">
              <div className="rounded-2xl border border-landing-border bg-landing-surface shadow-landing-md overflow-hidden">
                <div className="h-10 border-b border-landing-border bg-landing-surface-elevated flex items-center px-4 gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-landing-border-hover" />
                  <span className="w-2.5 h-2.5 rounded-full bg-landing-border-hover" />
                  <span className="w-2.5 h-2.5 rounded-full bg-landing-border-hover" />
                  <span className="ml-2 text-xs font-mono text-landing-text-muted truncate">app.cursus.edu.vn</span>
                </div>
                {/* minHeight (not a fixed height) floors the card so it
                    always reads as a substantial "app window" rather than
                    shrink-wrapping to whichever step has the least content —
                    steps with 1 row vs 2 rows still occupy comparable space. */}
                <div className="p-7 flex flex-col gap-5" style={{ minHeight: 320 }}>
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-xl bg-landing-accent-soft flex items-center justify-center shrink-0">
                      <ActiveIcon size={22} aria-hidden="true" className="text-landing-accent" />
                    </div>
                    <div className="text-base lg:text-lg font-semibold text-landing-text">
                      {t(`landing.${active.titleKey}`)}
                    </div>
                  </div>
                  {/* flex-1 + justify-center: a step with 1 row vs 2 rows
                      used to both start flush under the description, leaving
                      1-row steps with a dead gap above the footer dots (the
                      "why is this so bare" complaint). Centering in the
                      remaining space instead makes every step read as
                      intentionally composed regardless of row count. */}
                  <div key={active.key} className="flex-1 flex flex-col justify-center gap-2.5 animate-fade-up" style={{ animationDuration: '350ms' }}>
                    <WorkflowMockup stepKey={active.key} lang={lang} />
                  </div>

                  {/* Progress dots — redundant with the "i/6" label already
                      read by screen readers in the steps list, so this is
                      purely decorative (aria-hidden): a quick-glance sense
                      of position that also gives the card's remaining
                      space, on steps with only one row, a clear purpose
                      instead of trailing off into blank padding. */}
                  <div className="mt-auto pt-4 border-t border-landing-border flex items-center justify-center gap-1.5" aria-hidden="true">
                    {STEPS.map((s, i) => (
                      <span
                        key={s.key}
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                          i === activeIndex ? 'w-6 bg-landing-accent' : 'w-1.5 bg-landing-border-hover'
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
