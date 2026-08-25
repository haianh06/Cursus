const { chromium } = require('playwright');

const SCREENS = [
  { path: '/student', name: 'overview' },
  { path: '/student/planner', name: 'planner' },
  { path: '/student/today', name: 'today' },
  { path: '/student/reflection', name: 'reflection' },
  { path: '/student/practice', name: 'practice' },
  { path: '/student/settings', name: 'settings' },
];

async function login(page) {
  await page.goto('https://cursus-mu.vercel.app/demo/select-role', { waitUntil: 'load', timeout: 30000 });
  await page.waitForTimeout(1000);
  await page.getByText('Khám phá vai trò Sinh viên', { exact: false }).first().click();
  await page.waitForTimeout(2000);
}

async function shootAll(page, prefix) {
  for (const s of SCREENS) {
    await page.goto(`https://cursus-mu.vercel.app${s.path}`, { waitUntil: 'load' });
    await page.waitForTimeout(1800);
    await page.screenshot({ path: `qa_shots/v_${prefix}_${s.name}.png`, fullPage: true });
  }
}

(async () => {
  const browser = await chromium.launch();

  // Dark mode (desktop)
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await login(page);
    const darkBtn = page.locator('button:has(svg.lucide-moon)').first();
    if (await darkBtn.count() > 0) await darkBtn.click();
    else await page.locator('button', { hasText: /Chế độ tối/ }).first().click().catch(() => {});
    await page.waitForTimeout(500);
    await shootAll(page, 'dark');
    await page.close();
  }

  // English (desktop)
  {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    await login(page);
    await page.locator('button[aria-label="Switch to English"]').first().click();
    await page.waitForTimeout(500);
    await shootAll(page, 'en');
    await page.close();
  }

  // Mobile (~390px)
  {
    const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
    await login(page);
    await shootAll(page, 'mobile');
    await page.close();
  }

  // Tablet (~768px)
  {
    const page = await browser.newPage({ viewport: { width: 768, height: 1024 } });
    await login(page);
    await shootAll(page, 'tablet');
    await page.close();
  }

  await browser.close();
  console.log('done');
})();
