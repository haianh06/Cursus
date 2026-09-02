import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin overview dashboard', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/overview');
    await expect(page.getByRole('heading', { name: 'Tổng quan', level: 1 })).toBeVisible();
  });

  test('renders system status, school pulse, work queue and signals sections', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Trạng thái hệ thống' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Nhịp độ trường' })).toBeVisible();
    await expect(page.getByText('Sinh viên hoạt động')).toBeVisible();
    await expect(page.getByText('Giảng viên hoạt động')).toBeVisible();
    await expect(page.getByRole('heading', { name: /Hàng đợi công việc/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Tín hiệu' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Thay đổi quan trọng gần đây' })).toBeVisible();
  });

  test('sidebar navigation reaches every governance/observe screen', async ({ page }) => {
    const nav = [
      ['Người dùng', /\/admin\/people$/],
      ['Phân tích', /\/admin\/analytics$/],
      ['Chi phí AI', /\/admin\/ai-usage$/],
      ['Chương trình học', /\/admin\/governance\/curriculum$/],
      ['Lớp học', /\/admin\/governance\/sections$/],
      ['Học kỳ & lịch thi', /\/admin\/governance\/academic$/],
      ['Chính sách AI', /\/admin\/governance\/ai-policy$/],
      ['EduSync', /\/admin\/governance\/edusync$/],
      ['Tài khoản', /\/admin\/governance\/access$/],
      ['Cấu hình', /\/admin\/governance\/settings$/],
      ['Nhật ký hệ thống', /\/admin\/governance\/logs$/],
    ];
    for (const [label, urlPattern] of nav) {
      await page.getByRole('link', { name: label, exact: true }).click();
      await expect(page).toHaveURL(urlPattern);
    }
  });
});
