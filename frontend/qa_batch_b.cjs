const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1300 } });
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

  // Reflection
  await page.goto('https://cursus-mu.vercel.app/student/reflection', { waitUntil: 'load' });
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'qa_shots/07_reflection_questions.png', fullPage: true });

  const q1 = page.locator('button', { hasText: 'Hoàn thành phần lớn' });
  if (await q1.count() > 0) {
    await q1.click();
    await page.getByText('Khá tập trung phần lớn thời gian', { exact: true }).click();
    await page.getByText('Hơi căng thẳng nhưng vẫn ổn', { exact: true }).click();
    await page.getByText('Quản lý khá tốt, ít bị dồn', { exact: true }).click();
    await page.getByText('Động lực khá tốt', { exact: true }).click();
    await page.locator('textarea').first().fill('QA pass ghi chu tu do.');
    await page.locator('button:has-text("Xem trước bản ghi nhớ")').click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: 'qa_shots/08_reflection_memory.png', fullPage: true });
  } else {
    console.log('reflection already confirmed for this week, screenshotting current state');
  }

  // Practice
  await page.goto('https://cursus-mu.vercel.app/student/practice', { waitUntil: 'load' });
  await page.waitForTimeout(2200);
  await page.screenshot({ path: 'qa_shots/09_practice.png', fullPage: true });

  // Try requesting a practice set (mutation test + loading/result state)
  const reqBtn = page.locator('button', { hasText: 'Yêu cầu bộ luyện tập' }).first();
  if (await reqBtn.count() > 0) {
    await reqBtn.click();
    await page.waitForTimeout(1000);
    await page.screenshot({ path: 'qa_shots/10_practice_loading.png', fullPage: true });
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'qa_shots/11_practice_result.png', fullPage: true });
  }

  // Settings
  await page.goto('https://cursus-mu.vercel.app/student/settings', { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'qa_shots/12_settings.png', fullPage: true });

  console.log('=== errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
