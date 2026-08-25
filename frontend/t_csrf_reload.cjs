const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });

  let meBody = null;
  page.on('response', async (r) => {
    if (r.url().endsWith('/auth/me') && r.request().method() === 'GET') {
      try { meBody = await r.text(); } catch {}
    }
  });

  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);

  // Full reload - simulates a fresh page load with only cookies persisted (in-memory JS state wiped)
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(2000);
  console.log('me body after reload:', meBody);

  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  const [response] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/plans/timetable/blocks') && r.request().method() === 'POST'),
    (async () => {
      await page.locator('button:has-text("Thêm tự học")').click();
      await page.waitForTimeout(400);
      await page.locator('input[placeholder="Tự học"]').fill('Post-reload CSRF check');
      await page.locator('button:has-text("Lưu")').click();
    })(),
  ]);
  console.log('post-reload create-block status:', response.status());
  await browser.close();
})();
