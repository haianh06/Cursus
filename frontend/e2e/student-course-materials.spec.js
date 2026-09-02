import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Student course materials viewer', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Sinh viên');
  });

  test('lists sandbox SSA101 documents and shows content on selection', async ({ page }) => {
    await page.goto('/student/courses/course_mock_ssa101');
    const listEntry = page.getByRole('button', { name: /Syllabus SSA101/i });
    await expect(listEntry).toBeVisible({ timeout: 10000 });
    await listEntry.click();
    await expect(page.getByRole('heading', { name: /Syllabus SSA101/i })).toBeVisible({ timeout: 10000 });
  });

  test('a ?doc= query param preselects that document (the source-label deep-link path)', async ({ page }) => {
    // doc_clean_0c7e3e1ca09f76173c03 is a real, currently-seeded SSA101
    // document ("3. Exploring College (tiết 3)"); the old
    // doc_catalog_ssa101_chunks fixture this test used to target was an
    // intentionally-purged superseded mock doc (see
    // real_curriculum_service.purge_superseded_mock_catalog_docs).
    await page.goto('/student/courses/course_mock_ssa101?doc=doc_clean_0c7e3e1ca09f76173c03');
    await expect(page.getByRole('heading', { name: /Exploring College/i })).toBeVisible({ timeout: 10000 });
  });

  test('a course a student is not enrolled in is not browsable', async ({ page }) => {
    await page.goto('/student/courses/OTH999');
    await expect(page.getByRole('alert')).toBeVisible({ timeout: 10000 });
  });
});
