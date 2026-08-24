import { test, expect } from '@playwright/test';
import { DEMO_ACCOUNTS, loginAs } from './helpers';

test.describe('Student core flows (smoke)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, DEMO_ACCOUNTS.student);
  });

  test('dashboard (home) loads with no crash', async ({ page }) => {
    await page.goto('/student/home');
    await expect(page).toHaveURL(/\/student\/home/);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page.getByText(/error boundary|something went wrong/i)).toHaveCount(0);
  });

  test('weekly plan page loads and lists at least one enrolled course', async ({ page }) => {
    await page.goto('/student/plan');
    await expect(page).toHaveURL(/\/student\/plan/);
    await expect(page.locator('h1').first()).toBeVisible();
    // CEA201 is one of student_ethan's seeded enrollments — asserted via the
    // visible practice-card button rather than the <option> text in the
    // course-select dropdown, which Playwright treats as not "visible".
    await expect(page.getByRole('button', { name: /CEA201/ }).first()).toBeVisible({ timeout: 10000 });
  });

  test('the practice card on weekly plan links into /student/practice', async ({ page }) => {
    await page.goto('/student/plan');
    const practiceButton = page.getByRole('button', { name: /CEA201/ }).first();
    await expect(practiceButton).toBeVisible({ timeout: 10000 });
    await practiceButton.click();
    await expect(page).toHaveURL(/\/student\/practice\?course=CEA201/);
  });

  test('reflection page loads with no crash', async ({ page }) => {
    await page.goto('/student/reflection');
    await expect(page).toHaveURL(/\/student\/reflection/);
    await expect(page.getByText(/error boundary|something went wrong/i)).toHaveCount(0);
  });
});
