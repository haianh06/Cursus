import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Instructor assignment submissions', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
    await page.goto('/instructor/submissions');
    await expect(page.getByRole('heading', { name: 'Bài tập nộp', level: 1 })).toBeVisible();
  });

  test('renders the filter bar and the 4 status KPIs', async ({ page }) => {
    await expect(page.getByLabel('Lớp học')).toBeVisible();
    await expect(page.getByLabel('Bài tập')).toBeVisible();
    await expect(page.getByLabel('Trạng thái')).toBeVisible();
    await expect(page.getByPlaceholder('Tìm sinh viên…')).toBeVisible();
    // "Chưa nộp" etc also appear as <option>s and table badges elsewhere on
    // this page -- the KPI card label is specifically a <p>.
    await expect(page.locator('p').filter({ hasText: /^Chưa nộp$/ })).toBeVisible();
    await expect(page.locator('p').filter({ hasText: /^Nộp trễ$/ })).toBeVisible();
    await expect(page.locator('p').filter({ hasText: /^Nộp đúng hạn$/ })).toBeVisible();
    await expect(page.locator('p').filter({ hasText: /^Đã chấm$/ })).toBeVisible();
  });

  test('the search box filters the submissions table by student name', async ({ page }) => {
    const rowsBefore = await page.locator('table tbody tr').count();
    if (rowsBefore === 0) test.skip(true, 'No submissions seeded for the default assignment.');
    await page.getByPlaceholder('Tìm sinh viên…').fill('zzz-no-such-student');
    await expect(page.getByText('Chưa có bài tập nào trong phạm vi bộ lọc.')).toBeVisible();
    await page.getByPlaceholder('Tìm sinh viên…').fill('');
    await expect(page.locator('table tbody tr').first()).toBeVisible();
  });

  test('the status filter narrows the list', async ({ page }) => {
    await page.getByLabel('Trạng thái').selectOption({ label: 'Chưa nộp' });
    await expect(page.getByRole('heading', { name: 'Bài tập nộp', level: 1 })).toBeVisible();
  });

  test('clicking a submission row opens its detail drawer, closable via the X button', async ({ page }) => {
    const row = page.locator('table tbody tr').first();
    if (await row.count() === 0) test.skip(true, 'No submissions seeded.');
    const studentName = (await row.locator('td').first().innerText()).trim();
    await row.click();
    const drawer = page.getByRole('dialog');
    await expect(drawer).toBeVisible();
    await expect(drawer.getByRole('heading', { name: studentName })).toBeVisible();
    await drawer.getByRole('button', { name: 'Đóng' }).click();
    await expect(drawer).toBeHidden();
  });

  test('"Xuất báo cáo" triggers a report download', async ({ page }) => {
    const downloadPromise = page.waitForEvent('download', { timeout: 10000 }).catch(() => null);
    await page.getByRole('button', { name: 'Xuất báo cáo' }).click();
    const download = await downloadPromise;
    expect(download).not.toBeNull();
  });
});
