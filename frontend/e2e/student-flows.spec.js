import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Student core flows (smoke)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Sinh viên');
  });

  test('dashboard (home) loads with no crash', async ({ page }) => {
    await page.goto('/student/home');
    await expect(page).toHaveURL(/\/student\/home/);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.getByText(/error boundary|something went wrong/i)).toHaveCount(0);
  });

  test('weekly planner loads and lists the sandbox course', async ({ page }) => {
    await page.goto('/student/planner');
    await expect(page).toHaveURL(/\/student\/planner/);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.getByLabel('Môn học')).toHaveValue('SSA101', { timeout: 10000 });
  });

  test('reflection page loads with no crash', async ({ page }) => {
    await page.goto('/student/reflection');
    await expect(page).toHaveURL(/\/student\/reflection/);
    await expect(page.getByText(/error boundary|something went wrong/i)).toHaveCount(0);
  });
});
