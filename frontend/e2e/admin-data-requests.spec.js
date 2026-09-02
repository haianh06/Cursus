import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin data requests (DSAR)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/data-requests');
    await expect(page.getByRole('heading', { name: 'Yêu cầu dữ liệu', level: 1 })).toBeVisible();
  });

  test('renders the status summary cards and the request list/empty state', async ({ page }) => {
    // Scope to the summary card region -- these status words can also
    // appear as badges in the request table/detail drawer once requests exist.
    const summary = page.getByLabel('Tổng hợp yêu cầu dữ liệu');
    await expect(summary.getByText('Mới')).toBeVisible();
    await expect(summary.getByText('Đang xử lý')).toBeVisible();
    await expect(summary.getByText('Hoàn tất')).toBeVisible();
    await expect(summary.getByText('Từ chối')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Yêu cầu dữ liệu (DSAR)' })).toBeVisible();
  });

  // This screen is reachable only via a legacy redirect or a work-queue
  // link -- there is no persistent sidebar entry for it (ADMIN_PATHS.dataRequests
  // is absent from NAV_GROUPS in adminNavigationConfig.js). Confirmed
  // intentional-looking (icon + legacy redirect both exist), so recorded as
  // an observation rather than "fixed" -- see final report.
  test('the legacy /admin/datarequests URL still redirects here', async ({ page }) => {
    await page.goto('/admin/datarequests');
    await expect(page).toHaveURL(/\/admin\/data-requests$/);
  });
});
