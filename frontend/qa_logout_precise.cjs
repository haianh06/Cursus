const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/auth/logout') || u.includes('/auth/me') || u.includes('/auth/refresh') || u.includes('/auth/demo-session')) {
      console.log(`${r.status()} ${r.request().method()} ${u}`);
    }
  });

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);

  const matches = await page.locator('text=Đăng xuất').count();
  console.log('number of "Đăng xuất" matches on page:', matches);
  const logoutBtnCount = await page.locator('#logout-btn').count();
  console.log('#logout-btn count:', logoutBtnCount);

  await page.locator('#logout-btn').first().click();
  await page.waitForTimeout(1500);
  console.log('--- after #logout-btn click, url:', page.url());

  await page.reload({ waitUntil: 'load' });
  await page.waitForTimeout(2000);
  console.log('--- after reload, url:', page.url());
  await page.screenshot({ path: 'qa_csrf_shots/logout_precise.png', fullPage: true });

  await browser.close();
})();
