const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/auth/logout') || u.includes('/auth/me') || u.includes('/auth/refresh')) {
      console.log(`${r.status()} ${r.request().method()} ${u}`);
    }
  });

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);

  // Click logout and reload IMMEDIATELY, without waiting for the logout
  // request to finish -- simulating an impatient user hitting refresh
  // right after clicking logout.
  await page.locator('button', { hasText: /Đăng xuất/ }).first().click();
  await page.waitForTimeout(30); // barely any time for the request to land
  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(2000);
  console.log('--- after race reload, url:', page.url());
  const cookiesAfter = await page.context().cookies();
  console.log('--- cookies after race:', cookiesAfter.map(c => c.name));
  await page.screenshot({ path: 'qa_csrf_shots/logout_race.png', fullPage: true });

  await browser.close();
})();
