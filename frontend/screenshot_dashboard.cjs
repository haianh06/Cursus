const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  page.on('console', msg => console.log('CONSOLE', msg.type(), msg.text()));
  page.on('pageerror', err => console.log('PAGEERROR', err.message));
  await page.goto('http://localhost:5173/login', { waitUntil: 'networkidle' });
  await page.waitForTimeout(500);
  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  await emailInput.fill('admin@example.com');
  const passInput = page.locator('input[type="password"]').first();
  await passInput.fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'after_login.png', fullPage: true });
  console.log('url after login', page.url());
  await browser.close();
})();
