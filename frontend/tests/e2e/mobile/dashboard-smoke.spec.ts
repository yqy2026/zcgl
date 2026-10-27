import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

test.describe('Mobile Smoke', () => {
  test('should render asset units in mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await ensureAuthenticated(page);
    await page.goto('/asset-operations/units');
    await expect(page).toHaveURL(/\/asset-operations\/units/);
    await expect(page.getByRole('heading', { name: '资产单元' })).toBeVisible({
      timeout: 15_000,
    });

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
