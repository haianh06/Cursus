const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  let meResponse = null;
  page.on('response', async r => {
    if (r.url().includes('/auth/me') && r.status() === 200) {
      meResponse = await r.json().catch(() => null);
    }
  });
  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  console.log('me response is_demo:', meResponse ? meResponse.is_demo : 'no /auth/me captured');
  console.log('full me response:', JSON.stringify(meResponse));
  await browser.close();
})();
