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
  const moonBtn = page.locator('svg.lucide-moon, svg.lucide-sun').first();
  if (await moonBtn.count()) { await moonBtn.click({ force: true }); await page.waitForTimeout(400); }
  const cls = await page.evaluate(() => document.documentElement.className);
  console.log('html class:', cls);
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  const cls2 = await page.evaluate(() => document.documentElement.className);
  console.log('html class after nav:', cls2);
  const block = page.locator('.absolute.rounded-md.border', { hasText: 'CSI106 Lecture' }).first();
  console.log('block count:', await block.count());
  if (await block.count()) {
    const info = await block.evaluate((el) => {
      const s = getComputedStyle(el);
      return { bg: s.backgroundColor, border: s.borderColor, color: s.color, cls: el.className };
    });
    console.log(JSON.stringify(info, null, 2));
  }
  await browser.close();
})();
