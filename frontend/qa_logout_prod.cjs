const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/auth/')) {
      console.log(`${r.status()} ${r.request().method()} ${u}`);
    }
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForLoadState('networkidle').catch(() => {});
  await page.waitForTimeout(3000);
  console.log('=== settled at:', page.url());

  const cookiesBefore = await page.context().cookies();
  console.log('cookies before logout:', cookiesBefore.map(c => c.name));

  await page.locator('#logout-btn').first().click();
  await page.waitForTimeout(2500);
  console.log('=== after logout click:', page.url());
  await page.screenshot({ path: 'qa_csrf_shots/prod_after_logout.png', fullPage: true });

  const cookiesAfter = await page.context().cookies();
  console.log('cookies after logout:', cookiesAfter.map(c => c.name));

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(3000);
  console.log('=== after reload:', page.url());
  await page.screenshot({ path: 'qa_csrf_shots/prod_after_reload.png', fullPage: true });

  await browser.close();
})();
