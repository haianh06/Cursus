import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin term & exams (Học kỳ & lịch thi)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/governance/academic');
    await expect(page.getByRole('heading', { name: 'Học kỳ hiện hành' })).toBeVisible();
  });

  test('renders the term overview card, calendar and the active-term form pre-filled', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Fall 2026', exact: true })).toBeVisible();
    await expect(page.getByText('Đang hoạt động')).toBeVisible();
    await expect(page.getByRole('heading', { name: /^tháng \d+ năm \d+$/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Lịch đánh giá sắp tới' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Lịch thi theo môn' })).toBeVisible();

    // Term config fields aren't <label for>-associated, so target them by
    // container position instead of accessible name.
    const nameInput = page.locator('#term-config input').first();
    await expect(nameInput).toHaveValue('Fall 2026');
  });

  test('"Chỉnh sửa học kỳ" scrolls to the term-config form', async ({ page }) => {
    await page.getByRole('button', { name: 'Chỉnh sửa học kỳ' }).click();
    await expect(page.locator('#term-config')).toBeInViewport();
  });

  test('the course-exam picker lists real curriculum courses', async ({ page }) => {
    const courseSelect = page.locator('div.card', { has: page.getByRole('heading', { name: 'Lịch thi theo môn' }) })
      .locator('select').first();
    await expect(courseSelect).toBeVisible();
    const options = await courseSelect.locator('option').allTextContents();
    expect(options.some((o) => o.includes('CEA201'))).toBe(true);
  });
});
