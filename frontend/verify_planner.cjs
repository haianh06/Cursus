const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });
  page.on('pageerror', err => console.log('PAGEERROR', err.message));
  page.on('console', msg => { if (msg.type() === 'error') console.log('CONSOLE ERROR', msg.text()); });
  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'verify_planner.png', fullPage: true });
  console.log('final url', page.url());
  await browser.close();
})();
