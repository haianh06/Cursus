import { defineConfig, devices } from '@playwright/test';

/**
 * E2E tests run against the dev stack from docker-compose.yml
 * (frontend on :3000, backend on :8000) — they do NOT start their own
 * server. Run `docker compose up -d` first, then `npx playwright test`.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    // Infinite CSS animations (e.g. the chat launcher's breathing pulse) never
    // settle for Playwright's actionability "stable" check, causing spurious
    // click timeouts. The app already honors prefers-reduced-motion to turn
    // these off, so opt into that here rather than special-casing selectors.
    reducedMotion: 'reduce',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
