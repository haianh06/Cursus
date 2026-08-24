import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { ArrowUp } from 'lucide-react';

// Mounted once for the whole app (see App.jsx), so it renders on both the
// marketing/auth pages (brand-blue territory) and the logged-in dashboard
// (teal --accent territory) — this tells it which color rule applies.
const DASHBOARD_PATH_RE = /^\/(student|instructor|admin)(\/|$)/;

/**
 * ScrollToTop — Floating button that appears at the bottom-right of the viewport
 * once the user scrolls past a threshold (400px).
 *
 * Provides a clean home affordance on long marketing pages without adding
 * clutter to the navigation menu.
 */
export default function ScrollToTop() {
  const [visible, setVisible] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const { pathname } = useLocation();
  const isDashboardScope = DASHBOARD_PATH_RE.test(pathname);

  useEffect(() => {
    const handleScroll = () => {
      if (window.scrollY > 400) {
        setVisible(true);
      } else {
        setVisible(false);
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  useEffect(() => {
    const handleChatToggle = (e) => {
      if (e.detail) {
        setChatOpen(!!e.detail.open);
      }
    };
    window.addEventListener('curi-chat-toggle', handleChatToggle);
    return () => window.removeEventListener('curi-chat-toggle', handleChatToggle);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
      
    });
  };

  return (
    <button
      type="button"
      onClick={scrollToTop}
      aria-label="Cuộn lên đầu trang"
      className={`scroll-to-top ${visible && !chatOpen ? 'scroll-to-top--visible' : ''} ${isDashboardScope ? '' : 'scroll-to-top--brand'}`}
    >
      <ArrowUp size={18} />
    </button>
  );
}
