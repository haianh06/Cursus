import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin analytics', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/analytics');
    await expect(page.getByRole('heading', { name: 'Phân tích', level: 1 })).toBeVisible();
  });

  test('renders the aggregate KPI summary and methodology note', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Tổng hợp phân tích' })).toBeVisible();
    await expect(page.getByText('Môn đã nạp', { exact: true })).toBeVisible();
    await expect(page.getByText('Tài liệu', { exact: true })).toBeVisible();
    await expect(page.getByText('Chunks', { exact: true })).toBeVisible();
    await expect(page.getByText('Sinh viên cần chú ý', { exact: true })).toBeVisible();
    await expect(page.getByText(/Lưu ý phương pháp/)).toBeVisible();
  });
});

test.describe('Admin AI usage / cost', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/ai-usage');
    await expect(page.getByRole('heading', { name: 'Chi phí AI', level: 1 })).toBeVisible();
  });

  test('renders the per-feature cost table and methodology note', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Chi phí AI theo tính năng' })).toBeVisible();
    // "Lần gọi" appears as both the KPI label <p> and a table column header.
    await expect(page.getByRole('columnheader', { name: 'Lần gọi' })).toBeVisible();
    await expect(page.getByText('Độ trễ trung bình', { exact: true })).toBeVisible();
    await expect(page.getByText('Tỷ lệ lỗi', { exact: true })).toBeVisible();
    await expect(page.getByRole('table')).toBeVisible();
    await expect(page.getByText(/Lưu ý phương pháp/)).toBeVisible();
  });

  test('the 7/30/90-day window toggle switches the active period', async ({ page }) => {
    const group = page.getByRole('group', { name: 'Chi phí AI theo tính năng' });
    const btn30 = group.getByRole('button', { name: '30 ngày' });
    const btn7 = group.getByRole('button', { name: '7 ngày' });
    await expect(btn30).toHaveAttribute('aria-pressed', 'true');
    await btn7.click();
    await expect(btn7).toHaveAttribute('aria-pressed', 'true');
    await expect(btn30).toHaveAttribute('aria-pressed', 'false');
  });
});
