import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin system log (Nhật ký hệ thống)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/governance/logs');
    await expect(page.getByRole('heading', { name: 'Nhật ký hệ thống', level: 1 })).toBeVisible();
  });

  test('renders the totals cards and the event table', async ({ page }) => {
    await expect(page.getByText('Tổng sự kiện')).toBeVisible();
    await expect(page.getByText('Thành công')).toBeVisible();
    await expect(page.getByText('Cảnh báo')).toBeVisible();
    await expect(page.getByText('Bị từ chối')).toBeVisible();
    await expect(page.getByRole('table')).toBeVisible();
  });

  test('the category filter buttons narrow the event list', async ({ page }) => {
    const allBtn = page.getByRole('button', { name: /^Tất cả \d+/ });
    const authBtn = page.getByRole('button', { name: /^Đăng nhập & phiên \d+/ });
    await expect(allBtn).toHaveAttribute('aria-pressed', 'true');
    await authBtn.click();
    await expect(authBtn).toHaveAttribute('aria-pressed', 'true');
    await expect(allBtn).toHaveAttribute('aria-pressed', 'false');
  });

  test('clicking a row\'s detail toggle opens the event-details side panel', async ({ page }) => {
    const firstToggle = page.getByRole('button', { name: /Xem chi tiết|toggle/i }).first();
    await firstToggle.click();
    const detailsPanel = page.getByRole('complementary', { name: /Chi tiết sự kiện|Event details/ });
    await expect(detailsPanel).toBeVisible();
    await expect(detailsPanel.getByText('Metadata')).toBeVisible();
  });
});
