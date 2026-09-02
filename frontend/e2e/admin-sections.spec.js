import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin class sections (Lớp học)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/governance/sections');
    await expect(page.getByRole('table')).toBeVisible();
  });

  test('renders the section table with course/instructor/roster columns', async ({ page }) => {
    await expect(page.getByRole('columnheader', { name: 'Môn' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Giảng viên' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Sĩ số' })).toBeVisible();
    await expect(page.getByRole('row').filter({ hasText: 'CEA201' })).toBeVisible();
  });

  test('"Danh sách sinh viên" opens the section roster, closable', async ({ page }) => {
    const row = page.getByRole('row').filter({ hasText: 'CEA201' });
    await row.getByRole('button', { name: 'Danh sách sinh viên' }).click();
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    await expect(modal).toContainText('CEA201');
    await modal.getByRole('button', { name: /Đóng|Hủy/ }).first().click();
    await expect(modal).toBeHidden();
  });

  test('"Xoá" opens a delete confirmation that can be cancelled (no section removed)', async ({ page }) => {
    const rowsBefore = await page.getByRole('row').count();
    const row = page.getByRole('row').filter({ hasText: 'CEA201' });
    await row.getByRole('button', { name: 'Xoá' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: 'Hủy' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole('row')).toHaveCount(rowsBefore);
  });

  test('"Thêm lớp" opens the create-section form, cancellable', async ({ page }) => {
    await page.getByRole('button', { name: 'Thêm lớp' }).click();
    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await dialog.getByRole('button', { name: /Hủy|Đóng/ }).first().click();
    await expect(dialog).toBeHidden();
  });
});
