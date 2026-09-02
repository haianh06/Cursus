import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Instructor weekly digest', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
    await page.goto('/instructor/digest');
    await expect(page.getByRole('heading', { name: 'Digest tuần', level: 1 })).toBeVisible();
  });

  test('renders period/class filters and the digest summary sections', async ({ page }) => {
    await expect(page.getByLabel('Khoảng thời gian')).toBeVisible();
    await expect(page.getByLabel('Lớp học')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Case rủi ro mới', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Lượt chặn guardrail mới', exact: true })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Điểm sáng của lớp' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Gợi ý hành động cho tuần tới' })).toBeVisible();
  });

  test('changing the period reloads the summary without crashing', async ({ page }) => {
    await page.getByLabel('Khoảng thời gian').selectOption({ label: '30 ngày qua' });
    await expect(page.getByRole('heading', { name: 'Digest tuần', level: 1 })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Case rủi ro mới', exact: true })).toBeVisible();
  });

  test('changing the class filter reloads the summary without crashing', async ({ page }) => {
    await page.getByLabel('Lớp học').selectOption({ label: 'SSA101 — Kỹ năng học thuật / Academic Skills' });
    await expect(page.getByRole('heading', { name: 'Digest tuần', level: 1 })).toBeVisible();
  });

  test('"Gửi digest qua email" sends the digest', async ({ page }) => {
    await page.getByRole('button', { name: 'Gửi digest qua email' }).click();
    await expect(page.getByText(/đã gửi|sent/i)).toBeVisible({ timeout: 10000 });
  });
});
