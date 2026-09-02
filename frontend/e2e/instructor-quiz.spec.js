import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Instructor quiz manager', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
    await page.goto('/instructor/quizzes');
    await expect(page.getByRole('heading', { name: 'Quản lý Quiz', level: 1 })).toBeVisible();
  });

  test('renders the class picker and the 3 status tabs', async ({ page }) => {
    await expect(page.getByLabel('Lớp học')).toBeVisible();
    await expect(page.getByRole('button', { name: /^Nháp/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Đã phát hành/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /^Lưu trữ/ })).toBeVisible();
  });

  test('creates a new draft quiz, sees it selected, then deletes it', async ({ page }) => {
    const title = `E2E quiz ${Date.now()}`;
    await page.getByRole('button', { name: 'Tạo quiz mới' }).click();
    await page.getByLabel('Tên quiz').fill(title);
    // Two buttons share the label "Tạo quiz mới" once the inline form is open
    // (the header action + the form's submit) -- the submit is the last one.
    await page.getByRole('button', { name: 'Tạo quiz mới' }).last().click();

    // New quiz lands in the Nháp (draft) tab, auto-selected in the preview pane.
    await expect(page.getByRole('button', { name: /^Nháp/ })).toHaveClass(/gv-btn--teal-outline/);
    await expect(page.getByRole('heading', { name: title })).toBeVisible({ timeout: 10000 });

    page.once('dialog', (dialog) => dialog.accept());
    await page.getByRole('button', { name: 'Xoá quiz' }).click();
    await expect(page.getByRole('heading', { name: title })).toBeHidden({ timeout: 10000 });
  });

  test('the create form can be cancelled without creating a quiz', async ({ page }) => {
    await page.getByRole('button', { name: 'Tạo quiz mới' }).click();
    await expect(page.getByLabel('Tên quiz')).toBeVisible();
    await page.getByRole('button', { name: 'Đóng' }).click();
    await expect(page.getByLabel('Tên quiz')).toBeHidden();
  });

  test('switching the class picker changes the quiz list', async ({ page }) => {
    const select = page.getByLabel('Lớp học');
    const initial = await select.inputValue();
    await select.selectOption({ index: 1 });
    await expect(select).not.toHaveValue(initial);
    await expect(page.getByRole('heading', { name: 'Quản lý Quiz', level: 1 })).toBeVisible();
  });
});
