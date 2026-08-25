const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const mutResults = [];

  page.on('response', async (r) => {
    const method = r.request().method();
    if (method === 'POST' || method === 'PATCH' || method === 'DELETE' || method === 'PUT') {
      mutResults.push(`${method} ${r.status()} ${r.url()}`);
    }
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.getByText('Kế hoạch tuần', { exact: false }).first().click();
  await page.waitForTimeout(1500);

  // Try "Thêm tự học" (create timetable block) - separate mutation endpoint
  await page.locator('button:has-text("Thêm tự học")').click();
  await page.waitForTimeout(500);
  await page.locator('input[placeholder="Tự học"]').fill('Test CSRF block');
  await page.locator('button:has-text("Lưu")').click();
  await page.waitForTimeout(2000);
  console.log('after add self-study, url:', page.url());
  console.log(mutResults.join('\n'));
  await browser.close();
})();
