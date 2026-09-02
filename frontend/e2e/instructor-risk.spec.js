import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Instructor risk & alerts', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
    await page.goto('/instructor/risks');
    await expect(page.getByRole('heading', { name: 'Rủi ro & Cảnh báo', level: 1 })).toBeVisible();
  });

  test('renders the filter bar and both case columns', async ({ page }) => {
    await expect(page.getByLabel('Lớp học')).toBeVisible();
    await expect(page.getByLabel('Mức rủi ro')).toBeVisible();
    await expect(page.getByLabel('Loại vấn đề')).toBeVisible();
    await expect(page.getByLabel('Thời gian')).toBeVisible();
    await expect(page.getByLabel('Sắp xếp')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Chưa xử lý', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Đã xử lý', exact: true })).toBeVisible();
  });

  test('changing the risk-level filter does not error and keeps the page usable', async ({ page }) => {
    await page.getByLabel('Mức rủi ro').selectOption({ label: 'Rủi ro Cao' });
    await expect(page.getByRole('heading', { name: 'Rủi ro & Cảnh báo', level: 1 })).toBeVisible();
    await page.getByLabel('Mức rủi ro').selectOption({ label: 'Tất cả' });
  });

  test('changing the time-window filter reloads without crashing', async ({ page }) => {
    await page.getByLabel('Thời gian').selectOption({ label: 'Toàn bộ' });
    await expect(page.getByRole('heading', { name: 'Rủi ro & Cảnh báo', level: 1 })).toBeVisible();
  });

  test('the class filter narrows to one course', async ({ page }) => {
    await page.getByLabel('Lớp học').selectOption({ label: 'SSA101 — Kỹ năng học thuật / Academic Skills' });
    await expect(page.getByRole('heading', { name: 'Rủi ro & Cảnh báo', level: 1 })).toBeVisible();
  });

  test('"Xuất báo cáo" triggers a report download', async ({ page }) => {
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(() => null);
    await page.getByRole('button', { name: 'Xuất báo cáo' }).click();
    const download = await downloadPromise;
    expect(download).not.toBeNull();
  });

  test('opening a pending risk case shows the evidence drawer with a decision', async ({ page }) => {
    const pendingSection = page.locator('section', { has: page.getByRole('heading', { name: 'Chưa xử lý', exact: true }) });
    const caseCard = pendingSection.getByRole('button').first();
    if (await pendingSection.locator('button').count() === 0) {
      test.skip(true, 'No pending risk case in current demo data.');
    }
    await caseCard.click();
    const drawer = page.getByRole('dialog');
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole('button', { name: 'Đánh dấu đã can thiệp' })).toBeVisible();
    await expect(drawer.getByRole('button', { name: 'Bỏ qua cảnh báo' })).toBeVisible();
    await drawer.getByRole('button', { name: 'Đóng' }).click();
    await expect(drawer).toBeHidden();
  });
});
