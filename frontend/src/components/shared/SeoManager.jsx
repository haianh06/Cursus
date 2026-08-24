import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useLanguage } from '../../context/LanguageContext';
import { vi } from '../../locales/vi';
import { en } from '../../locales/en';

const dictionaries = { vi, en };

/**
 * Owns <title>/meta description/OG/Twitter/JSON-LD tags for the whole app.
 * Mounted inside <BrowserRouter> so it reacts to both language AND route
 * changes — before this, every public route (including /login,
 * /request-access, /demo/select-role) served the identical homepage
 * title/description/OG card, which meant non-JS crawlers and link
 * unfurlers (Slack, Zalo, Facebook) indexed/previewed them as duplicates.
 * Routes without an explicit entry in `seo.routes` (dashboard/auth pages
 * behind login) fall back to the site-wide default — they're disallowed in
 * robots.txt anyway, so they don't need their own listing.
 */
export default function SeoManager() {
  const { lang } = useLanguage();
  const { pathname } = useLocation();

  useEffect(() => {
    const dict = dictionaries[lang] || dictionaries.vi;
    const routeOverride = dict.seo?.routes?.[pathname];
    const seoTitle = routeOverride?.title || dict.seo?.title;
    const seoDescription = routeOverride?.description || dict.seo?.description;
    if (!seoTitle || !seoDescription) return;

    document.title = seoTitle;

    const setMeta = (selector, attr, value) => {
      const el = document.head.querySelector(selector);
      if (el) el.setAttribute(attr, value);
    };
    setMeta('meta[name="description"]', 'content', seoDescription);
    setMeta('meta[property="og:title"]', 'content', seoTitle);
    setMeta('meta[property="og:description"]', 'content', seoDescription);
    setMeta('meta[name="twitter:title"]', 'content', seoTitle);
    setMeta('meta[name="twitter:description"]', 'content', seoDescription);

    let canonical = document.head.querySelector('link[rel="canonical"]');
    if (canonical) {
      canonical.setAttribute('href', `${window.location.origin}${pathname}`);
    }

    const ldJson = document.head.querySelector('script[type="application/ld+json"]');
    if (ldJson) {
      try {
        const data = JSON.parse(ldJson.textContent);
        data.description = dict.seo?.description;
        ldJson.textContent = JSON.stringify(data);
      } catch {
        // Ignore malformed JSON-LD rather than breaking navigation.
      }
    }
  }, [lang, pathname]);

  return null;
}
