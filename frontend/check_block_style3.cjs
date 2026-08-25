const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(1500);
  await page.locator('#theme-toggle').click();
  await page.waitForTimeout(400);
  console.log('html class:', await page.evaluate(() => document.documentElement.className));
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  console.log('html class after nav:', await page.evaluate(() => document.documentElement.className));
  const block = page.locator('.absolute.rounded-md.border', { hasText: 'CSI106 Lecture' }).first();
  if (await block.count()) {
    const info = await block.evaluate((el) => {
      const s = getComputedStyle(el);
      const parent = el.closest('.card');
      const parentBg = parent ? getComputedStyle(parent).backgroundColor : null;
      return { bg: s.backgroundColor, border: s.borderColor, color: s.color, parentBg };
    });
    console.log(JSON.stringify(info, null, 2));
  }
  await page.screenshot({ path: 'shots/16_dark_planner_confirmed.png', fullPage: true });
  await browser.close();
})();
