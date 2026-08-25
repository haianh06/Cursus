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

  const block = page.locator('div[title="Tự học"]').first();
  await block.scrollIntoViewIfNeeded();
  await page.waitForTimeout(300);
  const box = await block.boundingBox();
  console.log('block box (after scroll into view):', box);
  await block.click();
  await page.waitForTimeout(500);

  const panelInfo = await page.evaluate(() => {
    const panels = [...document.querySelectorAll('.card.p-5.space-y-3.absolute')];
    return panels.map(p => p.getBoundingClientRect());
  });
  console.log('panel rect:', JSON.stringify(panelInfo));
  await page.screenshot({ path: 'qa_popover_shots/debug2.png', fullPage: false });
  await browser.close();
})();
