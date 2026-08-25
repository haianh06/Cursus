const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('dialog', async d => { await d.accept(); });
  page.on('request', req => {
    console.log('>> REQ', req.method(), req.url());
  });
  page.on('response', async r => {
    console.log('<< RES', r.status(), r.request().method(), r.url());
  });
  page.on('requestfinished', req => {
    console.log('== FINISHED', req.method(), req.url());
  });
  page.on('requestfailed', req => {
    console.log('!! FAILED', req.method(), req.url(), req.failure()?.errorText);
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2500);
  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2500);

  const block = page.locator('div[title="Tự học"]').first();
  if (await block.count() === 0) { console.log('no block'); await browser.close(); return; }
  await block.click({ force: true });
  await page.waitForTimeout(600);
  console.log('=== clicking Xoá ===');
  await page.locator('button', { hasText: /^Xoá$/ }).first().click();
  await page.waitForTimeout(3000);
  console.log('=== done ===');

  await browser.close();
})();
