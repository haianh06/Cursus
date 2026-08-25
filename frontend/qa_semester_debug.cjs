const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push('CONSOLE: ' + msg.text()); });
  page.on('response', async r => {
    const u = r.url();
    if (u.includes('/api/')) {
      console.log(r.status(), r.request().method(), u);
    }
  });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);

  await page.goto('https://cursus-mu.vercel.app/student/semester-setup', { waitUntil: 'load' });
  await page.waitForTimeout(5000);
  await page.screenshot({ path: 'qa_shots/14b_semester_setup_wait5s.png', fullPage: true });

  console.log('=== page errors ===');
  console.log(errors.join('\n') || '(none)');
  await browser.close();
})();
