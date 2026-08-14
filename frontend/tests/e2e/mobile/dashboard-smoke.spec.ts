import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

test.describe('Mobile Smoke', () => {
  test('should render dashboard in mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await ensureAuthenticated(page);
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
    const dashboardTitle = page
      .getByRole('heading', { name: /资产管理看板|工作台|Dashboard/i })
      .first();
    await expect(dashboardTitle).toBeVisible({ timeout: 15_000 });

    await expect(page.getByLabel('主导航侧边栏')).toHaveCount(0);
    const openMenuButton = page.getByRole('button', { name: '打开菜单' });
    await expect(openMenuButton).toBeVisible();

    await openMenuButton.click();
    const mobileMenu = page.getByRole('dialog', { name: '移动端导航菜单' });
    await expect(mobileMenu).toBeVisible();

    await page.getByRole('button', { name: '关闭菜单' }).click();
    await expect(mobileMenu).not.toBeVisible();
  });
});
