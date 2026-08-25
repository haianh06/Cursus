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

  const info = await page.evaluate(() => {
    const results = [];
    let el = document.querySelector('.card.p-5') || document.body;
    while (el) {
      const cs = getComputedStyle(el);
      if (cs.transform !== 'none' || cs.perspective !== 'none' || cs.filter !== 'none' || cs.willChange.includes('transform')) {
        results.push({ tag: el.tagName, cls: el.className, transform: cs.transform, filter: cs.filter, willChange: cs.willChange });
      }
      el = el.parentElement;
    }
    return { scrollY: window.scrollY, docScrollHeight: document.documentElement.scrollHeight, transformedAncestors: results };
  });
  console.log(JSON.stringify(info, null, 2));
  await browser.close();
})();
