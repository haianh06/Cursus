import { test, expect } from '@playwright/test';
import { startSandboxAs } from './helpers';

test.describe('Admin AI policy (guardrail rules + risk score policy)', () => {
  test.beforeEach(async ({ page }) => {
    await startSandboxAs(page, 'Quản trị viên');
    await page.goto('/admin/governance/ai-policy');
    await expect(page.getByRole('heading', { name: 'Chính sách AI', level: 1 })).toBeVisible();
  });

  test('renders the guardrail rule list and the risk policy signal table', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Rule Guardrail' })).toBeVisible();
    await expect(page.getByText('Chặn nhờ làm bài hộ (tiếng Việt)')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Chính sách điểm rủi ro (Risk score)' })).toBeVisible();
    await expect(page.getByRole('table')).toBeVisible();
  });

  test('previewing a guardrail rule toggle requires a reason of >= 5 chars', async ({ page }) => {
    // Both the guardrail section and the risk-policy section below it use
    // the identical label "Lý do thay đổi" for their own reason textarea --
    // scope to the guardrail section specifically via its own aria-labelledby.
    const guardrailSection = page.locator('section[aria-labelledby="guardrail-title"]');
    const reasonField = guardrailSection.getByLabel('Lý do thay đổi');
    const ruleItem = page.locator('li', { hasText: 'Chặn nhờ làm bài hộ (tiếng Việt)' });
    const previewBtn = ruleItem.getByRole('button', { name: 'Xem trước thay đổi' });

    // Too short: preview call is blocked client-side, no preview panel appears.
    await reasonField.fill('ab');
    await previewBtn.click();
    await expect(page.getByText(/Lý do phải|ít nhất 5 ký tự/i).first()).toBeVisible();

    // Valid reason -> a read-only preview panel renders (does not publish).
    await reasonField.fill('E2E test preview only, not publishing');
    await previewBtn.click();
    await expect(page.getByText(/Bản xem trước/)).toBeVisible({ timeout: 10000 });
  });

  test('a core-locked, currently-enabled guardrail rule cannot be toggled off from here', async ({ page }) => {
    const lockedItem = page.locator('li', { hasText: 'Chặn prompt injection' });
    await expect(lockedItem.getByRole('button', { name: 'Xem trước thay đổi' })).toBeDisabled();
  });

  test('risk-policy preview works without a reason, but publish is gated on one', async ({ page }) => {
    const previewBtn = page.getByRole('button', { name: 'Xem trước tác động' });
    await expect(previewBtn).toBeEnabled();
    await previewBtn.click();

    const publishBtn = page.getByRole('button', { name: 'Publish version mới' });
    await expect(publishBtn).toBeVisible({ timeout: 10000 });
    // No reason typed yet -- publish must stay disabled so nothing is
    // published just from clicking "preview" (this test never confirms it).
    await expect(publishBtn).toBeDisabled();
  });
});
