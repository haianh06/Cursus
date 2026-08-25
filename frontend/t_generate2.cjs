const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('response', async r => {
    if (r.url().includes('/plans/generate')) {
      let body = '';
      try { body = await r.text(); } catch (e) { body = '(no body: ' + e.message + ')'; }
      console.log('RESPONSE', r.status(), r.url());
      console.log('BODY:', body);
    }
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.getByText('Kế hoạch tuần', { exact: false }).first().click();
  await page.waitForTimeout(1500);

  await page.locator('#plan-goal').fill('Hoàn thành phần 1 đồ án SSA101');
  await page.locator('button:has-text("Tạo kế hoạch nháp")').click();
  await page.waitForTimeout(4000);
  console.log('final url:', page.url());
  await browser.close();
})();
