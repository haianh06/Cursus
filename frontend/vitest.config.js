import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Separate from vite.config.js on purpose: vitest.config.js takes full
// priority over vite.config.js when both exist (Vite's own dev/build config
// is untouched), and `test.exclude` here keeps Vitest out of e2e/ (that
// directory is Playwright-only -- see playwright.config.js).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.js'],
    exclude: ['node_modules', 'e2e/**'],
    globals: true,
  },
});
