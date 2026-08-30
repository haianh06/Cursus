import React, { useState, useEffect, useRef } from 'react';
import { useLanguage } from '../../context/LanguageContext';
import usePrefersReducedMotion from '../../hooks/usePrefersReducedMotion';
import LandingNavbar from '../landing/LandingNavbar';
import LandingHero from '../landing/LandingHero';
import LandingTrustStrip from '../landing/LandingTrustStrip';
import LandingProduct from '../landing/LandingProduct';
import LandingWorkflow from '../landing/LandingWorkflow';
import LandingFeatureBento from '../landing/LandingFeatureBento';
import LandingGroundedQA from '../landing/LandingGroundedQA';
import LandingGuardrail from '../landing/LandingGuardrail';
import LandingLecturerHITL from '../landing/LandingLecturerHITL';
import LandingPrivacy from '../landing/LandingPrivacy';
import LandingFAQ from '../landing/LandingFAQ';
import LandingFooter from '../landing/LandingFooter';
import LandingChatWidget from '../landing/LandingChatWidget';

const SECTION_IDS = ['home', 'product', 'how-it-works', 'grounded', 'for-instructors', 'academic-integrity'];
// Ids the navbar actually has a link for — `grounded` (and the unlabeled
// Bento feature section between how-it-works and grounded) are real scroll
// stops but aren't nav destinations, so passing through them must not clear
// the navbar's highlight (verified live: without this filter, scrolling
// through that stretch leaves every nav link unhighlighted for ~1200px).
// `try-it` is NOT a scroll section at all — that nav item opens
// LandingChatWidget instead (see handleNavClick below), there's no
// matching `id="try-it"` element to scroll to or observe.
const NAV_SECTION_IDS = new Set(['home', 'product', 'how-it-works', 'for-instructors', 'academic-integrity']);

export default function LandingPage() {
  const { t, lang } = useLanguage();
  const reducedMotion = usePrefersReducedMotion();
  const [activeSection, setActiveSection] = useState('home');
  const [scrollProgress, setScrollProgress] = useState(0);
  const mainRef = useRef(null);
  const isFirstLangRender = useRef(true);

  // A brief opacity-only crossfade on locale switch — signals "content
  // just changed" without remounting anything (no key={lang} anywhere) and
  // without touching scroll position, video playback, or layout.
  useEffect(() => {
    if (isFirstLangRender.current) {
      isFirstLangRender.current = false;
      return;
    }
    const el = mainRef.current;
    if (!el || reducedMotion) return;
    el.classList.remove('landing-lang-pulse');
    // eslint-disable-next-line no-void -- forces a reflow so the animation restarts on every switch
    void el.offsetWidth;
    el.classList.add('landing-lang-pulse');
  }, [lang, reducedMotion]);

  const handleNavClick = (e, id) => {
    e.preventDefault();
    if (id === 'try-it') {
      window.dispatchEvent(new Event('landing-chat:open'));
      return;
    }
    const target = document.getElementById(id);
    if (!target) return;
    // replaceState (not pushState): section jumps are a single logical
    // position on this page, not separate history stops — pushState here
    // would fill the back-button history with every anchor click.
    window.history.replaceState(null, '', id === 'home' ? window.location.pathname : `#${id}`);
    target.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
  };

  // Initial-load hash handling: a direct load of "/" with no hash (or an
  // unrecognized hash) must start at Home, never at whatever section a
  // stale hash/back-forward-cache scroll position implies. A direct load
  // with a hash matching a real section may land there.
  useEffect(() => {
    if ('scrollRestoration' in window.history) {
      window.history.scrollRestoration = 'manual';
    }
    const hash = window.location.hash.replace('#', '');
    if (hash === 'try-it') {
      window.dispatchEvent(new Event('landing-chat:open'));
      window.history.replaceState(null, '', window.location.pathname);
      window.scrollTo(0, 0);
      return;
    }
    if (hash && SECTION_IDS.includes(hash) && hash !== 'home') {
      const target = document.getElementById(hash);
      if (target) {
        target.scrollIntoView({ behavior: 'auto', block: 'start' });
        setActiveSection(hash);
        return;
      }
    }
    if (hash) {
      window.history.replaceState(null, '', window.location.pathname);
    }
    window.scrollTo(0, 0);
  }, []);

  useEffect(() => {
    let ticking = false;
    const updateNavbar = () => {
      const scrollTop = window.scrollY;
      const docHeight = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress(docHeight > 0 ? Math.min(1, scrollTop / docHeight) : 0);

      if (scrollTop <= 20) setActiveSection('home');
      ticking = false;
    };
    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(updateNavbar);
    };

    updateNavbar();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (window.scrollY <= 20) return;
        const intersecting = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
        // Non-nav sections (proof-strip, grounded, the Bento feature strip)
        // are real scroll stops but not nav destinations — skip them so the
        // navbar keeps highlighting the last real section instead of going
        // dark while the user scrolls past.
        const navEntry = intersecting.find((e) => NAV_SECTION_IDS.has(e.target.id));
        if (navEntry) {
          setActiveSection(navEntry.target.id);
        }
      },
      {
        rootMargin: '-82px 0px -45% 0px',
        threshold: 0,
      }
    );

    SECTION_IDS.forEach((id) => {
      const el = document.getElementById(id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <div className="landing-page-scope font-sans selection:bg-landing-accent-soft">
      <a href="#main-content" className="landing-skip-link">
        {t('landing.skipToContent')}
      </a>

      {/* SCROLL PROGRESS BAR — track is a near-invisible warm-neutral hairline;
          the fill is monochrome (near-black in light mode, ivory in dark),
          matching the "94% neutral" rule rather than borrowing the app's
          teal accent. Driven by transform: scaleX() only (never width), so
          it never triggers layout, and it's read off rAF-throttled scroll
          updates, not raw scroll events. */}
      <div className="fixed top-0 left-0 right-0 h-[3px] bg-landing-border/40 z-[1200]" aria-hidden="true">
        <div
          className="h-full w-full bg-landing-text origin-left"
          style={{
            transform: `scaleX(${scrollProgress})`,
            transition: reducedMotion ? 'none' : 'transform 150ms linear'
          }}
        />
      </div>

      <LandingNavbar activeSection={activeSection} handleNavClick={handleNavClick} />

      {/* overflow-x-clip (not overflow-hidden, and not overflow-x-hidden):
          clips decorative elements that bleed past the viewport width (hero
          video, blurred accent blobs) without breaking position:sticky
          descendants. Any `overflow` value other than `visible` makes an
          element the nearest scrolling ancestor for sticky — that's what
          the old overflow-hidden did, silently breaking the "how it works"
          step preview's sticky positioning for the whole page even though
          this element never scrolled independently. Plain overflow-x-hidden
          doesn't fix it either: per the CSS overflow spec, pairing a
          non-visible overflow-x with a visible overflow-y forces the
          visible axis to compute as auto — still a scroll container.
          overflow: clip is the one value exempt from that pairing rule (it
          establishes no scrolling mechanism at all), confirmed live with
          Playwright: overflow-y stayed computed as true `visible` and the
          sticky panel held at its offset through the full scroll. */}
      <main ref={mainRef} id="main-content" tabIndex={-1} className="landing-main min-h-screen bg-landing-bg text-landing-text flex flex-col relative overflow-x-clip transition-colors duration-300 focus:outline-none">
        <LandingHero />
        <LandingTrustStrip />
        <LandingProduct />
        <LandingWorkflow />
        <LandingFeatureBento />
        <LandingGroundedQA />
        <LandingLecturerHITL />
        <LandingGuardrail />
        <LandingPrivacy />
        <LandingFAQ />
        <LandingFooter />
      </main>

      <LandingChatWidget />
    </div>
  );
}
