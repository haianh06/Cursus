import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin accounts (Tài khoản)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/governance/access');
    await expect(page.getByRole('heading', { name: 'Lời mời & Người dùng', level: 1 })).toBeVisible();
  });

  test('renders the account summary and the member table with row actions', async ({ page }) => {
    // Scope to the summary card region -- "Đang hoạt động" etc also appear
    // as per-row status text in the member table below.
    const summary = page.getByLabel('Tổng hợp tài khoản');
    await expect(summary.getByText('Đang hoạt động')).toBeVisible();
    await expect(summary.getByText('Lời mời chờ')).toBeVisible();
    await expect(summary.getByText('Đã khoá')).toBeVisible();
    const row = page.getByRole('row').filter({ hasText: 'instructor@example.com' });
    await expect(row.getByRole('button', { name: 'Khoá' })).toBeVisible();
    await expect(row.getByRole('button', { name: 'Đặt lại mật khẩu' })).toBeVisible();
    await expect(row.getByRole('link', { name: 'Xem hồ sơ 360' })).toBeVisible();
  });

  test('"Xem hồ sơ 360" navigates to that member\'s 360 profile', async ({ page }) => {
    const row = page.getByRole('row').filter({ hasText: 'studenthaianh@example.com' });
    await row.getByRole('link', { name: 'Xem hồ sơ 360' }).click();
    await expect(page).toHaveURL(/\/admin\/students\/student_haianh$/);
  });

  test('"Mời thành viên" opens the invite form, cancellable without sending an invite', async ({ page }) => {
    const pendingBefore = await page.getByText('Lời mời chờ').locator('..').locator('p.text-2xl').innerText();
    await page.getByRole('button', { name: 'Mời thành viên' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: /Hủy|Đóng/ }).first().click();
    await expect(dialog).toBeHidden();
    await expect(page.getByText('Lời mời chờ').locator('..').locator('p.text-2xl')).toHaveText(pendingBefore);
  });
});
