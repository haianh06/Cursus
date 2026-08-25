const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  page.on('response', async r => {
    if (r.url().includes('/plans/timetable/blocks/sb_41f8d807a7')) console.log('RES', r.status());
  });
  page.on('requestfailed', req => {
    if (req.url().includes('/plans/timetable/blocks/sb_41f8d807a7')) console.log('FAILED', req.failure()?.errorText);
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2500);
  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2500);

  const info = await page.evaluate(async () => {
    const meRes = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/auth/me', { credentials: 'include' });
    const me = await meRes.json();
    try {
      const res = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/plans/timetable/blocks/sb_41f8d807a7', {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'X-CSRF-Token': me.csrf_token },
      });
      return { status: res.status };
    } catch (e) {
      return { error: e.message };
    }
  });
  console.log('specific fresh block delete result:', JSON.stringify(info));

  await browser.close();
})();
