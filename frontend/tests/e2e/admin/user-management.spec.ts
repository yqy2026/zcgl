import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

test.describe('Admin User Management', () => {
  test('should open user management page with admin session', async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/system/users');

    await expect(page).toHaveURL(/\/system\/users/);
    const headingLocator = page.getByRole('heading', { name: /用户管理|User Management/ }).first();
    const tableLocator = page.locator('.ant-table').first();

    const hasHeading = await headingLocator
      .waitFor({ state: 'visible', timeout: 8_000 })
      .then(() => true)
      .catch(() => false);
    const hasTable = await tableLocator
      .waitFor({ state: 'visible', timeout: 8_000 })
      .then(() => true)
      .catch(() => false);

    expect(hasHeading || hasTable).toBe(true);
  });
});
