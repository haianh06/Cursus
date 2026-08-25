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

  // Lecture-based plan (not in sidebar)
  await page.goto('https://cursus-mu.vercel.app/student/lecture-plan', { waitUntil: 'load' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'qa_shots/13_lecture_plan.png', fullPage: true });

  // Semester setup wizard (not in sidebar)
  await page.goto('https://cursus-mu.vercel.app/student/semester-setup', { waitUntil: 'load' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'qa_shots/14_semester_setup.png', fullPage: true });

  // Self-study Pomodoro session — reached by creating a self-study block on
  // the Timetable (Planner page) then starting it.
  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2000);
  const addBtn = page.locator('button', { hasText: /Thêm tự học/ }).first();
  if (await addBtn.count() > 0) {
    await addBtn.click();
    await page.waitForTimeout(500);
    await page.screenshot({ path: 'qa_shots/15_selfstudy_create_modal.png', fullPage: true });
    const saveBtn = page.locator('button', { hasText: /^Lưu$/ }).first();
    if (await saveBtn.count() > 0) {
      await saveBtn.click();
      await page.waitForTimeout(1200);
    }
    // Click the newly created self-study block to reopen the modal, then start it.
    const block = page.locator('text=Tự học').first();
    if (await block.count() > 0) {
      await block.click();
      await page.waitForTimeout(500);
      const startBtn = page.locator('button', { hasText: /Bắt đầu tự học/ }).first();
      if (await startBtn.count() > 0) {
        await startBtn.click();
        await page.waitForTimeout(2000);
        await page.screenshot({ path: 'qa_shots/16_selfstudy_session.png', fullPage: true });
      } else {
        console.log('start button not found after opening block modal');
        await page.screenshot({ path: 'qa_shots/16_selfstudy_block_modal.png', fullPage: true });
      }
    } else {
      console.log('created self-study block not found on calendar');
    }
  } else {
    console.log('Add self-study button not found on planner page');
  }

  console.log('=== errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
