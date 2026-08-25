const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
  page.on('pageerror', err => console.log('PAGEERROR', err.message));
  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  await page.locator('#plan-goal').fill('Hoàn thành phần 1 đồ án SSA101 và ôn tập các môn còn lại');
  await page.locator('button:has-text("Tạo kế hoạch nháp")').click();
  await page.waitForTimeout(3000);
  await page.screenshot({ path: 'layout_with_plan.png', fullPage: true });
  await browser.close();
})();
