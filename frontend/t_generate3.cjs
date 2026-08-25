const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });

  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);

  const res = await page.request.post('https://cursus-backend-53yc.onrender.com/api/v1/plans/generate', {
    data: {
      goalText: 'Hoàn thành phần 1 đồ án SSA101',
      subjectCode: 'SSA101',
      availableHours: 8,
      preferredSessions: ['EVENING'],
      availability: [{date: '2026-08-24', availableMinutes: 60}],
    },
  });
  console.log('status', res.status());
  console.log('body', await res.text());
  await browser.close();
})();
