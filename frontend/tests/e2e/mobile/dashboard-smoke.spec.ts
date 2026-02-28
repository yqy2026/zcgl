import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

test.describe('Mobile Smoke', () => {
  test('should render dashboard in mobile viewport', async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
    const dashboardTitle = page
      .getByRole('heading', { name: /资产管理看板|工作台|Dashboard/i })
      .first();
    await expect(dashboardTitle).toBeVisible({ timeout: 15_000 });
  });
});
