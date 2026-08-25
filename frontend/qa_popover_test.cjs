const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 700 } });

  await page.goto('http://localhost:5173/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1200);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  // Scroll the timetable down a bit so a block near the bottom of the page is clicked
  const block = page.locator('div[title]').filter({ hasText: 'Lecture' }).first();
  await block.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  await block.click({ force: true });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'qa_popover_shots/edit_popover.png', fullPage: false });

  await page.keyboard.press('Escape').catch(() => {});
  await page.locator('button[aria-label="prev"]').first().click().catch(() => {});

  // Test the "Thêm tự học" cell-click flow near the bottom of a short viewport
  await page.mouse.click(700, 650);
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'qa_popover_shots/create_popover.png', fullPage: false });

  await browser.close();
})();
