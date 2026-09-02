import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Instructor teaching schedule', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
    await page.goto('/instructor/schedule');
    await expect(page.getByRole('heading', { name: 'Lịch giảng dạy', level: 1 })).toBeVisible();
  });

  test('renders the week-start date picker', async ({ page }) => {
    const dateInput = page.locator('input[type="date"]');
    await expect(dateInput).toBeVisible();
  });

  test('changing the week reloads the schedule without crashing', async ({ page }) => {
    const dateInput = page.locator('input[type="date"]');
    const current = await dateInput.inputValue();
    const nextWeek = new Date(current);
    nextWeek.setDate(nextWeek.getDate() + 7);
    await dateInput.fill(nextWeek.toISOString().slice(0, 10));
    await expect(page.getByRole('heading', { name: 'Lịch giảng dạy', level: 1 })).toBeVisible();
  });

  test('cancelling a class session requires a reason of at least 3 characters', async ({ page }) => {
    const cancelBtn = page.getByRole('button', { name: 'Hủy buổi' }).first();
    if (await cancelBtn.count() === 0) {
      test.skip(true, 'No scheduled class session in the current week to cancel.');
    }
    await cancelBtn.click();
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    const confirmBtn = modal.getByRole('button', { name: 'Xác nhận hủy' });

    // A reason under 3 chars is silently rejected (no request fires, modal
    // stays open) -- there's no disabled/validation-message affordance on
    // the button itself, so we assert on the modal staying open instead.
    await modal.locator('textarea').fill('ab');
    await confirmBtn.click();
    await expect(modal).toBeVisible();

    await modal.getByRole('button', { name: 'Đóng' }).click();
    await expect(modal).toBeHidden();
  });
});
