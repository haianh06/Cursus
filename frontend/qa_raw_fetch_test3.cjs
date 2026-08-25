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

  const blockId = await page.evaluate(() => {
    const el = document.querySelector('div[title="Tự học"]');
    return el ? el.closest('[key]')?.getAttribute('key') : null;
  });

  // React doesn't expose block id via DOM directly; grab it from a GET call instead
  const result = await page.evaluate(async () => {
    const meRes = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/auth/me', { credentials: 'include' });
    const me = await meRes.json();
    const csrf = me.csrf_token;

    const weekRes = await fetch('https://cursus-backend-53yc.onrender.com/api/v1/plans/timetable?week_start=2026-08-24', { credentials: 'include' });
    const week = await weekRes.json();
    const selfStudyBlock = (week.blocks || []).find(b => b.title === 'Tự học' || (b.title || '').toLowerCase().includes('tự học'));
    if (!selfStudyBlock) return { error: 'no self-study block found', sample: (week.blocks || []).slice(0,3) };

    try {
      const res = await fetch(`https://cursus-backend-53yc.onrender.com/api/v1/plans/timetable/blocks/${selfStudyBlock.id}`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'X-CSRF-Token': csrf },
      });
      const text = await res.text().catch(() => '');
      return { ok: true, status: res.status, body: text, blockId: selfStudyBlock.id };
    } catch (e) {
      return { ok: false, error: e.message, name: e.name, blockId: selfStudyBlock.id };
    }
  });
  console.log('REAL delete attempt:', JSON.stringify(result, null, 2));

  await browser.close();
})();
