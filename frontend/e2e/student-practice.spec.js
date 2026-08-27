import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Student practice', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Sinh viên');
    await page.goto('/student/practice');
  });

  test('loads the sandbox course without an error boundary', async ({ page }) => {
    await expect(page.getByLabel('Môn học')).toHaveValue('SSA101', { timeout: 10000 });
    await expect(page.getByText(/error boundary|something went wrong/i)).toHaveCount(0);
  });

  test('uses an academic week bounded to the supported 1..10 range', async ({ page }) => {
    const week = page.getByTestId('practice-week-number');

    // The opening week is anchored to the student's semester start_date
    // (CursusContext -> activeSemester), not the calendar ISO week, so it
    // moves as the semester progresses. Assert the invariant, not a literal:
    // this used to hardcode '10' back when the value was a clamped ISO week.
    await expect(week).toHaveText(/^([1-9]|10)$/);
    const initial = Number(await week.textContent());

    // "Tuần sau" walks up and clamps at 10, never past it.
    for (let i = initial; i < 10; i += 1) {
      await page.getByRole('button', { name: 'Tuần sau' }).click();
    }
    await expect(week).toHaveText('10');
    await page.getByRole('button', { name: 'Tuần sau' }).click();
    await expect(week).toHaveText('10');

    await page.getByRole('button', { name: 'Tuần trước' }).click();
    await expect(week).toHaveText('9');
  });

  test('offers the request flow when no published set exists', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Yêu cầu bộ luyện tập' }).first()).toBeEnabled({ timeout: 10000 });
  });
});
