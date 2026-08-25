const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('response', r => { if (r.status() >= 400 && !r.url().includes('/auth/me') && !r.url().includes('/auth/refresh')) errors.push(`HTTP ${r.status()} ${r.url()}`); });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);

  await page.getByText('Kế hoạch tuần', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 't_03_planner.png', fullPage: true });
  console.log('URL:', page.url());
  console.log(errors.join('\n') || '(no unexpected errors)');
  await browser.close();
})();
