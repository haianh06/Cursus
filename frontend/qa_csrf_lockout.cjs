const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('response', r => {
    const u = r.url();
    if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.request().method()} ${u}`);
  });

  // Land on the site once so the cookie domain/path exist, then plant a
  // stale/invalid refresh_token + access_token cookie -- simulating a
  // browser that has a dead session from before (the exact scenario the
  // user hit: fresh page load, no in-memory CSRF token yet, but a bad
  // cookie already present).
  await page.goto('http://localhost:5173/', { waitUntil: 'load' });
  await page.context().addCookies([
    { name: 'refresh_token', value: 'not-a-real-jwt', domain: 'localhost', path: '/' },
    { name: 'access_token', value: 'not-a-real-jwt', domain: 'localhost', path: '/' },
  ]);

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'qa_csrf_shots/after_stale_cookie.png', fullPage: true });

  const url = page.url();
  console.log('final URL:', url);
  console.log('=== 4xx/5xx responses ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
