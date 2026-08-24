import React, { useEffect, useRef, useState } from 'react';

/**
 * Scroll-reveal wrapper for landing sections. Content is visible by
 * default (no JS / IntersectionObserver support = no motion, not
 * hidden content) and animates in once when it enters the viewport.
 */
export default function LandingReveal({ as: Tag = 'div', className = '', children, ...rest }) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === 'undefined') {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.2, rootMargin: '0px 0px -60px 0px' }
    );
    observer.observe(node);

    // Safety net: full-page screenshot tools (Playwright, visual-regression
    // CI) resize the viewport instantly rather than firing real scroll
    // events, so a section far below the fold may never receive an
    // intersection callback during capture. Content must never stay
    // permanently invisible, so force it in after a short delay regardless.
    const fallback = setTimeout(() => setVisible(true), 1200);

    return () => {
      observer.disconnect();
      clearTimeout(fallback);
    };
  }, []);

  return (
    <Tag
      ref={ref}
      className={`landing-reveal ${visible ? 'landing-reveal-visible' : ''} ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}
