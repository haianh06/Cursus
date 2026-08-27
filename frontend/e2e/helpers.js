export async function startSandboxAs(page, roleName) {
  await page.goto('/demo/select-role');
  await page.getByRole('button', { name: new RegExp(`Khám phá vai trò ${roleName}`, 'i') }).click();
  await page.waitForURL(/\/(student|instructor|admin)(\/|$)/, { timeout: 15000 });
  await page.getByRole('button', { name: 'Đăng xuất' }).waitFor({ state: 'visible' });
}
