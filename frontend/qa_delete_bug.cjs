const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('dialog', async d => { console.log('DIALOG:', d.type(), d.message()); await d.accept(); });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/plans/timetable/blocks')) {
      let body = null;
      try { body = await r.text(); } catch {}
      console.log(`${r.status()} ${r.request().method()} ${u}  body=${body}`);
    }
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2500);

  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2500);

  const block = page.locator('div[title="Tự học"]').first();
  const count = await block.count();
  console.log('Tự học blocks found:', count);
  if (count === 0) {
    console.log('no self-study block found on this week; aborting');
    await browser.close();
    return;
  }
  await block.click({ force: true });
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'qa_delete_shots/before_delete.png', fullPage: true });

  await page.locator('button', { hasText: /^Xoá$/ }).first().click();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'qa_delete_shots/after_delete.png', fullPage: true });

  await browser.close();
})();
