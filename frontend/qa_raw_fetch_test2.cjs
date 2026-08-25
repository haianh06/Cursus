const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2500);

  const result = await page.evaluate(async () => {
    try {
      const res = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/plans/timetable/blocks/sb_nonexistent', {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'X-CSRF-Token': 'fake-value-abc' },
      });
      return { ok: true, status: res.status };
    } catch (e) {
      return { ok: false, error: e.message, name: e.name };
    }
  });
  console.log('with fake X-CSRF-Token:', JSON.stringify(result));

  await browser.close();
})();
