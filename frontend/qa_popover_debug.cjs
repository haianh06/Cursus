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

  const block = page.locator('div[title="Tự học"]').first();
  const count = await block.count();
  console.log('existing Tự học blocks:', count);
  if (count === 0) { console.log('none found'); await browser.close(); return; }
  const box = await block.boundingBox();
  console.log('block box:', box);
  await block.click({ force: true, position: { x: 5, y: 5 } });
  await page.waitForTimeout(500);

  const panelInfo = await page.evaluate(() => {
    const panels = [...document.querySelectorAll('.card.p-5.space-y-3.absolute')];
    return panels.map(p => ({ top: p.style.top, left: p.style.left, rect: p.getBoundingClientRect() }));
  });
  console.log('panel style/rect:', JSON.stringify(panelInfo));
  console.log('window size:', await page.evaluate(() => ({ w: window.innerWidth, h: window.innerHeight })));

  await page.screenshot({ path: 'qa_popover_shots/debug.png', fullPage: false });
  await browser.close();
})();
