import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from './helpers/auth';

test.describe('@asset-operations asset unit flow', () => {
  test.beforeEach(async ({ page }) => {
    await ensureAuthenticated(page);
  });

  test('loads the v5 list and sends keyword search to the asset-unit API', async ({ page }) => {
    await page.goto('/asset-operations/units');
    await expect(page).toHaveURL(/\/asset-operations\/units$/);
    await expect(page.getByRole('heading', { name: '资产单元' })).toBeVisible();

    const searchInput = page.getByLabel('搜索单元编号、名称或地址');
    await expect(searchInput).toBeVisible();
    await searchInput.fill('测试');

    const searchRequest = page.waitForRequest(request => {
      const url = new URL(request.url());
      return (
        request.method() === 'GET' &&
        url.pathname.endsWith('/api/v1/asset-units') &&
        url.searchParams.get('q') === '测试'
      );
    });
    await searchInput.press('Enter');
    await searchRequest;

    await expect(page.locator('.ant-table')).toBeVisible();
  });
});
