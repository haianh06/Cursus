const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1500);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2500);
  await page.goto('https://cursus-mu.vercel.app/student/planner', { waitUntil: 'load' });
  await page.waitForTimeout(2500);

  const cookies = await page.context().cookies();
  const info = await page.evaluate(async () => {
    const meRes = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/auth/me', { credentials: 'include' });
    const me = await meRes.json();
    const weekRes = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/plans/timetable?week_start=2026-08-24', { credentials: 'include' });
    const week = await weekRes.json();
    const selfStudyBlock = (week.blocks || []).find(b => (b.title || '').toLowerCase().includes('tự học') || (b.title || '').toLowerCase().includes('tu hoc'));
    return { csrf: me.csrf_token, blockId: selfStudyBlock ? selfStudyBlock.id : null };
  });

  console.log('CSRF:', info.csrf);
  console.log('BLOCK_ID:', info.blockId);
  console.log('COOKIE_HEADER:', cookies.map(c => `${c.name}=${c.value}`).join('; '));

  await browser.close();
})();
