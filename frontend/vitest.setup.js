import '@testing-library/jest-dom/vitest';

// jsdom doesn't implement matchMedia -- usePrefersReducedMotion (and any
// other media-query hook) needs at least this much of the interface to not
// throw during mount in every test that renders the app shell.
if (typeof window !== 'undefined' && !window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}
