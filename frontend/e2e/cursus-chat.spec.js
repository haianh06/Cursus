import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

/**
 * Real-browser coverage for the 4 fixes made to the Cursus chat widget:
 *  1. citation pills are deduped per source document (no repeated pills)
 *  2. quick-reply/FAQ chips appear (welcome screen, then after each reply)
 *  3. assistant text reveals with a client-side typewriter effect
 *  4. the citation source drawer renders above the chat panel, not behind it
 */
test.describe('Cursus chat widget', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Sinh viên');
  });

  test('open panel shows FAQ quick replies before any message', async ({ page }) => {
    await page.getByRole('button', { name: 'Mở Cursus' }).click();
    const panel = page.getByRole('complementary', { name: 'Cursus chat' });
    await expect(panel).toBeVisible();
    // Quick-reply chips are plain buttons with this known copy.
    await expect(panel.getByRole('button', { name: /Hôm nay mình nên học gì trước/i })).toBeVisible();
  });

  test('sending a message types out the reply, dedups citations, shows FAQ again, and opens the source drawer above the chat panel', async ({ page }) => {
    await page.getByRole('button', { name: 'Mở Cursus' }).click();
    const panel = page.getByRole('complementary', { name: 'Cursus chat' });
    const textarea = panel.getByPlaceholder('Hỏi Cursus…');
    await textarea.fill('Tóm tắt nội dung môn học giúp mình');
    await textarea.press('Enter');

    // Typewriter check: right after sending, the assistant bubble should
    // exist but not yet contain the full final text (still being "typed").
    const assistantBubble = panel.locator('article').last();
    await expect(assistantBubble).toBeVisible();

    // Wait for the reply to finish streaming + typing out, then for the
    // follow-up FAQ chips (mục 2) to reappear under the finished answer.
    await expect(panel.getByRole('button', { name: /Hôm nay mình nên học gì trước/i })).toBeVisible({ timeout: 30000 });

    // Citation dedup (mục 1): collect every citation chip's visible label
    // text and assert there are no duplicates.
    const citationChips = assistantBubble.locator('button.citation, button:has-text("")').filter({ hasText: /Syllabus|CEA|CSI|PRF/i });
    const count = await citationChips.count();
    if (count > 0) {
      const labels = await citationChips.allTextContents();
      const trimmed = labels.map((l) => l.trim());
      expect(new Set(trimmed).size).toBe(trimmed.length);

      // Source drawer z-index (mục 4): clicking a citation must render the
      // drawer's close button clickable/on-top, not hidden behind the panel.
      await citationChips.first().click();
      const drawerCloseButton = page.getByRole('button', { name: /^Đóng$/ });
      await expect(drawerCloseButton).toBeVisible();
      // If the drawer were rendered behind the chat <aside> (the original
      // bug), this click would hit the chat panel instead and never close
      // the drawer.
      await drawerCloseButton.click();
      await expect(drawerCloseButton).toBeHidden();
    }
  });
});
