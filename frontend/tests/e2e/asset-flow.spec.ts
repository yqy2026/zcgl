import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from './helpers/auth';

test.describe('Asset Management Flow', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('should load list and support keyword search', async ({ page }) => {
    await page.goto('/owner/assets');
    await expect(page).toHaveURL(/\/owner\/assets$/);

    const searchInput = page
      .locator('input[id="search"], input[placeholder*="搜索"], input[placeholder*="关键字"]')
      .first();
    await expect(searchInput).toBeVisible();
    await searchInput.fill('测试');

    const searchButton = page.getByRole('button', { name: /搜索|查询/ }).first();
    const hasSearchButton = await searchButton.isVisible().catch(() => false);
    if (hasSearchButton) {
      await searchButton.click();
    } else {
      await searchInput.press('Enter');
    }
    await page.waitForLoadState('networkidle');

    const hasTable = await page
      .locator('.ant-table')
      .first()
      .isVisible()
      .catch(() => false);
    const hasEmpty = await page
      .locator('.ant-empty')
      .first()
      .isVisible()
      .catch(() => false);

    expect(hasTable || hasEmpty).toBe(true);
  });
});
