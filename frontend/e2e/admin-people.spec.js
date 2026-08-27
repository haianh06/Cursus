import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin people directory', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/people');
    await expect(page.getByRole('heading', { name: 'Người dùng', level: 1 })).toBeVisible();
  });

  test('opens a student 360 profile when the student name is clicked', async ({ page }) => {
    await page.getByRole('link', { name: 'Nguyễn Minh', exact: true }).click();

    await expect(page).toHaveURL(/\/admin\/students\/stu_minh_demo$/);
    await expect(page.getByRole('heading', { name: 'Nguyễn Minh' })).toBeVisible();
  });

  test('opens the selected instructor 360 profile from the table action with the keyboard', async ({ page }) => {
    const instructorRow = page.getByRole('row').filter({ hasText: 'Cô Hương' });
    const profileLink = instructorRow.getByRole('link', { name: 'Mở hồ sơ 360' });

    await profileLink.focus();
    await expect(profileLink).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(page).toHaveURL(/\/admin\/instructors\/[^/]+$/);
    await expect(page.getByRole('heading', { name: 'Cô Hương' })).toBeVisible();
  });
});
