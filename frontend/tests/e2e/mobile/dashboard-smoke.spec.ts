import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

test.describe('Mobile Smoke', () => {
  test('should render dashboard in mobile viewport', async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
    const hasDashboardTitle = await page
      .getByText(/工作台|Dashboard|资产管理看板/)
      .first()
      .isVisible()
      .catch(() => false);
    expect(hasDashboardTitle).toBe(true);
  });
});
