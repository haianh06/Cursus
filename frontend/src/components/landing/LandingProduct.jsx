import React, { useRef, useState } from 'react';
import { CalendarClock, MessageSquareQuote, RotateCcw, Users, ShieldCheck, Clock, FileText, Sparkles, AlertCircle } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import LandingReveal from './LandingReveal';
const CAPABILITIES = [
  { key: 'productCap1', icon: CalendarClock },
  { key: 'productCap2', icon: MessageSquareQuote },
  { key: 'productCap3', icon: RotateCcw },
  { key: 'productCap4', icon: Users },
  { key: 'productCap5', icon: ShieldCheck }
];

const MockupPlan = ({ lang }) => (
  <div className="flex flex-col gap-3.5">
    <div className="flex items-center justify-between mb-1.5">
      <span className="text-[10px] font-bold uppercase tracking-widest text-landing-accent">{lang === 'vi' ? 'Tuần 3 • 15/09 - 21/09' : 'Week 3 • Sep 15 - 21'}</span>
      <span className="text-[9px] font-mono font-medium bg-landing-surface-elevated border border-landing-border px-2 py-0.5 rounded text-landing-text-muted uppercase tracking-wider">SSA101</span>
    </div>
    <div className="p-3.5 rounded-xl border border-landing-border bg-landing-surface shadow-sm relative overflow-hidden group">
      <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-landing-accent rounded-l-xl"></div>
      <div className="flex items-start gap-3.5 pl-2">
        <div className="mt-0.5 shrink-0 w-3.5 h-3.5 rounded-full border-[1.5px] border-landing-accent flex items-center justify-center">
          <div className="w-1.5 h-1.5 rounded-full bg-landing-accent"></div>
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-landing-text truncate">{lang === 'vi' ? 'Đọc Syllabus & Rubric' : 'Read the syllabus & rubric'}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-landing-text-muted"><Clock size={11}/> 45 min</span>
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-landing-text-muted"><FileText size={11}/> Syllabus_SSA101.pdf</span>
          </div>
        </div>
      </div>
    </div>
    <div className="p-3.5 rounded-xl border border-landing-border border-dashed bg-transparent opacity-90">
      <div className="flex items-start gap-3.5">
        <div className="mt-0.5 shrink-0 w-3.5 h-3.5 rounded-full border-[1.5px] border-landing-border flex items-center justify-center"></div>
        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-medium text-landing-text-secondary truncate">{lang === 'vi' ? 'Lên ý tưởng Functional Req.' : 'Draft functional requirements'}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-landing-text-muted"><Clock size={11}/> 1h 20m</span>
          </div>
        </div>
      </div>
    </div>
  </div>
);

const MockupQA = ({ lang }) => (
  <div className="flex flex-col gap-4">
    <div className="flex items-end gap-2.5 self-end max-w-[85%]">
      <div className="px-4 py-3 bg-landing-surface-elevated rounded-2xl rounded-tr-sm border border-landing-border shadow-sm">
        <p className="text-[13px] text-landing-text">{lang === 'vi' ? 'Trọng số điểm của bài Assignment 1 là bao nhiêu vậy?' : 'How much is Assignment 1 worth?'}</p>
      </div>
      <div className="w-6 h-6 rounded-full bg-landing-surface-elevated border border-landing-border shrink-0 flex items-center justify-center text-[9px] font-bold text-landing-text-muted uppercase">{lang === 'vi' ? 'SV' : 'ST'}</div>
    </div>

    <div className="flex items-start gap-2.5 max-w-[95%]">
      <div className="w-6 h-6 rounded-full bg-landing-accent/10 shrink-0 flex items-center justify-center text-landing-accent mt-1 border border-landing-accent/20">
        <Sparkles size={11} />
      </div>
      <div className="flex flex-col gap-2.5">
        <div className="px-4 py-3.5 bg-landing-accent-soft/40 rounded-2xl rounded-tl-sm border border-landing-accent/20 shadow-sm">
          <p className="text-[13px] text-landing-text leading-relaxed">
            {lang === 'vi' ? (
              <>Theo đề cương môn học, bài <strong>Assignment 1</strong> chiếm <strong>15%</strong> tổng điểm. Bạn cần nộp trên hệ thống trước 23:59 Chủ Nhật tuần này.</>
            ) : (
              <>Per the syllabus, <strong>Assignment 1</strong> is worth <strong>15%</strong> of your total grade. You need to submit it on the system before 11:59 PM this Sunday.</>
            )}
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-landing-border bg-landing-surface shadow-sm hover:border-landing-accent/50 transition-colors w-fit group">
          <FileText size={13} className="text-landing-accent" />
          <span className="text-[11px] font-medium text-landing-text-secondary group-hover:text-landing-text transition-colors">{lang === 'vi' ? 'Syllabus SSA101 — Tr. 3' : 'Syllabus SSA101 — p. 3'}</span>
        </div>
      </div>
    </div>
  </div>
);

const MockupReflect = ({ lang }) => (
  <div className="flex flex-col gap-4">
    <div className="grid grid-cols-3 gap-3">
      <div className="p-3.5 rounded-xl border border-landing-border bg-landing-surface-elevated flex flex-col items-center justify-center text-center shadow-sm">
        <span className="text-[9px] font-bold text-landing-text-muted uppercase tracking-widest mb-1.5">{lang === 'vi' ? 'Kế hoạch' : 'Planned'}</span>
        <span className="text-xl font-mono font-bold text-landing-text">{lang === 'vi' ? '7h00' : '7h00m'}</span>
      </div>
      <div className="p-3.5 rounded-xl border border-landing-border bg-landing-surface-elevated flex flex-col items-center justify-center text-center shadow-sm">
        <span className="text-[9px] font-bold text-landing-text-muted uppercase tracking-widest mb-1.5">{lang === 'vi' ? 'Thực tế' : 'Actual'}</span>
        <span className="text-xl font-mono font-bold text-landing-text">{lang === 'vi' ? '6h30' : '6h30m'}</span>
      </div>
      <div className="p-3.5 rounded-xl border border-landing-accent/30 bg-landing-accent-soft flex flex-col items-center justify-center text-center shadow-sm relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-landing-accent/10 to-transparent pointer-events-none"></div>
        <span className="text-[9px] font-bold text-landing-accent-hover uppercase tracking-widest mb-1.5 relative z-10">{lang === 'vi' ? 'Hiệu suất' : 'Efficiency'}</span>
        <span className="text-xl font-mono font-bold text-landing-accent relative z-10">93%</span>
      </div>
    </div>
    <div className="p-4 rounded-xl border border-landing-border bg-landing-surface shadow-sm">
      <p className="text-[11px] font-bold text-landing-text mb-2.5 uppercase tracking-wide">{lang === 'vi' ? 'Điều gì giúp bạn hoàn thành tốt tuần này?' : 'What helped you get through this week?'}</p>
      <div className="w-full p-3.5 rounded-lg border border-landing-border-hover bg-landing-surface-elevated/40 text-[13px] text-landing-text-secondary leading-relaxed shadow-inner">
        {lang === 'vi'
          ? 'Việc chia nhỏ bài tập lớn thành 3 task nhỏ giúp mình không bị ngợp. Tuy nhiên hôm thứ 5 mình có hơi mất tập trung...'
          : 'Breaking the big assignment into 3 smaller tasks kept me from feeling overwhelmed. Though I did lose focus a bit on Thursday...'}
      </div>
    </div>
  </div>
);

const MockupInstructor = ({ lang }) => (
  <div className="flex flex-col gap-3">
    <div className="flex items-center justify-between mb-2">
      <span className="text-[10px] font-bold text-landing-text uppercase tracking-widest">{lang === 'vi' ? 'Cảnh báo Sinh viên' : 'Student Alerts'}</span>
      <span className="flex items-center gap-1.5 text-[9px] font-bold text-red-600 bg-red-500/10 px-2 py-1 rounded-md border border-red-500/20 tracking-wider uppercase"><AlertCircle size={10}/> 3 High Risk</span>
    </div>

    <div className="p-4 rounded-xl border-l-[3px] border-l-red-500 border-y border-r border-landing-border bg-landing-surface shadow-sm flex items-center justify-between gap-4">
      <div className="flex items-center gap-3.5">
        <div className="w-9 h-9 rounded-full bg-landing-surface-elevated border border-landing-border flex items-center justify-center shrink-0 font-bold text-landing-text text-[11px] shadow-sm tracking-wider">NM</div>
        <div>
          <p className="text-[13px] font-bold text-landing-text">Nguyễn Minh</p>
          <p className="text-[11px] font-medium text-landing-text-muted mt-0.5">SE160012 • <span className="text-red-500/90 font-semibold">{lang === 'vi' ? 'Vắng 2 tuần liên tiếp' : 'Absent 2 weeks in a row'}</span></p>
        </div>
      </div>
      <button className="px-3 py-1.5 rounded-md bg-landing-surface-elevated border border-landing-border text-[11px] font-bold text-landing-text hover:bg-landing-border-hover transition-colors shadow-sm">
        {lang === 'vi' ? 'Can thiệp' : 'Intervene'}
      </button>
    </div>

    <div className="p-4 rounded-xl border-l-[3px] border-l-yellow-500 border-y border-r border-landing-border bg-landing-surface shadow-sm flex items-center justify-between gap-4 opacity-70">
      <div className="flex items-center gap-3.5">
        <div className="w-9 h-9 rounded-full bg-landing-surface-elevated border border-landing-border flex items-center justify-center shrink-0 font-bold text-landing-text text-[11px] shadow-sm tracking-wider">TA</div>
        <div>
          <p className="text-[13px] font-bold text-landing-text">Trần An</p>
          <p className="text-[11px] font-medium text-landing-text-muted mt-0.5">SE160105 • <span className="text-yellow-600 font-semibold">{lang === 'vi' ? 'Trễ 1 deadline' : '1 late deadline'}</span></p>
        </div>
      </div>
    </div>
  </div>
);

const MockupGuardrail = ({ lang }) => (
  <div className="flex flex-col gap-4">
    <div className="flex items-end gap-2.5 self-end max-w-[85%]">
      <div className="px-4 py-3 bg-landing-surface-elevated rounded-2xl rounded-tr-sm border border-landing-border shadow-sm">
        <p className="text-[13px] text-landing-text">{lang === 'vi' ? 'Viết giùm mình đoạn code Python để crawl dữ liệu bài Lab 3 với.' : 'Can you write the Python code to crawl the Lab 3 data for me?'}</p>
      </div>
      <div className="w-6 h-6 rounded-full bg-landing-surface-elevated border border-landing-border shrink-0 flex items-center justify-center text-[9px] font-bold text-landing-text-muted uppercase">{lang === 'vi' ? 'SV' : 'ST'}</div>
    </div>

    <div className="flex items-start gap-2.5 max-w-[95%]">
      <div className="w-6 h-6 rounded-full bg-orange-500/10 shrink-0 flex items-center justify-center text-orange-500 mt-1 border border-orange-500/20">
        <ShieldCheck size={11} />
      </div>
      <div className="flex flex-col gap-2.5">
        <div className="px-4 py-3.5 bg-orange-500/5 rounded-2xl rounded-tl-sm border border-orange-500/20 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-[3px] bg-orange-500/40"></div>
          <p className="text-[13px] text-landing-text leading-relaxed">
            {lang === 'vi' ? (
              <>
                Xin lỗi, mình không thể viết code hoàn chỉnh thay bạn (theo <span className="font-medium text-orange-600/90 underline decoration-orange-500/30 underline-offset-2 cursor-help">chính sách học thuật</span>).
                <br/><br/>
                Tuy nhiên, để crawl dữ liệu, bạn có thể bắt đầu bằng việc import <code>requests</code> và <code>BeautifulSoup</code>. Bạn đã thử gọi URL chưa?
              </>
            ) : (
              <>
                Sorry, I can't write the complete code for you (per <span className="font-medium text-orange-600/90 underline decoration-orange-500/30 underline-offset-2 cursor-help">academic policy</span>).
                <br/><br/>
                That said, to crawl the data you can start by importing <code>requests</code> and <code>BeautifulSoup</code>. Have you tried calling the URL yet?
              </>
            )}
          </p>
        </div>
      </div>
    </div>
  </div>
);

function CapabilityCanvas({ lang, capKey }) {
  switch (capKey) {
    case 'productCap1': return <MockupPlan lang={lang} />;
    case 'productCap2': return <MockupQA lang={lang} />;
    case 'productCap3': return <MockupReflect lang={lang} />;
    case 'productCap4': return <MockupInstructor lang={lang} />;
    case 'productCap5': return <MockupGuardrail lang={lang} />;
    default: return null;
  }
}

export default function LandingProduct() {
  const { t, lang } = useLanguage();
  const [activeIndex, setActiveIndex] = useState(0);
  const active = CAPABILITIES[activeIndex];
  const tabRefs = useRef([]);

  // Deliberately manual, not scroll- or clock-linked. Two things were tried
  // and both failed for this content: a timed auto-cycle (NN/G: ~1%
  // engagement past slide 1, "moving target" for anyone still reading —
  // removed), then scroll-linked auto-select copied from the how-it-works
  // section (technically sound, but 5 short one-line capabilities don't
  // carry enough content to fill the scroll runway that mechanism needs —
  // it just produced dead empty gaps between tabs with no timeline line to
  // explain them, i.e. looked broken, not premium). This is parallel
  // content (5 capabilities that coexist, not a sequence) — full manual
  // control via click/keyboard is the correct fit, not a fallback.
  const focusAndSelect = (index) => {
    setActiveIndex(index);
    tabRefs.current[index]?.focus();
  };

  const handleTabKeyDown = (e, index) => {
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      focusAndSelect((index + 1) % CAPABILITIES.length);
    } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      focusAndSelect((index - 1 + CAPABILITIES.length) % CAPABILITIES.length);
    }
  };

  return (
    <section id="product" className="py-20 lg:py-28 px-6 lg:px-10 bg-landing-surface-muted relative z-10">
      <LandingReveal className="max-w-[1200px] mx-auto">
        <div className="max-w-[720px] mb-12 lg:mb-16">
          <p className="text-xs font-semibold uppercase tracking-wide text-landing-text-muted mb-3">
            {t('landing.productKicker')}
          </p>
          <h2 className="landing-section-heading text-landing-text font-display text-[clamp(2rem,3.4vw,2.75rem)] mb-4">
            {t('landing.productTitle')}
          </h2>
          <p className="text-landing-text-secondary text-lg leading-relaxed">
            {t('landing.productDesc')}
          </p>
        </div>

        {/* Desktop: vertical capability selector + product canvas */}
        <div className="hidden lg:grid grid-cols-[minmax(0,0.32fr)_minmax(0,0.68fr)] gap-10">
          <div role="tablist" aria-orientation="vertical" aria-label={t('landing.productKicker')} className="flex flex-col gap-1.5">
            {CAPABILITIES.map(({ key, icon: Icon }, index) => {
              const isActive = index === activeIndex;
              return (
                <button
                  key={key}
                  ref={(el) => { tabRefs.current[index] = el; }}
                  role="tab"
                  id={`product-tab-${key}`}
                  aria-selected={isActive}
                  aria-controls="product-canvas-panel"
                  tabIndex={isActive ? 0 : -1}
                  onClick={() => setActiveIndex(index)}
                  onKeyDown={(e) => handleTabKeyDown(e, index)}
                  className={`text-left px-4 py-3.5 rounded-xl border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent flex items-start gap-3 ${
                    isActive
                      ? 'border-landing-border-hover bg-landing-surface-elevated shadow-landing-sm'
                      : 'border-transparent hover:bg-landing-surface-elevated/60'
                  }`}
                >
                  <Icon size={18} className={`shrink-0 mt-0.5 ${isActive ? 'text-landing-accent' : 'text-landing-text-muted'}`} />
                  <span className="min-w-0">
                    <span className={`block text-sm ${isActive ? 'font-semibold text-landing-text' : 'font-medium text-landing-text-secondary'}`}>
                      {t(`landing.${key}Name`)}
                    </span>
                    <span className="block text-xs text-landing-text-muted mt-0.5 leading-snug">
                      {t(`landing.${key}Blurb`)}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>

          <div
            id="product-canvas-panel"
            role="tabpanel"
            aria-labelledby={`product-tab-${active.key}`}
            className="rounded-2xl border border-landing-border bg-landing-surface shadow-landing-md overflow-hidden"
          >
            {/* Same "app window" chrome as the how-it-works mockup — this
                section's whole point is "one system", so the two panels
                should read as the same product, not two different design
                languages side by side on the same page. */}
            <div className="h-10 border-b border-landing-border bg-landing-surface-elevated flex items-center px-4 gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-landing-border-hover" />
              <span className="w-2.5 h-2.5 rounded-full bg-landing-border-hover" />
              <span className="w-2.5 h-2.5 rounded-full bg-landing-border-hover" />
              <span className="ml-2 text-xs font-mono text-landing-text-muted truncate">app.cursus.edu.vn</span>
            </div>
            {/* key={active.key} retriggers animate-fade-up on every tab
                switch — without it the panel used to swap content instantly
                with zero motion, which is what read as "flat" next to the
                how-it-works section's animated preview. */}
            <div key={active.key} className="p-6 lg:p-8 animate-fade-up" style={{ animationDuration: '250ms' }}>
              <div className="flex items-center gap-3 mb-5">
                <div className="w-10 h-10 rounded-xl bg-landing-accent-soft flex items-center justify-center shrink-0">
                  <active.icon size={19} className="text-landing-accent" />
                </div>
                <h3 className="text-base font-semibold text-landing-text">{t(`landing.${active.key}Name`)}</h3>
              </div>
              <CapabilityCanvas lang={lang} capKey={active.key} />
            </div>
          </div>
        </div>

        {/* Mobile/tablet: stacked native disclosure panels — accessible by
            default (no custom JS needed for open/close/keyboard). */}
        <div className="lg:hidden flex flex-col gap-3">
          {CAPABILITIES.map(({ key, icon: Icon }, index) => (
            <details key={key} className="group rounded-xl border border-landing-border bg-landing-surface-elevated overflow-hidden" open={index === 0}>
              <summary className="cursor-pointer list-none px-4 py-3.5 flex items-center gap-3 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent">
                <Icon size={18} className="shrink-0 text-landing-text-muted group-open:text-landing-accent" />
                <span className="text-sm font-semibold text-landing-text">{t(`landing.${key}Name`)}</span>
              </summary>
              <div className="px-4 pb-4">
                <p className="text-xs text-landing-text-muted mb-3">{t(`landing.${key}Blurb`)}</p>
                <CapabilityCanvas lang={lang} capKey={key} />
              </div>
            </details>
          ))}
        </div>
      </LandingReveal>
    </section>
  );
}
