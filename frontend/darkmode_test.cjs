const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);
  const moonBtn = page.locator('svg.lucide-moon, svg.lucide-sun').first();
  console.log('moon/sun icon found:', await moonBtn.count());
  if (await moonBtn.count()) {
    await moonBtn.click({ force: true });
    await page.waitForTimeout(500);
  }
  await page.screenshot({ path: 'shots/14_dark_mode.png', fullPage: true });
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'shots/15_dark_planner.png', fullPage: true });
  console.log('errors:', errors.length, errors.join(' | '));
  await browser.close();
})();
