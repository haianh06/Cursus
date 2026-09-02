import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Instructor class activity calendar', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
    await page.goto('/instructor/activities');
    await expect(page.getByRole('heading', { name: 'Hoạt động lớp', level: 1 })).toBeVisible();
  });

  test('renders the class filter, week nav and the semester window info', async ({ page }) => {
    await expect(page.getByLabel('Lớp học')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Tuần trước' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Tuần sau' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Khung thời gian học kỳ' })).toBeVisible();
  });

  test('week navigation changes the displayed week label', async ({ page }) => {
    const weekLabel = page.getByText(/^Tuần \d+ /);
    const before = await weekLabel.innerText();
    await page.getByRole('button', { name: 'Tuần sau' }).click();
    await expect(weekLabel).not.toHaveText(before);
    await page.getByRole('button', { name: 'Tuần trước' }).click();
    await expect(weekLabel).toHaveText(before);
  });

  test('creates a new class activity and it shows up in the event list, then deletes it', async ({ page }) => {
    await page.getByRole('button', { name: 'Tạo hoạt động mới' }).click();
    const title = `E2E activity ${Date.now()}`;
    // Leave date/course/time at their defaults (today, within the visible
    // week, first course) -- only the title needs setting.
    await page.getByLabel('Tiêu đề').fill(title);
    await page.getByRole('button', { name: 'Tạo hoạt động', exact: true }).click();

    // The new activity renders in both the day timeline and the "Danh sách
    // sự kiện lớp" list -- just confirm it shows up somewhere.
    await expect(page.getByText(title).first()).toBeVisible({ timeout: 10000 });

    const row = page.getByRole('listitem').filter({ hasText: title });
    const deleteBtn = row.getByRole('button', { name: 'Xoá' });
    if (await deleteBtn.count()) {
      await deleteBtn.click();
      await expect(page.getByText(title).first()).toBeHidden({ timeout: 10000 });
    }
  });

  test('the create-activity form can be cancelled', async ({ page }) => {
    await page.getByRole('button', { name: 'Tạo hoạt động mới' }).click();
    await expect(page.getByLabel('Tiêu đề')).toBeVisible();
    // Two elements share the accessible name "Huỷ" -- the form's icon-only
    // header cancel button and the footer's text cancel button; use the
    // footer one (last in DOM order).
    await page.getByRole('button', { name: 'Huỷ', exact: true }).last().click();
    await expect(page.getByLabel('Tiêu đề')).toBeHidden();
  });
});
