const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2000);
  await page.mouse.wheel(0, 500);
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'layout_scrolled_page.png' });
  // now scroll INSIDE the right column specifically
  const rightCol = page.locator('aside, div').filter({ hasText: 'Kế hoạch đề xuất' }).first();
  await page.mouse.move(1300, 500);
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(300);
  await page.screenshot({ path: 'layout_scrolled_rightcol.png' });
  await browser.close();
})();
