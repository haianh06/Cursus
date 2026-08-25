const { chromium } = require('playwright');
function fmt(d) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  let createdId = null;
  page.on('response', async r => {
    if (r.url().includes('/plans/timetable/blocks') && r.request().method() === 'POST') {
      const body = await r.json().catch(() => null);
      createdId = body?.id;
    }
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2500);
  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2500);

  const now = new Date();
  const start = new Date(now.getTime() + 5 * 60 * 60000);
  const end = new Date(now.getTime() + (5 * 60 + 30) * 60000);
  await page.locator('button', { hasText: /Thêm tự học/ }).first().click();
  await page.waitForTimeout(400);
  const inputs = page.locator('input[type="datetime-local"]');
  await inputs.nth(0).fill(fmt(start));
  await inputs.nth(1).fill(fmt(end));
  await page.locator('button', { hasText: /^Lưu$/ }).first().click();
  await page.waitForTimeout(1500);

  console.log('CREATED_BLOCK_ID:', createdId);
  await browser.close();
})();
