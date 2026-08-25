const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('response', r => {
    const u = r.url();
    if (r.status() >= 400 && !u.includes('/auth/me') && !u.includes('/auth/refresh') && !u.includes('/plans/weekly')) {
      errors.push(`HTTP ${r.status()} ${r.request().method()} ${u}`);
    }
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  console.log('logged in, url:', page.url());
  await page.screenshot({ path: 'p1_overview.png', fullPage: true });

  // Test: generate plan (the original CSRF-broken action)
  await page.getByText('Kế hoạch tuần', { exact: false }).first().click();
  await page.waitForTimeout(1500);
  await page.locator('#plan-goal').fill('Kiểm tra CSRF fix trên production');
  const [genResp] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/plans/generate')),
    page.locator('button:has-text("Tạo kế hoạch nháp")').click(),
  ]);
  console.log('generate plan status:', genResp.status());
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'p2_plan_generated.png', fullPage: true });
  console.log('url after generate:', page.url());

  console.log('=== errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
