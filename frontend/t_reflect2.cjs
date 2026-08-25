const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1300 } });
  const errors = [];
  page.on('pageerror', e => errors.push('PAGEERROR: ' + e.message));

  await page.goto('http://localhost:5173/login', { waitUntil: 'load' });
  await page.waitForTimeout(500);
  await page.locator('input[type="email"], input[name="email"]').first().fill('studenthaianh@example.com');
  await page.locator('input[type="password"]').first().fill('test123@');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(2000);
  await page.goto('http://localhost:5173/student/reflection', { waitUntil: 'load' });
  await page.waitForTimeout(1500);

  // Answer each MCQ with a "concerning" option to trigger a lighter-load suggestion
  await page.getByText('Hoàn thành một phần nhỏ', { exact: true }).click();
  await page.getByText('Rất khó tập trung, hay xao nhãng', { exact: true }).click();
  await page.getByText('Rất căng thẳng, quá tải', { exact: true }).click();
  await page.getByText('Thường xuyên trễ deadline / dồn việc', { exact: true }).click();
  await page.getByText('Rất thiếu động lực, uể oải', { exact: true }).click();
  await page.locator('textarea').first().fill('Tuần này mình khá đuối, ngủ không đủ giấc nên khó tập trung.');

  await page.locator('button:has-text("Xem trước bản ghi nhớ")').click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'r2_memory.png', fullPage: true });

  await page.locator('button:has-text("Xác nhận & dùng cho tuần sau")').click();
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'r3_done.png', fullPage: true });

  await page.locator('button:has-text("Tạo kế hoạch tuần sau")').click();
  console.log('waiting for next-week plan (real LLM calls)...');
  await page.waitForTimeout(15000);
  await page.screenshot({ path: 'r4_nextplan.png', fullPage: true });

  console.log('errors:', errors.join('\n') || '(none)');
  await browser.close();
})();
