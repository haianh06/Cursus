const { chromium } = require('playwright');
function fmt(d) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('dialog', async d => { await d.accept(); });
  page.on('response', async r => {
    if (r.url().includes('/plans/timetable/blocks')) console.log('RES', r.status(), r.request().method(), r.url());
  });
  page.on('requestfailed', req => {
    if (req.url().includes('/plans/timetable/blocks')) console.log('FAILED', req.method(), req.url(), req.failure()?.errorText);
  });

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  const now = new Date();
  const start = new Date(now.getTime() + 60 * 60000);
  const end = new Date(now.getTime() + 90 * 60000);
  await page.locator('button', { hasText: /Thêm tự học/ }).first().click();
  await page.waitForTimeout(400);
  const inputs = page.locator('input[type="datetime-local"]');
  await inputs.nth(0).fill(fmt(start));
  await inputs.nth(1).fill(fmt(end));
  await page.locator('button', { hasText: /^Lưu$/ }).first().click();
  await page.waitForTimeout(1200);

  const block = page.locator('div[title="Tự học"]').last();
  await block.click({ force: true });
  await page.waitForTimeout(500);
  await page.locator('button', { hasText: /^Xoá$/ }).first().click();
  await page.waitForTimeout(2000);

  await browser.close();
})();
