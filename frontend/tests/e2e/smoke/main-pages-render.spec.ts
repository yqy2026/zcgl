import { expect, test } from '@playwright/test';
import { ensureAuthenticated } from '../helpers/auth';

/**
 * 资产运营 v5 主页面渲染冒烟：
 * - v5 生产路径必须渲染出关键内容标记，且绝不渲染 404 页；
 * - V1-4 已退役的旧业务路径必须明确渲染 404，不能复活或静默空白。
 */

const main = (page: import('@playwright/test').Page) => page.locator('main');

const PAGES: Array<{ name: string; path: string; marker: RegExp }> = [
  { name: '资产单元', path: '/asset-operations/units', marker: /资产单元/ },
  {
    name: '上游合同',
    path: '/asset-operations/contracts/upstream',
    marker: /上游合同/,
  },
  {
    name: '终端合同',
    path: '/asset-operations/contracts/terminal',
    marker: /终端合同/,
  },
  {
    name: '录入已签合同',
    path: '/asset-operations/contracts/intake',
    marker: /录入已签合同/,
  },
];

const RETIRED_PATHS = [
  '/dashboard',
  '/assets/list',
  '/assets/new',
  '/contract-center/list',
  '/contract-center/import',
  '/operations/ledger',
  '/property-certificates',
  '/property-certificates/import',
  '/project',
] as const;

test.describe('主页面渲染冒烟', () => {
  for (const { name, path, marker } of PAGES) {
    test(`访问 ${name} (${path}) 渲染出页面内容而非空白`, async ({ page }) => {
      await ensureAuthenticated(page);
      await page.goto(path);
      await expect(page).toHaveURL(new RegExp(path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));

      // 关键内容标记必须出现在 main 内
      await expect(main(page).getByText(marker).first()).toBeVisible({ timeout: 15_000 });

      // 不得是 404 页
      await expect(main(page).getByText(/页面不存在/)).toHaveCount(0);
    });
  }

  for (const path of RETIRED_PATHS) {
    test(`已退役业务路径 ${path} 明确不可达`, async ({ page }) => {
      await ensureAuthenticated(page);
      await page.goto(path);

      await expect(page).toHaveURL(new RegExp(path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
      await expect(main(page).getByText(/页面不存在/)).toBeVisible({ timeout: 15_000 });
      await expect(main(page)).not.toBeEmpty();
    });
  }

  test('未注册路由渲染 404 页而非空白 main', async ({ page }) => {
    await ensureAuthenticated(page);
    await page.goto('/no-such-page-xyz');

    await expect(page.getByText(/页面不存在/)).toBeVisible({ timeout: 15_000 });
    await expect(main(page)).not.toBeEmpty();
  });
});
