export async function startSandboxAs(page, roleName) {
  // Infinite CSS animations (e.g. the chat launcher's breathing pulse) never
  // settle for Playwright's actionability "stable" check, causing spurious
  // click timeouts on unrelated elements. The app already honors
  // prefers-reduced-motion to turn these off; the context-level
  // `reducedMotion: 'reduce'` playwright.config.js option doesn't reliably
  // propagate to matchMedia in this Chromium build, so emulate it directly.
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/demo/select-role');
  await page.getByRole('button', { name: new RegExp(`Khám phá vai trò ${roleName}`, 'i') }).click();
  await page.waitForURL(/\/(student|instructor|admin)(\/|$)/, { timeout: 15000 });
  await page.getByRole('button', { name: 'Đăng xuất' }).waitFor({ state: 'visible' });
}
