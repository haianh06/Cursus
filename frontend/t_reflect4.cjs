const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1300 } });
  page.on('console', m => console.log('CONSOLE', m.type(), m.text()));
  page.on('pageerror', e => console.log('PAGEERROR', e.message));
  page.on('requestfailed', r => console.log('REQFAILED', r.url(), r.failure()?.errorText));

  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/reflection', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  await page.getByText('Hoàn thành một phần nhỏ', { exact: true }).click();
  const btn = page.locator('button:has-text("Xem trước bản ghi nhớ")');
  console.log('button count:', await btn.count());
  console.log('button disabled?', await btn.first().isDisabled());
  await btn.first().click();
  await page.waitForTimeout(2000);
  const errBanner = await page.locator('[role="alert"]').textContent().catch(() => null);
  console.log('alert banner:', errBanner);
  await browser.close();
})();
