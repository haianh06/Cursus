import React from 'react';
import usePrefersReducedMotion from '../../hooks/usePrefersReducedMotion';

/**
 * Cursus Assistant mascot — the ONE canonical mascot for the whole app.
 * Single SVG geometry (the detailed robot: head, torso, chest mark, arms,
 * legs, floating screen/book/cap/pages), scaled by `size` — never a
 * different drawing per size. Replaces the old CuriAvatar (simple round
 * head) and the old default export of this file (detailed robot with an
 * unmanaged size prop); this consolidation is intentional, not incidental.
 *
 * `size` accepts a named tier or a raw pixel number:
 *   - 'launcher' (52px) — floating chat bubble / tiny header icons
 *   - 'avatar'   (88px) — mid-size panel/context headers
 *   - 'hero'     (240px) — auth screens, boot loader, large error states
 *   - any number — used as-is (existing call sites pass a range of pixel
 *     sizes; forcing every one into exactly 3 buckets would just be
 *     busywork without changing what's on screen)
 *
 * Below COMPACT_THRESHOLD px, the secondary details (arms, legs, floating
 * cap/pages/screen/book/sparkle, antenna) are not rendered at all, and the
 * viewBox crops in tight on the head + chest — same paths, just a smaller
 * window onto them, so the character reads as "standing closer to camera"
 * instead of "the same busy scene, shrunk until it's mud." This is cheaper
 * and more consistent than maintaining a second simplified SVG.
 */

const SIZE_PRESETS = { launcher: 52, avatar: 88, hero: 240 };
const COMPACT_THRESHOLD = 56;

function resolvePx(size) {
  if (typeof size === 'number') return size;
  if (size in SIZE_PRESETS) return SIZE_PRESETS[size];
  return 150;
}

export default function CursusMascot({ size = 150, className = '', state = 'idle', animate = true }) {
  const reducedMotion = usePrefersReducedMotion();
  const animationsEnabled = animate && !reducedMotion;
  const [mountWave, setMountWave] = React.useState(false);

  React.useEffect(() => {
    if (!animationsEnabled) return undefined;
    setMountWave(true);
    const timer = setTimeout(() => setMountWave(false), 1500);
    return () => clearTimeout(timer);
  }, [animationsEnabled]);

  // Random blink + idle look-around — ported from the old CuriAvatar so the
  // "breathing, alive" feel isn't lost just because the geometry changed.
  // Driven by JS state + inline `transform`/`transition`, not a CSS
  // `@keyframes` animation, so the site's blanket
  // `prefers-reduced-motion { animation: none }` rule can't catch it —
  // gated on the hook directly instead. `animate=false` (EmptyState's
  // static use) opts out entirely, same as the old CuriAvatar's `animate`.
  const [isBlinking, setIsBlinking] = React.useState(false);
  const [lookOffset, setLookOffset] = React.useState({ x: 0, y: 0 });

  React.useEffect(() => {
    if (!animationsEnabled || state === 'error' || state === 'offline' || state === 'sleep' || state === 'inactive') return undefined;
    let blinkTimeout;
    const scheduleBlink = () => {
      const delay = 4000 + Math.random() * 3000;
      blinkTimeout = setTimeout(() => {
        setIsBlinking(true);
        setTimeout(() => setIsBlinking(false), 140);
        scheduleBlink();
      }, delay);
    };
    scheduleBlink();
    return () => clearTimeout(blinkTimeout);
  }, [state, animationsEnabled]);

  React.useEffect(() => {
    if (!animationsEnabled || state !== 'idle') { setLookOffset({ x: 0, y: 0 }); return undefined; }
    let lookTimeout;
    const scheduleLook = () => {
      lookTimeout = setTimeout(() => {
        const x = (Math.random() - 0.5) * 3;
        const y = (Math.random() - 0.5) * 2;
        setLookOffset({ x, y });
        scheduleLook();
      }, 3800 + Math.random() * 2200);
    };
    scheduleLook();
    return () => clearTimeout(lookTimeout);
  }, [state, animationsEnabled]);

  const px = resolvePx(size);
  const isCompact = px <= COMPACT_THRESHOLD;
  const renderSize = typeof size === 'number' || size in SIZE_PRESETS ? px : size;

  // ── Unified state vocabulary — the union of every state string any
  // current caller (AuthLayout, App.jsx boot loader, ErrorState,
  // ApiErrorScreen, FeatureErrorBoundary) already passes. No new states
  // invented; this just gives all of them one visual home.
  const isError = state === 'error';
  const isOffline = state === 'offline';
  const isSleepDim = state === 'sleep' || state === 'inactive';
  const isSuccess = state === 'success' || state === 'celebrate';
  const isCelebrate = state === 'celebrate';
  const isThinking = state === 'thinking';
  const isLoadingPulse = state === 'loading' || isThinking;
  const isPasswordCover = state === 'typing-password';
  const isSleepyEyes = isPasswordCover || isSleepDim;
  const isEmailTilt = state === 'typing-email' || state === 'typing';
  const isWarning = state === 'warning' || state === 'warn';
  const isWaving = mountWave || state === 'wave' || state === 'greet' || state === 'greeting' || state === 'greeting-wave';
  const isListening = state === 'listening';
  const isAnswering = state === 'answering';
  const isHappy = state === 'happy';
  const isHoverPop = state === 'hover' || state === 'excited';

  const eyeScale = isSuccess || isHoverPop ? 1.08 : isListening ? 1.03 : 1;
  const eyeShiftX = isListening ? -1.2 : 0;

  // Brand-blue everywhere the two legacy components disagreed (Mascot's
  // headphones were hardcoded green — see the removal note this file
  // replaces at the bottom of the old Mascot.jsx). Green/amber/red are kept
  // as genuine status signals (success/warning/error), not default chrome.
  const chestColor1 = isError ? '#ef4444' : isSuccess ? '#10B981' : isWarning ? '#f59e0b' : 'var(--brand-blue)';
  const chestColor2 = isError ? '#f87171' : isSuccess ? '#34D399' : isWarning ? '#fb923c' : 'var(--brand-blue-hover)';
  const strokeColor = '#A7B5C6';
  const bodyStrokeWidth = isCompact ? 2.2 : 1.5;
  const eyeStrokeWidth = isCompact ? 1.8 : 1.2;

  const dimmed = isSleepDim;

  return (
    <svg
      width={renderSize}
      height={renderSize}
      viewBox={isCompact ? '38 8 104 106' : '0 0 180 180'}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`${isCompact ? '' : 'mascot-float'} ${className}`}
      aria-label="Cursus Assistant — Cursus learning companion"
      role="img"
      style={{ opacity: dimmed ? 0.6 : 1, transition: 'opacity 300ms ease-out' }}
    >
      <defs>
        <linearGradient id="mascotBodyGrad" x1="60" y1="50" x2="120" y2="130" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="#FFFFFF" />
          <stop offset="75%" stopColor="#E2E8F0" />
          <stop offset="100%" stopColor="#CBD5E1" />
        </linearGradient>
        <linearGradient id="mascotFaceGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#E9E7FF" />
          <stop offset="100%" stopColor="#DDF4FF" />
        </linearGradient>
        {!isCompact && (
          <>
            <linearGradient id="mascotScreenGrad" x1="15" y1="60" x2="70" y2="105" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="rgba(36, 104, 201, 0.35)" />
              <stop offset="100%" stopColor="rgba(36, 104, 201, 0.04)" />
            </linearGradient>
            {/* Deep-navy foot shadow — matches the launcher bubble's
                glow/shadow color (rgba(20,49,92,…)) so every "effect around
                the mascot" reads as one consistent color, distinct from the
                brand-blue used on the mascot's own eyes/chest/headphones. */}
            <radialGradient id="mascotPlatformGlow" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(20, 49, 92, 0.45)" />
              <stop offset="100%" stopColor="rgba(20, 49, 92, 0)" />
            </radialGradient>
            <linearGradient id="mascotBookGrad" x1="125" y1="50" x2="155" y2="80" gradientUnits="userSpaceOnUse">
              <stop offset="0%" stopColor="#60A5FA" />
              <stop offset="100%" stopColor="#2563EB" />
            </linearGradient>
          </>
        )}
      </defs>

      {!isCompact && (
        <>
          {/* Floating platform shadow — one consistent sky-blue tint at the
              feet, replacing the old 3-stop cyan/sky-blue gradient stack. */}
          <ellipse cx="90" cy="157" rx="26" ry="5" fill="url(#mascotPlatformGlow)" />

          <g opacity="0.75">
            <path d="M125 35 L135 31 L145 35 L135 39 Z" fill="#475569" />
            <path d="M130 37 L130 42 C130 44 140 44 140 42 L140 37" fill="#334155" />
            <path d="M141 35 L145 42 L143 43" stroke="#F59E0B" strokeWidth="0.8" fill="none" />
            <animateTransform attributeName="transform" type="translate" values="0,0; 0,-4; 0,0" dur="3.5s" repeatCount="indefinite" />
          </g>

          <g opacity="0.7">
            <rect x="25" y="45" width="12" height="15" rx="1" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="0.8" transform="rotate(-15 25 45)" />
            <line x1="28" y1="50" x2="34" y2="48" stroke="#94A3B8" strokeWidth="0.8" />
            <line x1="27" y1="54" x2="33" y2="52" stroke="#94A3B8" strokeWidth="0.8" />
            <animateTransform attributeName="transform" type="translate" values="0,0; -3,-3; 0,0" dur="4.2s" repeatCount="indefinite" />
          </g>

          <rect x="78" y="122" width="8" height="14" rx="3.5" fill="url(#mascotBodyGrad)" stroke={strokeColor} strokeWidth="1" />
          <rect x="94" y="122" width="8" height="14" rx="3.5" fill="url(#mascotBodyGrad)" stroke={strokeColor} strokeWidth="1" />
          <ellipse cx="82" cy="136" rx="8" ry="4" fill="#94A3B8" />
          <ellipse cx="98" cy="136" rx="8" ry="4" fill="#94A3B8" />
        </>
      )}

      {/* Torso + chest mark — always visible, even at compact size (part of
          the minimum "recognizable Cursus Assistant" set per the spec). */}
      <rect x="63" y="78" width="54" height="44" rx="18" fill="url(#mascotBodyGrad)" stroke={strokeColor} strokeWidth={bodyStrokeWidth} />
      <g className={isLoadingPulse ? 'animate-pulse' : ''}>
        <polygon points="90,92 97,96 97,104 90,108 83,104 83,96" fill={chestColor1} />
        <polygon points="90,94 95,97 95,103 90,106 85,103 85,97" fill={chestColor2} />
        <circle cx="90" cy="100" r="2.5" fill={isError ? '#fee2e2' : '#EAF2FF'} />
      </g>

      {!isCompact && (
        <>
          <path d="M117 88 C124 92 128 102 122 110 C120 114 116 115 114 112" stroke="url(#mascotBodyGrad)" strokeWidth="8" strokeLinecap="round" fill="none" />
          {isPasswordCover ? (
            <path d="M63 90 C57 73 53 50 68 45" stroke="url(#mascotBodyGrad)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          ) : isWaving ? (
            <path d="M63 90 C51 80 46 60 56 46" stroke="url(#mascotBodyGrad)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" fill="none" className="mascot-arm-wave" style={{ transformOrigin: '63px 90px' }} />
          ) : (
            <path d="M63 90 C49 88 40 80 47 74" stroke="url(#mascotBodyGrad)" strokeWidth="8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          )}
          <circle
            cx={isPasswordCover ? 68 : isWaving ? 56 : 44}
            cy={isPasswordCover ? 45 : isWaving ? 46 : 75}
            r="3.5"
            fill="#CBD5E1"
            className={isWaving ? 'mascot-arm-wave' : ''}
            style={isWaving ? { transformOrigin: '63px 90px' } : undefined}
          />
        </>
      )}

      <rect x="83" y="74" width="14" height="6" rx="2" fill="#94A3B8" />

      <g style={{
        transform: isEmailTilt ? 'rotate(-3deg) translate(-2px, 1px)' : undefined,
        transformOrigin: '90px 58px',
        transition: 'transform 200ms ease-out'
      }}>
        <rect x="46" y="14" width="88" height="62" rx="28" fill="url(#mascotBodyGrad)" stroke={strokeColor} strokeWidth={bodyStrokeWidth} />
        <rect x="52" y="21" width="76" height="48" rx="19" fill="url(#mascotFaceGrad)" stroke="#A7B5C6" strokeWidth={isCompact ? 1.2 : 0.8} opacity={isOffline ? 0.75 : 1} />

        {!isError && !isOffline && (
          <>
            <ellipse cx="61" cy="58" rx="3.5" ry="1.5" fill="#FB923C" opacity="0.32" />
            <ellipse cx="119" cy="58" rx="3.5" ry="1.5" fill="#FB923C" opacity="0.32" />
          </>
        )}

        {isSleepyEyes ? (
          <>
            <path d="M65 44 Q73 50 81 44" stroke="#0C1E36" strokeWidth="2.5" strokeLinecap="round" fill="none" />
            <path d="M99 44 Q107 50 115 44" stroke="#0C1E36" strokeWidth="2.5" strokeLinecap="round" fill="none" />
          </>
        ) : isThinking ? (
          <>
            <ellipse cx="72" cy="40" rx="12.5" ry="16.5" fill="#FFFFFF" stroke="#0C1E36" strokeWidth={eyeStrokeWidth} />
            <ellipse cx="72" cy="36" rx="8.2" ry="11.5" fill="#0C1E36" />
            <circle cx="75.5" cy="32.5" r="2.8" fill="var(--brand-blue)" />
            <circle cx="77.2" cy="30.8" r="2" fill="#FFFFFF" />
            <ellipse cx="108" cy="40" rx="12.5" ry="16.5" fill="#FFFFFF" stroke="#0C1E36" strokeWidth={eyeStrokeWidth} />
            <ellipse cx="108" cy="36" rx="8.2" ry="11.5" fill="#0C1E36" />
            <circle cx="111.5" cy="32.5" r="2.8" fill="var(--brand-blue)" />
            <circle cx="113.2" cy="30.8" r="2" fill="#FFFFFF" />
          </>
        ) : isHappy ? (
          <>
            <path d="M62 40 Q72 30 82 40" stroke="#0C1E36" strokeWidth="3" strokeLinecap="round" fill="none" />
            <path d="M98 40 Q108 30 118 40" stroke="#0C1E36" strokeWidth="3" strokeLinecap="round" fill="none" />
          </>
        ) : (
          <>
            <g
              style={{
                transformOrigin: '72px 40px',
                transform: `translate(${lookOffset.x + eyeShiftX}px, ${lookOffset.y}px) scale(${isBlinking ? 1 : eyeScale}, ${isBlinking ? 0.08 : eyeScale})`,
                transition: 'transform 120ms ease-out'
              }}
            >
              <ellipse cx="72" cy="40" rx="12.5" ry="16.5" fill="#FFFFFF" stroke="#0C1E36" strokeWidth={eyeStrokeWidth} opacity={isOffline ? 0.5 : 1} />
              <ellipse cx="72" cy="40" rx="8.2" ry="11.5" fill="#0C1E36" opacity={isOffline ? 0.5 : 1} />
              {!isOffline && (
                <>
                  <ellipse cx="72" cy="40" rx="8.2" ry="11.5" fill="none" stroke="var(--brand-blue)" strokeWidth="1" opacity="0.8" className={isListening ? 'animate-pulse' : ''} />
                  <circle cx="75.5" cy="36.5" r="2.8" fill="var(--brand-blue)" />
                  <circle cx="77.2" cy="34.8" r="2" fill="#FFFFFF" />
                  <circle cx="68.5" cy="43.5" r="1" fill="#FFFFFF" />
                  <ellipse cx="68.5" cy="45.5" rx="2.5" ry="0.9" fill="#8B5CF6" opacity="0.6" />
                  <ellipse cx="74.5" cy="46" rx="2.2" ry="0.8" fill="#FB923C" opacity="0.65" />
                </>
              )}
            </g>

            {isWaving ? (
              <path d="M98 40 Q108 47 118 40" stroke="#0C1E36" strokeWidth="3.2" strokeLinecap="round" fill="none" />
            ) : (
              <g
                style={{
                  transformOrigin: '108px 40px',
                  transform: `translate(${-lookOffset.x + eyeShiftX}px, ${lookOffset.y}px) scale(${isBlinking ? 1 : eyeScale}, ${isBlinking ? 0.08 : eyeScale})`,
                  transition: 'transform 120ms ease-out'
                }}
              >
                <ellipse cx="108" cy="40" rx="12.5" ry="16.5" fill="#FFFFFF" stroke="#0C1E36" strokeWidth={eyeStrokeWidth} opacity={isOffline ? 0.5 : 1} />
                <ellipse cx="108" cy="40" rx="8.2" ry="11.5" fill="#0C1E36" opacity={isOffline ? 0.5 : 1} />
                {!isOffline && (
                  <>
                    <ellipse cx="108" cy="40" rx="8.2" ry="11.5" fill="none" stroke="var(--brand-blue)" strokeWidth="1" opacity="0.8" className={isListening ? 'animate-pulse' : ''} />
                    <circle cx="111.5" cy="36.5" r="2.8" fill="var(--brand-blue)" />
                    <circle cx="113.2" cy="34.8" r="2" fill="#FFFFFF" />
                    <circle cx="104.5" cy="43.5" r="1" fill="#FFFFFF" />
                    <ellipse cx="104.5" cy="45.5" rx="2.5" ry="0.9" fill="#8B5CF6" opacity="0.6" />
                    <ellipse cx="110.5" cy="46" rx="2.2" ry="0.8" fill="#FB923C" opacity="0.65" />
                  </>
                )}
              </g>
            )}
          </>
        )}

        {isWarning && (
          <>
            <path d="M60 22 L70 26" stroke="#f59e0b" strokeWidth="1.8" strokeLinecap="round" />
            <path d="M120 22 L110 26" stroke="#f59e0b" strokeWidth="1.8" strokeLinecap="round" />
          </>
        )}

        {isError || isOffline ? (
          <path d="M84 59 L96 59" stroke="#0C1E36" strokeWidth="1.5" strokeLinecap="round" />
        ) : isSuccess ? (
          <path d="M82 56 Q90 61 98 56" stroke="#0C1E36" strokeWidth="2.2" strokeLinecap="round" fill="none" className="mascot-mouth" />
        ) : (
          <path d="M84 57 Q90 60 96 57" stroke="#0C1E36" strokeWidth="2.2" strokeLinecap="round" fill="none" className={isAnswering ? 'curi-mouth-talk-anim' : 'mascot-mouth'} />
        )}

        {!isCompact && (
          <g className="curi-sparkle-anim" style={{ transformOrigin: '90px 14px' }}>
            <path d="M90 4 L91.5 8 L95 9 L91.5 10 L90 14 L88.5 10 L85 9 L88.5 8 Z" fill="var(--brand-blue)" />
          </g>
        )}

        {/* Headphones — unified to brand-blue (previously hardcoded green in
            the old Mascot.jsx, one of the two color systems this merges). */}
        <rect x="41" y="32" width="5" height="18" rx="2.5" fill="var(--brand-blue)" />
        <circle cx="43" cy="41" r="4.5" fill="var(--brand-blue-hover)" opacity="0.8" />
        <rect x="134" y="32" width="5" height="18" rx="2.5" fill="var(--brand-blue)" />
        <circle cx="137" cy="41" r="4.5" fill="var(--brand-blue-hover)" opacity="0.8" />
      </g>

      {!isCompact && (
        <>
          <g>
            <polygon points="12,65 52,58 52,98 12,105" fill="url(#mascotScreenGrad)" stroke={isCelebrate ? '#10b981' : 'var(--brand-blue)'} strokeWidth="1" strokeOpacity="0.8" />
            {isCelebrate ? (
              <path d="M22 84 L27 89 L38 77" stroke="#10b981" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" className="animate-check-pop" />
            ) : (
              <>
                <circle cx="23" cy="80" r="4" fill="var(--brand-blue)" opacity="0.6" />
                <line x1="30" y1="76" x2="45" y2="73" stroke="var(--brand-blue)" strokeWidth="1.5" opacity="0.8" />
                <line x1="30" y1="81" x2="42" y2="79" stroke="var(--brand-blue)" strokeWidth="1" opacity="0.8" />
                <line x1="30" y1="86" x2="45" y2="84" stroke="#F59E0B" strokeWidth="1" opacity="0.8" />
              </>
            )}
            <animateTransform attributeName="transform" type="translate" values="0,0; 0,-3; 0,0" dur="3s" repeatCount="indefinite" />
          </g>

          <g>
            <path d="M130 78 L142 72 L142 88 L130 94 Z" fill="url(#mascotBookGrad)" />
            <path d="M142 72 L154 78 L154 94 L142 88 Z" fill="#60A5FA" />
            <path d="M130 78 Q142 82 154 78" stroke="#FFFFFF" strokeWidth="1" fill="none" />
            <animateTransform attributeName="transform" type="translate" values="0,0; 0,-6; 0,0" dur="4s" repeatCount="indefinite" />
          </g>

          {isThinking ? (
            <g transform="translate(125, 18)">
              <circle cx="0" cy="0" r="2" fill="var(--brand-blue)" className="think-dot-1" />
              <circle cx="6" cy="0" r="2" fill="var(--brand-blue)" className="think-dot-2" />
              <circle cx="12" cy="0" r="2" fill="var(--brand-blue)" className="think-dot-3" />
            </g>
          ) : (
            <g>
              <path d="M110 20 L112 24 L116 25 L112 26 L110 30 L108 26 L104 25 L108 24 Z" fill="#F59E0B" />
              <animateTransform attributeName="transform" type="translate" values="0,0; 2,2; 0,0" dur="4.5s" repeatCount="indefinite" />
            </g>
          )}
        </>
      )}
    </svg>
  );
}
