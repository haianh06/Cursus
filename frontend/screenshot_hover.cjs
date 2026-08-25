const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2500);
  const chart = page.locator('svg[aria-label*="ngày"]').first();
  const box = await chart.boundingBox();
  // hover over the peak (Th 6, ~5th of 7 points)
  await page.mouse.move(box.x + box.width * (4.5/6), box.y + box.height * 0.5);
  await page.waitForTimeout(400);
  await page.screenshot({ path: 'hover.png', clip: { x: box.x - 20, y: box.y - 40, width: box.width + 40, height: box.height + 80 } });
  await browser.close();
})();
