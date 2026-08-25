const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('response', r => { if (r.status() >= 400 && !r.url().includes('/auth/me') && !r.url().includes('/auth/refresh') && !r.url().includes('/plans/weekly')) errors.push(`HTTP ${r.status()} ${r.url()}`); });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.getByText('Kế hoạch tuần', { exact: false }).first().click();
  await page.waitForTimeout(1500);

  await page.locator('#plan-goal').fill('Hoàn thành phần 1 đồ án SSA101');
  await page.locator('button:has-text("Tạo kế hoạch nháp")').click();
  console.log('waiting for AI plan generation (real Gemini call)...');
  await page.waitForSelector('text=Kế hoạch đề xuất', { timeout: 45000 }).catch((e) => console.log('TIMEOUT waiting for plan:', e.message));
  await page.waitForTimeout(500);
  await page.screenshot({ path: 't_04_plan_generated.png', fullPage: true });
  console.log(errors.join('\n') || '(no unexpected errors)');
  await browser.close();
})();
