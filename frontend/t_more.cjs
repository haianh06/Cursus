const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
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

  // topbar avatar dropdown
  await page.locator('button:has-text("Demo Student"), [class*="cursor-pointer"]:has-text("Demo Student")').first().click({ timeout: 5000 }).catch(async () => {
    // fallback: click the avatar circle "D"
    await page.locator('text="D"').first().click().catch(() => {});
  });
  await page.waitForTimeout(600);
  await page.screenshot({ path: 't_09_avatar_menu.png' });

  // direct navigate settings
  await page.goto('https://cursus-mu.vercel.app/student/settings', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 't_10_settings.png', fullPage: true });

  // dark mode toggle
  await page.locator('button[aria-label*="theme" i], button:has(svg)').first();
  await page.locator('svg').first();
  await page.goto('https://cursus-mu.vercel.app/student', { waitUntil: 'load' });
  await page.waitForTimeout(1000);
  const themeBtn = page.locator('header button, nav button').filter({ has: page.locator('svg') });
  await page.locator('[class*="header"] button, header button').nth(1).click().catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: 't_11_darkmode.png' });

  // EN toggle
  await page.getByText('EN', { exact: true }).first().click().catch(() => {});
  await page.waitForTimeout(800);
  await page.screenshot({ path: 't_12_english.png' });

  // direct URLs not in sidebar
  for (const path of ['/student/lecture-plan', '/student/semester-setup', '/student/companion']) {
    await page.goto('https://cursus-mu.vercel.app' + path, { waitUntil: 'load' }).catch(e => errors.push('NAV FAIL ' + path + ': ' + e.message));
    await page.waitForTimeout(1500);
    await page.screenshot({ path: 't_13_' + path.replace(/\//g, '_') + '.png', fullPage: true });
  }

  console.log('=== errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
