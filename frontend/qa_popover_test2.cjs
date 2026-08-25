const { chromium } = require('playwright');
function fmt(d) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 700 } });

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  // Create a self-study block near the bottom of the visible calendar area
  await page.locator('button', { hasText: /Thêm tự học/ }).first().click();
  await page.waitForTimeout(400);
  const now = new Date();
  const start = new Date(now.getTime() + 60 * 60000);
  const end = new Date(now.getTime() + 90 * 60000);
  const inputs = page.locator('input[type="datetime-local"]');
  await inputs.nth(0).fill(fmt(start));
  await inputs.nth(1).fill(fmt(end));
  await page.locator('button', { hasText: /^Lưu$/ }).first().click();
  await page.waitForTimeout(1200);

  const block = page.locator('div[title="Tự học"]').last();
  await block.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const box = await block.boundingBox();
  console.log('block position:', box);
  await block.click({ force: true, position: { x: 5, y: 5 } });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'qa_popover_shots/edit_popover2.png', fullPage: false });

  await browser.close();
})();
