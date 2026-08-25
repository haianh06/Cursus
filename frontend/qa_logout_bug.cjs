const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/auth/logout') || u.includes('/auth/me') || u.includes('/auth/refresh')) {
      const setCookie = r.headers()['set-cookie'];
      console.log(`${r.status()} ${r.request().method()} ${u}${setCookie ? '  Set-Cookie: ' + setCookie : ''}`);
    }
  });

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  console.log('--- logged in, url:', page.url());

  const cookiesBefore = await page.context().cookies();
  console.log('--- cookies before logout:', cookiesBefore.map(c => c.name));

  await page.locator('button', { hasText: /Đăng xuất/ }).first().click();
  await page.waitForTimeout(1500);
  console.log('--- after logout click, url:', page.url());

  const cookiesAfter = await page.context().cookies();
  console.log('--- cookies after logout:', cookiesAfter.map(c => `${c.name}=${c.value.slice(0,10)}`));

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(2000);
  console.log('--- after reload, url:', page.url());
  await page.screenshot({ path: 'qa_csrf_shots/after_logout_reload.png', fullPage: true });

  await browser.close();
})();
