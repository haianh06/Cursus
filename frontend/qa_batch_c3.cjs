const { chromium } = require('playwright');

function fmt(d) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

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

  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2000);

  const now = new Date();
  const start = new Date(now.getTime() + 1 * 60000);
  const end = new Date(now.getTime() + 40 * 60000);

  const addBtn = page.locator('button', { hasText: /Thêm tự học/ }).first();
  await addBtn.click();
  await page.waitForTimeout(400);
  const inputs = page.locator('input[type="datetime-local"]');
  await inputs.nth(0).fill(fmt(start));
  await inputs.nth(1).fill(fmt(end));
  await page.screenshot({ path: 'qa_shots/20_selfstudy_create_filled.png', fullPage: true });
  const saveBtn = page.locator('button', { hasText: /^Lưu$/ }).first();
  await saveBtn.click();
  await page.waitForTimeout(1200);

  const block = page.locator('div[title="Tự học"]').last();
  if (await block.count() > 0) {
    await block.click({ force: true });
    await page.waitForTimeout(600);
    const startBtn = page.locator('button', { hasText: /Bắt đầu tự học/ }).first();
    if (await startBtn.count() > 0) {
      await startBtn.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'qa_shots/21_selfstudy_active.png', fullPage: true });
    } else {
      console.log('start button not found');
      await page.screenshot({ path: 'qa_shots/21_selfstudy_modal_debug.png', fullPage: true });
    }
  } else {
    console.log('block not found');
  }

  console.log('=== errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
