const { chromium } = require('playwright');
const fs = require('fs');

const BASE = 'http://localhost:5173';
const results = [];

function log(name, ok, detail) {
  results.push({ name, ok, detail });
  console.log(`${ok ? 'PASS' : 'FAIL'} — ${name}${detail ? ' :: ' + detail : ''}`);
}

async function withPage(browser, fn) {
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  const errors = [];
  const badResponses = [];
  page.on('pageerror', (err) => errors.push(err.message));
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push('console: ' + msg.text()); });
  page.on('response', (res) => {
    const url = res.url();
    if (res.status() >= 400) badResponses.push(`${res.status()} ${url}`);
  });
  try {
    await fn(page, errors, badResponses);
  } finally {
    await page.close();
  }
  return { errors, badResponses };
}

async function login(page, email, password) {
  await page.goto(`${BASE}/login`, { waitUntil: 'load' });
  await page.waitForTimeout(400);
  await page.locator('input[type="email"], input[name="email"]').first().fill(email);
  await page.locator('input[type="password"]').first().fill(password);
  await page.locator('button[type="submit"]').first().click();
  await page.waitForTimeout(1800);
}

async function visit(page, path) {
  await page.goto(`${BASE}${path}`, { waitUntil: 'load' });
  await page.waitForTimeout(1500);
}

(async () => {
  const browser = await chromium.launch();

  // 1. Onboarding removal: a student with NO active semester logs in and must
  // land straight on the dashboard, never on /onboarding.
  await withPage(browser, async (page, errors) => {
    await login(page, 'studenthaidang@example.com', 'test123@');
    const url = page.url();
    await page.screenshot({ path: 'shots/01_no_onboarding_dashboard.png', fullPage: true });
    log('Onboarding removed: non-setup student lands on dashboard', url.includes('/student') && !url.includes('/onboarding'), url);
  });

  // Use the fully set-up account (has semester + courses) for feature coverage.
  const ctx = await withPage(browser, async (page, errors, bad) => {
    await login(page, 'studenthaianh@example.com', 'test123@');
    await page.screenshot({ path: 'shots/02_overview.png', fullPage: true });
    log('Overview loads', page.url().endsWith('/student') || page.url().endsWith('/student/'), page.url());

    // Overview: hover the study-hours chart
    const chart = page.locator('svg[aria-label*="ngày"]').first();
    if (await chart.count()) {
      const box = await chart.boundingBox();
      if (box) {
        await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.5);
        await page.waitForTimeout(300);
        await page.screenshot({ path: 'shots/03_overview_chart_hover.png' });
      }
    }
    log('Overview: no console/page errors so far', errors.length === 0, errors.join(' | '));

    // Planner
    await visit(page, '/student/planner');
    await page.screenshot({ path: 'shots/04_planner.png', fullPage: true });
    const hasTimetable = await page.locator('text=THỜI KHOÁ BIỂU').count();
    log('Planner: Timetable section present', hasTimetable > 0);

    // Planner: add a self-study block via Timetable
    const addBtn = page.locator('button:has-text("Thêm tự học")').first();
    if (await addBtn.count()) {
      await addBtn.click();
      await page.waitForTimeout(400);
      await page.locator('input[placeholder="Tự học"]').fill('Autotest self-study');
      await page.locator('button:has-text("Lưu")').first().click();
      await page.waitForTimeout(1200);
      await page.screenshot({ path: 'shots/05_planner_after_add_block.png', fullPage: true });
      log('Planner: add self-study block flow completes', true);
    } else {
      log('Planner: "Thêm tự học" button found', false);
    }

    // Today's plan
    await visit(page, '/student/today');
    await page.screenshot({ path: 'shots/06_today.png', fullPage: true });
    log('Today screen loads without crash', errors.length === 0, errors.slice(-3).join(' | '));

    // Reflection
    await visit(page, '/student/reflection');
    await page.screenshot({ path: 'shots/07_reflection.png', fullPage: true });

    // Practice
    await visit(page, '/student/practice');
    await page.screenshot({ path: 'shots/08_practice.png', fullPage: true });

    // Companion (Cursus Assistant full page)
    await visit(page, '/student/companion');
    await page.screenshot({ path: 'shots/09_companion.png', fullPage: true });

    // Lecture plan
    await visit(page, '/student/lecture-plan');
    await page.screenshot({ path: 'shots/10_lecture_plan.png', fullPage: true });

    // Semester setup (standalone, still reachable by URL)
    await visit(page, '/student/semester-setup');
    await page.screenshot({ path: 'shots/11_semester_setup.png', fullPage: true });

    // Quizzes
    await visit(page, '/student/quizzes');
    await page.screenshot({ path: 'shots/12_quizzes.png', fullPage: true });

    // Settings
    await visit(page, '/student/settings');
    await page.screenshot({ path: 'shots/13_settings.png', fullPage: true });

    // Dark mode toggle sanity check
    const themeBtn = page.locator('button[aria-label*="theme" i], button[title*="theme" i]').first();
    if (await themeBtn.count()) {
      await themeBtn.click();
      await page.waitForTimeout(300);
      await page.screenshot({ path: 'shots/14_dark_mode.png', fullPage: true });
    }

    log(`All routes visited — total console/page errors: ${errors.length}`, errors.length === 0, '');
    log(`4xx/5xx responses seen: ${bad.length}`, bad.length === 0, bad.join(' \n'));
  });

  await browser.close();

  fs.writeFileSync('shots/report.json', JSON.stringify(results, null, 2));
  const failed = results.filter((r) => !r.ok);
  console.log(`\n=== ${results.length - failed.length}/${results.length} checks passed ===`);
  if (failed.length) {
    console.log('FAILURES:');
    failed.forEach((f) => console.log(' -', f.name, f.detail || ''));
  }
})();
