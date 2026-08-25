const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.getByText('Kế hoạch tuần', { exact: false }).first().click();
  await page.waitForTimeout(1500);

  await page.locator('#plan-goal').fill('Hoàn thành phần 1 đồ án SSA101');

  const [response] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/plans/generate')),
    page.locator('button:has-text("Tạo kế hoạch nháp")').click(),
  ]);
  console.log('status', response.status());
  const body = await response.text();
  console.log('body', body);
  await browser.close();
})();
