import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Instructor home / dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
    await page.goto('/instructor');
    await expect(page.getByRole('heading', { name: /Chào mừng trở lại/i, level: 1 })).toBeVisible();
  });

  test('renders the 4 KPI cards and the class comparison table', async ({ page }) => {
    await expect(page.getByText('Sinh viên có nguy cơ')).toBeVisible();
    await expect(page.getByText('Case quá hạn')).toBeVisible();
    await expect(page.getByText('Guardrail chờ xem xét')).toBeVisible();
    await expect(page.getByText('Tỷ lệ hoàn thành tuần')).toBeVisible();

    const compareHeading = page.getByRole('heading', { name: 'So sánh giữa các lớp' });
    await expect(compareHeading).toBeVisible();
    // Scope to the comparison table specifically -- the "Cần chú ý ngay"
    // table above it can also contain rows mentioning SSA101 (a student's
    // course), which would otherwise match too.
    const compareTable = page.locator('section', { has: compareHeading }).getByRole('table');
    await expect(compareTable.getByRole('row').filter({ hasText: 'SSA101' })).toBeVisible();
  });

  test('the class filter narrows the dashboard to a single course', async ({ page }) => {
    const select = page.getByLabel('Lớp học');
    await select.selectOption({ label: 'SSA101 — Kỹ năng học thuật / Academic Skills' });
    // Subtitle grows a "<code> — N sinh viên" suffix once a single course is selected.
    await expect(page.getByText(/SSA101 — \d+ sinh viên/)).toBeVisible();
  });

  test('"Xem SV rủi ro" navigates to the risk page', async ({ page }) => {
    await page.getByRole('button', { name: 'Xem SV rủi ro' }).click();
    await expect(page).toHaveURL(/\/instructor\/risks$/);
    await expect(page.getByRole('heading', { name: 'Rủi ro & Cảnh báo', level: 1 })).toBeVisible();
  });

  test('"Xem Guardrail chờ duyệt" navigates to the guardrail review queue', async ({ page }) => {
    await page.getByRole('button', { name: 'Xem Guardrail chờ duyệt' }).click();
    await expect(page).toHaveURL(/\/instructor\/guardrail-reviews$/);
  });

  test('each quick action button navigates to its labeled destination', async ({ page }) => {
    // Scope to the main content: the sidebar has nav buttons with the same
    // labels as these dashboard quick-action buttons.
    const main = page.locator('#main-content');
    await main.getByRole('button', { name: 'Hoạt động lớp' }).click();
    await expect(page).toHaveURL(/\/instructor\/activities$/);
    await expect(page.getByRole('heading', { name: 'Hoạt động lớp', level: 1 })).toBeVisible();

    await page.goto('/instructor');
    await main.getByRole('button', { name: 'Quản lý Quiz' }).click();
    await expect(page).toHaveURL(/\/instructor\/quizzes$/);

    await page.goto('/instructor');
    await main.getByRole('button', { name: 'Bài tập nộp' }).click();
    await expect(page).toHaveURL(/\/instructor\/submissions$/);
  });

  test('"Gửi digest tuần" sends the digest email and shows a confirmation', async ({ page }) => {
    await page.getByRole('button', { name: 'Gửi digest tuần' }).click();
    await expect(page.getByText(/đã gửi|đã được gửi|sent/i)).toBeVisible({ timeout: 10000 });
  });

  test('the "Cần chú ý ngay" row for a pending risk case opens that student profile', async ({ page }) => {
    const attentionSection = page.locator('section', { has: page.getByRole('heading', { name: 'Cần chú ý ngay' }) });
    const firstRow = attentionSection.locator('tbody tr').first();
    if (await firstRow.count() === 0) {
      test.skip(true, 'No pending risk case in current demo data to click through.');
    }
    await firstRow.getByRole('button').first().click();
    await expect(page).toHaveURL(/\/instructor\/students\/[^/]+$/);
  });

  test('sidebar navigation covers every instructor screen', async ({ page }) => {
    const nav = [
      ['Rủi ro & Cảnh báo', /\/instructor\/risks$/],
      ['Hoạt động lớp', /\/instructor\/activities$/],
      ['Quản lý Quiz', /\/instructor\/quizzes$/],
      ['Bài tập nộp', /\/instructor\/submissions$/],
      ['Digest', /\/instructor\/digest$/],
      ['Xét duyệt Guardrail', /\/instructor\/guardrail-reviews$/],
    ];
    for (const [label, urlPattern] of nav) {
      await page.getByRole('complementary').getByRole('button', { name: label, exact: true }).click();
      await expect(page).toHaveURL(urlPattern);
    }
  });
});
