const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/auth/')) {
      let body = null;
      try { body = await r.json(); } catch {}
      console.log(`${r.status()} ${r.request().method()} ${u}${body?.is_demo !== undefined ? '  is_demo=' + body.is_demo : ''}`);
    }
  });

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(3000);
  console.log('=== settled at:', page.url());

  await page.locator('#logout-btn').first().click();
  await page.waitForTimeout(1500);
  console.log('=== after logout click:', page.url());
  await browser.close();
})();
