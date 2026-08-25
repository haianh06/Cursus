const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  await page.route('**/plans/generate', async (route) => {
    const response = await route.fetch();
    const body = await response.text();
    console.log('INTERCEPTED status', response.status());
    console.log('INTERCEPTED body', body);
    await route.fulfill({ response, body });
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.getByText('Kế hoạch tuần', { exact: false }).first().click();
  await page.waitForTimeout(1500);

  await page.locator('#plan-goal').fill('Hoàn thành phần 1 đồ án SSA101');
  await page.locator('button:has-text("Tạo kế hoạch nháp")').click();
  await page.waitForTimeout(3000);
  await browser.close();
})();
