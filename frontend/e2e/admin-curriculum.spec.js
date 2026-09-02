import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin curriculum management', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/governance/curriculum');
    await expect(page.getByRole('heading', { name: 'Chương trình học', level: 1 })).toBeVisible();
  });

  test('renders the status summary cards and the course table', async ({ page }) => {
    // Scope to the summary region -- "Đang xử lý"/"Chưa nạp" are also
    // <option> labels in the status filter below.
    const summary = page.getByLabel('Tổng hợp trạng thái chương trình học');
    await expect(summary.getByText('Môn đã nạp', { exact: true })).toBeVisible();
    await expect(summary.getByText('Đang xử lý')).toBeVisible();
    await expect(summary.getByText('Chưa nạp')).toBeVisible();
    await expect(summary.getByText('Tổng chunks')).toBeVisible();
    await expect(page.getByRole('table', { name: 'Danh sách Curriculum' })).toBeVisible();
  });

  test('search narrows the course list to matching subject code/name', async ({ page }) => {
    await page.getByRole('searchbox', { name: 'Tìm môn học' }).fill('OTP101');
    await expect(page.getByRole('button', { name: 'OTP101', exact: true })).toBeVisible();
    await expect(page.getByText(/Hiển thị 1\//)).toBeVisible();
  });

  test('the status filter narrows the list to only ingested courses', async ({ page }) => {
    await page.getByLabel('Lọc theo trạng thái').selectOption({ label: 'Đã nạp' });
    await expect(page.getByRole('heading', { name: 'Chương trình học', level: 1 })).toBeVisible();
    // Every visible status badge should now read "Đã nạp".
    const badges = page.locator('table tbody tr td:nth-child(5)');
    const count = await badges.count();
    for (let i = 0; i < count; i++) {
      await expect(badges.nth(i)).toContainText('Đã nạp');
    }
  });

  test('"Xem tài liệu" expands the inline document list for an ingested course', async ({ page }) => {
    await page.getByRole('searchbox', { name: 'Tìm môn học' }).fill('OTP101');
    const viewDocsBtn = page.getByRole('button', { name: 'Xem tài liệu: OTP101' });
    await expect(viewDocsBtn).toHaveAttribute('aria-expanded', 'false');
    await viewDocsBtn.click();
    await expect(viewDocsBtn).toHaveAttribute('aria-expanded', 'true');
    await viewDocsBtn.click();
    await expect(viewDocsBtn).toHaveAttribute('aria-expanded', 'false');
  });

  test('"Xem chi tiết chương trình" opens the curriculum detail modal', async ({ page }) => {
    await page.getByRole('searchbox', { name: 'Tìm môn học' }).fill('OTP101');
    await page.getByRole('button', { name: 'Xem chi tiết chương trình: OTP101' }).click();
    const modal = page.getByRole('dialog');
    await expect(modal).toBeVisible();
    await expect(modal.getByText('OTP101')).toBeVisible();
  });

  test('"Thêm môn học" opens the add-course form, cancellable without creating one', async ({ page }) => {
    await page.getByRole('button', { name: 'Thêm môn học' }).click();
    const heading = page.getByRole('heading', { name: 'Thêm môn học mới' });
    await expect(heading).toBeVisible();
    // Two "Hủy" buttons: the header's icon-only X and the footer's text
    // button -- use the footer one (last in DOM order).
    await page.getByRole('button', { name: 'Hủy', exact: true }).last().click();
    await expect(heading).toBeHidden();
  });
});
