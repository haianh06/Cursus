const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('response', r => { if (r.status() >= 400) errors.push(`HTTP ${r.status()} ${r.request().method()} ${r.url()}`); });

  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);

  await page.goto('http://localhost:5173/student/reflection', { waitUntil: 'load' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'r1_questions.png', fullPage: true });
  console.log('errors after load:', errors.join('\n') || '(none)');
  await browser.close();
})();
