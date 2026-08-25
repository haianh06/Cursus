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
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'qa_shots/01_overview.png', fullPage: true });

  // Overview: hover/open notifications
  await page.locator('button:has(svg)').filter({ hasText: '' }).first();
  const bell = page.locator('[class*="cursor-pointer"]').filter({ has: page.locator('svg') });
  await page.mouse.move(1140, 27);
  await page.locator('header, [class*="topbar"], div').first();
  // click bell icon area (approx position from earlier screenshots)
  await page.locator('svg').nth(2).click({ force: true }).catch(() => {});
  await page.waitForTimeout(600);
  await page.screenshot({ path: 'qa_shots/02_overview_notifications.png', fullPage: true });
  await page.keyboard.press('Escape').catch(() => {});

  // Weekly plan full flow
  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1800);
  await page.screenshot({ path: 'qa_shots/03_planner_initial.png', fullPage: true });

  await page.locator('#plan-goal').fill('QA pass: hoan thanh phan 1 do an SSA101');
  const genBtn = page.locator('button', { hasText: /Tạo kế hoạch nháp|Tạo lại kế hoạch/ });
  const [genResp] = await Promise.all([
    page.waitForResponse(r => r.url().includes('/plans/generate')).catch(() => null),
    genBtn.click(),
  ]);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: 'qa_shots/04_planner_generated.png', fullPage: true });
  console.log('generate status:', genResp?.status());

  // Today's Plan
  await page.goto('https://cursus-mu.vercel.app/student/today', { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'qa_shots/05_today.png', fullPage: true });

  // switch to week view on Today's plan to see more
  const weekBtn = page.locator('button:has-text("Tuần")').first();
  if (await weekBtn.count() > 0) {
    await weekBtn.click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: 'qa_shots/06_today_week_view.png', fullPage: true });
  }

  console.log('=== errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
