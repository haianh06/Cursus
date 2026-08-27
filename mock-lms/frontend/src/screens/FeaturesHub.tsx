import { useEffect, useState } from 'react';
import { Layers, GitFork, Search, BookOpen, ShieldCheck, UserCheck, GraduationCap, ArrowRight, ClipboardList } from 'lucide-react';
import type { Identity, SyllabusSummary } from '../types';
import { useLanguage } from '../context/LanguageContext';
import { listSyllabi } from '../lib/api';

// The hero videos/posters live under public/media/hero/ with fixed filenames
// (not Vite-hashed like the JS/CSS bundle), so browsers cache them
// aggressively by URL. Bump this whenever the underlying media files change
// so viewers actually see the new footage instead of a stale cached copy.
const HERO_MEDIA_VERSION = '2';

const ROLE_ICON: Record<Identity['role'], typeof GraduationCap> = {
  INSTRUCTOR: UserCheck,
  ADMIN: ShieldCheck,
  STUDENT: GraduationCap,
};

export function FeaturesHub({ identity, onNavigate }: { identity: Identity; onNavigate: (path: string) => void }) {
  const { t } = useLanguage();
  const roleKey = identity.role.toLowerCase() as 'instructor' | 'admin' | 'student';
  const roleInfo = {
    titlePrefix: t(`hero.${roleKey}TitlePrefix`),
    titleAccent: t(`hero.${roleKey}TitleAccent`),
    subtitle: t(`hero.${roleKey}Subtitle`),
    tag: t(`hero.${roleKey}Tag`),
  };
  const HeaderIcon = ROLE_ICON[identity.role];

  // Was 2 hardcoded buttons (CSI106 + a nonexistent "SWE201c" code) --
  // scripts/seed_syllabi_from_chunks.py now ingests real syllabus detail
  // for all 44 courses, so this preview pulls whatever's actually in the
  // DB instead of listing the same 2 forever regardless of what's seeded.
  const [previewSyllabi, setPreviewSyllabi] = useState<SyllabusSummary[] | null>(null);
  useEffect(() => {
    listSyllabi().then((rows) => setPreviewSyllabi(rows.slice(0, 4))).catch(() => setPreviewSyllabi([]));
  }, []);

  const cards = [
    {
      onClick: () => onNavigate('/courses/curriculum'),
      icon: Layers,
      title: t('hub.curriculumTitle'),
      desc: t('hub.curriculumDesc'),
      cta: t('hub.curriculumCta'),
    },
    {
      onClick: () => onNavigate('/courses/learning-path'),
      icon: GitFork,
      title: t('hub.learningPathTitle'),
      desc: t('hub.learningPathDesc'),
      cta: t('hub.learningPathCta'),
    },
    {
      onClick: () => onNavigate('/courses/search'),
      icon: Search,
      title: t('hub.syllabusTitle'),
      desc: t('hub.syllabusDesc'),
      cta: t('hub.syllabusCta'),
    },
    {
      onClick: () => onNavigate('/courses/assignments'),
      icon: ClipboardList,
      title: t('hub.assignmentsTitle'),
      desc: identity.role === 'ADMIN' ? t('hub.assignmentsDescAdmin') : t('hub.assignmentsDescOther'),
      cta: t('hub.assignmentsCta'),
    },
  ];

  return (
    <div className="w-full bg-slate-50/50 min-h-[calc(100vh-140px)]">
      <Hero identity={identity} roleInfo={roleInfo} HeaderIcon={HeaderIcon} onNavigate={onNavigate} />

      <div className="py-12 px-4 sm:px-6 flex justify-center">
        <div className="w-full max-w-6xl space-y-8 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {cards.map((c) => {
            return (
              <div
                key={c.title}
                onClick={c.onClick}
                className="card p-6 cursor-pointer flex flex-col justify-between group"
              >
                <div className="space-y-3">
                  <div className="w-10 h-10 rounded-md bg-slate-50 border border-slate-200 text-slate-600 flex items-center justify-center transition-colors group-hover:text-[var(--accent)] group-hover:border-[var(--accent)]/30 group-hover:bg-[var(--accent)]/5">
                    <c.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-slate-900 group-hover:text-[var(--accent)] transition-colors">{c.title}</h2>
                    <p className="text-xs text-slate-500 mt-1 leading-relaxed">{c.desc}</p>
                  </div>
                </div>
                <div className="pt-4 flex items-center justify-between text-xs font-semibold text-slate-600 group-hover:text-[var(--accent)] transition-colors">
                  <span>{c.cta}</span>
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>

        <div className="card p-6 space-y-4 mt-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide flex items-center space-x-2">
              <BookOpen className="w-4 h-4 text-slate-500" />
              <span>{t('hub.availableSyllabiHeading')}</span>
            </h2>
            <button
              onClick={() => onNavigate('/courses/search')}
              className="text-xs font-semibold text-[var(--accent)] hover:underline cursor-pointer"
            >
              {t('hub.availableSyllabiSeeAll')}
            </button>
          </div>
          {previewSyllabi === null ? (
            <p className="text-xs text-slate-400 py-4 text-center">{t('app.loading')}</p>
          ) : previewSyllabi.length === 0 ? (
            <p className="text-xs text-slate-400 py-4 text-center">{t('hub.availableSyllabiEmpty')}</p>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {previewSyllabi.map((s) => (
                <button
                  key={s.subjectCode}
                  onClick={() => onNavigate(`/courses/syllabus/${encodeURIComponent(s.subjectCode)}`)}
                  className="p-3.5 border border-slate-200 rounded-[var(--radius-sm)] text-left cursor-pointer transition-colors hover:border-[var(--accent)] hover:bg-slate-50"
                >
                  <span className="mono text-[10px] font-bold text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">{s.subjectCode}</span>
                  <h3 className="font-bold text-xs text-slate-900 mt-2">{s.courseNameEnglish}</h3>
                  <span className="text-[11px] text-slate-500 mt-1 block">
                    {s.cloCount} CLO &bull; {s.sessionCount} {t('hub.sessionsUnit')}
                    {s.questionCount > 0 && <> &bull; {s.questionCount} {t('hub.questionsUnit')}</>}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
        </div>
      </div>
    </div>
  );
}

function Hero({
  identity,
  roleInfo,
  HeaderIcon,
  onNavigate,
}: {
  identity: Identity;
  roleInfo: { titlePrefix: string; titleAccent: string; subtitle: string; tag: string };
  HeaderIcon: typeof GraduationCap;
  onNavigate: (path: string) => void;
}) {
  const { t } = useLanguage();
  return (
    // Bottom-anchored, left-aligned composition (closer to the Univet
    // reference's actual text placement than a dead-centered block) --
    // capped height instead of a near-full-viewport poster. Taller than the
    // previous pass (680/760 vs 620/680) specifically to give the wordmark
    // and the text block their own vertical bands with real clearance
    // between them -- at the old height the wordmark's glyphs and the
    // eyebrow/heading physically overlapped (see the mask tuning below).
    <div className="relative w-full overflow-hidden px-6 sm:px-10 lg:px-16 flex flex-col justify-end min-h-[680px] lg:min-h-[760px] pt-24 pb-14 sm:pb-16">
      {/* Background videos — day/night pair, switched by the OS/browser
          color-scheme like the Cursus landing hero (LandingHero.jsx) rather
          than a role/user toggle. */}
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="metadata"
        poster={`/static/dist/media/hero/cursus-hero-day-poster.webp?v=${HERO_MEDIA_VERSION}`}
        className="absolute inset-0 w-full h-full object-cover object-[center_30%] dark:hidden"
        src={`/static/dist/media/hero/cursus-hero-day.mp4?v=${HERO_MEDIA_VERSION}`}
      />
      <video
        autoPlay
        loop
        muted
        playsInline
        preload="metadata"
        poster={`/static/dist/media/hero/cursus-hero-night-poster.webp?v=${HERO_MEDIA_VERSION}`}
        className="absolute inset-0 w-full h-full object-cover object-[center_30%] hidden dark:block"
        src={`/static/dist/media/hero/cursus-hero-night.mp4?v=${HERO_MEDIA_VERSION}`}
      />

      {/* Cinematic scrim. The previous version dipped to 35% opacity
          through the vertical middle -- exactly where the giant wordmark
          sits -- so the busiest, highest-detail part of the cityscape
          (windows, building edges) was also the LEAST darkened, and a
          pale low-opacity wordmark has no chance of reading as clean
          letterforms against that much visual noise (this is why it
          looked like an illegible smudge, not a font, in the screenshot).
          Keeps a consistent darker floor everywhere so the wordmark gets
          a calm backdrop the way Univet's flat sky gradient gives theirs. */}
      <div className="absolute inset-0 bg-gradient-to-t from-[#050505]/85 via-[#050505]/60 to-[#050505]/65" />

      {/* Placed in the top sky area revealed by object-[center_30%], sized
          and masked to fully fade out well above the text block (see the
          hero-height/wordmark-size comment on the outer div for why that
          separation matters). The mask used to be on this OUTER div, so its
          percentages were relative to the whole hero's height -- that made
          the fade hard to reason about relative to the letters themselves
          and read as a uniform light-grey wash rather than a crisp top half
          dissolving into a faded bottom half. Moved onto the glyph span
          itself (inline-block, so its box is just the glyph's own height)
          so 0%-100% maps directly to the letters: top half fully solid,
          second half dissolving to nothing by the very bottom -- the
          "half clear / half faded" look of the Univet reference. */}
      <div className="absolute inset-0 flex items-start justify-center pt-2 sm:pt-3 select-none pointer-events-none overflow-hidden" aria-hidden="true">
        <span
          className="inline-block font-display text-[clamp(4rem,15vw,14rem)] font-bold text-white/[0.85] whitespace-nowrap leading-none"
          style={{
            letterSpacing: '-0.02em',
            WebkitMaskImage: 'linear-gradient(to bottom, black 45%, transparent 92%)',
            maskImage: 'linear-gradient(to bottom, black 45%, transparent 92%)',
          }}
        >
          EDUSYNC
        </span>
      </div>

      <div className="relative w-full max-w-[680px] z-10">
        {/* Eyebrow — Reverted to original pill design */}
        <span
          role="text"
          aria-label={roleInfo.tag}
          className="px-4 py-1.5 rounded-full bg-white/90 border border-white/40 shadow-sm text-[#0f172a] text-[11px] font-bold uppercase tracking-[0.05em] inline-flex items-center gap-2 mb-5"
          style={{ backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)' }}
        >
          <span aria-hidden="true" className="inline-flex shrink-0">
            <HeaderIcon className="w-3.5 h-3.5" />
          </span>
          <span>{roleInfo.tag}</span>
        </span>

        {/* H1 — Prestigious serif display font, matching UNIVET's heading style */}
        <h1 className="font-display text-[clamp(2.5rem,4.5vw,4rem)] font-bold leading-[1.1] text-white drop-shadow-[0_2px_12px_rgba(0,0,0,0.8)]">
          {roleInfo.titlePrefix} {roleInfo.titleAccent}
        </h1>

        {/* Supporting paragraph — completes the eyebrow/H1/body/CTA
            hierarchy; line length capped so it reads as a caption, not a
            second block of body copy. */}
        <p className="mt-4 text-base text-white/85 max-w-[560px] leading-relaxed drop-shadow-[0_2px_10px_rgba(0,0,0,0.7)]">
          {roleInfo.subtitle}
        </p>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <button onClick={() => onNavigate('/courses/curriculum')} className="btn btn-primary">
            {t('hero.ctaCurriculum')}
          </button>
          <button onClick={() => onNavigate('/courses/search')} className="btn btn-secondary">
            {t('hero.ctaSyllabus')}
          </button>
        </div>

        {/* Stats — inline metadata continuing the same column (divider
            rules, not a boxed/centered row) so it reads as part of the
            hero's own composition rather than a separate stat-bar widget. */}
        <div className="mt-10 flex flex-wrap items-center divide-x divide-white/15">
          <Stat value="9" label={t('hero.statSemesters')} first />
          <Stat value="146" label={t('hero.statCredits')} />
          <Stat value="2" label={t('hero.statSyllabi')} />
          {identity.role === 'ADMIN' && <Stat value="Live" label={t('hero.statSync')} />}
        </div>
      </div>
    </div>
  );
}

function Stat({ value, label, first }: { value: string; label: string; first?: boolean }) {
  return (
    <div className={`flex items-baseline gap-2 ${first ? 'pr-5' : 'px-5'}`}>
      <span className="text-lg font-bold text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.5)]">{value}</span>
      <span className="text-[11px] uppercase tracking-wide text-white/60 drop-shadow-[0_1px_4px_rgba(0,0,0,0.5)]">{label}</span>
    </div>
  );
}
