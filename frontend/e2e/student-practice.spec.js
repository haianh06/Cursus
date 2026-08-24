import { test, expect } from '@playwright/test';
import { DEMO_ACCOUNTS, loginAs } from './helpers';

// student_ethan is enrolled in CEA201, and an APPROVED week-1 pack already
// exists there (20 items: 10 MCQ + 10 flashcards) — seeded ahead of this
// suite via the real API rather than re-requesting it per test.
const PRACTICE_URL = '/student/practice?course=CEA201&week=1';

test.describe('Student practice — MCQ / Flashcard / Mixed quiz UX', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, DEMO_ACCOUNTS.student);
    await page.goto(PRACTICE_URL);
    await expect(page.getByTestId('tab-mcq')).toBeVisible({ timeout: 10000 });
  });

  test('MCQ tab: navigator lists all 10 questions and jumps out of order', async ({ page }) => {
    await expect(page.getByTestId('question-navigator').locator('button')).toHaveCount(10);
    await page.getByTestId('nav-item-4').click();
    await expect(page.getByText('5/10')).toBeVisible();
    await page.getByTestId('nav-item-0').click();
    await expect(page.getByText('1/10')).toBeVisible();
  });

  test('picking the right answer (labeled "A.") shows correct feedback and marks the navigator', async ({ page }) => {
    await page.getByTestId('nav-item-0').click();
    // Every MCQ in this fallback-generated pack has correctKey "A" — the
    // option whose own displayed label is "A." is always right, regardless
    // of where shuffling put it on screen.
    await page.getByRole('button', { name: /^A\./ }).click();
    await page.getByTestId('mcq-check').click();
    await expect(page.getByTestId('mcq-feedback')).toHaveAttribute('data-correct', 'true');
    await expect(page.getByTestId('nav-item-0')).toHaveAttribute('data-status', 'correct');
  });

  test('picking a wrong answer shows incorrect feedback and marks the navigator', async ({ page }) => {
    await page.getByTestId('nav-item-1').click();
    await page.getByRole('button', { name: /^B\./ }).click();
    await page.getByTestId('mcq-check').click();
    await expect(page.getByTestId('mcq-feedback')).toHaveAttribute('data-correct', 'false');
    await expect(page.getByTestId('nav-item-1')).toHaveAttribute('data-status', 'incorrect');
  });

  test('Next is disabled from advancing past a locked option set until Check is pressed', async ({ page }) => {
    await page.getByTestId('nav-item-2').click();
    await expect(page.getByTestId('mcq-check')).toBeDisabled();
    await page.getByRole('button', { name: /^A\./ }).click();
    await expect(page.getByTestId('mcq-check')).toBeEnabled();
  });

  test('keyboard: arrows navigate, letter keys match the on-screen label (not DOM position), Enter checks then advances', async ({ page }) => {
    await page.getByTestId('nav-item-0').click();
    await page.locator('body').click(); // ensure focus isn't trapped in an option button
    await page.keyboard.press('ArrowRight');
    await expect(page.getByText('2/10')).toBeVisible();
    await page.keyboard.press('ArrowLeft');
    await expect(page.getByText('1/10')).toBeVisible();

    await page.keyboard.press('a');
    await expect(page.getByTestId('mcq-check')).toBeEnabled();
    await page.keyboard.press('Enter');
    await expect(page.getByTestId('mcq-feedback')).toBeVisible();
    await expect(page.getByTestId('mcq-feedback')).toHaveAttribute('data-correct', 'true');
    await page.keyboard.press('Enter');
    await expect(page.getByText('2/10')).toBeVisible();
  });

  // No test here for "keyboard shortcuts ignore an on-page textarea": this
  // branch (the course+week practice flow) has no textarea anywhere on the
  // page today — that only exists on the not-yet-merged instructor-driven
  // practice-set redesign (PR #18). The defensive check in the keydown
  // handler (skip INPUT/TEXTAREA/contenteditable targets) stays in the code
  // as forward-proofing for that merge, but there's nothing on this page to
  // exercise it against right now.

  test('progress (shuffle order + answers) survives a full page reload', async ({ page }) => {
    await page.getByTestId('nav-item-2').click();
    await page.getByRole('button', { name: /^A\./ }).click();
    await page.getByTestId('mcq-check').click();
    await expect(page.getByTestId('mcq-feedback')).toBeVisible();

    await page.reload();
    await expect(page.getByTestId('tab-mcq')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText('3/10')).toBeVisible();
    await expect(page.getByTestId('mcq-feedback')).toBeVisible();
    await expect(page.getByTestId('nav-item-2')).toHaveAttribute('data-status', 'correct');
  });

  test('summary tallies correct/incorrect/unanswered and "review unresolved" filters to mistakes only', async ({ page }) => {
    await page.getByTestId('nav-item-0').click();
    await page.getByRole('button', { name: /^A\./ }).click();
    await page.getByTestId('mcq-check').click();

    await page.getByTestId('nav-item-1').click();
    await page.getByRole('button', { name: /^B\./ }).click();
    await page.getByTestId('mcq-check').click();

    await page.getByTestId('summary-toggle').click();
    await expect(page.getByTestId('stat-correct')).toContainText('1');
    await expect(page.getByTestId('stat-incorrect')).toContainText('1');
    await expect(page.getByTestId('stat-unanswered')).toContainText('8');

    await page.getByTestId('review-unresolved-btn').click();
    await expect(page.getByTestId('review-only-banner')).toBeVisible();
    // Only the 1 wrong answer is "unresolved" — the 8 untouched questions
    // are not dragged into the review pass.
    await expect(page.getByTestId('question-navigator').locator('button')).toHaveCount(1);

    await page.getByRole('button', { name: 'Quay lại toàn bộ' }).click();
    await expect(page.getByTestId('review-only-banner')).toHaveCount(0);
    await expect(page.getByTestId('question-navigator').locator('button')).toHaveCount(10);
  });

  test('restart reshuffles and clears all answers', async ({ page }) => {
    await page.getByTestId('nav-item-0').click();
    await page.getByRole('button', { name: /^A\./ }).click();
    await page.getByTestId('mcq-check').click();
    await page.getByTestId('summary-toggle').click();
    await page.getByTestId('restart-btn').click();
    await expect(page.getByTestId('question-navigator').locator('button').first()).toHaveAttribute('data-status', 'unanswered');
  });

  test('Flashcard tab: flip reveals the answer, then self-rating is recorded', async ({ page }) => {
    await page.getByTestId('tab-cards').click();
    await expect(page.getByTestId('question-navigator').locator('button')).toHaveCount(10);
    await page.getByTestId('flashcard-flip').click();
    await expect(page.getByTestId('flashcard-flip')).toHaveAttribute('data-flipped', 'true');
    await page.getByTestId('flashcard-known').click();
    await expect(page.getByTestId('nav-item-0')).toHaveAttribute('data-status', 'correct');
  });

  test('Flashcard "didn\'t know" marks the navigator item incorrect', async ({ page }) => {
    await page.getByTestId('tab-cards').click();
    await page.getByTestId('flashcard-flip').click();
    await page.getByTestId('flashcard-unknown').click();
    await expect(page.getByTestId('nav-item-0')).toHaveAttribute('data-status', 'incorrect');
  });

  test('Mixed tab combines both kinds into one 20-item sequence', async ({ page }) => {
    await page.getByTestId('tab-mixed').click();
    await expect(page.getByTestId('question-navigator').locator('button')).toHaveCount(20);
    await expect(page.getByText('1/20')).toBeVisible();
  });

  test('source citation is shown for a revealed answer', async ({ page }) => {
    await page.getByTestId('nav-item-0').click();
    await page.getByRole('button', { name: /^A\./ }).click();
    await page.getByTestId('mcq-check').click();
    await expect(page.locator('[data-testid="mcq-feedback"] .citation')).toBeVisible();
  });
});
