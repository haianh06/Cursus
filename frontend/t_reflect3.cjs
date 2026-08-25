const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1300 } });
  page.on('response', async (r) => {
    if (r.url().includes('/reflections')) {
      console.log('RESP', r.status(), r.request().method(), r.url());
      if (r.status() >= 400) console.log('BODY', await r.text().catch(()=>'?'));
    }
  });
  page.on('pageerror', e => console.log('PAGEERROR', e.message));

  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/reflection', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  await page.getByText('Hoàn thành một phần nhỏ', { exact: true }).click();
  await page.getByText('Rất khó tập trung, hay xao nhãng', { exact: true }).click();
  await page.getByText('Rất căng thẳng, quá tải', { exact: true }).click();
  await page.getByText('Thường xuyên trễ deadline / dồn việc', { exact: true }).click();
  await page.getByText('Rất thiếu động lực, uể oải', { exact: true }).click();
  await page.locator('textarea').first().fill('Tuần này mình khá đuối, ngủ không đủ giấc nên khó tập trung.');

  await page.locator('button:has-text("Xem trước bản ghi nhớ")').click();
  await page.waitForTimeout(2500);
  console.log('step visible now, url:', page.url());
  await browser.close();
})();
