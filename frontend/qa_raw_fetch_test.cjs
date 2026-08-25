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
      });
      return { ok: true, status: res.status, headers: [...res.headers.entries()] };
    } catch (e) {
      return { ok: false, error: e.message, name: e.name };
    }
  });
  console.log('raw fetch DELETE result:', JSON.stringify(result, null, 2));

  const getResult = await page.evaluate(async () => {
    try {
      const res = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/auth/me', { credentials: 'include' });
      return { ok: true, status: res.status };
    } catch (e) {
      return { ok: false, error: e.message };
    }
  });
  console.log('raw fetch GET /auth/me result:', JSON.stringify(getResult));

  await browser.close();
})();
