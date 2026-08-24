import { test, expect } from '@playwright/test';
import { DEMO_ACCOUNTS, loginAs } from './helpers';

// This page is reachable from a practice-screen source-label link
// (`sourceDocumentId` present), but the currently seeded CEA201 pack's
// content comes from the file-based demo index, which carries no document
// id (verified against the live dev API) — so it's tested directly by URL,
// which is exactly how a real source-label link would land here.
test.describe('Student course materials viewer', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, DEMO_ACCOUNTS.student);
  });

  test('lists CEA201 documents and shows content on selection', async ({ page }) => {
    await page.goto('/student/courses/CEA201');
    // Scope to the clickable list-item button — the content pane on the
    // right renders the same title as a heading once a document loads, so
    // an unscoped text match is ambiguous between the two.
    const listEntry = page.getByRole('button', { name: /CEA201 Syllabus/ });
    await expect(listEntry).toBeVisible({ timeout: 10000 });
    await listEntry.click();
    await expect(page.getByText(/Learning outcomes|von Neumann/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('a ?doc= query param preselects that document (the source-label deep-link path)', async ({ page }) => {
    await page.goto('/student/courses/CEA201?doc=doc_mock_cea201_lecture_cache.md');
    await expect(page.getByText(/Cache/i).first()).toBeVisible({ timeout: 10000 });
  });

  test('a course a student is not enrolled in is not browsable', async ({ page }) => {
    await page.goto('/student/courses/OTH999');
    await expect(page.getByText(/không tải được|could not load|not found|error/i).first()).toBeVisible({ timeout: 10000 });
  });
});
