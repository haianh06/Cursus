const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
  await page.goto('https://cursus-mu.vercel.app/student/reflection', { waitUntil: 'load' });
  await page.waitForTimeout(1500);
  const bodyText = await page.textContent('body');
  console.log('has new 6-question label:', bodyText.includes('6 câu hỏi cố định'));
  console.log('has old 7-question label:', bodyText.includes('7 câu hỏi cố định'));
  console.log('has accomplishment_level style question:', bodyText.includes('Mức độ hoàn thành kế hoạch'));
  await page.screenshot({ path: 'deploy_check_reflection.png', fullPage: true });
  await browser.close();
})();
