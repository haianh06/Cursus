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

  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2000);

  const existingBlock = page.locator('div[title="Tự học"]').first();
  if (await existingBlock.count() === 0) {
    const addBtn = page.locator('button', { hasText: /Thêm tự học/ }).first();
    await addBtn.click();
    await page.waitForTimeout(400);
    const saveBtn = page.locator('button', { hasText: /^Lưu$/ }).first();
    await saveBtn.click();
    await page.waitForTimeout(1200);
  }

  await page.screenshot({ path: 'qa_shots/17_selfstudy_created.png', fullPage: true });

  const block = page.locator('div[title="Tự học"]').first();
  console.log('block count:', await block.count());
  if (await block.count() > 0) {
    await block.click({ force: true });
    await page.waitForTimeout(600);
    await page.screenshot({ path: 'qa_shots/18_selfstudy_edit_modal.png', fullPage: true });
    const startBtn = page.locator('button', { hasText: /Bắt đầu tự học/ }).first();
    console.log('start btn count:', await startBtn.count());
    if (await startBtn.count() > 0) {
      await startBtn.click();
      await page.waitForTimeout(2000);
      await page.screenshot({ path: 'qa_shots/19_selfstudy_session.png', fullPage: true });
    }
  }

  console.log('=== errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
