import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

// user_06769f95eb5a4b04b4d95e6ca83050af ("Trịnh Hải Đăng") is enrolled in
// all 4 of the sandbox instructor's (Cô Hương) sections -- a real owned
// student, unlike the unrelated same-named `student_haidang` demo account
// that only belongs to a different instructor's SSA101 section.
const OWNED_STUDENT_ID = 'user_06769f95eb5a4b04b4d95e6ca83050af';

test.describe('Instructor student 360 profile', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Giảng viên');
  });

  test('renders the profile without crashing and shows courses/notes sections', async ({ page }) => {
    const pageErrors = [];
    page.on('pageerror', (err) => pageErrors.push(err.message));

    await page.goto(`/instructor/students/${OWNED_STUDENT_ID}`);
    await expect(page.getByRole('heading', { name: 'Trịnh Hải Đăng' })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Ghi chú riêng' })).toBeVisible();

    expect(pageErrors, `Unexpected JS errors: ${pageErrors.join('; ')}`).toHaveLength(0);
  });

  test('a student not owned by this instructor is not accessible', async ({ page }) => {
    // student_haidang only belongs to a different instructor's section.
    await page.goto('/instructor/students/student_haidang');
    await expect(page.getByRole('heading', { name: /không thể/i })).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('Student not found')).toBeVisible();
  });

  test('adding and deleting a private note works', async ({ page }) => {
    await page.goto(`/instructor/students/${OWNED_STUDENT_ID}`);
    await expect(page.getByRole('heading', { name: 'Trịnh Hải Đăng' })).toBeVisible({ timeout: 10000 });

    const noteText = `E2E note ${Date.now()}`;
    await page.getByPlaceholder(/ghi chú/i).fill(noteText);
    await page.getByRole('button', { name: /Thêm ghi chú/i }).click();
    await expect(page.getByText(noteText)).toBeVisible({ timeout: 10000 });

    // Notes list is sorted newest-first (backend orders by created_at DESC),
    // so the note we just added is always the first delete button.
    await page.getByText(noteText).waitFor({ state: 'visible' });
    await page.getByRole('button', { name: 'Xoá ghi chú' }).first().click();
    await expect(page.getByText(noteText)).toBeHidden({ timeout: 10000 });
  });
});
