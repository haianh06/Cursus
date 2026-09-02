import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin settings (Cấu hình)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/governance/settings');
    await expect(page.getByRole('heading', { name: 'Cấu hình', level: 2 })).toBeVisible();
  });

  test('renders both toggles and the default-semester form', async ({ page }) => {
    await expect(page.getByRole('switch', { name: /Chế độ demo/ })).toBeVisible();
    await expect(page.getByRole('switch', { name: /Tự động cảnh báo nguy cơ/ })).toBeVisible();
    await expect(page.locator('#default-semester')).toBeVisible();
  });

  test('toggling "Chế độ demo" flips its state and shows a saved confirmation (reverted after)', async ({ page }) => {
    const toggle = page.getByRole('switch', { name: /Chế độ demo/ });
    const initial = await toggle.getAttribute('aria-checked');

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-checked', String(initial !== 'true'), { timeout: 10000 });
    await expect(page.getByText(/đã lưu|saved/i)).toBeVisible();

    // Revert so the org-wide demo-mode flag is unchanged for the rest of the suite.
    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-checked', initial, { timeout: 10000 });
  });

  test('the default-semester save button stays disabled until the value changes', async ({ page }) => {
    const input = page.locator('#default-semester');
    const saveBtn = page.getByRole('button', { name: 'Lưu' });
    await expect(saveBtn).toBeDisabled();
    const original = await input.inputValue();
    await input.fill(`${original}-e2e`);
    await expect(saveBtn).toBeEnabled();
    // Revert without saving so nothing persists.
    await input.fill(original);
    await expect(saveBtn).toBeDisabled();
  });
});
