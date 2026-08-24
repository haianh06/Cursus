import { test, expect } from '@playwright/test';
import { DEMO_ACCOUNTS, loginAs } from './helpers';

test.describe('Auth', () => {
  test('student can log in with the seeded demo account', async ({ page }) => {
    await loginAs(page, DEMO_ACCOUNTS.student);
    await expect(page).toHaveURL(/\/student(\/|$)/);
    await expect(page.locator('h1').first()).toBeVisible();
  });

  test('wrong password is rejected with an inline error, not a redirect', async ({ page }) => {
    await page.goto('/login');
    await page.locator('#login-email').fill(DEMO_ACCOUNTS.student.email);
    await page.locator('#login-password').fill('definitely-wrong-password');
    await page.locator('#login-submit').click();
    await expect(page).toHaveURL(/\/login/);
    await expect(page.getByText(/mật khẩu|password|sai|invalid|incorrect/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('logout returns to the login screen and blocks re-entry without a session', async ({ page }) => {
    await loginAs(page, DEMO_ACCOUNTS.student);
    await page.locator('#logout-btn').click();
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
    await page.goto('/student/practice');
    await expect(page).toHaveURL(/\/login/);
  });
});
