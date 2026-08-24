// Seeded demo accounts (src/constants/roles.js DEMO_USERS, backed by the
// dev Postgres seed) — not real people.
export const DEMO_ACCOUNTS = {
  student: { email: 'student.demo@example.test', password: 'password123' },
  instructor: { email: 'instructor.demo@example.test', password: 'password123' },
  admin: { email: 'admin.demo@example.test', password: 'AdminPassword123' },
};

export async function loginAs(page, account) {
  await page.goto('/login');
  await page.locator('#login-email').fill(account.email);
  await page.locator('#login-password').fill(account.password);
  await page.locator('#login-submit').click();
  await page.waitForURL(/\/(student|instructor|admin)(\/|$)/, { timeout: 15000 });
}
