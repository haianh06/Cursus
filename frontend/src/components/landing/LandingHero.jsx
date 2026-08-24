import React, { useRef, useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, FileText, ShieldCheck, UserCheck, Play, Pause, ChevronDown, CalendarClock, BookOpen } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';
import { useTheme } from '../../context/ThemeContext';
import usePrefersReducedMotion from '../../hooks/usePrefersReducedMotion';
import useIsMobileViewport from '../../hooks/useIsMobileViewport';

const PROOF_ITEMS = [
  { icon: FileText, key: 'heroProofItem1', verified: true },
  { icon: ShieldCheck, key: 'heroProofItem2' },
  { icon: UserCheck, key: 'heroProofItem3' }
];

export default function LandingHero() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const { theme } = useTheme();
  const reducedMotion = usePrefersReducedMotion();
  const isMobileViewport = useIsMobileViewport();
  const [playing, setPlaying] = useState(false); // start false to avoid jarring, or maybe true? Webflow usually autoplays. Let's do true.

  const dayVideoRef = useRef(null);
  const nightVideoRef = useRef(null);
  const heroSectionRef = useRef(null);
  // Stop retrying play() after the first failed load so a bad/missing asset
  // doesn't keep firing errors every time playback toggles/theme changes.
  const [nightVideoUnavailable, setNightVideoUnavailable] = useState(false);
  const isNight = theme === 'dark';
  // Both videos previously kept decoding/painting for as long as the tab was
  // open, even scrolled thousands of pixels away — measured with a scripted
  // scroll + real frame timing: ~18% of frames were under 30fps and one
  // spiked to 85ms (11fps) with the hero nowhere in the viewport. Pausing
  // both the instant the hero itself scrolls out of view (and resuming,
  // still frame-synced, when it scrolls back in) removes that continuous
  // decode cost from the rest of the page.
  const [isHeroVisible, setIsHeroVisible] = useState(true);

  useEffect(() => {
    const el = heroSectionRef.current;
    if (!el) return undefined;
    const observer = new IntersectionObserver(
      ([entry]) => setIsHeroVisible(entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  // Video is skipped entirely (not just hidden) on mobile so the file is never downloaded.
  const showVideo = !reducedMotion && !isMobileViewport;
  const posterObjectPosition = isMobileViewport ? '70% center' : 'right center';

  // Autoplay handler
  useEffect(() => {
    if (!reducedMotion) {
      setPlaying(true);
    }
  }, [reducedMotion]);

  // Sync videos when playing state changes (or the hero scrolls off-screen)
  useEffect(() => {
    const dayVid = dayVideoRef.current;
    const nightVid = nightVideoRef.current;
    if (!dayVid || !nightVid) return;

    if (playing && !reducedMotion && isHeroVisible) {
      dayVid.play().catch(() => setPlaying(false));
      if (!nightVideoUnavailable) {
        nightVid.play().catch(() => setNightVideoUnavailable(true));
      }
    } else {
      dayVid.pause();
      if (!nightVideoUnavailable) nightVid.pause();
    }
  }, [playing, reducedMotion, nightVideoUnavailable, isHeroVisible]);

  // Keep videos synced
  const handleTimeUpdate = () => {
    const dayVid = dayVideoRef.current;
    const nightVid = nightVideoRef.current;
    if (!dayVid || !nightVid) return;

    // Sync night video to day video if they drift > 0.5s
    if (Math.abs(dayVid.currentTime - nightVid.currentTime) > 0.5) {
      nightVid.currentTime = dayVid.currentTime;
    }
  };

  const togglePlaying = useCallback(() => setPlaying((p) => !p), []);

  return (
    <section
      ref={heroSectionRef}
      id="home"
      className="relative z-10 overflow-hidden flex items-center px-6 lg:px-10 h-[100svh]"
    >
      {/* Background Videos (Focal Point kept on the right: subject/laptop/hands) */}
      <div className="absolute inset-0 z-0 bg-[#050505]">
        {showVideo && (
          <>
            <video
              ref={dayVideoRef}
              src="/media/hero/cursus-hero-day.mp4"
              poster="/media/hero/cursus-hero-day-poster.webp"
              className="absolute inset-0 w-full h-full object-cover transition-opacity duration-[var(--motion-cinematic)]"
              style={{ opacity: isNight ? 0 : 1, objectPosition: 'right center' }}
              muted
              playsInline
              loop
              preload="metadata"
              fetchPriority={isNight ? 'auto' : 'high'}
              onTimeUpdate={handleTimeUpdate}
            />
            <video
              ref={nightVideoRef}
              src="/media/hero/cursus-hero-night.mp4"
              poster="/media/hero/cursus-hero-night-poster.webp"
              className="absolute inset-0 w-full h-full object-cover transition-opacity duration-[var(--motion-cinematic)]"
              style={{ opacity: isNight ? 1 : 0, objectPosition: 'right center' }}
              muted
              playsInline
              loop
              preload="metadata"
              fetchPriority={isNight ? 'high' : 'auto'}
              onError={() => setNightVideoUnavailable(true)}
            />
          </>
        )}
        {!showVideo && (
          // Mobile (portrait / <=768px) never mounts <video>, so the .mp4 is never fetched.
          // Also used as the reduced-motion fallback (desktop, static "right center" framing).
          // TODO: 70% center is a temporary approximation for the portrait crop — replace with
          // a dedicated mobile-cropped poster (day + night) once the framing is verified on device.
          <img
            src={isNight ? "/media/hero/cursus-hero-night-poster.webp" : "/media/hero/cursus-hero-day-poster.webp"}
            alt=""
            className="absolute inset-0 w-full h-full object-cover transition-opacity duration-700"
            style={{ objectPosition: posterObjectPosition }}
            fetchPriority="high"
          />
        )}
        {/* Screen-content mask — the day/night hero footage shows an illustrated
            laptop with placeholder UI text that reads as gibberish up close
            (an unfinished mock, not real product copy). A `backdrop-filter`
            box reads as an obvious censor patch — hard rectangular edge,
            flat grey, visibly "hiding something". Blurring the DIV ITSELF
            with `filter` (not its backdrop) lets the blur soften its own
            edges into a feathered glow with no visible boundary, and a warm
            amber tint (matching the desk lamp lighting already in the shot)
            reads as screen glow/reflection instead of a patch. Desktop/video
            only — the mobile poster crop (`70% center`) puts the laptop in
            a different spot, so this would misalign there. */}
        {!isMobileViewport && (
          <div
            className="absolute z-[1] pointer-events-none"
            style={{ left: '51%', top: '60%', width: '13%', height: '15%' }}
            aria-hidden="true"
          >
            {/* Repositioned from an earlier estimate that measured wrong —
                real pixel measurement (Chrome headless, video frame paused
                and inspected directly) put the laptop screen's actual
                content area at roughly x:53-62%, y:63-73% of the 1280x900
                reference frame; this box is deliberately a bit larger and
                shifted to fully contain that, since the video isn't a
                static image and the "screen content" mockup shifts/evolves
                across the loop (confirmed by sampling multiple timestamps).
                Pale blue-white "glare" instead of a warm/dark tint — a real
                laptop screen's glare reads as convincing regardless of
                whether the frame underneath happens to be a bright white
                table UI or the darker desk wood, where the previous warm
                brown tint looked like a flat grey smudge on light frames. */}
            <div
              className="absolute inset-[12%] rounded-full"
              style={{
                backgroundColor: 'rgba(225,235,248,0.55)',
                filter: 'blur(18px)',
              }}
            />
          </div>
        )}

        {/* Bottom-right corner vignette — the source hero footage vendor
            occasionally leaves a small watermark/logo baked into this exact
            corner of a render (spotted once in a screenshot; not
            reproducible in this build's current .mp4 files after scanning
            both day/night videos across their full ~5s loop at 0.5s steps
            plus both static posters — the night video's file-modified time
            is notably newer than every other hero asset, consistent with
            it already having been re-exported to remove it). Kept as a
            standing, tasteful fade regardless — corner vignettes are a
            normal cinematic touch here, not just a cover-up, and it's cheap
            insurance against a watermark reappearing in a future re-render
            without needing another manual audit. */}
        {!isMobileViewport && (
          <div
            className="absolute bottom-0 right-0 w-[16%] h-[14%] pointer-events-none z-[1]"
            style={{ background: 'radial-gradient(circle at 100% 100%, rgba(5,5,5,0.55) 0%, rgba(5,5,5,0) 70%)' }}
            aria-hidden="true"
          />
        )}
      </div>

      {/* Cinematic Scrim (Horizontal Gradient: Dark left, Transparent right)
          Day and night use different strength/tint: a flat #050505 scrim at
          the same opacity for both crushed the day poster's naturally light
          room (cream wall, fairy lights) down to near-black, so the left
          side — where the heading actually sits — looked identical between
          themes and the day/night switch read as having no effect there.
          Night keeps the stronger near-black scrim (matches the darker
          night art); day uses a warmer, lower-opacity scrim so the brighter
          scene shows through while keeping the heading/eyebrow legible. */}
      <div
        className={`absolute inset-0 z-10 pointer-events-none bg-gradient-to-r ${
          isNight
            ? 'from-[#050505] via-[#050505]/70 md:via-[#050505]/50 to-transparent'
            : 'from-[#0d0a06]/90 via-[#0d0a06]/45 md:via-[#0d0a06]/28 to-transparent'
        }`}
      />

      {/* Hero Content - Left Aligned over negative space */}
      <div className="relative z-20 w-full max-w-[1440px] mx-auto flex flex-col items-start text-left mt-6 md:mt-8">
        <div className="w-full max-w-[660px] animate-in fade-in slide-in-from-bottom-8 duration-1000 fill-mode-both">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-md border border-white/20 mb-1 sm:mb-3 drop-shadow-md">
            <span className="w-2 h-2 rounded-full bg-landing-accent animate-pulse" />
            <p className="text-[13px] font-semibold uppercase tracking-[0.08em] text-white/90">
              {t('landing.heroEyebrow')}
            </p>
          </div>
          <h1 className="landing-hero-heading font-display mb-1 sm:mb-3 drop-shadow-2xl">
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-white via-white to-white/80 pb-2">{t('landing.heroTitleLine1')}</span>
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-landing-accent to-indigo-300">{t('landing.heroTitleLine2')}</span>
          </h1>
          <p className="body-text hero-desc-compact text-white/85 mb-3 sm:mb-6 drop-shadow-lg font-light leading-relaxed max-w-[90%]">
            {t('landing.heroDesc')}
          </p>
          
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-start gap-2 sm:gap-4 w-full sm:w-auto animate-in fade-in slide-in-from-bottom-8 duration-1000 delay-200 fill-mode-both">
            <button
              onClick={() => navigate('/demo/select-role')}
              // The shadow's rgba(36,104,201,…) is --brand-blue's own RGB at a
              // stronger alpha than --brand-blue-glow provides (0.4/0.55 vs
              // 0.16) — a deliberately more intense glow for this specific
              // large hero CTA, kept literal rather than a fragile
              // Tailwind-arbitrary-value color-mix() expression.
              className="group relative h-[48px] sm:h-[60px] min-w-[220px] sm:min-w-[240px] px-8 bg-landing-cta text-landing-cta-fg hover:bg-landing-cta-hover text-base font-semibold rounded-2xl transition-all duration-300 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-landing-accent focus-visible:ring-offset-2 flex items-center justify-center gap-3 shadow-[0_0_40px_rgba(36,104,201,0.4)] hover:shadow-[0_0_60px_rgba(36,104,201,0.55)] overflow-hidden"
            >
              <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-in-out" />
              <span className="relative z-10">{t('landing.heroCtaPrimary')}</span>
              <ArrowRight size={18} className="relative z-10 transition-transform duration-[var(--motion-fast)] group-hover:translate-x-1.5" />
            </button>
            <a
              href="#how-it-works"
              className="h-[48px] sm:h-[60px] min-w-[180px] sm:min-w-[200px] px-8 border border-white/20 hover:border-white/40 bg-white/5 hover:bg-white/15 backdrop-blur-lg text-white text-base font-medium rounded-2xl transition-all duration-300 active:scale-[0.98] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white flex items-center justify-center shadow-lg"
            >
              {t('landing.heroCtaSecondary')}
            </a>
          </div>

          <ul className="mt-3 sm:mt-6 flex flex-wrap sm:flex-nowrap justify-start items-center gap-x-4 sm:gap-x-5 gap-y-1 animate-in fade-in duration-1000 delay-500 fill-mode-both">
            {PROOF_ITEMS.map(({ icon: Icon, key, verified }) => (
              <li key={key} className="flex items-center gap-2 text-xs sm:text-sm font-medium text-white/70 drop-shadow-sm whitespace-nowrap">
                <div className={`shrink-0 p-1 rounded-full ${verified ? 'bg-landing-accent-soft text-landing-accent' : 'bg-white/10 text-white/70'} backdrop-blur-sm`}>
                  <Icon size={14} aria-hidden="true" />
                </div>
                {t(`landing.${key}`)}
              </li>
            ))}
          </ul>

          {/* Mobile-only product preview — the hero video/poster is cropped
              hard on mobile (70% center) to keep the subject in frame,
              which means phone visitors saw text only, no visual proof of
              what the product actually looks like. A small static mockup
              card (same browser-chrome pattern as the "Cách hoạt động"
              section) fills that gap without needing a dedicated
              mobile-cropped video asset. */}
          {isMobileViewport && (
            <div className="mt-6 w-full max-w-[340px] rounded-2xl border border-white/15 bg-white/[0.07] backdrop-blur-md overflow-hidden shadow-2xl animate-in fade-in duration-1000 delay-700 fill-mode-both">
              <div className="h-8 border-b border-white/10 bg-white/5 flex items-center px-3 gap-1.5">
                <span className="w-2 h-2 rounded-full bg-white/25" />
                <span className="w-2 h-2 rounded-full bg-white/25" />
                <span className="w-2 h-2 rounded-full bg-white/25" />
                <span className="ml-2 text-[9px] font-mono text-white/40 truncate">app.cursus.edu.vn</span>
              </div>
              <div className="p-3.5 flex flex-col gap-2">
                <div className="flex items-center gap-2 text-white/90 text-xs font-semibold">
                  <CalendarClock size={13} className="text-landing-accent shrink-0" />
                  {t('landing.heroMobilePreviewLabel')}
                </div>
                <div className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-white/75">
                  {t('landing.heroMobilePreviewTask')}
                </div>
                <div className="rounded-lg border border-landing-accent/30 bg-landing-accent/15 px-3 py-2 flex items-center gap-1.5 text-[10px] font-semibold text-landing-accent">
                  <BookOpen size={11} className="shrink-0" />
                  {t('landing.heroMobilePreviewCitation')}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Floating Controls */}
      {!reducedMotion && (
        <div className="absolute bottom-8 right-8 lg:right-12 z-30">
          <button
            type="button"
            onClick={togglePlaying}
            className="w-11 h-11 flex items-center justify-center rounded-full bg-black/30 hover:bg-black/50 backdrop-blur-md border border-white/10 text-white transition-all active:scale-[0.95] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
            aria-label={playing ? t('landing.heroPauseLabel') : t('landing.heroPlayLabel')}
          >
            {playing ? <Pause size={16} className="fill-white" /> : <Play size={16} className="fill-white ml-0.5" />}
          </button>
        </div>
      )}

      {/* Scroll Cue (Left aligned with text container) */}
      <div className="absolute bottom-8 left-6 lg:left-10 z-30 w-full max-w-[1440px] mx-auto pointer-events-none">
        <div className="flex flex-col items-start gap-2 opacity-70 animate-bounce">
          <ChevronDown size={24} className="text-white" />
        </div>
      </div>
    </section>
  );
}
