const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  let loginBody = null;
  page.on('response', async (r) => {
    if (r.url().endsWith('/auth/login') && r.request().method() === 'POST') {
      try { loginBody = await r.text(); } catch {}
    }
  });

  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);

  console.log('login response body:', loginBody);

  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  const [response] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/plans/timetable/blocks') && r.request().method() === 'POST'),
    (async () => {
      await page.locator('button:has-text("Thêm tự học")').click();
      await page.waitForTimeout(400);
      await page.locator('input[placeholder="Tự học"]').fill('CSRF fix verification block');
      await page.locator('button:has-text("Lưu")').click();
    })(),
  ]);
  console.log('create-block status:', response.status());
  console.log('create-block body:', await response.text());
  console.log('final url:', page.url());
  console.log('errors:', errors.join('\n') || '(none)');
  await browser.close();
})();
